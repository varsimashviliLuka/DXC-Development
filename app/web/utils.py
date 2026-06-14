"""Shared helpers for server-rendered routes."""

from flask import flash

from app.utils.errors import AppError
from app.utils.validators import ValidationError


def flash_exception(exc: Exception) -> None:
  if isinstance(exc, AppError):
    flash(exc.message, "error")
  elif isinstance(exc, ValidationError):
    flash(str(exc), "error")
  elif isinstance(exc, ValueError):
    flash(str(exc), "error")
  else:
    flash("An unexpected error occurred.", "error")


def form_value(form, key, default=""):
  if not form:
    return default
  value = form.get(key, default)
  return value if value is not None else default
