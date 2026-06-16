"""Transaction and payment import service."""

import logging
import uuid
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import joinedload

from app.enums import TransactionStatus, TransactionType
from app.extensions import db
from app.models import Subscription, Transaction, User
from app.services.bank_import_service import BankImportService
from app.utils.errors import AppError

logger = logging.getLogger(__name__)


class TransactionService:
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
    limit: int = 200,
  ) -> list[Transaction]:
    """
    Admin-only: search across all transactions.

    Notes:
    - filtering by `subscription_payment_reference` is done in Python because it's a computed value.
    """
    query = (
      Transaction.query.options(
        joinedload(Transaction.user),
        joinedload(Transaction.subscription).joinedload(Subscription.building),
        joinedload(Transaction.bank_import),
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
        # exclusive upper bound (end of day)
        end_dt = (
          datetime.combine(d + timedelta(days=1), time.min)
          .replace(tzinfo=timezone.utc)
        )
        query = query.filter(Transaction.created_at < end_dt)
      except ValueError:
        pass

    if phone_number and phone_number.strip():
      pattern = f"%{phone_number.strip()}%"
      query = query.join(User).filter(User.phone_number.ilike(pattern))

    if id_number and id_number.strip():
      pattern = f"%{id_number.strip()}%"
      query = query.join(User).filter(User.id_number.ilike(pattern))

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
      pattern = f"%{free_text.strip()}%"
      query = query.filter(
        db.or_(
          Transaction.reference.ilike(pattern),
          Transaction.description.ilike(pattern),
          User.phone_number.ilike(pattern),
          User.id_number.ilike(pattern),
          # building is included in joinedload; matching is best-effort here
        )
      ).join(User)

    # Pull more than `limit` so we can apply Python-only subscription reference filtering.
    fetch_limit = min(max(limit * 10, limit), 2000)
    txns = query.limit(fetch_limit).all()

    if subscription_payment_reference and subscription_payment_reference.strip():
      ref = subscription_payment_reference.strip()
      if ref:
        filtered: list[Transaction] = []
        for txn in txns:
          sub = txn.subscription
          if not sub or not sub.building:
            continue
          pr = sub.payment_reference
          if pr and ref in pr:
            filtered.append(txn)
        txns = filtered

    return txns[:limit]

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
    db.session.commit()
    logger.info(
      "Recorded payment user_id=%s amount=%s reference=%s",
      user.id,
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
