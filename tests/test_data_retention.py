from datetime import date
from decimal import Decimal

import pytest

from app.extensions import db
from app.models import Building, Subscription, Transaction, User
from app.services.subscription_service import SubscriptionService

USER_ID_NUMBER = "01024096118"


@pytest.fixture
def billed_subscription(app, client, admin_headers, registered_user):
  building = client.post(
    "/api/v1/buildings",
    json={"building_number": "B-300", "name": "Retention Building"},
    headers=admin_headers,
  ).get_json()
  with app.app_context():
    user_id = User.query.filter_by(id_number=USER_ID_NUMBER).first().id
  sub = client.post(
    "/api/v1/subscriptions",
    json={
      "user_id": user_id,
      "building_id": building["id"],
      "door_number": "7C",
      "monthly_fee": 25.00,
      "next_payment_due": date.today().isoformat(),
    },
    headers=admin_headers,
  ).get_json()
  with app.app_context():
    SubscriptionService.process_due_payments(for_date=date.today())
  return {"user_id": user_id, "building_id": building["id"], "subscription_id": sub["id"]}


def test_user_with_payment_history_cannot_be_deleted(app, client, admin_headers, billed_subscription):
  response = client.delete(f"/api/v1/users/{billed_subscription['user_id']}", headers=admin_headers)

  assert response.status_code == 409
  assert "inactive" in response.get_json()["message"]
  with app.app_context():
    assert db.session.get(User, billed_subscription["user_id"]) is not None
    assert Transaction.query.filter_by(user_id=billed_subscription["user_id"]).count() == 1


def test_user_without_history_can_still_be_deleted(app, client, admin_headers, registered_user):
  with app.app_context():
    user_id = User.query.filter_by(id_number=USER_ID_NUMBER).first().id

  response = client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)

  assert response.status_code == 204
  with app.app_context():
    assert db.session.get(User, user_id) is None


def test_subscription_with_payment_history_cannot_be_deleted(app, client, admin_headers, billed_subscription):
  sub_id = billed_subscription["subscription_id"]

  response = client.delete(f"/api/v1/subscriptions/{sub_id}", headers=admin_headers)

  assert response.status_code == 409
  with app.app_context():
    assert db.session.get(Subscription, sub_id) is not None


def test_building_with_billed_subscription_cannot_be_deleted(app, client, admin_headers, billed_subscription):
  building_id = billed_subscription["building_id"]

  response = client.delete(f"/api/v1/buildings/{building_id}", headers=admin_headers)

  assert response.status_code == 409
  with app.app_context():
    assert db.session.get(Building, building_id) is not None


def test_admin_web_delete_shows_message_and_keeps_user(app, client, billed_subscription):
  client.post("/auth/login", data={"id_number": "01011000001", "password": "TestAdmin123!"})

  response = client.post(
    f"/admin/users/{billed_subscription['user_id']}/delete",
    follow_redirects=True,
  )

  assert response.status_code == 200
  assert b"payment history" in response.data
  with app.app_context():
    assert db.session.get(User, billed_subscription["user_id"]) is not None


def test_non_numeric_page_parameter_does_not_crash(client):
  client.post("/auth/login", data={"id_number": "01011000001", "password": "TestAdmin123!"})

  assert client.get("/admin/users?page=abc").status_code == 200
