"""RESTX API namespaces."""

from flask import g
from flask_restx import Namespace, Resource, fields
from werkzeug.datastructures import FileStorage

from app.enums import SubscriptionStatus, UserStatus
from app.extensions import limiter
from app.security.decorators import active_user_required, admin_required, jwt_required_custom
from app.services.auth_service import AuthService
from app.services.building_service import BuildingService
from app.services.chip_service import ChipService
from app.services.subscription_service import SubscriptionService
from app.services.transaction_service import TransactionService
from app.services.user_service import UserService
from app.utils.errors import AppError
from app.utils.validators import ValidationError

auth_ns = Namespace("auth", description="Authentication")
users_ns = Namespace("users", description="User management (admin)")
buildings_ns = Namespace("buildings", description="Building management (admin)")
subscriptions_ns = Namespace("subscriptions", description="Door subscriptions (admin)")
chips_ns = Namespace("chips", description="Physical chip management (admin)")
transactions_ns = Namespace("transactions", description="Payment transactions (admin)")
me_ns = Namespace("me", description="Current user profile")
health_ns = Namespace("health", description="Health checks")

login_model = auth_ns.model(
  "Login",
  {
    "phone_number": fields.String(required=True, example="+995592159199"),
    "password": fields.String(required=True, example="SecurePass123"),
  },
)

token_response = auth_ns.model(
  "TokenResponse",
  {
    "access_token": fields.String,
    "user": fields.Raw,
  },
)

change_password_model = me_ns.model(
  "ChangePassword",
  {
    "current_password": fields.String(required=True),
    "new_password": fields.String(required=True),
  },
)

register_user_model = users_ns.model(
  "RegisterUser",
  {
    "phone_number": fields.String(required=True),
    "id_number": fields.String(required=True),
    "password": fields.String(required=True),
    "email": fields.String,
    "first_name": fields.String,
    "last_name": fields.String,
    "status": fields.String(enum=[s.value for s in UserStatus], default="active"),
  },
)

building_model = buildings_ns.model(
  "Building",
  {
    "building_number": fields.String(required=True),
    "name": fields.String(required=True),
    "address": fields.String,
  },
)

subscription_model = subscriptions_ns.model(
  "Subscription",
  {
    "user_id": fields.Integer(required=True),
    "building_id": fields.Integer(required=True),
    "door_number": fields.String(required=True),
    "monthly_fee": fields.Float(required=True),
    "next_payment_due": fields.String(description="YYYY-MM-DD"),
    "status": fields.String(
      enum=[s.value for s in SubscriptionStatus],
      default="active",
    ),
  },
)

chip_model = chips_ns.model(
  "Chip",
  {
    "user_id": fields.Integer(required=True),
    "chip_number": fields.String(required=True),
  },
)

csv_upload_parser = transactions_ns.parser()
csv_upload_parser.add_argument(
  "file",
  type=FileStorage,
  location="files",
  required=True,
  help="Georgian bank statement CSV export (TBC/BoG format)",
)

pagination_parser = users_ns.parser()
pagination_parser.add_argument("page", type=int, default=1, location="args")
pagination_parser.add_argument("per_page", type=int, default=20, location="args")


def _handle_errors(fn):
  from functools import wraps
  from flask_restx import abort

  @wraps(fn)
  def wrapper(*args, **kwargs):
    try:
      return fn(*args, **kwargs)
    except AppError as exc:
      abort(exc.status_code, exc.message)
    except ValidationError as exc:
      abort(400, str(exc))
    except ValueError as exc:
      abort(400, str(exc))

  return wrapper


@auth_ns.route("/login")
class LoginResource(Resource):
  @limiter.limit("10 per minute")
  @_handle_errors
  @auth_ns.expect(login_model, validate=True)
  @auth_ns.marshal_with(token_response)
  def post(self):
    """Authenticate with phone number and password."""
    payload = auth_ns.payload
    return AuthService.login(payload["phone_number"], payload["password"])


@auth_ns.route("/me")
class AuthMeResource(Resource):
  @_handle_errors
  @jwt_required_custom
  def get(self):
    """Return the currently authenticated user."""
    return g.current_user.to_dict()


@users_ns.route("")
class UsersResource(Resource):
  @_handle_errors
  @admin_required
  @users_ns.expect(register_user_model, validate=True)
  def post(self):
    """Admin-only: register a new user."""
    payload = users_ns.payload
    status = UserStatus(payload.get("status", UserStatus.ACTIVE.value))
    user = AuthService.register_user(
      phone_number=payload["phone_number"],
      id_number=payload["id_number"],
      password=payload["password"],
      email=payload.get("email"),
      first_name=payload.get("first_name"),
      last_name=payload.get("last_name"),
      status=status,
    )
    return user.to_dict(), 201

  @_handle_errors
  @admin_required
  @users_ns.expect(pagination_parser)
  def get(self):
    """Admin-only: list registered users."""
    args = pagination_parser.parse_args()
    page = UserService.list_users(page=args["page"], per_page=args["per_page"])
    return {
      "items": [u.to_dict() for u in page.items],
      "total": page.total,
      "page": page.page,
      "per_page": page.per_page,
      "pages": page.pages,
    }


@users_ns.route("/<int:user_id>")
class UserResource(Resource):
  @_handle_errors
  @jwt_required_custom
  def get(self, user_id):
    user = UserService.get_by_id(user_id)
    if not g.current_user.is_admin() and g.current_user.id != user_id:
      from app.utils.errors import ForbiddenError

      raise ForbiddenError("Access denied")
    return user.to_dict()

  @_handle_errors
  @admin_required
  def patch(self, user_id):
    payload = users_ns.payload or {}
    status = UserStatus(payload["status"]) if "status" in payload else None
    user = UserService.update_user(
      user_id,
      actor=g.current_user,
      status=status,
      first_name=payload.get("first_name"),
      last_name=payload.get("last_name"),
      email=payload.get("email"),
      password=payload.get("password"),
    )
    return user.to_dict()


@buildings_ns.route("")
class BuildingsResource(Resource):
  @_handle_errors
  @admin_required
  @buildings_ns.expect(building_model, validate=True)
  def post(self):
    payload = buildings_ns.payload
    building = BuildingService.create(
      building_number=payload["building_number"],
      name=payload["name"],
      address=payload.get("address"),
    )
    return building.to_dict(), 201

  @_handle_errors
  @admin_required
  @buildings_ns.expect(pagination_parser)
  def get(self):
    args = pagination_parser.parse_args()
    page = BuildingService.list_buildings(page=args["page"], per_page=args["per_page"])
    return {
      "items": [b.to_dict() for b in page.items],
      "total": page.total,
      "page": page.page,
      "per_page": page.per_page,
      "pages": page.pages,
    }


@buildings_ns.route("/<int:building_id>")
class BuildingResource(Resource):
  @_handle_errors
  @admin_required
  def get(self, building_id):
    return BuildingService.get_by_id(building_id).to_dict()


@subscriptions_ns.route("")
class SubscriptionsResource(Resource):
  @_handle_errors
  @admin_required
  @subscriptions_ns.expect(subscription_model, validate=True)
  def post(self):
    from datetime import datetime
    from decimal import Decimal

    payload = subscriptions_ns.payload
    due = None
    if payload.get("next_payment_due"):
      due = datetime.strptime(payload["next_payment_due"], "%Y-%m-%d").date()

    status = SubscriptionStatus(payload.get("status", SubscriptionStatus.ACTIVE.value))
    subscription = SubscriptionService.create(
      user_id=payload["user_id"],
      building_id=payload["building_id"],
      door_number=payload["door_number"],
      monthly_fee=Decimal(str(payload["monthly_fee"])),
      next_payment_due=due,
      status=status,
    )
    return subscription.to_dict(include_building=True), 201

  @_handle_errors
  @admin_required
  @subscriptions_ns.expect(pagination_parser)
  def get(self):
    args = pagination_parser.parse_args()
    page = SubscriptionService.list_all(page=args["page"], per_page=args["per_page"])
    return {
      "items": [s.to_dict(include_building=True, include_user=True) for s in page.items],
      "total": page.total,
      "page": page.page,
      "per_page": page.per_page,
      "pages": page.pages,
    }


@subscriptions_ns.route("/<int:subscription_id>")
class SubscriptionResource(Resource):
  @_handle_errors
  @admin_required
  def get(self, subscription_id):
    sub = SubscriptionService.get_by_id(subscription_id)
    return sub.to_dict(include_building=True, include_user=True)

  @_handle_errors
  @admin_required
  def patch(self, subscription_id):
    payload = subscriptions_ns.payload or {}
    if "status" not in payload:
      subscriptions_ns.abort(400, "status is required")
    status = SubscriptionStatus(payload["status"])
    sub = SubscriptionService.update_status(subscription_id, status)
    return sub.to_dict(include_building=True)


@chips_ns.route("")
class ChipsResource(Resource):
  @_handle_errors
  @admin_required
  @chips_ns.expect(chip_model, validate=True)
  def post(self):
    payload = chips_ns.payload
    chip = ChipService.create(
      user_id=payload["user_id"],
      chip_number=payload["chip_number"],
    )
    return chip.to_dict(include_user=True), 201

  @_handle_errors
  @admin_required
  @chips_ns.expect(pagination_parser)
  def get(self):
    args = pagination_parser.parse_args()
    page = ChipService.list_all(page=args["page"], per_page=args["per_page"])
    return {
      "items": [c.to_dict(include_user=True) for c in page.items],
      "total": page.total,
      "page": page.page,
      "per_page": page.per_page,
      "pages": page.pages,
    }


@chips_ns.route("/<int:chip_id>")
class ChipResource(Resource):
  @_handle_errors
  @admin_required
  def get(self, chip_id):
    return ChipService.get_by_id(chip_id).to_dict(include_user=True)

  @_handle_errors
  @admin_required
  def delete(self, chip_id):
    """Deactivate a chip."""
    chip = ChipService.deactivate(chip_id)
    return chip.to_dict()


@chips_ns.route("/<int:chip_id>/activate")
class ActivateChipResource(Resource):
  @_handle_errors
  @admin_required
  def post(self, chip_id):
    """Activate a deactivated chip."""
    chip = ChipService.activate(chip_id)
    return chip.to_dict()


@transactions_ns.route("/import")
class TransactionImportResource(Resource):
  @_handle_errors
  @admin_required
  @transactions_ns.expect(csv_upload_parser)
  def post(self):
    """Admin-only: import payments from a CSV file."""
    args = csv_upload_parser.parse_args()
    upload = args["file"]
    if not upload.filename.lower().endswith(".csv"):
      transactions_ns.abort(400, "Only .csv files are accepted")
    return TransactionService.import_payments_from_csv(upload.stream)


@me_ns.route("")
class MeResource(Resource):
  @_handle_errors
  @active_user_required
  def get(self):
    """Dashboard summary for the logged-in user."""
    return UserService.get_profile_summary(g.current_user)


@me_ns.route("/password")
class MePasswordResource(Resource):
  @_handle_errors
  @jwt_required_custom
  @me_ns.expect(change_password_model, validate=True)
  def post(self):
    """Change the current user's password."""
    payload = me_ns.payload
    AuthService.change_password(
      g.current_user,
      payload["current_password"],
      payload["new_password"],
    )
    return {"message": "Password updated successfully"}


@me_ns.route("/subscriptions")
class MeSubscriptionsResource(Resource):
  @_handle_errors
  @active_user_required
  def get(self):
    subs = SubscriptionService.list_for_user(g.current_user.id)
    return [s.to_dict(include_building=True) for s in subs]


@me_ns.route("/chips")
class MeChipsResource(Resource):
  @_handle_errors
  @active_user_required
  def get(self):
    chips = ChipService.list_for_user(g.current_user.id)
    return [c.to_dict() for c in chips]


@me_ns.route("/transactions")
class MeTransactionsResource(Resource):
  @_handle_errors
  @active_user_required
  def get(self):
    transactions = TransactionService.list_for_user(g.current_user.id)
    return [t.to_dict() for t in transactions]


@health_ns.route("")
class HealthResource(Resource):
  def get(self):
    return {"status": "ok"}
