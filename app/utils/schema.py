"""Lightweight schema helpers for dev databases without migrations."""

import logging

from sqlalchemy import inspect, text

from app.extensions import db

logger = logging.getLogger(__name__)

_ADMIN_COMMENT_COLUMNS = (
  ("users", "admin_comment"),
  ("buildings", "admin_comment"),
  ("subscriptions", "admin_comment"),
)


def ensure_admin_comment_columns() -> None:
  inspector = inspect(db.engine)
  for table_name, column_name in _ADMIN_COMMENT_COLUMNS:
    if table_name not in inspector.get_table_names():
      continue
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in columns:
      continue
    db.session.execute(
      text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT")
    )
    logger.info("Added column %s.%s", table_name, column_name)
  db.session.commit()


def ensure_building_number_non_unique() -> None:
  inspector = inspect(db.engine)
  if "buildings" not in inspector.get_table_names():
    return

  for index in inspector.get_indexes("buildings"):
    if index.get("unique") and "building_number" in index.get("column_names", []):
      index_name = index["name"]
      try:
        db.session.execute(text(f'DROP INDEX IF EXISTS "{index_name}"'))
        logger.info("Dropped unique index %s on buildings.building_number", index_name)
      except Exception as exc:
        logger.warning("Could not drop index %s: %s", index_name, exc)
        db.session.rollback()

  try:
    db.session.execute(
      text("ALTER TABLE buildings DROP CONSTRAINT IF EXISTS buildings_building_number_key")
    )
  except Exception:
    db.session.rollback()

  db.session.commit()


def migrate_legacy_user_phones() -> None:
  """Copy users.phone_number into user_phones for databases created before multi-phone."""
  inspector = inspect(db.engine)
  if "users" not in inspector.get_table_names():
    return
  if "user_phones" not in inspector.get_table_names():
    return

  user_columns = {column["name"] for column in inspector.get_columns("users")}
  if "phone_number" not in user_columns:
    return

  from app.models import UserPhone

  rows = db.session.execute(
    text(
      "SELECT id, phone_number FROM users "
      "WHERE phone_number IS NOT NULL AND TRIM(phone_number) != ''"
    )
  )
  migrated = 0
  for user_id, phone_number in rows:
    phone = (phone_number or "").strip()
    if not phone:
      continue
    if UserPhone.query.filter_by(phone_number=phone).first():
      continue
    if UserPhone.query.filter_by(user_id=user_id).first():
      continue
    db.session.add(
      UserPhone(
        user_id=user_id,
        phone_number=phone,
        label="Personal",
        is_primary=True,
      )
    )
    migrated += 1
  if migrated:
    db.session.commit()
    logger.info("Migrated %s legacy phone numbers to user_phones", migrated)
