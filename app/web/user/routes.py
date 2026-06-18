"""User portal web routes."""

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app.services.auth_service import AuthService
from app.services.chip_service import ChipService
from app.services.subscription_service import SubscriptionService
from app.services.transaction_service import TransactionService
from app.services.user_service import UserService
from app.web.decorators import active_user_required, login_required
from app.web.utils import flash_exception, form_value

user_bp = Blueprint("user", __name__)

USER_LIST_PER_PAGE = 20


@user_bp.route("/")
@active_user_required
def dashboard():
  summary = UserService.get_profile_summary(g.current_user)
  return render_template("user/dashboard.html", summary=summary)


@user_bp.route("/subscriptions")
@active_user_required
def subscriptions():
  page = SubscriptionService.list_for_user_paginated(
    g.current_user.id,
    page=int(request.args.get("page", 1)),
    per_page=USER_LIST_PER_PAGE,
  )
  return render_template(
    "user/subscriptions.html",
    subscriptions=page.items,
    pagination=page,
  )


@user_bp.route("/chips")
@active_user_required
def chips():
  page = ChipService.list_for_user_paginated(
    g.current_user.id,
    page=int(request.args.get("page", 1)),
    per_page=USER_LIST_PER_PAGE,
  )
  return render_template(
    "user/chips.html",
    chips=page.items,
    pagination=page,
  )


@user_bp.route("/transactions")
@active_user_required
def transactions():
  page = TransactionService.list_for_user_paginated(
    g.current_user.id,
    page=int(request.args.get("page", 1)),
    per_page=USER_LIST_PER_PAGE,
  )
  return render_template(
    "user/transactions.html",
    transactions=page.items,
    pagination=page,
  )


@user_bp.route("/profile")
@login_required
def profile():
  return render_template("user/profile.html", user=g.current_user)


@user_bp.route("/password", methods=["GET", "POST"])
@login_required
def password():
  if request.method == "POST":
    try:
      AuthService.change_password(
        g.current_user,
        form_value(request.form, "current_password"),
        form_value(request.form, "new_password"),
      )
      flash("Password updated successfully.", "success")
      return redirect(url_for("user.profile"))
    except Exception as exc:
      flash_exception(exc)

  return render_template("user/password.html")
