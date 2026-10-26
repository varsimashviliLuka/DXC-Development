"""APScheduler integration."""

import logging
import os
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

try:
  import fcntl
except ImportError:  # Windows
  fcntl = None

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

# Held open for the life of the process; the OS releases the lock if the process dies.
_lock_file = None

STARTUP_CATCH_UP_DELAY = timedelta(seconds=30)


def _acquire_scheduler_lock(app) -> bool:
  """Allow only one process per machine (gunicorn workers, debug reloader) to run jobs."""
  global _lock_file
  if fcntl is None:
    logger.warning("File locking unavailable; make sure only one process runs the scheduler")
    return True

  os.makedirs(app.instance_path, exist_ok=True)
  handle = open(os.path.join(app.instance_path, "scheduler.lock"), "w")
  try:
    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
  except OSError:
    handle.close()
    return False
  _lock_file = handle
  return True


def init_scheduler(app):
  if not app.config.get("SCHEDULER_ENABLED", True):
    logger.info("Scheduler disabled by configuration")
    return scheduler

  if scheduler.running:
    return scheduler

  if not _acquire_scheduler_lock(app):
    logger.info("Scheduler already running in another process (pid %s skips it)", os.getpid())
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
    coalesce=True,
    # Also run shortly after startup to catch up periods missed while the server was down.
    next_run_time=datetime.now(scheduler.timezone) + STARTUP_CATCH_UP_DELAY,
  )
  scheduler.add_job(
    func=lambda: heartbeat_job(app),
    trigger="interval",
    minutes=30,
    id="scheduler_heartbeat",
    replace_existing=True,
  )

  scheduler.start()
  logger.info("Background scheduler started in pid %s", os.getpid())
  return scheduler


def shutdown_scheduler():
  if scheduler.running:
    scheduler.shutdown(wait=False)
    logger.info("Background scheduler stopped")
