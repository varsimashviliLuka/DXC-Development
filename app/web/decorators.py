"""Session-based auth decorators for web routes."""

import logging
from functools import wraps

from flask import flash, g, redirect, session, url_for

from app.enums import UserRole, UserStatus
from app.extensions import db
from app.models import User
from app.web.utils import flash_exception

logger = logging.getLogger(__name__)


def _load_session_user():
  if getattr(g, "current_user", None) is not None:
    return g.current_user

  user_id = session.get("user_id")
  if not user_id:
    return None

  user = db.session.get(User, int(user_id))
  if not user:
    session.clear()
    return None

  g.current_user = user
  return user


def login_required(view):
  @wraps(view)
  def wrapped(*args, **kwargs):
    user = _load_session_user()
    if not user:
      flash("Please log in to continue.", "warning")
      return redirect(url_for("auth.login"))
    return view(*args, **kwargs)

  return wrapped


def admin_required(view):
  @wraps(view)
  def wrapped(*args, **kwargs):
    user = _load_session_user()
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
    user = _load_session_user()
    if not user:
      return redirect(url_for("auth.login"))
    if user.is_admin():
      return redirect(url_for("admin.dashboard"))
    if user.status != UserStatus.ACTIVE:
      flash_exception(Exception("Your account is not active."))
      return redirect(url_for("auth.login"))
    return view(*args, **kwargs)

  return wrapped
