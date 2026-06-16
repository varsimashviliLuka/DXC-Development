"""User management service."""

import logging
from decimal import Decimal

from app.enums import UserRole, UserStatus
from app.extensions import db
from app.models import User
from app.security.password import hash_password
from app.utils.errors import ConflictError, ForbiddenError, NotFoundError
from app.utils.validators import normalize_phone, validate_email, validate_id_number, validate_password

logger = logging.getLogger(__name__)


class UserService:
  @staticmethod
  def get_by_id(user_id: int) -> User:
    user = db.session.get(User, user_id)
    if not user:
      raise NotFoundError("User not found")
    return user

  @staticmethod
  def _users_query(search: str | None = None):
    query = User.query.filter(User.role != UserRole.ADMIN)
    q = (search or "").strip()
    if q:
      pattern = f"%{q}%"
      query = query.filter(
        db.or_(
          User.phone_number.ilike(pattern),
          User.id_number.ilike(pattern),
          User.email.ilike(pattern),
          User.first_name.ilike(pattern),
          User.last_name.ilike(pattern),
        )
      )
    return query.order_by(User.id)

  @staticmethod
  def list_users(page: int = 1, per_page: int = 20, search: str | None = None):
    return UserService._users_query(search).paginate(
      page=page,
      per_page=per_page,
      error_out=False,
    )

  @staticmethod
  def search_users(search: str = "", limit: int = 20):
    limit = min(max(limit, 1), 50)
    return UserService._users_query(search).limit(limit).all()

  @staticmethod
  def update_user(
    user_id: int,
    *,
    actor: User,
    phone_number: str | None = None,
    id_number: str | None = None,
    status: UserStatus | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    balance: Decimal | None = None,
    password: str | None = None,
    admin_comment: str | None = None,
    admin_comment_set: bool = False,
  ) -> User:
    user = UserService.get_by_id(user_id)
    if user.is_admin() and not actor.is_admin():
      raise ForbiddenError("Cannot modify admin account")

    if phone_number is not None:
      phone = normalize_phone(phone_number)
      existing = User.query.filter(
        User.phone_number == phone, User.id != user.id
      ).first()
      if existing:
        raise ConflictError("Phone number already registered")
      user.phone_number = phone

    if id_number is not None:
      id_num = validate_id_number(id_number)
      existing = User.query.filter(User.id_number == id_num, User.id != user.id).first()
      if existing:
        raise ConflictError("ID number already registered")
      user.id_number = id_num

    if status is not None:
      user.status = status
    if first_name is not None:
      user.first_name = first_name.strip() or None
    if last_name is not None:
      user.last_name = last_name.strip() or None
    if email is not None:
      email_addr = validate_email(email)
      if email_addr and User.query.filter(
        User.email == email_addr, User.id != user.id
      ).first():
        raise ConflictError("Email address already registered")
      user.email = email_addr
    if balance is not None and actor.is_admin():
      user.balance = balance
    if password is not None:
      user.password_hash = hash_password(validate_password(password))
    if admin_comment_set:
      user.admin_comment = (admin_comment or "").strip() or None

    db.session.commit()
    logger.info("Updated user_id=%s by actor_id=%s", user.id, actor.id)
    return user

  @staticmethod
  def delete(user_id: int, *, actor: User) -> None:
    from app.enums import UserRole
    from app.models import BankImport, Subscription, Transaction

    user = UserService.get_by_id(user_id)
    if user.role == UserRole.ADMIN:
      raise ForbiddenError("Cannot delete admin accounts")
    if user.id == actor.id:
      raise ForbiddenError("Cannot delete your own account")

    subscription_ids = [sub.id for sub in Subscription.query.filter_by(user_id=user.id).all()]
    if subscription_ids:
      Transaction.query.filter(
        Transaction.subscription_id.in_(subscription_ids)
      ).delete(synchronize_session=False)

    Transaction.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    BankImport.query.filter_by(user_id=user.id).update(
      {BankImport.user_id: None},
      synchronize_session=False,
    )
    db.session.delete(user)
    db.session.commit()
    logger.info("Deleted user_id=%s by actor_id=%s", user_id, actor.id)

  @staticmethod
  def get_profile_summary(user: User) -> dict:
    from app.enums import ChipStatus
    from app.models import Chip, Subscription
    from app.services.transaction_service import TransactionService

    subscriptions = (
      Subscription.query.filter_by(user_id=user.id)
      .order_by(Subscription.id)
      .all()
    )
    total_monthly_fee = sum(float(s.monthly_fee) for s in subscriptions)
    overdue_count = sum(1 for s in subscriptions if s.status.value == "overdue")

    recent_transactions = TransactionService.list_for_user(user.id, limit=10)

    active_chips = Chip.query.filter_by(
      user_id=user.id, status=ChipStatus.ACTIVE
    ).all()

    return {
      "user": user.to_dict(),
      "summary": {
        "subscription_count": len(subscriptions),
        "active_chips": len(active_chips),
        "total_monthly_fee": total_monthly_fee,
        "account_balance": float(user.balance),
        "overdue_subscriptions": overdue_count,
      },
      "subscriptions": [s.to_dict(include_building=True) for s in subscriptions],
      "chips": [c.to_dict() for c in active_chips],
      "recent_transactions": [t.to_dict() for t in recent_transactions],
    }
