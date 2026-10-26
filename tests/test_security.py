import io
import re

import pytest
from flask import Flask
from flask.sessions import SecureCookieSessionInterface

from app import create_app
from app.config import ProductionConfig, TestingConfig, config_by_name
from app.enums import UserStatus
from app.models import User
from app.services.auth_service import AuthService

ADMIN_ID = "01011000001"
ADMIN_PASSWORD = "TestAdmin123!"
USER_ID = "01024096118"
USER_PASSWORD = "UserPass123"
STRONG_SECRET = "s" * 40
STRONG_JWT_SECRET = "j" * 40


def _make_app(**overrides):
  config_cls = type("OverrideConfig", (TestingConfig,), overrides)
  config_by_name["override"] = config_cls
  try:
    return create_app("override")
  finally:
    del config_by_name["override"]


def _create_user(app, *, id_number=USER_ID, password=USER_PASSWORD, status=UserStatus.ACTIVE):
  with app.app_context():
    AuthService.register_user(id_number=id_number, password=password, status=status)


def _web_login(client, id_number, password, **query):
  return client.post("/auth/login", query_string=query, data={
    "id_number": id_number,
    "password": password,
  })


def _api_token(client, id_number, password):
  response = client.post("/api/v1/auth/login", json={
    "id_number": id_number,
    "password": password,
  })
  assert response.status_code == 200
  return {"Authorization": f"Bearer {response.get_json()['access_token']}"}


def _csrf_token(client, path="/auth/login"):
  html = client.get(path).get_data(as_text=True)
  match = re.search(r'name="csrf_token" value="([^"]+)"', html)
  assert match, "form is missing its CSRF token"
  return match.group(1)


def test_session_signed_with_published_example_key_is_rejected(app, client):
  attacker = Flask("attacker")
  attacker.secret_key = "change-me-to-a-long-random-string-at-least-32-chars"
  with app.app_context():
    admin_id = User.query.filter_by(id_number=ADMIN_ID).first().id
  forged = SecureCookieSessionInterface().get_signing_serializer(attacker).dumps(
    {"user_id": admin_id, "auth_version": 0}
  )
  client.set_cookie("session", forged)

  response = client.get("/admin/users")

  assert response.status_code == 302
  assert "/auth/login" in response.location


def test_web_form_without_csrf_token_is_rejected():
  app = _make_app(WTF_CSRF_ENABLED=True)
  client = app.test_client()

  response = _web_login(client, ADMIN_ID, ADMIN_PASSWORD)

  assert response.status_code == 302
  assert client.get("/admin/").status_code == 302


def test_web_form_with_csrf_token_succeeds():
  app = _make_app(WTF_CSRF_ENABLED=True)
  client = app.test_client()
  token = _csrf_token(client)

  response = client.post("/auth/login", data={
    "id_number": ADMIN_ID,
    "password": ADMIN_PASSWORD,
    "csrf_token": token,
  })

  assert response.status_code == 302
  assert client.get("/admin/").status_code == 200


def test_json_api_does_not_require_csrf_token():
  app = _make_app(WTF_CSRF_ENABLED=True)
  _api_token(app.test_client(), ADMIN_ID, ADMIN_PASSWORD)


@pytest.mark.parametrize("target", [
  "//evil.example.com",
  "https://evil.example.com/",
  "/\\evil.example.com",
  "javascript:alert(1)",
])
def test_login_ignores_external_next_url(client, target):
  response = _web_login(client, ADMIN_ID, ADMIN_PASSWORD, next=target)

  assert response.status_code == 302
  assert "evil" not in response.location
  assert "javascript" not in response.location


def test_login_follows_local_next_url(client):
  response = _web_login(client, ADMIN_ID, ADMIN_PASSWORD, next="/admin/users")

  assert response.location.endswith("/admin/users")


def test_web_login_locks_account_after_repeated_failures():
  app = _make_app(RATELIMIT_ENABLED=True)
  _create_user(app)
  client = app.test_client()

  for _ in range(5):
    assert _web_login(client, USER_ID, "WrongPass123").status_code == 200

  assert _web_login(client, USER_ID, USER_PASSWORD).status_code == 429
  assert _web_login(client, ADMIN_ID, ADMIN_PASSWORD).status_code == 302


def test_successful_logins_do_not_count_toward_lockout():
  app = _make_app(RATELIMIT_ENABLED=True)
  _create_user(app)

  for _ in range(8):
    client = app.test_client()
    assert _web_login(client, USER_ID, USER_PASSWORD).status_code == 302


def test_api_login_locks_account_after_repeated_failures():
  app = _make_app(RATELIMIT_ENABLED=True)
  _create_user(app)
  client = app.test_client()

  for _ in range(5):
    response = client.post("/api/v1/auth/login", json={
      "id_number": USER_ID,
      "password": "WrongPass123",
    })
    assert response.status_code == 401

  response = client.post("/api/v1/auth/login", json={
    "id_number": USER_ID,
    "password": USER_PASSWORD,
  })
  assert response.status_code == 429


def test_password_change_signs_out_other_sessions(app):
  _create_user(app)
  device_a = app.test_client()
  device_b = app.test_client()
  _web_login(device_a, USER_ID, USER_PASSWORD)
  _web_login(device_b, USER_ID, USER_PASSWORD)
  token = _api_token(app.test_client(), USER_ID, USER_PASSWORD)

  response = device_a.post("/dashboard/password", data={
    "current_password": USER_PASSWORD,
    "new_password": "NewUserPass456",
  })

  assert response.status_code == 302
  assert device_a.get("/dashboard/").status_code == 200
  assert "/auth/login" in device_b.get("/dashboard/").location
  assert device_a.get("/api/v1/me", headers=token).status_code == 401


def test_suspending_user_revokes_sessions_and_tokens(app, client):
  _create_user(app)
  user_client = app.test_client()
  _web_login(user_client, USER_ID, USER_PASSWORD)
  user_token = _api_token(app.test_client(), USER_ID, USER_PASSWORD)
  admin_token = _api_token(client, ADMIN_ID, ADMIN_PASSWORD)
  with app.app_context():
    user_id = User.query.filter_by(id_number=USER_ID).first().id

  response = client.patch(f"/api/v1/users/{user_id}", json={"status": "suspended"}, headers=admin_token)

  assert response.status_code == 200
  assert "/auth/login" in user_client.get("/dashboard/profile").location
  assert client.get("/api/v1/me", headers=user_token).status_code == 401


def test_admin_password_reset_revokes_user_sessions(app, client):
  _create_user(app)
  user_client = app.test_client()
  _web_login(user_client, USER_ID, USER_PASSWORD)
  admin_token = _api_token(client, ADMIN_ID, ADMIN_PASSWORD)
  with app.app_context():
    user_id = User.query.filter_by(id_number=USER_ID).first().id

  client.patch(f"/api/v1/users/{user_id}", json={"password": "ResetPass789"}, headers=admin_token)

  assert "/auth/login" in user_client.get("/dashboard/").location


def test_inactive_user_lands_on_profile_instead_of_redirect_loop(app, client):
  _create_user(app, status=UserStatus.INACTIVE)

  response = _web_login(client, USER_ID, USER_PASSWORD)
  response = client.get(response.location, follow_redirects=True)

  assert response.status_code == 200
  assert response.request.path == "/dashboard/profile"


def test_unknown_and_malformed_id_numbers_get_the_same_error(client):
  unknown = client.post("/api/v1/auth/login", json={"id_number": "99999999999", "password": "x"})
  malformed = client.post("/api/v1/auth/login", json={"id_number": "abc", "password": "x"})

  assert unknown.status_code == malformed.status_code == 401
  assert unknown.get_json()["message"] == malformed.get_json()["message"]


def _production_settings(**overrides):
  settings = {
    "SECRET_KEY": STRONG_SECRET,
    "JWT_SECRET_KEY": STRONG_JWT_SECRET,
    "ADMIN_PASSWORD": "A-strong-admin-pass-9",
    "DEBUG": False,
    "SESSION_COOKIE_SECURE": True,
    "RATELIMIT_STORAGE_URI": "redis://localhost:6379",
  }
  settings.update(overrides)
  return settings


@pytest.mark.parametrize("overrides", [
  {"SECRET_KEY": "change-me-to-a-long-random-string-at-least-32-chars"},
  {"SECRET_KEY": "dev-secret-change-in-production"},
  {"SECRET_KEY": "short"},
  {"JWT_SECRET_KEY": STRONG_SECRET},
  {"ADMIN_PASSWORD": "ChangeMeAdmin123!"},
  {"ADMIN_PASSWORD": "short1"},
  {"DEBUG": True},
])
def test_production_config_rejects_insecure_settings(overrides):
  with pytest.raises(ValueError):
    ProductionConfig.validate(_production_settings(**overrides))


def test_production_config_accepts_strong_settings():
  ProductionConfig.validate(_production_settings())


def test_api_per_page_is_capped(client, admin_headers):
  response = client.get("/api/v1/users?per_page=100000", headers=admin_headers)

  assert response.status_code == 200
  assert response.get_json()["per_page"] == 100


def test_untrusted_request_id_is_replaced(client):
  forged = "abc | ERROR | app | admin password reset by attacker"
  response = client.get("/api/v1/health", headers={"X-Request-ID": forged})

  assert response.headers["X-Request-ID"] != forged
  assert re.fullmatch(r"[0-9a-f]{8}", response.headers["X-Request-ID"])


def test_safe_request_id_is_kept(client):
  response = client.get("/api/v1/health", headers={"X-Request-ID": "trace-123"})

  assert response.headers["X-Request-ID"] == "trace-123"


def test_html_pages_send_content_security_policy(client):
  headers = client.get("/auth/login").headers

  assert "script-src 'self'" in headers["Content-Security-Policy"]
  assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
  assert headers["X-Frame-Options"] == "DENY"


def test_logged_in_pages_are_not_cached(client):
  _web_login(client, ADMIN_ID, ADMIN_PASSWORD)

  assert client.get("/admin/").headers["Cache-Control"] == "no-store"


def test_api_docs_can_be_disabled():
  client = _make_app(API_DOCS_ENABLED=False).test_client()

  assert client.get("/api/v1/docs").status_code == 404
  assert client.get("/api/v1/swagger.json").status_code == 404


def test_oversized_upload_is_rejected(client):
  _web_login(client, ADMIN_ID, ADMIN_PASSWORD)
  big_file = io.BytesIO(b"x" * (6 * 1024 * 1024))

  response = client.post(
    "/admin/payments/import",
    data={"file": (big_file, "statement.csv")},
    content_type="multipart/form-data",
  )

  assert response.status_code == 413
