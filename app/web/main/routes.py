"""Public website and entry routes."""

from flask import (
  Blueprint,
  current_app,
  flash,
  redirect,
  render_template,
  request,
  url_for,
)
from flask_limiter.util import get_remote_address

from app.extensions import limiter
from app.i18n import LANGUAGE_COOKIE, LANGUAGE_COOKIE_MAX_AGE, LANGUAGES, get_locale, t
from app.services.inquiry_service import INQUIRY_SERVICES, InquiryService, InquiryValidationError
from app.translations import SERVICE_KEYS
from app.web.decorators import load_session_user
from app.web.utils import is_safe_next_url

main_bp = Blueprint("main", __name__)

# Hidden field real visitors never fill in; bots that fill every input get silently dropped.
HONEYPOT_FIELD = "website"


@main_bp.route("/")
def index():
  return render_template("public/index.html", services=SERVICE_KEYS)


@main_bp.route("/services")
def services():
  return render_template("public/services.html", services=SERVICE_KEYS)


@main_bp.route("/about")
def about():
  return render_template("public/about.html")


@main_bp.route("/contact", methods=["GET", "POST"])
@limiter.limit(
  lambda: current_app.config["CONTACT_ATTEMPT_RATE_LIMIT"],
  methods=["POST"],
)
@limiter.limit(
  lambda: current_app.config["CONTACT_RATE_LIMIT"],
  methods=["POST"],
  deduct_when=lambda response: response.status_code == 302,
)
def contact():
  form = request.form if request.method == "POST" else {"service": request.args.get("service", "")}
  errors = {}

  if request.method == "POST":
    if request.form.get(HONEYPOT_FIELD):
      current_app.logger.warning("Dropped contact form from %s (honeypot filled)", get_remote_address())
      flash(t("contact.success"), "success")
      return redirect(url_for("main.contact"))
    try:
      InquiryService.create(request.form, language=get_locale(), ip_address=get_remote_address())
      flash(t("contact.success"), "success")
      return redirect(url_for("main.contact"))
    except InquiryValidationError as exc:
      errors = exc.errors
      flash(t("contact.error.form"), "error")

  return render_template(
    "public/contact.html",
    form=form,
    errors=errors,
    services=INQUIRY_SERVICES,
    honeypot_field=HONEYPOT_FIELD,
  ), 400 if errors else 200


@main_bp.route("/lang/<code>")
def set_language(code):
  next_url = request.args.get("next")
  response = redirect(next_url if is_safe_next_url(next_url) else url_for("main.index"))
  if code in LANGUAGES:
    response.set_cookie(
      LANGUAGE_COOKIE,
      code,
      max_age=LANGUAGE_COOKIE_MAX_AGE,
      samesite="Lax",
      secure=current_app.config["SESSION_COOKIE_SECURE"],
      httponly=True,
    )
  return response


@main_bp.route("/account")
def account():
  user = load_session_user()
  if not user:
    return redirect(url_for("auth.login"))
  if user.is_admin():
    return redirect(url_for("admin.dashboard"))
  return redirect(url_for("user.dashboard"))
