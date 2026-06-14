"""Building management service."""

import logging

from app.extensions import db
from app.models import Building
from app.utils.errors import ConflictError, NotFoundError

logger = logging.getLogger(__name__)


class BuildingService:
  @staticmethod
  def create(*, building_number: str, name: str, address: str | None = None) -> Building:
    building_number = building_number.strip()
    name = name.strip()
    if not building_number or not name:
      raise ValueError("Building number and name are required")

    if Building.query.filter_by(building_number=building_number).first():
      raise ConflictError("Building number already exists")

    building = Building(
      building_number=building_number,
      name=name,
      address=(address or "").strip() or None,
    )
    db.session.add(building)
    db.session.commit()
    logger.info("Created building_id=%s number=%s", building.id, building_number)
    return building

  @staticmethod
  def get_by_id(building_id: int) -> Building:
    building = db.session.get(Building, building_id)
    if not building:
      raise NotFoundError("Building not found")
    return building

  @staticmethod
  def _buildings_query(search: str | None = None):
    query = Building.query
    q = (search or "").strip()
    if q:
      pattern = f"%{q}%"
      query = query.filter(
        db.or_(
          Building.building_number.ilike(pattern),
          Building.name.ilike(pattern),
          Building.address.ilike(pattern),
        )
      )
    return query.order_by(Building.id)

  @staticmethod
  def list_buildings(page: int = 1, per_page: int = 20, search: str | None = None):
    return BuildingService._buildings_query(search).paginate(
      page=page,
      per_page=per_page,
      error_out=False,
    )

  @staticmethod
  def search_buildings(search: str = "", limit: int = 20):
    limit = min(max(limit, 1), 50)
    return BuildingService._buildings_query(search).limit(limit).all()
