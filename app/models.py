"""SQLAlchemy models."""

from datetime import datetime, timezone

from app.enums import (
  ChipStatus,
  ImportMatchStatus,
  PaymentMatchMethod,
  SubscriptionStatus,
  TransactionStatus,
  TransactionType,
  UserRole,
  UserStatus,
)
from app.extensions import db


def utcnow():
  return datetime.now(timezone.utc)


class TimestampMixin:
  created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
  updated_at = db.Column(
    db.DateTime(timezone=True),
    default=utcnow,
    onupdate=utcnow,
    nullable=False,
  )


class User(TimestampMixin, db.Model):
  __tablename__ = "users"

  id = db.Column(db.Integer, primary_key=True)
  id_number = db.Column(db.String(11), unique=True, nullable=False, index=True)
  email = db.Column(db.String(255), unique=True, nullable=True, index=True)
  password_hash = db.Column(db.String(255), nullable=False)
  role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.USER)
  status = db.Column(db.Enum(UserStatus), nullable=False, default=UserStatus.ACTIVE)
  balance = db.Column(db.Numeric(12, 2), nullable=False, default=0)
  first_name = db.Column(db.String(100))
  last_name = db.Column(db.String(100))
  admin_comment = db.Column(db.Text, nullable=True)

  phones = db.relationship(
    "UserPhone",
    back_populates="user",
    lazy="dynamic",
    cascade="all, delete-orphan",
    order_by="UserPhone.is_primary.desc(), UserPhone.id",
  )
  subscriptions = db.relationship(
    "Subscription",
    back_populates="user",
    lazy="dynamic",
    cascade="all, delete-orphan",
  )
  chips = db.relationship(
    "Chip",
    back_populates="user",
    lazy="dynamic",
    cascade="all, delete-orphan",
  )
  transactions = db.relationship(
    "Transaction",
    back_populates="user",
    lazy="dynamic",
    foreign_keys="Transaction.user_id",
  )

  def is_admin(self):
    return self.role == UserRole.ADMIN

  @property
  def primary_phone(self) -> str | None:
    primary = self.phones.filter_by(is_primary=True).first()
    if primary:
      return primary.phone_number
    first = self.phones.first()
    return first.phone_number if first else None

  @property
  def display_name(self) -> str:
    name = " ".join(filter(None, [self.first_name, self.last_name])).strip()
    return name or self.id_number

  def to_dict(self, include_sensitive=False, include_admin=False):
    phone_list = [
      p.to_dict(include_label=include_admin)
      for p in self.phones.all()
    ]
    data = {
      "id": self.id,
      "id_number": self.id_number,
      "primary_phone": self.primary_phone,
      "phones": phone_list,
      "email": self.email,
      "role": self.role.value,
      "status": self.status.value,
      "balance": float(self.balance),
      "first_name": self.first_name,
      "last_name": self.last_name,
      "created_at": self.created_at.isoformat() if self.created_at else None,
      "updated_at": self.updated_at.isoformat() if self.updated_at else None,
    }
    # Backward compatibility for clients expecting phone_number
    data["phone_number"] = self.primary_phone
    if include_admin:
      data["admin_comment"] = self.admin_comment
    return data


class UserPhone(TimestampMixin, db.Model):
  """Phone numbers linked to a user (personal, family, etc.)."""

  __tablename__ = "user_phones"

  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
  phone_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
  label = db.Column(db.String(100), nullable=True)
  is_primary = db.Column(db.Boolean, nullable=False, default=False)

  user = db.relationship("User", back_populates="phones")

  def to_dict(self, include_label=False):
    data = {
      "id": self.id,
      "phone_number": self.phone_number,
      "is_primary": self.is_primary,
      "created_at": self.created_at.isoformat() if self.created_at else None,
    }
    if include_label:
      data["label"] = self.label
    return data


class Building(TimestampMixin, db.Model):
  __tablename__ = "buildings"

  id = db.Column(db.Integer, primary_key=True)
  building_number = db.Column(db.String(50), nullable=False, index=True)
  name = db.Column(db.String(200), nullable=False)
  address = db.Column(db.String(500))
  admin_comment = db.Column(db.Text, nullable=True)

  subscriptions = db.relationship(
    "Subscription",
    back_populates="building",
    lazy="dynamic",
  )

  def to_dict(self, include_admin=False):
    data = {
      "id": self.id,
      "building_number": self.building_number,
      "name": self.name,
      "address": self.address,
      "created_at": self.created_at.isoformat() if self.created_at else None,
      "updated_at": self.updated_at.isoformat() if self.updated_at else None,
    }
    if include_admin:
      data["admin_comment"] = self.admin_comment
    return data


class Subscription(TimestampMixin, db.Model):
  """Monthly access fee for a user at a specific door in a building."""

  __tablename__ = "subscriptions"
  __table_args__ = (
    db.UniqueConstraint(
      "building_id",
      "door_number",
      name="uq_subscriptions_building_door",
    ),
  )

  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
  building_id = db.Column(
    db.Integer,
    db.ForeignKey("buildings.id"),
    nullable=False,
    index=True,
  )
  door_number = db.Column(db.String(50), nullable=False)
  monthly_fee = db.Column(db.Numeric(12, 2), nullable=False, default=0)
  status = db.Column(
    db.Enum(SubscriptionStatus),
    nullable=False,
    default=SubscriptionStatus.ACTIVE,
  )
  next_payment_due = db.Column(db.Date, nullable=True)
  admin_comment = db.Column(db.Text, nullable=True)

  user = db.relationship("User", back_populates="subscriptions")
  building = db.relationship("Building", back_populates="subscriptions")
  transactions = db.relationship(
    "Transaction",
    back_populates="subscription",
    lazy="dynamic",
  )

  @property
  def payment_reference(self) -> str | None:
    if not self.building:
      return None
    from app.utils.payment_matching import build_payment_reference

    return build_payment_reference(
      self.building_id,
      self.building.building_number,
      self.door_number,
    )

  def to_dict(self, include_building=False, include_user=False, include_admin=False):
    data = {
      "id": self.id,
      "user_id": self.user_id,
      "building_id": self.building_id,
      "door_number": self.door_number,
      "payment_reference": self.payment_reference,
      "monthly_fee": float(self.monthly_fee),
      "status": self.status.value,
      "next_payment_due": (
        self.next_payment_due.isoformat() if self.next_payment_due else None
      ),
      "created_at": self.created_at.isoformat() if self.created_at else None,
      "updated_at": self.updated_at.isoformat() if self.updated_at else None,
    }
    if include_admin:
      data["admin_comment"] = self.admin_comment
    if include_building and self.building:
      data["building"] = self.building.to_dict(include_admin=include_admin)
    if include_user and self.user:
      data["user"] = self.user.to_dict(include_admin=include_admin)
    return data


class Chip(TimestampMixin, db.Model):
  """Physical chip assigned to a user. Can be activated or deactivated."""

  __tablename__ = "chips"

  id = db.Column(db.Integer, primary_key=True)
  chip_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
  user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
  status = db.Column(db.Enum(ChipStatus), nullable=False, default=ChipStatus.ACTIVE)
  deactivated_at = db.Column(db.DateTime(timezone=True), nullable=True)

  user = db.relationship("User", back_populates="chips")

  def to_dict(self, include_user=False):
    data = {
      "id": self.id,
      "chip_number": self.chip_number,
      "user_id": self.user_id,
      "status": self.status.value,
      "deactivated_at": (
        self.deactivated_at.isoformat() if self.deactivated_at else None
      ),
      "created_at": self.created_at.isoformat() if self.created_at else None,
      "updated_at": self.updated_at.isoformat() if self.updated_at else None,
    }
    if include_user and self.user:
      data["user"] = self.user.to_dict()
    return data


class Transaction(TimestampMixin, db.Model):
  """Payment and fee ledger entry."""

  __tablename__ = "transactions"

  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
  subscription_id = db.Column(
    db.Integer,
    db.ForeignKey("subscriptions.id"),
    nullable=True,
    index=True,
  )
  amount = db.Column(db.Numeric(12, 2), nullable=False)
  transaction_type = db.Column(db.Enum(TransactionType), nullable=False)
  status = db.Column(
    db.Enum(TransactionStatus),
    nullable=False,
    default=TransactionStatus.PENDING,
  )
  description = db.Column(db.String(500))
  reference = db.Column(db.String(100), unique=True, nullable=True)
  bank_import_id = db.Column(
    db.Integer,
    db.ForeignKey("bank_imports.id"),
    nullable=True,
    unique=True,
  )

  user = db.relationship("User", back_populates="transactions", foreign_keys=[user_id])
  subscription = db.relationship("Subscription", back_populates="transactions")
  bank_import = db.relationship("BankImport", back_populates="ledger_transaction")

  def to_dict(self):
    return {
      "id": self.id,
      "user_id": self.user_id,
      "subscription_id": self.subscription_id,
      "amount": float(self.amount),
      "transaction_type": self.transaction_type.value,
      "status": self.status.value,
      "description": self.description,
      "reference": self.reference,
      "bank_import_id": self.bank_import_id,
      "created_at": self.created_at.isoformat() if self.created_at else None,
      "updated_at": self.updated_at.isoformat() if self.updated_at else None,
    }


class BankImport(TimestampMixin, db.Model):
  """Raw bank statement row from CSV import."""

  __tablename__ = "bank_imports"

  id = db.Column(db.Integer, primary_key=True)
  bank_transaction_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
  import_batch_id = db.Column(db.String(36), nullable=False, index=True)
  transaction_date = db.Column(db.Date, nullable=True)
  description = db.Column(db.String(500))
  bank_transaction_type = db.Column(db.String(50))
  amount = db.Column(db.Numeric(12, 2), nullable=False)
  currency = db.Column(db.String(10), default="GEL")
  partner_account = db.Column(db.String(100))
  partner_name_raw = db.Column(db.String(500))
  partner_name = db.Column(db.String(500))
  partner_first_name = db.Column(db.String(100))
  partner_last_name = db.Column(db.String(100))
  partner_tax_code = db.Column(db.String(50), index=True)
  additional_information = db.Column(db.String(500))
  additional_description = db.Column(db.String(500))
  document_date = db.Column(db.Date, nullable=True)
  document_number = db.Column(db.String(100))
  op_code = db.Column(db.String(50))
  match_status = db.Column(
    db.Enum(ImportMatchStatus),
    nullable=False,
    default=ImportMatchStatus.UNMATCHED,
  )
  match_method = db.Column(db.Enum(PaymentMatchMethod), nullable=True)
  match_hint = db.Column(db.String(200))
  user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
  skip_reason = db.Column(db.String(500))

  user = db.relationship("User", foreign_keys=[user_id])
  ledger_transaction = db.relationship(
    "Transaction",
    back_populates="bank_import",
    uselist=False,
  )

  def to_dict(self):
    return {
      "id": self.id,
      "bank_transaction_id": self.bank_transaction_id,
      "transaction_date": (
        self.transaction_date.isoformat() if self.transaction_date else None
      ),
      "description": self.description,
      "bank_transaction_type": self.bank_transaction_type,
      "amount": float(self.amount),
      "currency": self.currency,
      "partner_name": self.partner_name,
      "partner_first_name": self.partner_first_name,
      "partner_last_name": self.partner_last_name,
      "partner_tax_code": self.partner_tax_code,
      "additional_description": self.additional_description,
      "match_status": self.match_status.value,
      "match_method": self.match_method.value if self.match_method else None,
      "match_hint": self.match_hint,
      "user_id": self.user_id,
      "skip_reason": self.skip_reason,
      "created_at": self.created_at.isoformat() if self.created_at else None,
    }
