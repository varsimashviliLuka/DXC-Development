"""Transaction and payment import service."""

import logging
import uuid
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import false
from sqlalchemy.orm import joinedload

from app.enums import TransactionStatus, TransactionType
from app.extensions import db
from app.models import Building, Subscription, Transaction, User, UserPhone
from app.services.bank_import_service import BankImportService
from app.utils.errors import AppError
from app.utils.search import filter_by_terms, search_terms, user_search_exprs

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_CREDIT_DESCRIPTION = "Admin balance credit"
DEFAULT_ADMIN_DEBIT_DESCRIPTION = "Admin balance debit"


class TransactionService:
  @staticmethod
  def _subscription_ids_for_payment_reference(reference: str) -> list[int]:
    ref = (reference or "").strip()
    if not ref:
      return []
    matches: list[int] = []
    for sub in Subscription.query.join(Building).all():
      pr = sub.payment_reference
      if pr and ref in pr:
        matches.append(sub.id)
    return matches

  @staticmethod
  def _admin_transactions_query(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    phone_number: str | None = None,
    id_number: str | None = None,
    transaction_reference: str | None = None,
    subscription_payment_reference: str | None = None,
    transaction_type: str | None = None,
    status: str | None = None,
    free_text: str | None = None,
  ):
    query = (
      Transaction.query.options(
        joinedload(Transaction.user),
        joinedload(Transaction.subscription).joinedload(Subscription.building),
      )
      .order_by(Transaction.created_at.desc())
    )

    if date_from:
      try:
        d = datetime.strptime(date_from, "%Y-%m-%d").date()
        start_dt = datetime.combine(d, time.min).replace(tzinfo=timezone.utc)
        query = query.filter(Transaction.created_at >= start_dt)
      except ValueError:
        pass

    if date_to:
      try:
        d = datetime.strptime(date_to, "%Y-%m-%d").date()
        end_dt = (
          datetime.combine(d + timedelta(days=1), time.min)
          .replace(tzinfo=timezone.utc)
        )
        query = query.filter(Transaction.created_at < end_dt)
      except ValueError:
        pass

    if phone_number and phone_number.strip():
      pattern = f"%{phone_number.strip()}%"
      query = (
        query.join(User)
        .outerjoin(UserPhone)
        .filter(UserPhone.phone_number.ilike(pattern))
        .distinct()
      )

    if id_number and id_number.strip():
      pattern = f"%{id_number.strip()}%"
      if "users" not in str(query):
        query = query.join(User)
      query = query.filter(User.id_number.ilike(pattern))

    if transaction_reference and transaction_reference.strip():
      pattern = f"%{transaction_reference.strip()}%"
      query = query.filter(Transaction.reference.ilike(pattern))

    if transaction_type and transaction_type.strip():
      try:
        query = query.filter(Transaction.transaction_type == TransactionType(transaction_type))
      except Exception:
        pass

    if status and status.strip():
      try:
        query = query.filter(Transaction.status == TransactionStatus(status))
      except Exception:
        pass

    if free_text and free_text.strip():
      terms = search_terms(free_text)
      query = query.join(User).outerjoin(UserPhone)
      query = filter_by_terms(
        query,
        terms,
        Transaction.reference,
        Transaction.description,
        *user_search_exprs(),
      ).distinct()

    if subscription_payment_reference and subscription_payment_reference.strip():
      sub_ids = TransactionService._subscription_ids_for_payment_reference(
        subscription_payment_reference
      )
      if sub_ids:
        query = query.filter(Transaction.subscription_id.in_(sub_ids))
      else:
        query = query.filter(false())

    return query

  @staticmethod
  def list_admin(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    phone_number: str | None = None,
    id_number: str | None = None,
    transaction_reference: str | None = None,
    subscription_payment_reference: str | None = None,
    transaction_type: str | None = None,
    status: str | None = None,
    free_text: str | None = None,
    page: int = 1,
    per_page: int = 20,
  ):
    """Admin-only paginated transaction search."""
    query = TransactionService._admin_transactions_query(
      date_from=date_from,
      date_to=date_to,
      phone_number=phone_number,
      id_number=id_number,
      transaction_reference=transaction_reference,
      subscription_payment_reference=subscription_payment_reference,
      transaction_type=transaction_type,
      status=status,
      free_text=free_text,
    )
    return query.paginate(page=page, per_page=per_page, error_out=False)

  @staticmethod
  def get_bank_import_details(transaction_id: int) -> dict | None:
    txn = (
      Transaction.query.options(
        joinedload(Transaction.user),
        joinedload(Transaction.subscription).joinedload(Subscription.building),
        joinedload(Transaction.bank_import),
      )
      .filter_by(id=transaction_id)
      .first()
    )
    if not txn or not txn.bank_import:
      return None

    b = txn.bank_import
    user = txn.user
    sub = txn.subscription
    user_name = " ".join(filter(None, [user.first_name, user.last_name])).strip() if user else ""

    return {
      "transaction_id": txn.id,
      "amount": float(txn.amount),
      "transaction_type": txn.transaction_type.value,
      "reference": txn.reference,
      "user_name": user_name or None,
      "user_id_number": user.id_number if user else None,
      "created_at": txn.created_at.isoformat() if txn.created_at else None,
      "bank": {
        "bank_transaction_id": b.bank_transaction_id,
        "import_batch_id": b.import_batch_id,
        "transaction_date": (
          b.transaction_date.isoformat() if b.transaction_date else None
        ),
        "amount": float(b.amount),
        "currency": b.currency,
        "bank_transaction_type": b.bank_transaction_type,
        "document_number": b.document_number,
        "description": b.description,
        "additional_information": b.additional_information,
        "additional_description": b.additional_description,
        "partner_name": b.partner_name,
        "partner_name_raw": b.partner_name_raw,
        "partner_first_name": b.partner_first_name,
        "partner_last_name": b.partner_last_name,
        "partner_tax_code": b.partner_tax_code,
        "partner_account": b.partner_account,
        "match_status": b.match_status.value,
        "match_method": b.match_method.value if b.match_method else None,
        "match_hint": b.match_hint,
        "skip_reason": b.skip_reason,
      },
      "subscription": (
        {
          "payment_reference": sub.payment_reference,
          "door_number": sub.door_number,
        }
        if sub
        else None
      ),
    }

  @staticmethod
  def record_payment(
    *,
    user: User,
    amount: Decimal,
    reference: str | None = None,
    description: str | None = None,
  ) -> Transaction:
    if amount <= 0:
      raise ValueError("Payment amount must be positive")

    if reference and Transaction.query.filter_by(reference=reference).first():
      raise AppError(f"Transaction reference already exists: {reference}", 409)

    user.balance += amount
    txn = Transaction(
      user_id=user.id,
      amount=amount,
      transaction_type=TransactionType.PAYMENT,
      status=TransactionStatus.COMPLETED,
      description=description or "Payment received",
      reference=reference or f"PAY-{uuid.uuid4().hex[:12].upper()}",
    )
    db.session.add(txn)

    from app.services.subscription_service import SubscriptionService

    SubscriptionService.reconcile_after_balance_change(user)
    db.session.commit()
    logger.info(
      "Recorded payment user_id=%s amount=%s reference=%s",
      user.id,
      amount,
      txn.reference,
    )
    return txn

  @staticmethod
  def record_admin_adjustment(
    *,
    user: User,
    amount: Decimal,
    direction: str,
    description: str | None = None,
  ) -> Transaction:
    if amount <= 0:
      raise ValueError("Amount must be positive")

    direction = (direction or "").strip().lower()
    if direction not in {"add", "subtract"}:
      raise ValueError("Direction must be add or subtract")

    if direction == "add":
      signed_amount = amount
      user.balance += amount
      txn_description = (description or "").strip() or DEFAULT_ADMIN_CREDIT_DESCRIPTION
    else:
      signed_amount = -amount
      user.balance -= amount
      txn_description = (description or "").strip() or DEFAULT_ADMIN_DEBIT_DESCRIPTION

    txn = Transaction(
      user_id=user.id,
      amount=signed_amount,
      transaction_type=TransactionType.ADJUSTMENT,
      status=TransactionStatus.COMPLETED,
      description=txn_description,
      reference=f"ADJ-{uuid.uuid4().hex[:12].upper()}",
    )
    db.session.add(txn)

    from app.services.subscription_service import SubscriptionService

    SubscriptionService.reconcile_after_balance_change(user)
    db.session.commit()
    logger.info(
      "Admin balance adjustment user_id=%s direction=%s amount=%s reference=%s",
      user.id,
      direction,
      amount,
      txn.reference,
    )
    return txn

  @staticmethod
  def import_payments_from_csv(file_stream) -> dict:
    """Import Georgian bank statement CSV (TBC/BoG export format)."""
    return BankImportService.import_bank_csv(file_stream)

  @staticmethod
  def list_for_user(user_id: int, limit: int = 50):
    return (
      Transaction.query.filter_by(user_id=user_id)
      .order_by(Transaction.created_at.desc())
      .limit(limit)
      .all()
    )

  @staticmethod
  def list_for_user_paginated(user_id: int, page: int = 1, per_page: int = 20):
    return (
      Transaction.query.filter_by(user_id=user_id)
      .order_by(Transaction.created_at.desc())
      .paginate(page=page, per_page=per_page, error_out=False)
    )
