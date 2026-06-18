"""Application factory."""

import logging
import os
import uuid

from flask import Flask, g, jsonify, render_template, request, session

from app.api import register_api
from app.config import config_by_name
from app.extensions import db, jwt, limiter, migrate
from app.models import User
from app.scheduler import init_scheduler, shutdown_scheduler
from app.security.jwt_handlers import register_jwt_handlers
from app.services.auth_service import AuthService
from app.utils.errors import AppError
from app.utils.logging import setup_logging
from app.web import register_web_blueprints

logger = logging.getLogger(__name__)


def create_app(config_name=None):
  if config_name is None:
    config_name = os.getenv("FLASK_ENV", "development")

  app = Flask(__name__)
  app.config.from_object(config_by_name[config_name])

  if config_name == "production":
    config_by_name["production"].validate()

  setup_logging(app)

  db.init_app(app)
  migrate.init_app(app, db)
  jwt.init_app(app)
  register_jwt_handlers(jwt)
  limiter.init_app(app)

  @app.before_request
  def assign_request_id():
    g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])

  @app.after_request
  def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Request-ID"] = g.get("request_id", "-")
    if config_name == "production":
      response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

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
    return render_template("errors/404.html"), 404

  @app.errorhandler(429)
  def handle_rate_limit(error):
    if request.path.startswith("/api/"):
      return jsonify({"message": "Too many requests"}), 429
    return render_template("errors/error.html", message="Too many requests"), 429

  @app.errorhandler(500)
  def handle_internal_error(error):
    logger.exception("Unhandled error: %s", error)
    if request.path.startswith("/api/"):
      return jsonify({"message": "Internal server error"}), 500
    return render_template("errors/500.html"), 500

  @app.context_processor
  def inject_template_globals():
    user = None
    user_id = session.get("user_id")
    if user_id:
      user = db.session.get(User, int(user_id))
    return {"current_user": user}

  from flask import Blueprint

  api_blueprint = Blueprint("api", __name__, url_prefix="/api/v1")
  register_api(api_blueprint)
  app.register_blueprint(api_blueprint)
  register_web_blueprints(app)

  with app.app_context():
    from app import models  # noqa: F401

    db.create_all()
    from app.utils.schema import (
      ensure_admin_comment_columns,
      ensure_building_number_non_unique,
      migrate_legacy_user_phones,
    )

    ensure_admin_comment_columns()
    ensure_building_number_non_unique()
    migrate_legacy_user_phones()
    AuthService.ensure_admin_user(app.config)
    logger.info("Database initialized")

  if app.config.get("SCHEDULER_ENABLED"):
    init_scheduler(app)

  @app.teardown_appcontext
  def cleanup(exception=None):
    if exception:
      db.session.rollback()

  import atexit

  atexit.register(shutdown_scheduler)

  logger.info("Application created env=%s", config_name)
  return app
