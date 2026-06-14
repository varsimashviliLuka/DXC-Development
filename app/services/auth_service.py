"""Authentication service."""

import logging

from flask_jwt_extended import create_access_token

from app.enums import UserRole, UserStatus
from app.extensions import db
from app.models import User
from app.security.password import hash_password, verify_password
from app.utils.errors import ConflictError, UnauthorizedError
from app.utils.validators import (
  ValidationError,
  normalize_phone,
  validate_email,
  validate_id_number,
  validate_password,
)

logger = logging.getLogger(__name__)


class AuthService:
  @staticmethod
  def authenticate(phone_number: str, password: str) -> User:
    phone = normalize_phone(phone_number)
    user = User.query.filter_by(phone_number=phone).first()
    if not user or not verify_password(user.password_hash, password):
      logger.warning("Failed login attempt for phone=%s", phone)
      raise UnauthorizedError("Invalid phone number or password")

    if user.status == UserStatus.SUSPENDED:
      raise UnauthorizedError("Account is suspended")

    return user

  @staticmethod
  def login(phone_number: str, password: str) -> dict:
    user = AuthService.authenticate(phone_number, password)
    token = create_access_token(
      identity=str(user.id),
      additional_claims={"role": user.role.value},
    )
    logger.info("User logged in user_id=%s role=%s", user.id, user.role.value)
    return {"access_token": token, "user": user.to_dict()}

  @staticmethod
  def ensure_admin_user(app_config) -> User:
    phone = normalize_phone(app_config["ADMIN_PHONE"])
    id_number = validate_id_number(app_config["ADMIN_ID_NUMBER"])
    password = app_config["ADMIN_PASSWORD"]

    user = User.query.filter_by(phone_number=phone).first()
    if user:
      if user.role != UserRole.ADMIN:
        user.role = UserRole.ADMIN
        db.session.commit()
        logger.info("Promoted existing user_id=%s to admin", user.id)
      return user

    admin = User(
      phone_number=phone,
      id_number=id_number,
      password_hash=hash_password(password),
      role=UserRole.ADMIN,
      status=UserStatus.ACTIVE,
      first_name="System",
      last_name="Admin",
    )
    db.session.add(admin)
    db.session.commit()
    logger.info("Seeded default admin user phone=%s", phone)
    return admin

  @staticmethod
  def register_user(
    *,
    phone_number: str,
    id_number: str,
    password: str,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    status: UserStatus = UserStatus.ACTIVE,
  ) -> User:
    phone = normalize_phone(phone_number)
    id_num = validate_id_number(id_number)
    pwd = validate_password(password)
    email_addr = validate_email(email)

    if User.query.filter(
      (User.phone_number == phone) | (User.id_number == id_num)
    ).first():
      raise ConflictError("Phone number or ID number already registered")

    if email_addr and User.query.filter_by(email=email_addr).first():
      raise ConflictError("Email address already registered")

    user = User(
      phone_number=phone,
      id_number=id_num,
      email=email_addr,
      password_hash=hash_password(pwd),
      role=UserRole.USER,
      status=status,
      first_name=(first_name or "").strip() or None,
      last_name=(last_name or "").strip() or None,
    )
    db.session.add(user)
    db.session.commit()
    logger.info("Registered user_id=%s phone=%s", user.id, phone)
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
