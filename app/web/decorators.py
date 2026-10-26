"""Session-based auth decorators for web routes."""

import logging
from functools import wraps

from flask import flash, g, redirect, session, url_for

from app.enums import UserStatus
from app.extensions import db
from app.i18n import t
from app.models import User

logger = logging.getLogger(__name__)


def start_user_session(user: User) -> None:
  session.clear()
  session["user_id"] = user.id
  session["auth_version"] = user.auth_version or 0
  session.permanent = True


def load_session_user() -> User | None:
  """Return the logged-in user, or None if the session is missing, revoked, or suspended."""
  if getattr(g, "current_user", None) is not None:
    return g.current_user

  user_id = session.get("user_id")
  if not user_id:
    return None

  try:
    user = db.session.get(User, int(user_id))
  except (TypeError, ValueError):
    user = None

  if (
    not user
    or session.get("auth_version", 0) != (user.auth_version or 0)
    or user.status == UserStatus.SUSPENDED
  ):
    session.clear()
    return None

  g.current_user = user
  return user


def login_required(view):
  @wraps(view)
  def wrapped(*args, **kwargs):
    user = load_session_user()
    if not user:
      flash(t("login.required"), "warning")
      return redirect(url_for("auth.login"))
    return view(*args, **kwargs)

  return wrapped


def admin_required(view):
  @wraps(view)
  def wrapped(*args, **kwargs):
    user = load_session_user()
    if not user:
      return redirect(url_for("auth.login"))
    if not user.is_admin():
      logger.warning("Non-admin user_id=%s attempted web admin route", user.id)
      return redirect(url_for("user.dashboard"))
    return view(*args, **kwargs)

  return wrapped


def active_user_required(view):
  @wraps(view)
  def wrapped(*args, **kwargs):
    user = load_session_user()
    if not user:
      return redirect(url_for("auth.login"))
    if user.is_admin():
      return redirect(url_for("admin.dashboard"))
    if user.status != UserStatus.ACTIVE:
      flash(t("user.inactive"), "warning")
      return redirect(url_for("user.profile"))
    return view(*args, **kwargs)

  return wrapped
