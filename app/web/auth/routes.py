"""Authentication web routes."""

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_limiter.util import get_remote_address

from app.extensions import limiter
from app.i18n import t
from app.services.auth_service import AuthService
from app.utils.errors import UnauthorizedError
from app.web.decorators import load_session_user, start_user_session
from app.web.utils import is_safe_next_url

auth_bp = Blueprint("auth", __name__)

_LOGIN_ERROR_KEYS = {
  "Account is suspended": "login.suspended",
}


def _login_account_key() -> str:
  id_number = (request.form.get("id_number") or "").strip()
  return f"login-account:{id_number}" if id_number else f"login-ip:{get_remote_address()}"


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit(
  lambda: current_app.config["LOGIN_RATE_LIMIT_PER_IP"],
  methods=["POST"],
)
@limiter.limit(
  lambda: current_app.config["LOGIN_RATE_LIMIT_PER_ACCOUNT"],
  key_func=_login_account_key,
  methods=["POST"],
  deduct_when=lambda response: response.status_code != 302,
)
def login():
  if load_session_user():
    return redirect(url_for("main.account"))

  if request.method == "POST":
    id_number = request.form.get("id_number", "").strip()
    password = request.form.get("password", "")
    try:
      user = AuthService.authenticate(id_number, password)
      start_user_session(user)
      next_url = request.args.get("next") or request.form.get("next")
      if is_safe_next_url(next_url):
        return redirect(next_url)
      return redirect(url_for("main.account"))
    except UnauthorizedError as exc:
      flash(t(_LOGIN_ERROR_KEYS.get(exc.message, "login.invalid")), "error")

  return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
  session.clear()
  return redirect(url_for("main.index"))
