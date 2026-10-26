"""Outgoing email over SMTP, sent in the background so web requests never wait on the mail server."""

import logging
import smtplib
import ssl
import threading
from email.message import EmailMessage

logger = logging.getLogger(__name__)


class MailService:
  @staticmethod
  def is_configured(config) -> bool:
    return bool(
      config.get("MAIL_SERVER")
      and config.get("MAIL_USERNAME")
      and config.get("MAIL_PASSWORD")
      and config.get("CONTACT_NOTIFY_EMAIL")
    )

  @staticmethod
  def build_message(config, *, to: str, subject: str, body: str, reply_to: str | None = None) -> EmailMessage:
    message = EmailMessage()
    message["From"] = config.get("MAIL_DEFAULT_SENDER") or config["MAIL_USERNAME"]
    message["To"] = to
    # Header values containing line breaks would let user input inject extra headers.
    message["Subject"] = " ".join(subject.split())
    if reply_to:
      message["Reply-To"] = " ".join(reply_to.split())
    message.set_content(body)
    return message

  @staticmethod
  def deliver(config, message: EmailMessage) -> None:
    timeout = config.get("MAIL_TIMEOUT_SECONDS", 15)
    with smtplib.SMTP(config["MAIL_SERVER"], config["MAIL_PORT"], timeout=timeout) as smtp:
      if config.get("MAIL_USE_TLS", True):
        smtp.starttls(context=ssl.create_default_context())
      smtp.login(config["MAIL_USERNAME"], config["MAIL_PASSWORD"])
      smtp.send_message(message)

  @staticmethod
  def send_in_background(app, message: EmailMessage, *, on_sent=None) -> threading.Thread:
    config = dict(app.config)

    def run():
      try:
        MailService.deliver(config, message)
        logger.info("Sent email subject=%r to=%s", message["Subject"], message["To"])
        if on_sent:
          with app.app_context():
            on_sent()
      except Exception:
        logger.exception("Failed to send email subject=%r", message["Subject"])

    thread = threading.Thread(target=run, name="mail-sender", daemon=True)
    thread.start()
    return thread
