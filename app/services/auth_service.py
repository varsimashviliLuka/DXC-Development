"""Authentication service."""

import logging

from flask_jwt_extended import create_access_token

from app.enums import UserRole, UserStatus
from app.extensions import db
from app.models import User
from app.security.password import hash_password, verify_password
from app.services.phone_service import PhoneService
from app.utils.errors import ConflictError, UnauthorizedError
from app.utils.validators import (
  ValidationError,
  validate_email,
  validate_id_number,
  validate_password,
)

logger = logging.getLogger(__name__)


class AuthService:
  @staticmethod
  def authenticate(id_number: str, password: str) -> User:
    id_num = validate_id_number(id_number)
    user = User.query.filter_by(id_number=id_num).first()
    if not user or not verify_password(user.password_hash, password):
      logger.warning("Failed login attempt for id_number=%s", id_num)
      raise UnauthorizedError("Invalid ID number or password")

    if user.status == UserStatus.SUSPENDED:
      raise UnauthorizedError("Account is suspended")

    return user

  @staticmethod
  def login(id_number: str, password: str) -> dict:
    user = AuthService.authenticate(id_number, password)
    token = create_access_token(
      identity=str(user.id),
      additional_claims={"role": user.role.value},
    )
    logger.info("User logged in user_id=%s role=%s", user.id, user.role.value)
    return {"access_token": token, "user": user.to_dict()}

  @staticmethod
  def ensure_admin_user(app_config) -> User:
    id_number = validate_id_number(app_config["ADMIN_ID_NUMBER"])
    password = app_config["ADMIN_PASSWORD"]
    admin_phone = app_config.get("ADMIN_PHONE")

    user = User.query.filter_by(id_number=id_number).first()
    if user:
      if user.role != UserRole.ADMIN:
        user.role = UserRole.ADMIN
        db.session.commit()
        logger.info("Promoted existing user_id=%s to admin", user.id)
      if admin_phone and not user.phones.filter_by(is_primary=True).first():
        try:
          PhoneService.add_phone(user, admin_phone, label="Admin", is_primary=True)
          db.session.commit()
        except ConflictError:
          db.session.rollback()
      return user

    admin = User(
      id_number=id_number,
      password_hash=hash_password(password),
      role=UserRole.ADMIN,
      status=UserStatus.ACTIVE,
      first_name="System",
      last_name="Admin",
    )
    db.session.add(admin)
    db.session.flush()
    if admin_phone:
      PhoneService.add_phone(admin, admin_phone, label="Admin", is_primary=True)
    db.session.commit()
    logger.info("Seeded default admin user id_number=%s", id_number)
    return admin

  @staticmethod
  def register_user(
    *,
    id_number: str,
    password: str,
    phones: list[dict] | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    status: UserStatus = UserStatus.ACTIVE,
    admin_comment: str | None = None,
  ) -> User:
    id_num = validate_id_number(id_number)
    pwd = validate_password(password)
    email_addr = validate_email(email)

    if User.query.filter_by(id_number=id_num).first():
      raise ConflictError("ID number already registered")

    if email_addr and User.query.filter_by(email=email_addr).first():
      raise ConflictError("Email address already registered")

    user = User(
      id_number=id_num,
      email=email_addr,
      password_hash=hash_password(pwd),
      role=UserRole.USER,
      status=status,
      first_name=(first_name or "").strip() or None,
      last_name=(last_name or "").strip() or None,
      admin_comment=(admin_comment or "").strip() or None,
    )
    db.session.add(user)
    db.session.flush()

    if phones:
      PhoneService.replace_phones(user, phones)

    db.session.commit()
    logger.info("Registered user_id=%s id_number=%s", user.id, id_num)
    return user

  @staticmethod
  def change_password(user: User, current_password: str, new_password: str) -> None:
    if not verify_password(user.password_hash, current_password):
      raise UnauthorizedError("Current password is incorrect")

    new_pwd = validate_password(new_password)
    if verify_password(user.password_hash, new_pwd):
      raise ValidationError("New password must be different from current password")

    user.password_hash = hash_password(new_pwd)
    db.session.commit()
    logger.info("Password changed for user_id=%s", user.id)
