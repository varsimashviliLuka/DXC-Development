"""Subscription management service."""

import logging
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from app.enums import SubscriptionStatus, TransactionStatus, TransactionType
from app.extensions import db
from app.models import Building, Subscription, Transaction, User
from app.services.building_service import BuildingService
from app.services.user_service import UserService
from app.utils.errors import ConflictError, NotFoundError
from app.utils.validators import validate_door_number

logger = logging.getLogger(__name__)


class SubscriptionService:
  @staticmethod
  def create(
    *,
    user_id: int,
    building_id: int,
    door_number: str,
    monthly_fee: Decimal,
    next_payment_due: date | None = None,
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
  ) -> Subscription:
    user = UserService.get_by_id(user_id)
    building = BuildingService.get_by_id(building_id)
    door = validate_door_number(door_number)

    existing_door = Subscription.query.filter_by(
      building_id=building.id,
      door_number=door,
    ).first()
    if existing_door:
      raise ConflictError("Door number already assigned in this building")

    if monthly_fee < 0:
      raise ValueError("Monthly fee cannot be negative")

    due_date = next_payment_due or (date.today() + relativedelta(months=1))

    subscription = Subscription(
      user_id=user.id,
      building_id=building.id,
      door_number=door,
      monthly_fee=monthly_fee,
      status=status,
      next_payment_due=due_date,
    )
    db.session.add(subscription)
    db.session.commit()
    logger.info(
      "Created subscription_id=%s user_id=%s building_id=%s door=%s",
      subscription.id,
      user.id,
      building.id,
      door,
    )
    return subscription

  @staticmethod
  def get_by_id(subscription_id: int) -> Subscription:
    subscription = db.session.get(Subscription, subscription_id)
    if not subscription:
      raise NotFoundError("Subscription not found")
    return subscription

  @staticmethod
  def list_for_user(user_id: int):
    return (
      Subscription.query.filter_by(user_id=user_id)
      .order_by(Subscription.id)
      .all()
    )

  @staticmethod
  def _subscriptions_query(search: str | None = None):
    query = Subscription.query.join(User).join(Building)
    q = (search or "").strip()
    if q:
      pattern = f"%{q}%"
      query = query.filter(
        db.or_(
          Subscription.door_number.ilike(pattern),
          User.phone_number.ilike(pattern),
          User.id_number.ilike(pattern),
          Building.building_number.ilike(pattern),
          Building.name.ilike(pattern),
        )
      )
    return query.order_by(Subscription.id)

  @staticmethod
  def list_all(page: int = 1, per_page: int = 20, search: str | None = None):
    return SubscriptionService._subscriptions_query(search).paginate(
      page=page,
      per_page=per_page,
      error_out=False,
    )

  @staticmethod
  def update_status(subscription_id: int, status: SubscriptionStatus) -> Subscription:
    subscription = SubscriptionService.get_by_id(subscription_id)
    subscription.status = status
    db.session.commit()
    logger.info("Updated subscription_id=%s status=%s", subscription_id, status.value)
    return subscription

  @staticmethod
  def process_due_payments(for_date: date | None = None) -> dict:
    """Charge users for subscriptions due on the given date."""
    today = for_date or date.today()
    due_subs = Subscription.query.filter(
      Subscription.next_payment_due == today,
      Subscription.status.in_(
        [SubscriptionStatus.ACTIVE, SubscriptionStatus.OVERDUE]
      ),
    ).all()

    processed = 0
    marked_overdue = 0

    for sub in due_subs:
      user = sub.user
      fee = Decimal(sub.monthly_fee)
      user.balance -= fee

      txn = Transaction(
        user_id=user.id,
        subscription_id=sub.id,
        amount=-fee,
        transaction_type=TransactionType.FEE,
        status=TransactionStatus.COMPLETED,
        description=(
          f"Monthly fee for building {sub.building.building_number}, "
          f"door {sub.door_number}"
        ),
      )
      db.session.add(txn)

      if user.balance < 0:
        sub.status = SubscriptionStatus.OVERDUE
        marked_overdue += 1
      else:
        sub.status = SubscriptionStatus.ACTIVE

      sub.next_payment_due = sub.next_payment_due + relativedelta(months=1)
      processed += 1
      logger.info(
        "Charged subscription_id=%s user_id=%s fee=%s balance=%s",
        sub.id,
        user.id,
        fee,
        user.balance,
      )

    if processed:
      db.session.commit()
      logger.info(
        "Processed %s due subscriptions, %s marked overdue",
        processed,
        marked_overdue,
      )

    return {"processed": processed, "marked_overdue": marked_overdue}
