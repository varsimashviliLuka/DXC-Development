"""Authentication web routes."""

from flask import Blueprint, redirect, render_template, request, session, url_for

from app.services.auth_service import AuthService
from app.web.utils import flash_exception

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
  if session.get("user_id"):
    return redirect(url_for("main.index"))

  if request.method == "POST":
    phone = request.form.get("phone_number", "").strip()
    password = request.form.get("password", "")
    try:
      user = AuthService.authenticate(phone, password)
      session.clear()
      session["user_id"] = user.id
      session.permanent = True
      next_url = request.args.get("next") or request.form.get("next")
      if next_url and next_url.startswith("/"):
        return redirect(next_url)
      return redirect(url_for("main.index"))
    except Exception as exc:
      flash_exception(exc)

  return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
  session.clear()
  return redirect(url_for("auth.login"))
