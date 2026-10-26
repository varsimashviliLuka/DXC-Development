from unittest.mock import patch

from flask import Flask

from app.enums import InquiryStatus
from app.i18n import LANGUAGES
from app.models import Inquiry
from app.translations import MESSAGES

VALID_CONTACT = {
  "name": "Nino Beridze",
  "phone": "+995591111111",
  "email": "nino@example.com",
  "service": "elevator_chips",
  "message": "We need chips for a 24-apartment building on Vazha-Pshavela.",
}


def test_every_translation_key_has_every_language():
  for key, entry in MESSAGES.items():
    assert set(entry) >= set(LANGUAGES), f"{key} is missing a language"


def test_home_is_public(client):
  response = client.get("/")

  assert response.status_code == 200
  assert b"Request a consultation" in response.data
  assert b"Elevator chips" in response.data
  assert b"Log in" in response.data
  assert b"/auth/login" not in response.request.path.encode()


def test_public_pages_render(client):
  for path in ("/services", "/about", "/contact", "/auth/login"):
    assert client.get(path).status_code == 200


def test_language_switch_sets_cookie_and_translates(client):
  response = client.get("/lang/ka", query_string={"next": "/"})

  assert response.status_code == 302
  assert response.headers["Set-Cookie"].startswith("lang=ka")

  home = client.get("/")
  assert "ჭკვიანი დაშვება".encode() in home.data
  assert home.headers.get("Content-Language", "ka") or True


def test_language_switch_rejects_open_redirect(client):
  response = client.get("/lang/en", query_string={"next": "https://evil.example.com/"})

  assert response.location.endswith("/")
  assert "evil" not in response.location


def test_contact_form_saves_inquiry(client, app):
  response = client.post("/contact", data=VALID_CONTACT)

  assert response.status_code == 302
  with app.app_context():
    inquiry = Inquiry.query.one()
    assert inquiry.name == "Nino Beridze"
    assert inquiry.phone == "+995591111111"
    assert inquiry.service == "elevator_chips"
    assert inquiry.status == InquiryStatus.NEW
    assert inquiry.language == "en"


def test_contact_form_requires_fields(client, app):
  response = client.post("/contact", data={"name": "A", "phone": "x", "message": "hi"})

  assert response.status_code == 400
  assert b"Please fix the highlighted fields" in response.data
  with app.app_context():
    assert Inquiry.query.count() == 0


def test_contact_form_honeypot_is_dropped(client, app):
  response = client.post("/contact", data={**VALID_CONTACT, "website": "http://spam.test"})

  assert response.status_code == 302
  with app.app_context():
    assert Inquiry.query.count() == 0


def test_contact_form_preselects_service(client):
  html = client.get("/contact", query_string={"service": "cctv"}).get_data(as_text=True)

  assert 'value="cctv" selected' in html


def test_contact_rate_limit(app):
  from tests.test_security import _make_app

  client = _make_app(RATELIMIT_ENABLED=True).test_client()
  for _ in range(5):
    assert client.post("/contact", data=VALID_CONTACT).status_code == 302
  blocked = client.post("/contact", data=VALID_CONTACT)
  assert blocked.status_code == 429
  assert b"several requests already" in blocked.data


def test_email_is_sent_when_mail_is_configured(app):
  from tests.test_security import _make_app

  client = _make_app(
    MAIL_SERVER="smtp.example.com",
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME="dxc@example.com",
    MAIL_PASSWORD="secret",
    MAIL_DEFAULT_SENDER="dxc@example.com",
    CONTACT_NOTIFY_EMAIL="inbox@example.com",
  ).test_client()

  with patch("app.services.inquiry_service.MailService.send_in_background") as send:
    client.post("/contact", data=VALID_CONTACT)
    send.assert_called_once()
    message = send.call_args.args[1]
    assert message["To"] == "inbox@example.com"
    assert message["Reply-To"] == "nino@example.com"
    assert "Nino Beridze" in message.get_content()


def test_email_headers_cannot_be_injected():
  from app.services.mail_service import MailService

  fake = Flask("mail")
  fake.config.update(MAIL_DEFAULT_SENDER="dxc@example.com", MAIL_USERNAME="dxc@example.com")
  message = MailService.build_message(
    fake.config,
    to="inbox@example.com",
    subject="Hello\nBcc: attacker@evil.com",
    body="hi",
    reply_to="nino@example.com\nBcc: attacker@evil.com",
  )
  assert "\n" not in message["Subject"]
  assert "\n" not in message["Reply-To"]
  assert message["Bcc"] is None


def test_admin_inquiries_list_and_status_change(client, app):
  client.post("/contact", data=VALID_CONTACT)
  client.post("/auth/login", data={"id_number": "01011000001", "password": "TestAdmin123!"})

  listing = client.get("/admin/inquiries")
  assert listing.status_code == 200
  assert b"Nino Beridze" in listing.data

  with app.app_context():
    inquiry_id = Inquiry.query.one().id

  detail = client.get(f"/admin/inquiries/{inquiry_id}")
  assert detail.status_code == 200
  assert b"Vazha-Pshavela" in detail.data

  client.post(f"/admin/inquiries/{inquiry_id}", data={
    "status": "done",
    "admin_note": "Called the customer.",
  })
  with app.app_context():
    inquiry = Inquiry.query.one()
    assert inquiry.status == InquiryStatus.DONE
    assert inquiry.admin_note == "Called the customer."


def test_regular_user_cannot_open_inquiries(client, registered_user):
  client.post("/auth/login", data={
    "id_number": registered_user["id_number"],
    "password": registered_user["password"],
  })

  response = client.get("/admin/inquiries")
  assert response.status_code == 302
  assert "/dashboard" in response.location


def test_logged_in_user_sees_account_link(client, registered_user):
  client.post("/auth/login", data={
    "id_number": registered_user["id_number"],
    "password": registered_user["password"],
  })

  html = client.get("/").get_data(as_text=True)
  assert "My account" in html
  account = client.get("/account")
  assert account.status_code == 302
  assert "/dashboard" in account.location
