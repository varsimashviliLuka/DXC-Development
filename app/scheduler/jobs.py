"""APScheduler background jobs."""

import logging

from app.extensions import db

logger = logging.getLogger(__name__)


def process_due_subscription_payments_job(app):
  """Charge users for subscriptions due today and mark overdue if balance is negative."""
  with app.app_context():
    from app.services.subscription_service import SubscriptionService

    try:
      result = SubscriptionService.process_due_payments()
      logger.info("Scheduler: payment processing completed %s", result)
    except Exception:
      db.session.rollback()
      logger.exception("Scheduler: payment processing failed")


def heartbeat_job(app):
  """Lightweight heartbeat to confirm the scheduler is running."""
  with app.app_context():
    logger.debug("Scheduler heartbeat OK")
