"""Subscription management service."""

import logging
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from app.enums import SubscriptionStatus, TransactionStatus, TransactionType
from app.extensions import db
from app.models import Building, Subscription, Transaction, User, UserPhone
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
    admin_comment: str | None = None,
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
      admin_comment=(admin_comment or "").strip() or None,
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
    query = Subscription.query.join(User).outerjoin(UserPhone).join(Building)
    q = (search or "").strip()
    if q:
      pattern = f"%{q}%"
      query = query.filter(
        db.or_(
          Subscription.door_number.ilike(pattern),
          User.id_number.ilike(pattern),
          UserPhone.phone_number.ilike(pattern),
          Building.building_number.ilike(pattern),
          Building.name.ilike(pattern),
        )
      ).distinct()
    return query.order_by(Subscription.id)

  @staticmethod
  def list_all(page: int = 1, per_page: int = 20, search: str | None = None):
    return SubscriptionService._subscriptions_query(search).paginate(
      page=page,
      per_page=per_page,
      error_out=False,
    )

  @staticmethod
  def update(
    subscription_id: int,
    *,
    user_id: int | None = None,
    building_id: int | None = None,
    door_number: str | None = None,
    monthly_fee: Decimal | None = None,
    next_payment_due: date | None = None,
    next_payment_due_set: bool = False,
    status: SubscriptionStatus | None = None,
    admin_comment: str | None = None,
    admin_comment_set: bool = False,
  ) -> Subscription:
    subscription = SubscriptionService.get_by_id(subscription_id)

    if user_id is not None:
      subscription.user = UserService.get_by_id(user_id)

    if building_id is not None:
      subscription.building = BuildingService.get_by_id(building_id)

    if door_number is not None:
      subscription.door_number = validate_door_number(door_number)

    if monthly_fee is not None:
      if monthly_fee < 0:
        raise ValueError("Monthly fee cannot be negative")
      subscription.monthly_fee = monthly_fee

    if next_payment_due_set:
      subscription.next_payment_due = next_payment_due

    if status is not None:
      subscription.status = status

    if admin_comment_set:
      subscription.admin_comment = (admin_comment or "").strip() or None

    existing_door = Subscription.query.filter(
      Subscription.building_id == subscription.building_id,
      Subscription.door_number == subscription.door_number,
      Subscription.id != subscription.id,
    ).first()
    if existing_door:
      raise ConflictError("Door number already assigned in this building")

    db.session.commit()
    logger.info("Updated subscription_id=%s", subscription.id)
    return subscription

  @staticmethod
  def update_status(subscription_id: int, status: SubscriptionStatus) -> Subscription:
    subscription = SubscriptionService.get_by_id(subscription_id)
    subscription.status = status
    db.session.commit()
    logger.info("Updated subscription_id=%s status=%s", subscription_id, status.value)
    return subscription

  @staticmethod
  def delete(subscription_id: int) -> None:
    from app.models import Transaction

    subscription = SubscriptionService.get_by_id(subscription_id)
    Transaction.query.filter_by(subscription_id=subscription.id).delete(
      synchronize_session=False
    )
    db.session.delete(subscription)
    db.session.commit()
    logger.info("Deleted subscription_id=%s", subscription_id)

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
