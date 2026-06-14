"""Shared enumerations."""

import enum


class UserRole(str, enum.Enum):
  ADMIN = "admin"
  USER = "user"


class UserStatus(str, enum.Enum):
  ACTIVE = "active"
  INACTIVE = "inactive"
  SUSPENDED = "suspended"


class SubscriptionStatus(str, enum.Enum):
  ACTIVE = "active"
  INACTIVE = "inactive"
  OVERDUE = "overdue"
  SUSPENDED = "suspended"


class TransactionType(str, enum.Enum):
  PAYMENT = "payment"
  FEE = "fee"
  ADJUSTMENT = "adjustment"
  REFUND = "refund"


class TransactionStatus(str, enum.Enum):
  PENDING = "pending"
  COMPLETED = "completed"
  FAILED = "failed"
  CANCELLED = "cancelled"


class ChipStatus(str, enum.Enum):
  ACTIVE = "active"
  INACTIVE = "inactive"


class ImportMatchStatus(str, enum.Enum):
  MATCHED = "matched"
  UNMATCHED = "unmatched"
  SKIPPED = "skipped"
  DUPLICATE = "duplicate"


class PaymentMatchMethod(str, enum.Enum):
  UID_TOKEN = "uid_token"
  PARTNER_TAX_CODE = "partner_tax_code"
  PARTNER_NAME_ID = "partner_name_id"
  MANUAL = "manual"
