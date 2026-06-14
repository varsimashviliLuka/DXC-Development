"""Public entry routes."""

from flask import Blueprint, redirect, session, url_for

from app.extensions import db
from app.models import User

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
  user_id = session.get("user_id")
  if not user_id:
    return redirect(url_for("auth.login"))

  user = db.session.get(User, int(user_id))
  if not user:
    session.clear()
    return redirect(url_for("auth.login"))

  if user.is_admin():
    return redirect(url_for("admin.dashboard"))
  return redirect(url_for("user.dashboard"))
