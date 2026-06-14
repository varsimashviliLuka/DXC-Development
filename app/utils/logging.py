"""Structured logging setup for production use."""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging(app):
  """Configure application-wide logging with console and rotating file handlers."""
  log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
  log_format = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(request_id)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
  )

  class RequestIdFilter(logging.Filter):
    def filter(self, record):
      try:
        from flask import g, has_request_context

        record.request_id = g.request_id if has_request_context() else "-"
      except RuntimeError:
        record.request_id = "-"
      return True

  root_logger = logging.getLogger()
  root_logger.setLevel(log_level)

  for handler in list(root_logger.handlers):
    root_logger.removeHandler(handler)

  console_handler = logging.StreamHandler()
  console_handler.setLevel(log_level)
  console_handler.setFormatter(log_format)
  console_handler.addFilter(RequestIdFilter())
  root_logger.addHandler(console_handler)

  log_file = app.config.get("LOG_FILE")
  if log_file and not app.config.get("TESTING"):
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
    file_handler = RotatingFileHandler(
      log_file,
      maxBytes=10 * 1024 * 1024,
      backupCount=10,
      encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(log_format)
    file_handler.addFilter(RequestIdFilter())
    root_logger.addHandler(file_handler)

  logging.getLogger("werkzeug").setLevel(logging.WARNING)
  app.logger.info("Logging configured at level %s", logging.getLevelName(log_level))
