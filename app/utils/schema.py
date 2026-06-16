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
