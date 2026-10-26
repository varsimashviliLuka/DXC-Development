"""Subscription management service."""

import calendar
import logging
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.enums import SubscriptionStatus, TransactionStatus, TransactionType
from app.extensions import db
from app.models import Building, Subscription, Transaction, User, UserPhone
from app.services.building_service import BuildingService
from app.services.user_service import UserService
from app.utils.errors import ConflictError, NotFoundError
from app.utils.search import (
  building_search_exprs,
  filter_by_terms,
  search_terms,
  user_search_exprs,
)
from app.utils.validators import validate_door_number

logger = logging.getLogger(__name__)


def fee_reference(subscription_id: int, due: date) -> str:
  return f"FEE-{subscription_id}-{due.isoformat()}"


def next_billing_date(current: date, billing_day: int) -> date:
  following = current + relativedelta(months=1)
  last_day = calendar.monthrange(following.year, following.month)[1]
  return following.replace(day=min(billing_day, last_day))


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
      billing_day=due_date.day,
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
  def list_for_user_paginated(user_id: int, page: int = 1, per_page: int = 20):
    return (
      Subscription.query.filter_by(user_id=user_id)
      .options(joinedload(Subscription.building))
      .order_by(Subscription.id.desc())
      .paginate(page=page, per_page=per_page, error_out=False)
    )

  @staticmethod
  def _subscriptions_query(
    search: str | None = None,
    *,
    overdue_only: bool = False,
  ):
    query = (
      Subscription.query.join(User)
      .outerjoin(UserPhone)
      .join(Building)
      .options(
        joinedload(Subscription.user),
        joinedload(Subscription.building),
      )
    )
    if overdue_only:
      query = query.filter(Subscription.status == SubscriptionStatus.OVERDUE)
    terms = search_terms(search)
    if terms:
      query = filter_by_terms(
        query,
        terms,
        Subscription.door_number,
        *user_search_exprs(),
        *building_search_exprs(),
      ).distinct()
    return query.order_by(
      User.last_name.asc(),
      User.first_name.asc(),
      User.id_number.asc(),
      Building.building_number.asc(),
      Subscription.door_number.asc(),
    )

  @staticmethod
  def list_all(
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    *,
    overdue_only: bool = False,
  ):
    return SubscriptionService._subscriptions_query(
      search,
      overdue_only=overdue_only,
    ).paginate(
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
      subscription.billing_day = next_payment_due.day if next_payment_due else None

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
    if Transaction.query.filter_by(subscription_id=subscription.id).first():
      raise ConflictError(
        "This subscription has payment history and cannot be deleted. "
        "Set its status to inactive instead."
      )
    db.session.delete(subscription)
    db.session.commit()
    logger.info("Deleted subscription_id=%s", subscription_id)

  @staticmethod
  def process_due_payments(for_date: date | None = None) -> dict:
    """
    Charge every billing period that is due on or before the given date.

    Periods missed while the server was down are caught up one month at a time. Each fee
    carries a unique reference per subscription and due date, so a period can never be
    charged twice, even if two schedulers run at once.
    """
    today = for_date or date.today()
    due_ids = [
      row.id
      for row in db.session.query(Subscription.id).filter(
        Subscription.next_payment_due <= today,
        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.OVERDUE]),
      ).order_by(Subscription.id)
    ]

    processed = 0
    marked_overdue = 0

    for subscription_id in due_ids:
      try:
        charged, overdue = SubscriptionService._charge_due_periods(subscription_id, today)
        db.session.commit()
      except IntegrityError:
        db.session.rollback()
        logger.warning(
          "Skipped subscription_id=%s: fee already recorded by another process",
          subscription_id,
        )
        continue
      processed += charged
      marked_overdue += int(overdue)

    if processed:
      logger.info(
        "Charged %s due billing period(s), %s subscription(s) marked overdue",
        processed,
        marked_overdue,
      )

    return {"processed": processed, "marked_overdue": marked_overdue}

  @staticmethod
  def _charge_due_periods(subscription_id: int, today: date) -> tuple[int, bool]:
    sub = (
      Subscription.query.filter_by(id=subscription_id)
      .with_for_update()
      .populate_existing()
      .one()
    )
    if sub.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.OVERDUE):
      return 0, False

    user = sub.user
    fee = Decimal(sub.monthly_fee)
    charged = 0

    while sub.next_payment_due and sub.next_payment_due <= today:
      due = sub.next_payment_due
      reference = fee_reference(sub.id, due)
      if not Transaction.query.filter_by(reference=reference).first():
        user.adjust_balance(-fee)
        db.session.add(Transaction(
          user_id=user.id,
          subscription_id=sub.id,
          amount=-fee,
          transaction_type=TransactionType.FEE,
          status=TransactionStatus.COMPLETED,
          reference=reference,
          description=(
            f"Monthly fee for building {sub.building.building_number}, "
            f"door {sub.door_number} ({due.isoformat()})"
          ),
        ))
        db.session.flush()
        charged += 1
        logger.info(
          "Charged subscription_id=%s user_id=%s fee=%s due=%s",
          sub.id,
          user.id,
          fee,
          due,
        )
      sub.next_payment_due = next_billing_date(due, sub.billing_day or due.day)

    db.session.refresh(user, ["balance"])
    overdue = user.balance < 0
    sub.status = SubscriptionStatus.OVERDUE if overdue else SubscriptionStatus.ACTIVE
    return charged, overdue

  @staticmethod
  def reconcile_after_balance_change(user: User) -> dict:
    """
    When the account balance is no longer negative, restore overdue subscriptions to active.

    Fees that push balance below zero are handled in process_due_payments(); this covers
    the other direction when the user tops up via bank import or manual payment.
    """
    reactivated = 0
    if user.balance is None or user.balance < 0:
      return {"reactivated": 0}

    overdue_subs = Subscription.query.filter_by(
      user_id=user.id,
      status=SubscriptionStatus.OVERDUE,
    ).all()
    for sub in overdue_subs:
      sub.status = SubscriptionStatus.ACTIVE
      reactivated += 1

    if reactivated:
      logger.info(
        "Reactivated %s overdue subscription(s) for user_id=%s balance=%s",
        reactivated,
        user.id,
        user.balance,
      )

    return {"reactivated": reactivated}
