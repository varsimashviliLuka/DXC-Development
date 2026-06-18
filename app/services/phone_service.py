"""User phone number management."""

import logging

from app.extensions import db
from app.models import User, UserPhone
from app.utils.errors import ConflictError, NotFoundError
from app.utils.validators import normalize_phone

logger = logging.getLogger(__name__)


class PhoneService:
  @staticmethod
  def get_by_id(phone_id: int) -> UserPhone:
    phone = db.session.get(UserPhone, phone_id)
    if not phone:
      raise NotFoundError("Phone number not found")
    return phone

  @staticmethod
  def find_user_by_phone(phone_number: str) -> User | None:
    phone = normalize_phone(phone_number)
    record = UserPhone.query.filter_by(phone_number=phone).first()
    return record.user if record else None

  @staticmethod
  def _ensure_unique(phone: str, *, exclude_user_id: int | None = None) -> None:
    record = UserPhone.query.filter_by(phone_number=phone).first()
    if record and record.user_id != exclude_user_id:
      raise ConflictError("Phone number already registered to another user")

  @staticmethod
  def add_phone(
    user: User,
    phone_number: str,
    *,
    label: str | None = None,
    is_primary: bool = False,
  ) -> UserPhone:
    phone = normalize_phone(phone_number)
    PhoneService._ensure_unique(phone, exclude_user_id=user.id)

    if is_primary or not user.phones.count():
      UserPhone.query.filter_by(user_id=user.id, is_primary=True).update(
        {UserPhone.is_primary: False},
        synchronize_session=False,
      )
      is_primary = True

    record = UserPhone(
      user_id=user.id,
      phone_number=phone,
      label=(label or "").strip() or None,
      is_primary=is_primary,
    )
    db.session.add(record)
    db.session.flush()
    logger.info("Added phone user_id=%s phone=%s", user.id, phone)
    return record

  @staticmethod
  def remove_phone(phone_id: int, *, user_id: int | None = None) -> None:
    record = PhoneService.get_by_id(phone_id)
    if user_id is not None and record.user_id != user_id:
      raise NotFoundError("Phone number not found")
    was_primary = record.is_primary
    user_id = record.user_id
    db.session.delete(record)
    db.session.flush()
    if was_primary:
      next_phone = UserPhone.query.filter_by(user_id=user_id).first()
      if next_phone:
        next_phone.is_primary = True
    db.session.flush()

  @staticmethod
  def replace_phones(user: User, phones: list[dict]) -> list[UserPhone]:
    """
    Replace all phones for a user.

    Each item: {"phone_number": str, "label": str|None, "is_primary": bool}
    """
    cleaned: list[dict] = []
    seen: set[str] = set()
    for item in phones:
      raw = (item.get("phone_number") or "").strip()
      if not raw:
        continue
      phone = normalize_phone(raw)
      if phone in seen:
        raise ConflictError("Duplicate phone numbers in the same request")
      seen.add(phone)
      cleaned.append({
        "phone_number": phone,
        "label": (item.get("label") or "").strip() or None,
        "is_primary": bool(item.get("is_primary")),
      })

    for existing in list(user.phones):
      db.session.delete(existing)
    db.session.flush()

    if not cleaned:
      return []

    if not any(p["is_primary"] for p in cleaned):
      cleaned[0]["is_primary"] = True
    else:
      primary_set = False
      for item in cleaned:
        if item["is_primary"]:
          if primary_set:
            item["is_primary"] = False
          else:
            primary_set = True

    records: list[UserPhone] = []
    for item in cleaned:
      PhoneService._ensure_unique(item["phone_number"], exclude_user_id=user.id)
      record = UserPhone(
        user_id=user.id,
        phone_number=item["phone_number"],
        label=item["label"],
        is_primary=item["is_primary"],
      )
      db.session.add(record)
      records.append(record)
    db.session.flush()
    return records

  @staticmethod
  def phones_to_dict(user: User, *, include_label: bool = False) -> list[dict]:
    return [
      p.to_dict(include_label=include_label)
      for p in user.phones.order_by(UserPhone.is_primary.desc(), UserPhone.id)
    ]
