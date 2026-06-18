from datetime import date
from decimal import Decimal

import pytest

from app.enums import SubscriptionStatus
from app.extensions import db
from app.models import Subscription, User
from app.services.subscription_service import SubscriptionService
from app.services.transaction_service import TransactionService


@pytest.fixture
def user_with_subscription(app, client, admin_headers, registered_user):
  building = client.post(
    "/api/v1/buildings",
    json={"building_number": "B-200", "name": "Test Building"},
    headers=admin_headers,
  ).get_json()

  users = client.get("/api/v1/users", headers=admin_headers).get_json()["items"]
  user_id = next(u["id"] for u in users if u["id_number"] == registered_user["id_number"])

  sub = client.post(
    "/api/v1/subscriptions",
    json={
      "user_id": user_id,
      "building_id": building["id"],
      "door_number": "5B",
      "monthly_fee": 30.00,
      "next_payment_due": date.today().isoformat(),
    },
    headers=admin_headers,
  ).get_json()

  return {"user_id": user_id, "subscription_id": sub["id"]}


def test_process_due_payment_with_sufficient_balance(app, user_with_subscription):
  with app.app_context():
    user = db.session.get(User, user_with_subscription["user_id"])
    user.balance = Decimal("50.00")
    db.session.commit()

    result = SubscriptionService.process_due_payments(for_date=date.today())
    assert result["processed"] == 1
    assert result["marked_overdue"] == 0

    db.session.refresh(user)
    sub = db.session.get(Subscription, user_with_subscription["subscription_id"])
    assert float(user.balance) == 20.0
    assert sub.status == SubscriptionStatus.ACTIVE


def test_process_due_payment_marks_overdue_when_insufficient(app, user_with_subscription):
  with app.app_context():
    user = db.session.get(User, user_with_subscription["user_id"])
    user.balance = Decimal("10.00")
    db.session.commit()

    result = SubscriptionService.process_due_payments(for_date=date.today())
    assert result["processed"] == 1
    assert result["marked_overdue"] == 1

    db.session.refresh(user)
    sub = db.session.get(Subscription, user_with_subscription["subscription_id"])
    assert float(user.balance) == -20.0
    assert sub.status == SubscriptionStatus.OVERDUE


def test_payment_restores_overdue_subscription_to_active(app, user_with_subscription):
  with app.app_context():
    user = db.session.get(User, user_with_subscription["user_id"])
    sub = db.session.get(Subscription, user_with_subscription["subscription_id"])
    user.balance = Decimal("10.00")
    db.session.commit()

    SubscriptionService.process_due_payments(for_date=date.today())
    db.session.refresh(user)
    db.session.refresh(sub)
    assert sub.status == SubscriptionStatus.OVERDUE
    assert float(user.balance) == -20.0

    TransactionService.record_payment(
      user=user,
      amount=Decimal("25.00"),
      reference="TEST-RESTORE-REF",
    )
    db.session.refresh(sub)
    assert float(user.balance) == 5.0
    assert sub.status == SubscriptionStatus.ACTIVE


def test_partial_payment_keeps_subscription_overdue(app, user_with_subscription):
  with app.app_context():
    user = db.session.get(User, user_with_subscription["user_id"])
    sub = db.session.get(Subscription, user_with_subscription["subscription_id"])
    user.balance = Decimal("10.00")
    db.session.commit()

    SubscriptionService.process_due_payments(for_date=date.today())
    db.session.refresh(sub)
    assert sub.status == SubscriptionStatus.OVERDUE

    TransactionService.record_payment(
      user=user,
      amount=Decimal("10.00"),
      reference="TEST-PARTIAL-REF",
    )
    db.session.refresh(user)
    db.session.refresh(sub)
    assert float(user.balance) == -10.0
    assert sub.status == SubscriptionStatus.OVERDUE


def test_payment_increases_balance(app, registered_user, admin_headers, client):
  with app.app_context():
    user = User.query.filter_by(id_number=registered_user["id_number"]).first()
    TransactionService.record_payment(user=user, amount=Decimal("75.00"), reference="TEST-REF")
    db.session.refresh(user)
    assert float(user.balance) == 75.0
