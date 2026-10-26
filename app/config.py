"""Application configuration."""

import logging
import os
from datetime import timedelta

logger = logging.getLogger(__name__)

DEV_SECRET_KEY = "dev-secret-change-in-production"
DEFAULT_ADMIN_PASSWORD = "ChangeMeAdmin123!"
MIN_SECRET_LENGTH = 32
MIN_ADMIN_PASSWORD_LENGTH = 12


def _env_bool(name: str, default: bool) -> bool:
  return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _load_bank_accounts() -> list[dict]:
  accounts = []
  index = 1
  while os.getenv(f"BANK_{index}_IBAN"):
    accounts.append({
      "bank_name": os.getenv(f"BANK_{index}_NAME", ""),
      "iban": os.getenv(f"BANK_{index}_IBAN").replace(" ", "").upper(),
    })
    index += 1
  return accounts


class Config:
  """Base configuration."""

  APP_NAME = os.getenv("APP_NAME", "DXC")
  APP_NAME_FULL = os.getenv("APP_NAME_FULL", "Digital X Control")

  SECRET_KEY = os.getenv("SECRET_KEY", DEV_SECRET_KEY)
  JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
  JWT_ACCESS_TOKEN_EXPIRES = timedelta(
    seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))
  )
  JWT_TOKEN_LOCATION = ("headers",)
  JWT_HEADER_NAME = "Authorization"
  JWT_HEADER_TYPE = "Bearer"

  SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///elevator_chip.db")
  SQLALCHEMY_TRACK_MODIFICATIONS = False
  SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
  }

  RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
  RATELIMIT_DEFAULT = "200 per hour"
  RATELIMIT_HEADERS_ENABLED = True

  SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
  SCHEDULER_TIMEZONE = os.getenv("SCHEDULER_TIMEZONE", "UTC")

  LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
  LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")

  ADMIN_PHONE = os.getenv("ADMIN_PHONE", "+995591000001")
  ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
  ADMIN_ID_NUMBER = os.getenv("ADMIN_ID_NUMBER", "01011000001")

  DEFAULT_PHONE_REGION = os.getenv("DEFAULT_PHONE_REGION", "GE")

  COMPANY = {
    "name": os.getenv("COMPANY_NAME", APP_NAME_FULL),
    "legal_name": os.getenv("COMPANY_LEGAL_NAME", ""),
    "tax_id": os.getenv("COMPANY_TAX_ID", ""),
    "phone": os.getenv("COMPANY_PHONE", ""),
    "email": os.getenv("COMPANY_EMAIL", ""),
    "address": {
      "en": os.getenv("COMPANY_ADDRESS_EN", ""),
      "ka": os.getenv("COMPANY_ADDRESS_KA", ""),
    },
    "hours": {
      "en": os.getenv("COMPANY_HOURS_EN", ""),
      "ka": os.getenv("COMPANY_HOURS_KA", ""),
    },
    "map_url": os.getenv("COMPANY_MAP_URL", ""),
    "facebook_url": os.getenv("COMPANY_FACEBOOK_URL", ""),
    "instagram_url": os.getenv("COMPANY_INSTAGRAM_URL", ""),
  }

  BANK_RECIPIENT_NAME = os.getenv("BANK_RECIPIENT_NAME", COMPANY["legal_name"])
  BANK_ACCOUNTS = _load_bank_accounts()

  MAIL_SERVER = os.getenv("MAIL_SERVER", "")
  MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
  MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
  MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
  MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
  MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "") or MAIL_USERNAME
  CONTACT_NOTIFY_EMAIL = os.getenv("CONTACT_NOTIFY_EMAIL", "")
  MAIL_TIMEOUT_SECONDS = 15

  DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "ka")

  # Successful submissions per IP, plus a looser cap on all attempts (including invalid ones).
  CONTACT_RATE_LIMIT = os.getenv("CONTACT_RATE_LIMIT", "5 per hour")
  CONTACT_ATTEMPT_RATE_LIMIT = os.getenv("CONTACT_ATTEMPT_RATE_LIMIT", "30 per hour")

  PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
  SESSION_COOKIE_HTTPONLY = True
  SESSION_COOKIE_SAMESITE = "Lax"
  SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)

  # Tokens are bound to the session, so they live as long as the login does.
  WTF_CSRF_TIME_LIMIT = None

  MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", 5)) * 1024 * 1024
  API_MAX_PER_PAGE = 100
  API_DOCS_ENABLED = _env_bool("API_DOCS_ENABLED", True)

  # Number of reverse proxies (nginx etc.) in front of the app; needed for real client IPs.
  PROXY_FIX_X_FOR = int(os.getenv("PROXY_FIX_X_FOR", 0))

  LOGIN_RATE_LIMIT_PER_IP = os.getenv("LOGIN_RATE_LIMIT_PER_IP", "20 per minute")
  LOGIN_RATE_LIMIT_PER_ACCOUNT = os.getenv("LOGIN_RATE_LIMIT_PER_ACCOUNT", "5 per 15 minutes")

  # Apply pending migrations on startup; production must run `flask db upgrade` explicitly.
  AUTO_MIGRATE = _env_bool("AUTO_MIGRATE", True)

  RESTX_MASK_SWAGGER = False
  PROPAGATE_EXCEPTIONS = False


class DevelopmentConfig(Config):
  DEBUG = _env_bool("FLASK_DEBUG", False)


class ProductionConfig(Config):
  DEBUG = False
  AUTO_MIGRATE = _env_bool("AUTO_MIGRATE", False)
  SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", True)
  API_DOCS_ENABLED = _env_bool("API_DOCS_ENABLED", False)

  @staticmethod
  def validate(config) -> None:
    """Refuse to start production with missing, weak, or published secrets."""
    problems = []
    for key in ("SECRET_KEY", "JWT_SECRET_KEY"):
      value = config.get(key) or ""
      if (
        len(value) < MIN_SECRET_LENGTH
        or value == DEV_SECRET_KEY
        or "change-me" in value.lower()
      ):
        problems.append(f"{key} must be a random value of at least {MIN_SECRET_LENGTH} characters")
    if config.get("SECRET_KEY") == config.get("JWT_SECRET_KEY"):
      problems.append("JWT_SECRET_KEY must differ from SECRET_KEY")

    admin_password = config.get("ADMIN_PASSWORD") or ""
    if admin_password == DEFAULT_ADMIN_PASSWORD or len(admin_password) < MIN_ADMIN_PASSWORD_LENGTH:
      problems.append(
        f"ADMIN_PASSWORD must be changed and be at least {MIN_ADMIN_PASSWORD_LENGTH} characters"
      )

    if config.get("DEBUG"):
      problems.append("DEBUG must be off in production")

    if problems:
      raise ValueError("Insecure production configuration: " + "; ".join(problems))

    if not config.get("SESSION_COOKIE_SECURE"):
      logger.warning("SESSION_COOKIE_SECURE is off; session cookies can leak over plain HTTP")
    if str(config.get("RATELIMIT_STORAGE_URI", "")).startswith("memory://"):
      logger.warning("Rate limits use in-memory storage; use Redis when running multiple workers")


class TestingConfig(Config):
  TESTING = True
  SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
  SCHEDULER_ENABLED = False
  RATELIMIT_ENABLED = False
  WTF_CSRF_ENABLED = False
  DEFAULT_LANGUAGE = "en"
  MAIL_SERVER = ""
  MAIL_USERNAME = ""
  CONTACT_NOTIFY_EMAIL = ""
  ADMIN_PHONE = "+995591000001"
  ADMIN_PASSWORD = "TestAdmin123!"
  ADMIN_ID_NUMBER = "01011000001"


config_by_name = {
  "development": DevelopmentConfig,
  "production": ProductionConfig,
  "testing": TestingConfig,
}
