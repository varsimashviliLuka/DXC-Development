"""Input validation helpers."""

import re

import phonenumbers
from phonenumbers import NumberParseException


PHONE_PATTERN = re.compile(r"^\+?[1-9]\d{6,14}$")
ID_NUMBER_PATTERN = re.compile(r"^[A-Za-z0-9\-]{4,50}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_MIN_LENGTH = 8
DEFAULT_PHONE_REGION = "GE"


class ValidationError(ValueError):
  pass


def normalize_phone(phone: str, default_region: str | None = None) -> str:
  phone = (phone or "").strip()
  if not phone:
    raise ValidationError("Phone number is required")

  region = default_region or DEFAULT_PHONE_REGION

  try:
    if phone.startswith("+"):
      parsed = phonenumbers.parse(phone, None)
    else:
      parsed = phonenumbers.parse(phone, region)
    if not phonenumbers.is_valid_number(parsed):
      raise ValidationError("Invalid phone number")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
  except NumberParseException:
    if PHONE_PATTERN.match(phone):
      return phone if phone.startswith("+") else f"+{phone}"
    raise ValidationError("Invalid phone number format")


def validate_email(email: str | None) -> str | None:
  if email is None or not str(email).strip():
    return None
  email = str(email).strip().lower()
  if not EMAIL_PATTERN.match(email):
    raise ValidationError("Invalid email address")
  return email


def validate_id_number(id_number: str) -> str:
  id_number = (id_number or "").strip()
  if not ID_NUMBER_PATTERN.match(id_number):
    raise ValidationError(
      "ID number must be 4-50 alphanumeric characters (hyphens allowed)"
    )
  return id_number.upper()


def validate_password(password: str) -> str:
  if not password or len(password) < PASSWORD_MIN_LENGTH:
    raise ValidationError(
      f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
    )
  if password.isdigit() or password.isalpha():
    raise ValidationError("Password must contain both letters and numbers")
  return password


def validate_chip_number(chip_number: str) -> str:
  chip_number = (chip_number or "").strip().upper()
  if not re.match(r"^[A-Z0-9\-]{3,50}$", chip_number):
    raise ValidationError("Chip number must be 3-50 alphanumeric characters")
  return chip_number


def validate_door_number(door_number: str) -> str:
  door_number = (door_number or "").strip()
  if not door_number or len(door_number) > 50:
    raise ValidationError("Door number is required and must be at most 50 characters")
  return door_number
