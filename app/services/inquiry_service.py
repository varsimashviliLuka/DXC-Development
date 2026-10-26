"""Contact-form inquiries: validation, storage, admin workflow, and email notification."""

import logging

from flask import current_app, url_for

from app.enums import InquiryStatus
from app.extensions import db
from app.models import Inquiry, utcnow
from app.services.mail_service import MailService
from app.translations import SERVICE_KEYS
from app.utils.errors import NotFoundError
from app.utils.search import filter_by_terms, search_terms
from app.utils.validators import ValidationError, normalize_phone, validate_email

logger = logging.getLogger(__name__)

INQUIRY_SERVICES = (*SERVICE_KEYS, "other")
NAME_MAX_LENGTH = 100
MESSAGE_MIN_LENGTH = 10
MESSAGE_MAX_LENGTH = 2000


class InquiryValidationError(Exception):
  def __init__(self, errors: dict[str, str]):
    super().__init__("Invalid inquiry")
    self.errors = errors


class InquiryService:
  @staticmethod
  def validate(form) -> dict:
    """Return cleaned fields, or raise InquiryValidationError mapping field -> translation key."""
    errors = {}
    cleaned = {}

    name = " ".join((form.get("name") or "").split())
    if not 2 <= len(name) <= NAME_MAX_LENGTH:
      errors["name"] = "contact.error.name"
    cleaned["name"] = name

    try:
      cleaned["phone"] = normalize_phone(form.get("phone") or "")
    except ValidationError:
      errors["phone"] = "contact.error.phone"

    try:
      cleaned["email"] = validate_email(form.get("email"))
    except ValidationError:
      errors["email"] = "contact.error.email"

    service = form.get("service") or ""
    if service not in INQUIRY_SERVICES:
      errors["service"] = "contact.error.service"
    cleaned["service"] = service

    message = (form.get("message") or "").strip()
    if not MESSAGE_MIN_LENGTH <= len(message) <= MESSAGE_MAX_LENGTH:
      errors["message"] = "contact.error.message"
    cleaned["message"] = message

    if errors:
      raise InquiryValidationError(errors)
    return cleaned

  @staticmethod
  def create(form, *, language: str, ip_address: str | None) -> Inquiry:
    fields = InquiryService.validate(form)
    inquiry = Inquiry(**fields, language=language, ip_address=ip_address)
    db.session.add(inquiry)
    db.session.commit()
    logger.info("New inquiry_id=%s service=%s", inquiry.id, inquiry.service)
    InquiryService.notify_admins(inquiry)
    return inquiry

  @staticmethod
  def notify_admins(inquiry: Inquiry):
    app = current_app._get_current_object()
    if not MailService.is_configured(app.config):
      logger.info("Email not configured; inquiry_id=%s saved without notification", inquiry.id)
      return None

    message = MailService.build_message(
      app.config,
      to=app.config["CONTACT_NOTIFY_EMAIL"],
      subject=f"New inquiry #{inquiry.id}: {inquiry.name}",
      reply_to=inquiry.email,
      body=InquiryService._notification_body(inquiry),
    )
    inquiry_id = inquiry.id

    def mark_notified():
      record = db.session.get(Inquiry, inquiry_id)
      if record:
        record.notified_at = utcnow()
        db.session.commit()

    return MailService.send_in_background(app, message, on_sent=mark_notified)

  @staticmethod
  def _notification_body(inquiry: Inquiry) -> str:
    admin_url = url_for("admin.inquiry_detail", inquiry_id=inquiry.id, _external=True)
    return "\n".join([
      f"Name: {inquiry.name}",
      f"Phone: {inquiry.phone}",
      f"Email: {inquiry.email or '-'}",
      f"Service: {inquiry.service}",
      f"Language: {inquiry.language}",
      "",
      inquiry.message,
      "",
      f"Open in admin: {admin_url}",
    ])

  @staticmethod
  def get_by_id(inquiry_id: int) -> Inquiry:
    inquiry = db.session.get(Inquiry, inquiry_id)
    if not inquiry:
      raise NotFoundError("Inquiry not found")
    return inquiry

  @staticmethod
  def list_inquiries(*, status: InquiryStatus | None = None, search: str | None = None,
                     page: int = 1, per_page: int = 20):
    query = Inquiry.query
    if status:
      query = query.filter(Inquiry.status == status)
    terms = search_terms(search)
    if terms:
      query = filter_by_terms(query, terms, Inquiry.name, Inquiry.phone, Inquiry.email, Inquiry.message)
    return query.order_by(Inquiry.created_at.desc(), Inquiry.id.desc()).paginate(
      page=page,
      per_page=per_page,
      error_out=False,
    )

  @staticmethod
  def count_new() -> int:
    return Inquiry.query.filter_by(status=InquiryStatus.NEW).count()

  @staticmethod
  def update(inquiry_id: int, *, status: InquiryStatus, admin_note: str | None) -> Inquiry:
    inquiry = InquiryService.get_by_id(inquiry_id)
    inquiry.status = status
    inquiry.admin_note = (admin_note or "").strip() or None
    db.session.commit()
    logger.info("Updated inquiry_id=%s status=%s", inquiry.id, status.value)
    return inquiry
