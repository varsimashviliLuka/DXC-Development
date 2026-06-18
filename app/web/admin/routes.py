"""Admin web routes."""

from datetime import datetime
from decimal import Decimal

import os
import re
from pathlib import Path

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for

from app.enums import SubscriptionStatus, TransactionStatus, TransactionType, UserRole, UserStatus
from app.models import Building, User
from app.services.auth_service import AuthService
from app.services.bank_import_service import BankImportService
from app.services.building_service import BuildingService
from app.services.chip_service import ChipService
from app.services.subscription_service import SubscriptionService
from app.services.transaction_service import TransactionService
from app.services.user_service import UserService
from app.web.decorators import admin_required
from app.web.utils import flash_exception, form_value, parse_phones_from_form

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


TXN_FILTER_KEYS = (
  "date_from",
  "date_to",
  "phone_number",
  "id_number",
  "transaction_reference",
  "subscription_payment_reference",
  "transaction_type",
  "status",
  "q",
)


def _transaction_filter_params():
  return {k: request.args.get(k) for k in TXN_FILTER_KEYS if request.args.get(k)}


@admin_bp.route("/transactions", methods=["GET"])
@admin_required
def transactions():
  page = TransactionService.list_admin(
    date_from=form_value(request.args, "date_from") if request.args else None,
    date_to=form_value(request.args, "date_to") if request.args else None,
    phone_number=form_value(request.args, "phone_number") if request.args else None,
    id_number=form_value(request.args, "id_number") if request.args else None,
    transaction_reference=form_value(request.args, "transaction_reference")
    if request.args
    else None,
    subscription_payment_reference=form_value(request.args, "subscription_payment_reference")
    if request.args
    else None,
    transaction_type=form_value(request.args, "transaction_type") if request.args else None,
    status=form_value(request.args, "status") if request.args else None,
    free_text=form_value(request.args, "q") if request.args else None,
    page=int(request.args.get("page", 1)),
    per_page=20,
  )
  return render_template(
    "admin/transactions.html",
    transactions=page.items,
    pagination=page,
    filters=request.args,
    filter_params=_transaction_filter_params(),
    transaction_types=list(TransactionType),
    transaction_statuses=list(TransactionStatus),
  )


def _user_filter_params():
  params = {}
  q = _search_q()
  if q:
    params["q"] = q
  if request.args.get("negative_balance") == "1":
    params["negative_balance"] = "1"
  return params


def _negative_balance_filter():
  return request.args.get("negative_balance") == "1"


@admin_bp.route("/users", methods=["GET", "POST"])
@admin_required
def users():
  if request.method == "POST":
    try:
      status = UserStatus(request.form.get("status", UserStatus.ACTIVE.value))
      AuthService.register_user(
        id_number=form_value(request.form, "id_number"),
        password=form_value(request.form, "password"),
        phones=parse_phones_from_form(request.form) or None,
        email=form_value(request.form, "email") or None,
        first_name=form_value(request.form, "first_name") or None,
        last_name=form_value(request.form, "last_name") or None,
        status=status,
        admin_comment=form_value(request.form, "admin_comment") or None,
      )
      flash("User created.", "success")
      return redirect(url_for("admin.users"))
    except Exception as exc:
      flash_exception(exc)

  q = _search_q()
  negative_balance_only = _negative_balance_filter()
  page = UserService.list_users(
    page=int(request.args.get("page", 1)),
    per_page=20,
    search=q,
    negative_balance_only=negative_balance_only,
  )
  return render_template(
    "admin/users.html",
    users=page.items,
    pagination=page,
    form=request.form,
    statuses=list(UserStatus),
    search_q=q or "",
    negative_balance_only=negative_balance_only,
    filter_params=_user_filter_params(),
  )


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
  user = UserService.get_by_id(user_id)
  if request.method == "POST":
    try:
      password = form_value(request.form, "password")
      UserService.update_user(
        user_id,
        actor=g.current_user,
        id_number=form_value(request.form, "id_number"),
        status=UserStatus(form_value(request.form, "status", UserStatus.ACTIVE.value)),
        first_name=form_value(request.form, "first_name") or None,
        last_name=form_value(request.form, "last_name") or None,
        email=form_value(request.form, "email") or None,
        password=password or None,
        admin_comment=form_value(request.form, "admin_comment") or None,
        admin_comment_set=True,
        phones=parse_phones_from_form(request.form),
        phones_set=True,
      )
      flash("User updated.", "success")
      return redirect(url_for("admin.users"))
    except Exception as exc:
      flash_exception(exc)

  return render_template(
    "admin/user_edit.html",
    user=user,
    statuses=list(UserStatus),
    form=request.form,
    balance_form={},
  )


@admin_bp.route("/users/<int:user_id>/balance", methods=["POST"])
@admin_required
def adjust_user_balance(user_id):
  user = UserService.get_by_id(user_id)
  try:
    direction = form_value(request.form, "direction")
    amount_raw = form_value(request.form, "amount")
    if not amount_raw:
      raise ValueError("Enter an amount")
    amount = Decimal(amount_raw)
    reason = form_value(request.form, "reason") or None
    TransactionService.record_admin_adjustment(
      user=user,
      amount=amount,
      direction=direction,
      description=reason,
    )
    verb = "added to" if direction == "add" else "subtracted from"
    flash(f"{amount:.2f} ₾ {verb} account balance.", "success")
    return redirect(url_for("admin.edit_user", user_id=user_id))
  except Exception as exc:
    flash_exception(exc)
    return render_template(
      "admin/user_edit.html",
      user=UserService.get_by_id(user_id),
      statuses=list(UserStatus),
      form={},
      balance_form=request.form,
    )


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
  try:
    UserService.delete(user_id, actor=g.current_user)
    flash("User deleted.", "success")
  except Exception as exc:
    flash_exception(exc)
  return redirect(url_for("admin.users"))


@admin_bp.route("/buildings", methods=["GET", "POST"])
@admin_required
def buildings():
  if request.method == "POST":
    try:
      BuildingService.create(
        building_number=form_value(request.form, "building_number"),
        name=form_value(request.form, "name"),
        address=form_value(request.form, "address") or None,
        admin_comment=form_value(request.form, "admin_comment") or None,
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


@admin_bp.route("/buildings/<int:building_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_building(building_id):
  building = BuildingService.get_by_id(building_id)
  if request.method == "POST":
    try:
      BuildingService.update(
        building_id,
        building_number=form_value(request.form, "building_number"),
        name=form_value(request.form, "name"),
        address=form_value(request.form, "address") or None,
        admin_comment=form_value(request.form, "admin_comment") or None,
        admin_comment_set=True,
      )
      flash("Building updated.", "success")
      return redirect(url_for("admin.buildings"))
    except Exception as exc:
      flash_exception(exc)

  return render_template(
    "admin/building_edit.html",
    building=building,
    form=request.form,
  )


@admin_bp.route("/buildings/<int:building_id>/delete", methods=["POST"])
@admin_required
def delete_building(building_id):
  try:
    BuildingService.delete(building_id)
    flash("Building deleted.", "success")
  except Exception as exc:
    flash_exception(exc)
  return redirect(url_for("admin.buildings"))


def _subscription_filter_params():
  params = {}
  q = _search_q()
  if q:
    params["q"] = q
  if request.args.get("overdue") == "1":
    params["overdue"] = "1"
  return params


def _overdue_only_filter():
  return request.args.get("overdue") == "1"


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
        admin_comment=form_value(request.form, "admin_comment") or None,
      )
      flash("Subscription created.", "success")
      return redirect(url_for("admin.subscriptions"))
    except Exception as exc:
      flash_exception(exc)

  q = _search_q()
  overdue_only = _overdue_only_filter()
  page = SubscriptionService.list_all(
    page=int(request.args.get("page", 1)),
    per_page=20,
    search=q,
    overdue_only=overdue_only,
  )
  return render_template(
    "admin/subscriptions.html",
    subscriptions=page.items,
    pagination=page,
    statuses=list(SubscriptionStatus),
    form=request.form,
    search_q=q or "",
    overdue_only=overdue_only,
    filter_params=_subscription_filter_params(),
  )


@admin_bp.route("/subscriptions/<int:subscription_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_subscription(subscription_id):
  subscription = SubscriptionService.get_by_id(subscription_id)
  if request.method == "POST":
    try:
      due = None
      due_raw = form_value(request.form, "next_payment_due")
      if due_raw:
        due = datetime.strptime(due_raw, "%Y-%m-%d").date()

      SubscriptionService.update(
        subscription_id,
        user_id=int(form_value(request.form, "user_id")),
        building_id=int(form_value(request.form, "building_id")),
        door_number=form_value(request.form, "door_number"),
        monthly_fee=Decimal(form_value(request.form, "monthly_fee", "0")),
        next_payment_due=due,
        next_payment_due_set=True,
        status=SubscriptionStatus(
          form_value(request.form, "status", SubscriptionStatus.ACTIVE.value)
        ),
        admin_comment=form_value(request.form, "admin_comment") or None,
        admin_comment_set=True,
      )
      flash("Subscription updated.", "success")
      return redirect(url_for("admin.subscriptions"))
    except Exception as exc:
      flash_exception(exc)

  return render_template(
    "admin/subscription_edit.html",
    subscription=subscription,
    statuses=list(SubscriptionStatus),
    form=request.form,
  )


@admin_bp.route("/subscriptions/<int:subscription_id>/delete", methods=["POST"])
@admin_required
def delete_subscription(subscription_id):
  try:
    SubscriptionService.delete(subscription_id)
    flash("Subscription deleted.", "success")
  except Exception as exc:
    flash_exception(exc)
  return redirect(url_for("admin.subscriptions"))


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


@admin_bp.route("/chips/<int:chip_id>/delete", methods=["POST"])
@admin_required
def delete_chip(chip_id):
  try:
    ChipService.delete(chip_id)
    flash("Chip deleted.", "success")
  except Exception as exc:
    flash_exception(exc)
  return redirect(url_for("admin.chips"))


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


_LOG_LINE_RE = re.compile(
  r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
  r"\s*\|\s*(?P<level>\w+)\s*"
  r"\|\s*(?P<logger>[^\|]+?)\s*"
  r"\|\s*(?P<req_id>[^\|]+?)\s*"
  r"\|\s*(?P<message>.+)$"
)

def _parse_log_lines(path: str) -> list[dict]:
  parsed = []
  try:
    with open(path, encoding="utf-8", errors="replace") as fh:
      for raw in fh:
        line = raw.rstrip("\n")
        if not line.strip():
          continue
        m = _LOG_LINE_RE.match(line)
        if m:
          parsed.append({
            "ts": m.group("ts"),
            "level": m.group("level").strip(),
            "logger": m.group("logger").strip(),
            "req_id": m.group("req_id").strip(),
            "message": m.group("message").strip(),
            "raw": line,
          })
        else:
          if parsed:
            parsed[-1]["message"] += " " + line.strip()
            parsed[-1]["raw"] += "\n" + line
  except OSError:
    pass
  return parsed


@admin_bp.route("/logs")
@admin_required
def logs():
  log_file = current_app.config.get("LOG_FILE", "logs/app.log")
  all_lines = _parse_log_lines(log_file)

  level_filter = (request.args.get("level") or "").strip().upper() or None
  module_filter = (request.args.get("module") or "").strip() or None
  text_filter = (request.args.get("q") or "").strip() or None
  date_filter = (request.args.get("date") or "").strip() or None

  filtered = all_lines
  if level_filter:
    filtered = [l for l in filtered if l["level"] == level_filter]
  if module_filter:
    filtered = [l for l in filtered if module_filter.lower() in l["logger"].lower()]
  if text_filter:
    filtered = [l for l in filtered if text_filter.lower() in l["message"].lower()
                                     or text_filter.lower() in l["logger"].lower()]
  if date_filter:
    filtered = [l for l in filtered if l["ts"].startswith(date_filter)]

  filtered = list(reversed(filtered))

  per_page = 200
  total = len(filtered)
  page = max(1, int(request.args.get("page", 1)))
  pages = max(1, (total + per_page - 1) // per_page)
  page = min(page, pages)
  start = (page - 1) * per_page
  lines = filtered[start: start + per_page]

  all_levels = sorted({l["level"] for l in all_lines})
  log_file_size = 0
  try:
    log_file_size = os.path.getsize(log_file)
  except OSError:
    pass

  return render_template(
    "admin/logs.html",
    lines=lines,
    total=total,
    page=page,
    pages=pages,
    per_page=per_page,
    all_levels=all_levels,
    level_filter=level_filter or "",
    module_filter=module_filter or "",
    text_filter=text_filter or "",
    date_filter=date_filter or "",
    log_file=log_file,
    log_file_size=log_file_size,
    has_prev=page > 1,
    has_next=page < pages,
  )


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
