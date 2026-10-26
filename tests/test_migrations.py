from datetime import date

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from app import create_app
from app.config import TestingConfig, config_by_name
from app.extensions import db
from app.utils.schema import _migration_heads


def _file_db_app(db_path, **overrides):
  settings = {
    "TESTING": False,
    "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
    "LOG_FILE": "",
    "AUTO_MIGRATE": True,
    **overrides,
  }
  config_by_name["migration_test"] = type("MigrationTestConfig", (TestingConfig,), settings)
  try:
    return create_app("migration_test")
  finally:
    del config_by_name["migration_test"]


def test_migrations_build_schema_matching_models(tmp_path):
  app = _file_db_app(tmp_path / "fresh.db")

  with app.app_context():
    current, heads = _migration_heads()
    with db.engine.connect() as connection:
      diff = compare_metadata(MigrationContext.configure(connection), db.metadata)

  assert current == heads
  assert diff == []


def test_pre_migration_database_is_adopted_and_upgraded(tmp_path):
  db_path = tmp_path / "legacy.db"
  _file_db_app(db_path)
  engine = create_engine(f"sqlite:///{db_path}")
  with engine.begin() as connection:
    connection.execute(text("DROP TABLE alembic_version"))
    connection.execute(text("DROP TABLE IF EXISTS inquiries"))
    connection.execute(text("ALTER TABLE subscriptions DROP COLUMN billing_day"))
    connection.execute(text("ALTER TABLE users DROP COLUMN auth_version"))
    connection.execute(text(
      "INSERT INTO buildings (id, building_number, name, created_at, updated_at) "
      "VALUES (1, 'B-1', 'Old', '2026-01-01', '2026-01-01')"
    ))
    connection.execute(text(
      "INSERT INTO subscriptions (id, user_id, building_id, door_number, monthly_fee, status, "
      "next_payment_due, created_at, updated_at) "
      "VALUES (1, 1, 1, '1A', 30, 'ACTIVE', '2026-11-30', '2026-01-01', '2026-01-01')"
    ))
  engine.dispose()

  app = _file_db_app(db_path)

  with app.app_context():
    current, heads = _migration_heads()
    columns = {c["name"] for c in inspect(db.engine).get_columns("users")}
    billing_day = db.session.execute(text("SELECT billing_day FROM subscriptions")).scalar()
  assert current == heads
  assert "auth_version" in columns
  assert billing_day == 30


def test_production_refuses_to_start_with_pending_migrations(tmp_path):
  with pytest.raises(RuntimeError, match="flask db upgrade"):
    _file_db_app(tmp_path / "empty.db", AUTO_MIGRATE=False)
