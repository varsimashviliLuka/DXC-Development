"""Admin web routes."""

from datetime import datetime
from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.enums import SubscriptionStatus, UserRole, UserStatus
from app.models import Building, User
from app.services.auth_service import AuthService
from app.services.bank_import_service import BankImportService
from app.services.building_service import BuildingService
from app.services.chip_service import ChipService
from app.services.subscription_service import SubscriptionService
from app.services.transaction_service import TransactionService
from app.services.user_service import UserService
from app.web.decorators import admin_required
from app.web.utils import flash_exception, form_value

admin_bp = Blueprint("admin", __name__)


def _search_q():
  return request.args.get("q", "").strip() or None


@admin_bp.route("/")
@admin_required
def dashboard():
  users_count = User.query.filter(User.role != UserRole.ADMIN).count()
  buildings_count = Building.query.count()
  subs_page = SubscriptionService.list_all(page=1, per_page=5)
  chips_page = ChipService.list_all(page=1, per_page=5)
  unmatched_payments = BankImportService.list_unmatched(limit=10)
  unmatched_count = BankImportService.count_unmatched()
  return render_template(
    "admin/dashboard.html",
    users_count=users_count,
    buildings_count=buildings_count,
    recent_subscriptions=subs_page.items,
    recent_chips=chips_page.items,
    unmatched_payments=unmatched_payments,
    unmatched_count=unmatched_count,
  )


@admin_bp.route("/users", methods=["GET", "POST"])
@admin_required
def users():
  if request.method == "POST":
    try:
      status = UserStatus(request.form.get("status", UserStatus.ACTIVE.value))
      AuthService.register_user(
        phone_number=form_value(request.form, "phone_number"),
        id_number=form_value(request.form, "id_number"),
        password=form_value(request.form, "password"),
        email=form_value(request.form, "email") or None,
        first_name=form_value(request.form, "first_name") or None,
        last_name=form_value(request.form, "last_name") or None,
        status=status,
      )
      flash("User created.", "success")
      return redirect(url_for("admin.users"))
    except Exception as exc:
      flash_exception(exc)

  q = _search_q()
  page = UserService.list_users(
    page=int(request.args.get("page", 1)),
    per_page=20,
    search=q,
  )
  return render_template(
    "admin/users.html",
    users=page.items,
    pagination=page,
    form=request.form,
    statuses=list(UserStatus),
    search_q=q or "",
  )


@admin_bp.route("/buildings", methods=["GET", "POST"])
@admin_required
def buildings():
  if request.method == "POST":
    try:
      BuildingService.create(
        building_number=form_value(request.form, "building_number"),
        name=form_value(request.form, "name"),
        address=form_value(request.form, "address") or None,
      )
      flash("Building created.", "success")
      return redirect(url_for("admin.buildings"))
    except Exception as exc:
      flash_exception(exc)

  q = _search_q()
  page = BuildingService.list_buildings(
    page=int(request.args.get("page", 1)),
    per_page=20,
    search=q,
  )
  return render_template(
    "admin/buildings.html",
    buildings=page.items,
    pagination=page,
    form=request.form,
    search_q=q or "",
  )


@admin_bp.route("/subscriptions", methods=["GET", "POST"])
@admin_required
def subscriptions():
  if request.method == "POST":
    try:
      due = None
      due_raw = form_value(request.form, "next_payment_due")
      if due_raw:
        due = datetime.strptime(due_raw, "%Y-%m-%d").date()

      SubscriptionService.create(
        user_id=int(form_value(request.form, "user_id")),
        building_id=int(form_value(request.form, "building_id")),
        door_number=form_value(request.form, "door_number"),
        monthly_fee=Decimal(form_value(request.form, "monthly_fee", "0")),
        next_payment_due=due,
        status=SubscriptionStatus(
          form_value(request.form, "status", SubscriptionStatus.ACTIVE.value)
        ),
      )
      flash("Subscription created.", "success")
      return redirect(url_for("admin.subscriptions"))
    except Exception as exc:
      flash_exception(exc)

  q = _search_q()
  page = SubscriptionService.list_all(
    page=int(request.args.get("page", 1)),
    per_page=20,
    search=q,
  )
  return render_template(
    "admin/subscriptions.html",
    subscriptions=page.items,
    pagination=page,
    statuses=list(SubscriptionStatus),
    form=request.form,
    search_q=q or "",
  )


@admin_bp.route("/chips", methods=["GET", "POST"])
@admin_required
def chips():
  if request.method == "POST" and form_value(request.form, "action") == "create":
    try:
      ChipService.create(
        user_id=int(form_value(request.form, "user_id")),
        chip_number=form_value(request.form, "chip_number"),
      )
      flash("Chip assigned.", "success")
      return redirect(url_for("admin.chips"))
    except Exception as exc:
      flash_exception(exc)

  q = _search_q()
  page = ChipService.list_all(
    page=int(request.args.get("page", 1)),
    per_page=20,
    search=q,
  )
  return render_template(
    "admin/chips.html",
    chips=page.items,
    pagination=page,
    form=request.form,
    search_q=q or "",
  )


@admin_bp.route("/chips/<int:chip_id>/deactivate", methods=["POST"])
@admin_required
def deactivate_chip(chip_id):
  try:
    ChipService.deactivate(chip_id)
    flash("Chip deactivated.", "success")
  except Exception as exc:
    flash_exception(exc)
  return redirect(url_for("admin.chips"))


@admin_bp.route("/chips/<int:chip_id>/activate", methods=["POST"])
@admin_required
def activate_chip(chip_id):
  try:
    ChipService.activate(chip_id)
    flash("Chip activated.", "success")
  except Exception as exc:
    flash_exception(exc)
  return redirect(url_for("admin.chips"))


@admin_bp.route("/payments/import", methods=["GET", "POST"])
@admin_required
def import_payments():
  result = None
  if request.method == "POST":
    upload = request.files.get("file")
    if not upload or not upload.filename:
      flash_exception(ValueError("Please choose a CSV file."))
    else:
      try:
        result = TransactionService.import_payments_from_csv(upload.stream)
        flash(
          f"Import complete: {result['matched']} matched, "
          f"{result['unmatched']} unmatched, {result['skipped']} skipped.",
          "success",
        )
      except Exception as exc:
        flash_exception(exc)

  return render_template("admin/import_payments.html", result=result)


@admin_bp.route("/payments/unmatched")
@admin_required
def unmatched_payments():
  records = BankImportService.list_unmatched(limit=50)
  return render_template("admin/unmatched_payments.html", records=records)


@admin_bp.route("/payments/unmatched/<int:import_id>/assign", methods=["POST"])
@admin_required
def assign_unmatched_payment(import_id):
  try:
    user_id = int(form_value(request.form, "user_id"))
    BankImportService.assign_to_user(import_id, user_id)
    flash("Payment assigned and balance updated.", "success")
  except Exception as exc:
    flash_exception(exc)
  return redirect(url_for("admin.unmatched_payments"))


@admin_bp.route("/payments/unmatched/<int:import_id>/create-user", methods=["POST"])
@admin_required
def create_user_from_payment(import_id):
  try:
    BankImportService.create_user_and_assign(
      import_id,
      phone_number=form_value(request.form, "phone_number"),
      password=form_value(request.form, "password"),
      email=form_value(request.form, "email") or None,
    )
    flash("User created and payment credited.", "success")
  except Exception as exc:
    flash_exception(exc)
  return redirect(url_for("admin.unmatched_payments"))
