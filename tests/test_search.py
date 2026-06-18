"""Tests for multi-term search behavior."""

from app.extensions import db
from app.models import Building, User


def test_user_search_matches_full_name_with_space(app):
  with app.app_context():
    user = User(
      id_number="01124096118",
      first_name="Nino",
      last_name="Beridze",
      password_hash="x",
    )
    db.session.add(user)
    db.session.commit()

    from app.services.user_service import UserService

    results = UserService.search_users("Nino Ber")
    assert len(results) == 1
    assert results[0].id == user.id


def test_user_search_matches_single_name_token(app):
  with app.app_context():
    user = User(
      id_number="01124096119",
      first_name="Nino",
      last_name="Beridze",
      password_hash="x",
    )
    db.session.add(user)
    db.session.commit()

    from app.services.user_service import UserService

    results = UserService.search_users("Nino")
    assert len(results) == 1


def test_building_search_matches_number_and_name_together(app):
  with app.app_context():
    building = Building(building_number="45", name="Shartava")
    db.session.add(building)
    db.session.commit()

    from app.services.building_service import BuildingService

    results = BuildingService.search_buildings("45 shartava")
    assert len(results) == 1
    assert results[0].id == building.id


def test_building_search_matches_reversed_name_number(app):
  with app.app_context():
    building = Building(building_number="45", name="Shartava")
    db.session.add(building)
    db.session.commit()

    from app.services.building_service import BuildingService

    results = BuildingService.search_buildings("shartava 45")
    assert len(results) == 1
