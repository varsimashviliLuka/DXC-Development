import pytest

from app import create_app


@pytest.fixture
def app():
  application = create_app("testing")
  yield application


@pytest.fixture
def client(app):
  return app.test_client()


@pytest.fixture
def admin_headers(client):
  response = client.post(
    "/api/v1/auth/login",
    json={"phone_number": "+995591000001", "password": "TestAdmin123!"},
  )
  assert response.status_code == 200
  token = response.get_json()["access_token"]
  return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def registered_user(client, admin_headers):
  payload = {
    "phone_number": "+995592159199",
    "id_number": "USER1234",
    "password": "UserPass123",
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane.doe@example.com",
  }
  response = client.post("/api/v1/users", json=payload, headers=admin_headers)
  assert response.status_code == 201
  return payload


@pytest.fixture
def user_headers(client, registered_user):
  response = client.post(
    "/api/v1/auth/login",
    json={
      "phone_number": registered_user["phone_number"],
      "password": registered_user["password"],
    },
  )
  assert response.status_code == 200
  token = response.get_json()["access_token"]
  return {"Authorization": f"Bearer {token}"}
