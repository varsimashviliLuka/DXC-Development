"""Application configuration."""

import os
from datetime import timedelta


class Config:
  """Base configuration."""

  SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
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
  ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ChangeMeAdmin123!")
  ADMIN_ID_NUMBER = os.getenv("ADMIN_ID_NUMBER", "ADMIN0001")

  DEFAULT_PHONE_REGION = os.getenv("DEFAULT_PHONE_REGION", "GE")

  PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
  SESSION_COOKIE_HTTPONLY = True
  SESSION_COOKIE_SAMESITE = "Lax"

  RESTX_MASK_SWAGGER = False
  PROPAGATE_EXCEPTIONS = False


class DevelopmentConfig(Config):
  DEBUG = True


class ProductionConfig(Config):
  DEBUG = False

  @classmethod
  def validate(cls):
    if cls.SECRET_KEY == "dev-secret-change-in-production":
      raise ValueError("SECRET_KEY must be set in production")
    if cls.JWT_SECRET_KEY == cls.SECRET_KEY and "change-me" in cls.SECRET_KEY.lower():
      raise ValueError("JWT_SECRET_KEY must be set in production")


class TestingConfig(Config):
  TESTING = True
  SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
  SCHEDULER_ENABLED = False
  RATELIMIT_ENABLED = False
  ADMIN_PHONE = "+995591000001"
  ADMIN_PASSWORD = "TestAdmin123!"
  ADMIN_ID_NUMBER = "ADMIN0001"


config_by_name = {
  "development": DevelopmentConfig,
  "production": ProductionConfig,
  "testing": TestingConfig,
}
