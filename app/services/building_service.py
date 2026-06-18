"""Building management service."""

import logging

from app.extensions import db
from app.models import Building
from app.utils.errors import NotFoundError
from app.utils.search import building_search_exprs, filter_by_terms, search_terms

logger = logging.getLogger(__name__)


class BuildingService:
  @staticmethod
  def create(
    *,
    building_number: str,
    name: str,
    address: str | None = None,
    admin_comment: str | None = None,
  ) -> Building:
    building_number = building_number.strip()
    name = name.strip()
    if not building_number or not name:
      raise ValueError("Building number and name are required")

    building = Building(
      building_number=building_number,
      name=name,
      address=(address or "").strip() or None,
      admin_comment=(admin_comment or "").strip() or None,
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
    terms = search_terms(search)
    if terms:
      query = filter_by_terms(query, terms, *building_search_exprs())
    return query.order_by(Building.building_number.asc(), Building.name.asc())

  @staticmethod
  def list_buildings(page: int = 1, per_page: int = 20, search: str | None = None):
    return BuildingService._buildings_query(search).paginate(
      page=page,
      per_page=per_page,
      error_out=False,
    )

  @staticmethod
  def update(
    building_id: int,
    *,
    building_number: str | None = None,
    name: str | None = None,
    address: str | None = None,
    admin_comment: str | None = None,
    admin_comment_set: bool = False,
  ) -> Building:
    building = BuildingService.get_by_id(building_id)

    if building_number is not None:
      building_number = building_number.strip()
      if not building_number:
        raise ValueError("Building number is required")
      building.building_number = building_number

    if name is not None:
      name = name.strip()
      if not name:
        raise ValueError("Building name is required")
      building.name = name

    if address is not None:
      building.address = address.strip() or None

    if admin_comment_set:
      building.admin_comment = (admin_comment or "").strip() or None

    db.session.commit()
    logger.info("Updated building_id=%s", building.id)
    return building

  @staticmethod
  def delete(building_id: int) -> None:
    from app.models import Subscription, Transaction

    building = BuildingService.get_by_id(building_id)
    subscription_ids = [
      sub.id for sub in Subscription.query.filter_by(building_id=building.id).all()
    ]
    if subscription_ids:
      Transaction.query.filter(
        Transaction.subscription_id.in_(subscription_ids)
      ).delete(synchronize_session=False)
      Subscription.query.filter(
        Subscription.id.in_(subscription_ids)
      ).delete(synchronize_session=False)

    db.session.delete(building)
    db.session.commit()
    logger.info("Deleted building_id=%s", building_id)

  @staticmethod
  def search_buildings(search: str = "", limit: int = 20):
    limit = min(max(limit, 1), 50)
    return BuildingService._buildings_query(search).limit(limit).all()
