import io


def test_health(client):
  response = client.get("/api/v1/health")
  assert response.status_code == 200
  assert response.get_json()["status"] == "ok"


def test_missing_auth_returns_401(client):
  response = client.get("/api/v1/me")
  assert response.status_code == 401
  assert "Missing Authorization Header" in response.get_json()["message"]


def test_admin_login(client):
  response = client.post(
    "/api/v1/auth/login",
    json={"phone_number": "+995591000001", "password": "TestAdmin123!"},
  )
  assert response.status_code == 200
  data = response.get_json()
  assert "access_token" in data
  assert data["user"]["role"] == "admin"


def test_user_cannot_register_users(client, user_headers):
  response = client.post(
    "/api/v1/users",
    json={
      "phone_number": "+995555123456",
      "id_number": "NEWUSER1",
      "password": "AnotherPass123",
    },
    headers=user_headers,
  )
  assert response.status_code == 403


def test_admin_registers_user(client, admin_headers, registered_user):
  response = client.get("/api/v1/users", headers=admin_headers)
  assert response.status_code == 200
  data = response.get_json()
  assert data["total"] >= 1
  assert any(item["phone_number"] == registered_user["phone_number"] for item in data["items"])


def test_user_dashboard(client, user_headers, registered_user):
  response = client.get("/api/v1/me", headers=user_headers)
  assert response.status_code == 200
  data = response.get_json()
  assert "user" in data
  assert "summary" in data
  assert "chips" in data
  assert data["user"]["phone_number"] == registered_user["phone_number"]
  assert data["user"]["email"] == registered_user["email"]


def test_password_change(client, user_headers, registered_user):
  response = client.post(
    "/api/v1/me/password",
    json={"current_password": "UserPass123", "new_password": "NewUserPass456"},
    headers=user_headers,
  )
  assert response.status_code == 200

  old_login = client.post(
    "/api/v1/auth/login",
    json={
      "phone_number": registered_user["phone_number"],
      "password": "UserPass123",
    },
  )
  assert old_login.status_code == 401

  new_login = client.post(
    "/api/v1/auth/login",
    json={
      "phone_number": registered_user["phone_number"],
      "password": "NewUserPass456",
    },
  )
  assert new_login.status_code == 200


def test_building_subscription_and_chip_flow(client, admin_headers, registered_user):
  building_response = client.post(
    "/api/v1/buildings",
    json={
      "building_number": "B-101",
      "name": "Sunrise Tower",
      "address": "1 Main Street",
    },
    headers=admin_headers,
  )
  assert building_response.status_code == 201
  building_id = building_response.get_json()["id"]

  users_response = client.get("/api/v1/users", headers=admin_headers)
  user_id = next(
    u["id"]
    for u in users_response.get_json()["items"]
    if u["phone_number"] == registered_user["phone_number"]
  )

  subscription_response = client.post(
    "/api/v1/subscriptions",
    json={
      "user_id": user_id,
      "building_id": building_id,
      "door_number": "12A",
      "monthly_fee": 25.50,
    },
    headers=admin_headers,
  )
  assert subscription_response.status_code == 201
  sub = subscription_response.get_json()
  assert sub["door_number"] == "12A"
  assert sub["monthly_fee"] == 25.5
  assert "chip_number" not in sub

  chip_response = client.post(
    "/api/v1/chips",
    json={"user_id": user_id, "chip_number": "CHIP-001"},
    headers=admin_headers,
  )
  assert chip_response.status_code == 201

  login_response = client.post(
    "/api/v1/auth/login",
    json={
      "phone_number": registered_user["phone_number"],
      "password": registered_user["password"],
    },
  )
  user_token = login_response.get_json()["access_token"]
  me_subs = client.get(
    "/api/v1/me/subscriptions",
    headers={"Authorization": f"Bearer {user_token}"},
  )
  assert me_subs.status_code == 200
  assert len(me_subs.get_json()) == 1

  me_chips = client.get(
    "/api/v1/me/chips",
    headers={"Authorization": f"Bearer {user_token}"},
  )
  assert me_chips.status_code == 200
  assert len(me_chips.get_json()) == 1


def test_csv_payment_import(client, admin_headers, registered_user):
  from tests.bank_csv_fixtures import build_bank_csv, make_bank_csv_row

  # User id_number USER1234 — match via UID token (paying for self with explicit UID)
  csv_content = build_bank_csv(
    make_bank_csv_row(
      amount="100.0",
      partner_tax="01099999999",
      partner_name="Someone Else",
      additional_description="UID:USER1234",
      transaction_id="18705073767.20",
    )
  )
  response = client.post(
    "/api/v1/transactions/import",
    data={"file": (io.BytesIO(csv_content.encode("utf-8")), "payments.csv")},
    headers=admin_headers,
    content_type="multipart/form-data",
  )
  assert response.status_code == 200
  result = response.get_json()
  assert result["matched"] == 1

  users_response = client.get("/api/v1/users", headers=admin_headers)
  user = next(
    u for u in users_response.get_json()["items"]
    if u["phone_number"] == registered_user["phone_number"]
  )
  assert user["balance"] == 100.0


def test_bank_import_by_partner_tax_code(client, admin_headers):
  from tests.bank_csv_fixtures import build_bank_csv, make_bank_csv_row

  client.post(
    "/api/v1/users",
    json={
      "phone_number": "+995555111222",
      "id_number": "01010018012",
      "password": "UserPass123",
    },
    headers=admin_headers,
  )

  csv_content = build_bank_csv(
    make_bank_csv_row(
      partner_tax="01010018012",
      transaction_id="18705073768.20",
    )
  )
  response = client.post(
    "/api/v1/transactions/import",
    data={"file": (io.BytesIO(csv_content.encode("utf-8")), "bank.csv")},
    headers=admin_headers,
    content_type="multipart/form-data",
  )
  assert response.status_code == 200
  assert response.get_json()["matched"] == 1


def test_bank_import_unmatched(client, admin_headers):
  from tests.bank_csv_fixtures import build_bank_csv, make_bank_csv_row

  csv_content = build_bank_csv(
    make_bank_csv_row(
      partner_tax="01999999999",
      transaction_id="18705073769.20",
    )
  )
  response = client.post(
    "/api/v1/transactions/import",
    data={"file": (io.BytesIO(csv_content.encode("utf-8")), "bank.csv")},
    headers=admin_headers,
    content_type="multipart/form-data",
  )
  assert response.status_code == 200
  result = response.get_json()
  assert result["unmatched"] == 1


def test_login_rate_limit_not_triggered_on_success(client):
  for _ in range(3):
    response = client.post(
      "/api/v1/auth/login",
      json={"phone_number": "+995591000001", "password": "TestAdmin123!"},
    )
    assert response.status_code == 200

