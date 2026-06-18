"""Tests for admin balance adjustments."""

from decimal import Decimal

from app.enums import TransactionType
from app.extensions import db
from app.models import Transaction, User
from app.services.transaction_service import (
  DEFAULT_ADMIN_CREDIT_DESCRIPTION,
  DEFAULT_ADMIN_DEBIT_DESCRIPTION,
  TransactionService,
)


def test_admin_add_balance_creates_adjustment(app):
  with app.app_context():
    user = User(
      id_number="01124096120",
      first_name="Test",
      last_name="User",
      password_hash="x",
      balance=Decimal("10.00"),
    )
    db.session.add(user)
    db.session.commit()

    txn = TransactionService.record_admin_adjustment(
      user=user,
      amount=Decimal("25.50"),
      direction="add",
    )

    assert float(user.balance) == 35.5
    assert txn.transaction_type == TransactionType.ADJUSTMENT
    assert float(txn.amount) == 25.5
    assert txn.description == DEFAULT_ADMIN_CREDIT_DESCRIPTION


def test_admin_subtract_balance_uses_custom_reason(app):
  with app.app_context():
    user = User(
      id_number="01124096121",
      password_hash="x",
      balance=Decimal("100.00"),
    )
    db.session.add(user)
    db.session.commit()

    txn = TransactionService.record_admin_adjustment(
      user=user,
      amount=Decimal("15.00"),
      direction="subtract",
      description="Manual correction",
    )

    assert float(user.balance) == 85.0
    assert float(txn.amount) == -15.0
    assert txn.description == "Manual correction"


def test_admin_subtract_balance_default_description(app):
  with app.app_context():
    user = User(
      id_number="01124096122",
      password_hash="x",
      balance=Decimal("50.00"),
    )
    db.session.add(user)
    db.session.commit()

    txn = TransactionService.record_admin_adjustment(
      user=user,
      amount=Decimal("5.00"),
      direction="subtract",
      description="   ",
    )

    assert txn.description == DEFAULT_ADMIN_DEBIT_DESCRIPTION
    assert Transaction.query.filter_by(user_id=user.id).count() == 1
