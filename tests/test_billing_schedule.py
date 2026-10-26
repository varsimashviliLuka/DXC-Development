from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.enums import SubscriptionStatus, TransactionType
from app.extensions import db
from app.models import Subscription, Transaction, User
from app.scheduler import _acquire_scheduler_lock
from app.services.auth_service import AuthService
from app.services.building_service import BuildingService
from app.services.subscription_service import SubscriptionService, next_billing_date
from app.services.transaction_service import TransactionService


@pytest.fixture
def make_subscription(app):
  def _make(*, due: date, fee="30.00", balance="0.00", status=SubscriptionStatus.ACTIVE):
    user = AuthService.register_user(id_number="01024096118", password="UserPass123")
    user.balance = Decimal(balance)
    building = BuildingService.create(building_number="B-1", name="Test Building")
    sub = SubscriptionService.create(
      user_id=user.id,
      building_id=building.id,
      door_number="5B",
      monthly_fee=Decimal(fee),
      next_payment_due=due,
      status=status,
    )
    return user, sub

  with app.app_context():
    yield _make


def _fees(sub_id):
  return Transaction.query.filter_by(
    subscription_id=sub_id,
    transaction_type=TransactionType.FEE,
  ).order_by(Transaction.id).all()


def test_missed_periods_are_caught_up(make_subscription):
  user, sub = make_subscription(due=date(2026, 7, 15), balance="100.00")

  result = SubscriptionService.process_due_payments(for_date=date(2026, 10, 20))

  assert result["processed"] == 4
  assert [f.reference for f in _fees(sub.id)] == [
    f"FEE-{sub.id}-2026-07-15",
    f"FEE-{sub.id}-2026-08-15",
    f"FEE-{sub.id}-2026-09-15",
    f"FEE-{sub.id}-2026-10-15",
  ]
  db.session.refresh(user)
  db.session.refresh(sub)
  assert user.balance == Decimal("-20.00")
  assert sub.next_payment_due == date(2026, 11, 15)
  assert sub.status == SubscriptionStatus.OVERDUE


def test_running_twice_on_the_same_day_charges_once(make_subscription):
  user, sub = make_subscription(due=date(2026, 10, 26), balance="50.00")

  SubscriptionService.process_due_payments(for_date=date(2026, 10, 26))
  second = SubscriptionService.process_due_payments(for_date=date(2026, 10, 26))

  assert second["processed"] == 0
  assert len(_fees(sub.id)) == 1
  db.session.refresh(user)
  assert user.balance == Decimal("20.00")


def test_moving_due_date_back_does_not_recharge_paid_period(make_subscription):
  user, sub = make_subscription(due=date(2026, 10, 26), balance="50.00")
  SubscriptionService.process_due_payments(for_date=date(2026, 10, 26))

  SubscriptionService.update(sub.id, next_payment_due=date(2026, 10, 26), next_payment_due_set=True)
  result = SubscriptionService.process_due_payments(for_date=date(2026, 10, 26))

  assert result["processed"] == 0
  assert len(_fees(sub.id)) == 1
  db.session.refresh(sub)
  assert sub.next_payment_due == date(2026, 11, 26)


def test_end_of_month_billing_day_does_not_drift(make_subscription):
  _user, sub = make_subscription(due=date(2027, 1, 31), balance="500.00")

  SubscriptionService.process_due_payments(for_date=date(2027, 4, 1))

  assert [f.reference[-10:] for f in _fees(sub.id)] == ["2027-01-31", "2027-02-28", "2027-03-31"]
  db.session.refresh(sub)
  assert sub.next_payment_due == date(2027, 4, 30)


@pytest.mark.parametrize("current, billing_day, expected", [
  (date(2027, 1, 31), 31, date(2027, 2, 28)),
  (date(2027, 2, 28), 31, date(2027, 3, 31)),
  (date(2028, 1, 30), 30, date(2028, 2, 29)),
  (date(2026, 12, 15), 15, date(2027, 1, 15)),
])
def test_next_billing_date(current, billing_day, expected):
  assert next_billing_date(current, billing_day) == expected


def test_inactive_subscription_is_not_charged(make_subscription):
  user, sub = make_subscription(
    due=date(2026, 9, 1),
    balance="50.00",
    status=SubscriptionStatus.INACTIVE,
  )

  result = SubscriptionService.process_due_payments(for_date=date(2026, 10, 26))

  assert result["processed"] == 0
  db.session.refresh(user)
  assert user.balance == Decimal("50.00")


def test_balance_change_is_not_lost_when_object_is_stale(make_subscription):
  user, _sub = make_subscription(due=date(2026, 12, 1), balance="0.00")
  user_id = user.id
  # Another request credits the account while this session still holds the old balance.
  db.session.execute(text("UPDATE users SET balance = balance + 30 WHERE id = :id"), {"id": user_id})

  TransactionService.record_payment(user=user, amount=Decimal("10.00"), reference="LOST-UPDATE")

  db.session.expire_all()
  assert db.session.get(User, user_id).balance == Decimal("40.00")


def test_only_one_process_gets_the_scheduler_lock(tmp_path):
  import app.scheduler as scheduler_module

  class FakeApp:
    instance_path = str(tmp_path)

  previous = scheduler_module._lock_file
  scheduler_module._lock_file = None
  try:
    assert _acquire_scheduler_lock(FakeApp()) is True
    first = scheduler_module._lock_file
    assert _acquire_scheduler_lock(FakeApp()) is False
    first.close()
  finally:
    scheduler_module._lock_file = previous
