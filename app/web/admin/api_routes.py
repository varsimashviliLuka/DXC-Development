"""Admin JSON endpoints for searchable UI components."""

from flask import Blueprint, jsonify, request

from app.services.building_service import BuildingService
from app.services.user_service import UserService
from app.web.decorators import admin_required

admin_api_bp = Blueprint("admin_api", __name__)


def _user_option(user):
  name = " ".join(filter(None, [user.first_name, user.last_name])).strip()
  sub = " · ".join(filter(None, [user.id_number, name]))
  return {
    "id": user.id,
    "label": user.phone_number,
    "sub": sub or user.id_number,
  }


def _building_option(building):
  return {
    "id": building.id,
    "label": f"{building.building_number} (#{building.id})",
    "sub": building.name,
  }


@admin_api_bp.route("/search/users")
@admin_required
def search_users():
  q = request.args.get("q", "")
  limit = request.args.get("limit", 20, type=int)
  users = UserService.search_users(q, limit=limit)
  return jsonify([_user_option(u) for u in users])


@admin_api_bp.route("/search/buildings")
@admin_required
def search_buildings():
  q = request.args.get("q", "")
  limit = request.args.get("limit", 20, type=int)
  buildings = BuildingService.search_buildings(q, limit=limit)
  return jsonify([_building_option(b) for b in buildings])
