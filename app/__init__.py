"""Application factory."""

import logging
import os
import re
import uuid
from datetime import date
from urllib.parse import urlparse

from flask import (
  Flask,
  current_app,
  flash,
  g,
  jsonify,
  redirect,
  render_template,
  request,
  session,
  url_for,
)
from flask_wtf.csrf import CSRFError
from werkzeug.middleware.proxy_fix import ProxyFix

from app.api import register_api
from app.config import ProductionConfig, config_by_name
from app.extensions import csrf, db, jwt, limiter, migrate
from app.scheduler import init_scheduler, shutdown_scheduler
from app.security.jwt_handlers import register_jwt_handlers
from app.i18n import init_i18n, t
from app.services.auth_service import AuthService
from app.services.inquiry_service import InquiryService
from app.utils.errors import AppError
from app.utils.formatting import external_url
from app.utils.logging import setup_logging
from app.utils.schema import prepare_database, running_db_command
from app.web import register_web_blueprints
from app.web.decorators import load_session_user

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "migrations")

_REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9-]{1,64}")

_CONTENT_SECURITY_POLICY = "; ".join([
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self'",
  "img-src 'self' data:",
  "font-src 'self'",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
])


def _same_origin(url: str | None) -> bool:
  if not url:
    return False
  parsed = urlparse(url)
  return parsed.scheme in ("http", "https") and parsed.netloc == request.host


def create_app(config_name=None):
  if config_name is None:
    config_name = os.getenv("FLASK_ENV", "development")

  app = Flask(__name__)
  app.config.from_object(config_by_name[config_name])
  app.config["ENV_NAME"] = config_name

  setup_logging(app)

  if config_name == "production":
    ProductionConfig.validate(app.config)

  if app.config["PROXY_FIX_X_FOR"]:
    proxies = app.config["PROXY_FIX_X_FOR"]
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxies, x_proto=proxies, x_host=proxies)

  db.init_app(app)
  migrate.init_app(app, db, directory=MIGRATIONS_DIR, render_as_batch=True)
  jwt.init_app(app)
  register_jwt_handlers(jwt)
  limiter.init_app(app)
  init_i18n(app)

  @app.before_request
  def assign_request_id():
    incoming = request.headers.get("X-Request-ID", "")
    g.request_id = incoming if _REQUEST_ID_PATTERN.fullmatch(incoming) else uuid.uuid4().hex[:8]

  csrf.init_app(app)

  @app.after_request
  def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-Request-ID"] = g.get("request_id", "-")
    # Swagger UI relies on inline scripts, so it keeps its own defaults.
    if not request.path.startswith(("/api/", "/swaggerui/")):
      response.headers["Content-Security-Policy"] = _CONTENT_SECURITY_POLICY
    if session.get("user_id") and not request.path.startswith("/static/"):
      response.headers["Cache-Control"] = "no-store"
    if config_name == "production":
      response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

  @app.errorhandler(CSRFError)
  def handle_csrf_error(error):
    logger.warning("CSRF validation failed path=%s reason=%s", request.path, error.description)
    flash("Your session expired or the form was invalid. Please try again.", "error")
    return redirect(request.referrer if _same_origin(request.referrer) else url_for("main.index"))

  @app.errorhandler(413)
  def handle_too_large(_error):
    limit_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
    message = f"Upload is too large (limit {limit_mb} MB)"
    if request.path.startswith("/api/"):
      return jsonify({"message": message}), 413
    return render_template("errors/error.html", message=message), 413

  @app.errorhandler(AppError)
  def handle_app_error(error):
    logger.warning("AppError: %s", error.message)
    if request.path.startswith("/api/"):
      return jsonify({"message": error.message}), error.status_code
    return render_template("errors/error.html", message=error.message), error.status_code

  @app.errorhandler(404)
  def handle_not_found(_error):
    if request.path.startswith("/api/"):
      return jsonify({"message": "Resource not found"}), 404
    if load_session_user():
      return render_template("errors/404.html"), 404
    return render_template("public/message.html", message=t("error.not_found")), 404

  @app.errorhandler(429)
  def handle_rate_limit(error):
    if request.path.startswith("/api/"):
      return jsonify({"message": "Too many requests"}), 429
    public_messages = {
      url_for("main.contact"): "contact.too_many",
      url_for("auth.login"): "login.too_many",
    }
    if request.path in public_messages:
      return render_template("public/message.html", message=t(public_messages[request.path])), 429
    return render_template(
      "errors/error.html",
      message="Too many attempts. Please wait a few minutes and try again.",
    ), 429

  @app.errorhandler(500)
  def handle_internal_error(error):
    logger.exception("Unhandled error: %s", error)
    if request.path.startswith("/api/"):
      return jsonify({"message": "Internal server error"}), 500
    return render_template("errors/500.html"), 500

  @app.context_processor
  def inject_template_globals():
    user = load_session_user()
    return {
      "current_user": user,
      "new_inquiry_count": InquiryService.count_new() if user and user.is_admin() else 0,
      "current_year": date.today().year,
      "app_name": current_app.config["APP_NAME"],
      "app_name_full": current_app.config["APP_NAME_FULL"],
      "company": current_app.config["COMPANY"],
      "bank_recipient_name": current_app.config["BANK_RECIPIENT_NAME"],
      "bank_accounts": current_app.config["BANK_ACCOUNTS"],
    }

  @app.template_filter("external_url")
  def external_url_filter(value):
    return external_url(value)

  from flask import Blueprint

  api_blueprint = Blueprint("api", __name__, url_prefix="/api/v1")
  register_api(
    api_blueprint,
    app_name=app.config["APP_NAME"],
    docs_enabled=app.config["API_DOCS_ENABLED"],
  )
  csrf.exempt(api_blueprint)
  app.register_blueprint(api_blueprint)
  register_web_blueprints(app)

  @app.teardown_appcontext
  def cleanup(exception=None):
    if exception:
      db.session.rollback()

  # `flask db ...` commands manage the schema themselves and must not start background jobs.
  if running_db_command():
    return app

  with app.app_context():
    from app import models  # noqa: F401

    prepare_database(app)
    AuthService.ensure_admin_user(app.config)
    logger.info("Database initialized")

  if app.config.get("SCHEDULER_ENABLED"):
    init_scheduler(app)

  import atexit

  atexit.register(shutdown_scheduler)

  logger.info("Application created env=%s", config_name)
  return app
