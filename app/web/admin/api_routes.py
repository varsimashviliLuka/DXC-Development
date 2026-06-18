"""Admin JSON endpoints for searchable UI components."""

from flask import Blueprint, jsonify, request

from app.services.building_service import BuildingService
from app.services.user_service import UserService
from app.web.decorators import admin_required

admin_api_bp = Blueprint("admin_api", __name__)


def _user_option(user):
  name = " ".join(filter(None, [user.first_name, user.last_name])).strip()
  phones = user.phones.all()
  phone_bits = [p.phone_number for p in phones[:2]]
  if len(phones) > 2:
    phone_bits.append("…")
  sub = " · ".join(filter(None, [name, ", ".join(phone_bits) if phone_bits else None]))
  return {
    "id": user.id,
    "label": user.id_number,
    "sub": sub or user.id_number,
  }


def _building_option(building):
  return {
    "id": building.id,
    "label": building.building_number,
    "sub": building.name,
  }


@admin_api_bp.route("/transactions/<int:transaction_id>/bank-import")
@admin_required
def transaction_bank_import(transaction_id):
  from app.services.transaction_service import TransactionService

  details = TransactionService.get_bank_import_details(transaction_id)
  if not details:
    return jsonify({"message": "Bank import not found for this transaction"}), 404
  return jsonify(details)


@admin_api_bp.route("/check-phone")
@admin_required
def check_phone():
  from app.models import UserPhone
  from app.utils.validators import ValidationError, normalize_phone

  phone_raw = request.args.get("phone", "").strip()
  exclude_user_id = request.args.get("exclude_user_id", type=int)

  if not phone_raw:
    return jsonify({"ok": False, "message": "Enter a phone number first"})

  try:
    phone = normalize_phone(phone_raw)
  except ValidationError as exc:
    return jsonify({"ok": False, "message": str(exc)})

  record = UserPhone.query.filter_by(phone_number=phone).first()
  if record and record.user_id != exclude_user_id:
    return jsonify({
      "ok": False,
      "taken": True,
      "message": "This phone number is already registered to another user",
      "phone": phone,
    })

  return jsonify({"ok": True, "phone": phone})


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
