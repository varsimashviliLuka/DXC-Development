"""Authentication and authorization decorators."""

import logging
from functools import wraps

from flask import g
from flask_jwt_extended import get_jwt, verify_jwt_in_request
from flask_jwt_extended.exceptions import (
  FreshTokenRequired,
  InvalidHeaderError,
  JWTDecodeError,
  JWTExtendedException,
  NoAuthorizationError,
  RevokedTokenError,
  WrongTokenError,
)

from app.enums import UserRole, UserStatus
from app.extensions import db
from app.models import User
from app.utils.errors import ForbiddenError, UnauthorizedError

logger = logging.getLogger(__name__)


def _load_current_user():
  if getattr(g, "current_user", None) is not None:
    return g.current_user

  try:
    verify_jwt_in_request()
  except NoAuthorizationError:
    raise UnauthorizedError("Missing Authorization Header")
  except (InvalidHeaderError, JWTDecodeError, WrongTokenError, RevokedTokenError, FreshTokenRequired):
    raise UnauthorizedError("Invalid or expired token")
  except JWTExtendedException as exc:
    raise UnauthorizedError(str(exc))

  claims = get_jwt()
  user_id = claims.get("sub")
  if not user_id:
    raise UnauthorizedError("Invalid token")

  user = db.session.get(User, int(user_id))
  if not user:
    logger.warning("JWT references missing user_id=%s", user_id)
    raise UnauthorizedError("User not found")

  if user.status == UserStatus.SUSPENDED:
    raise ForbiddenError("Account is suspended")

  g.current_user = user
  return user


def jwt_required_custom(fn):
  @wraps(fn)
  def wrapper(*args, **kwargs):
    _load_current_user()
    return fn(*args, **kwargs)

  return wrapper


def admin_required(fn):
  @wraps(fn)
  def wrapper(*args, **kwargs):
    user = _load_current_user()
    if not user.is_admin():
      logger.warning("Non-admin user_id=%s attempted admin action", user.id)
      raise ForbiddenError("Admin access required")
    return fn(*args, **kwargs)

  return wrapper


def active_user_required(fn):
  @wraps(fn)
  def wrapper(*args, **kwargs):
    user = _load_current_user()
    if user.status != UserStatus.ACTIVE:
      raise ForbiddenError("Account is not active")
    return fn(*args, **kwargs)

  return wrapper
