"""Chip management service."""

import logging

from app.enums import ChipStatus
from app.extensions import db
from app.models import Chip, User, utcnow
from app.services.user_service import UserService
from app.utils.errors import ConflictError, NotFoundError
from app.utils.validators import validate_chip_number

logger = logging.getLogger(__name__)


class ChipService:
  @staticmethod
  def create(*, user_id: int, chip_number: str) -> Chip:
    user = UserService.get_by_id(user_id)
    chip_num = validate_chip_number(chip_number)

    if Chip.query.filter_by(chip_number=chip_num).first():
      raise ConflictError("Chip number already exists")

    chip = Chip(
      chip_number=chip_num,
      user_id=user.id,
      status=ChipStatus.ACTIVE,
    )
    db.session.add(chip)
    db.session.commit()
    logger.info("Created chip_id=%s user_id=%s chip=%s", chip.id, user.id, chip_num)
    return chip

  @staticmethod
  def get_by_id(chip_id: int) -> Chip:
    chip = db.session.get(Chip, chip_id)
    if not chip:
      raise NotFoundError("Chip not found")
    return chip

  @staticmethod
  def list_for_user(user_id: int):
    return Chip.query.filter_by(user_id=user_id).order_by(Chip.id).all()

  @staticmethod
  def _chips_query(search: str | None = None):
    query = Chip.query.join(User)
    q = (search or "").strip()
    if q:
      pattern = f"%{q}%"
      query = query.filter(
        db.or_(
          Chip.chip_number.ilike(pattern),
          User.phone_number.ilike(pattern),
          User.id_number.ilike(pattern),
        )
      )
    return query.order_by(Chip.id)

  @staticmethod
  def list_all(page: int = 1, per_page: int = 20, search: str | None = None):
    return ChipService._chips_query(search).paginate(
      page=page,
      per_page=per_page,
      error_out=False,
    )

  @staticmethod
  def activate(chip_id: int) -> Chip:
    chip = ChipService.get_by_id(chip_id)
    chip.status = ChipStatus.ACTIVE
    chip.deactivated_at = None
    db.session.commit()
    logger.info("Activated chip_id=%s chip=%s", chip.id, chip.chip_number)
    return chip

  @staticmethod
  def deactivate(chip_id: int) -> Chip:
    chip = ChipService.get_by_id(chip_id)
    if chip.status == ChipStatus.INACTIVE:
      return chip

    chip.status = ChipStatus.INACTIVE
    chip.deactivated_at = utcnow()
    db.session.commit()
    logger.info("Deactivated chip_id=%s chip=%s", chip.id, chip.chip_number)
    return chip

  @staticmethod
  def delete(chip_id: int) -> None:
    chip = ChipService.get_by_id(chip_id)
    db.session.delete(chip)
    db.session.commit()
    logger.info("Deleted chip_id=%s chip=%s", chip.id, chip.chip_number)

  @staticmethod
  def set_status(chip_id: int, active: bool) -> Chip:
    if active:
      return ChipService.activate(chip_id)
    return ChipService.deactivate(chip_id)
