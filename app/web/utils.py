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


def parse_phones_from_form(form) -> list[dict]:
  numbers = form.getlist("phone_number")
  labels = form.getlist("phone_label")
  try:
    primary_idx = int(form.get("phone_primary", "0") or 0)
  except ValueError:
    primary_idx = 0

  phones: list[dict] = []
  for index, number in enumerate(numbers):
    number = (number or "").strip()
    if not number:
      continue
    label = labels[index].strip() if index < len(labels) and labels[index] else ""
    phones.append({
      "phone_number": number,
      "label": label or None,
      "is_primary": index == primary_idx,
    })
  return phones
