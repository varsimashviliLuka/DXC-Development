"""APScheduler integration."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def init_scheduler(app):
  if not app.config.get("SCHEDULER_ENABLED", True):
    logger.info("Scheduler disabled by configuration")
    return scheduler

  if scheduler.running:
    return scheduler

  from app.scheduler.jobs import heartbeat_job, process_due_subscription_payments_job

  scheduler.configure(timezone=app.config.get("SCHEDULER_TIMEZONE", "UTC"))

  scheduler.add_job(
    func=lambda: process_due_subscription_payments_job(app),
    trigger="cron",
    hour=2,
    minute=0,
    id="process_due_subscription_payments",
    replace_existing=True,
  )
  scheduler.add_job(
    func=lambda: heartbeat_job(app),
    trigger="interval",
    minutes=30,
    id="scheduler_heartbeat",
    replace_existing=True,
  )

  scheduler.start()
  logger.info("Background scheduler started")
  return scheduler


def shutdown_scheduler():
  if scheduler.running:
    scheduler.shutdown(wait=False)
    logger.info("Background scheduler stopped")
