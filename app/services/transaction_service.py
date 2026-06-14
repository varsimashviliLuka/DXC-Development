"""Transaction and payment import service."""

import logging
import uuid
from decimal import Decimal

from app.enums import TransactionStatus, TransactionType
from app.extensions import db
from app.models import Transaction, User
from app.services.bank_import_service import BankImportService
from app.utils.errors import AppError

logger = logging.getLogger(__name__)


class TransactionService:
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
