"""Parse payment beneficiary hints from bank transfer text fields."""

import re

from app.enums import PaymentMatchMethod
from app.models import Building, Subscription, User
from app.utils.georgian_names import parse_georgian_partner_name

DIGITS_ONLY = re.compile(r"\d+")
REFERENCE_PART = re.compile(r"[^A-Za-z0-9]+")


def compact_reference_part(value: str) -> str:
  return REFERENCE_PART.sub("", value.strip())


def build_payment_reference(
  building_id: int,
  building_number: str,
  door_number: str,
) -> str:
  """
  Compact payment code: building.id + building_number + door_number (no separators).

  Example: id=3, building_number="500", door_number="12A" -> "350012A"
  """
  return (
    f"{building_id}"
    f"{compact_reference_part(building_number)}"
    f"{compact_reference_part(door_number)}"
  )


class PaymentMatcher:
  """
  Resolve which user receives a bank payment.

  Priority (first match wins):
    1. Building payment references in description fields (id + building_number + door)
    2. Partner's Tax Code matched to user id_number
    3. ID number extracted from end of Partner's Name
  """

  @staticmethod
  def _payment_reference_map() -> dict[str, Subscription]:
    mapping: dict[str, Subscription] = {}
    for subscription in Subscription.query.join(Building).all():
      if not subscription.building:
        continue
      reference = build_payment_reference(
        subscription.building_id,
        subscription.building.building_number,
        subscription.door_number,
      ).upper()
      mapping[reference] = subscription
    return mapping

  @classmethod
  def extract_door_references(cls, *texts: str | None) -> list[str]:
    reference_map = cls._payment_reference_map()
    if not reference_map:
      return []

    found: list[str] = []
    seen: set[str] = set()

    combined = " ".join(text for text in texts if text)
    if combined:
      for reference in sorted(reference_map.keys(), key=len, reverse=True):
        if reference in seen:
          continue
        if re.search(re.escape(reference), combined, re.IGNORECASE):
          seen.add(reference)
          found.append(reference)

    for text in texts:
      if not text:
        continue
      for part in re.split(r"[,;\s]+", text):
        token = compact_reference_part(part).upper()
        if token and token in reference_map and token not in seen:
          seen.add(token)
          found.append(token)

    return found

  @staticmethod
  def normalize_tax_code(value: str | None) -> str | None:
    if not value:
      return None
    digits = "".join(DIGITS_ONLY.findall(value))
    return digits or None

  @staticmethod
  def find_user_by_tax_code(tax_code: str | None) -> User | None:
    normalized = PaymentMatcher.normalize_tax_code(tax_code)
    if not normalized:
      return None

    user = User.query.filter_by(id_number=normalized).first()
    if user:
      return user

    # Match id_numbers that contain the same digit sequence (e.g. stored with prefix)
    for candidate in User.query.all():
      candidate_digits = PaymentMatcher.normalize_tax_code(candidate.id_number)
      if candidate_digits == normalized:
        return candidate
    return None

  @staticmethod
  def extract_id_from_partner_name(partner_name: str | None) -> str | None:
    return parse_georgian_partner_name(partner_name).id_suffix

  @staticmethod
  def resolve_users_by_door_references(
    door_references: list[str],
  ) -> tuple[list[User], list[str]]:
    if not door_references:
      return [], []

    reference_map = PaymentMatcher._payment_reference_map()
    users: list[User] = []
    seen_user_ids: set[int] = set()
    resolved_hints: list[str] = []

    for reference in door_references:
      subscription = reference_map.get(reference.upper())
      if not subscription:
        continue

      user = subscription.user
      if not user or not subscription.building:
        continue

      resolved_hints.append(
        build_payment_reference(
          subscription.building_id,
          subscription.building.building_number,
          subscription.door_number,
        )
      )
      if user.id in seen_user_ids:
        continue
      seen_user_ids.add(user.id)
      users.append(user)

    return users, resolved_hints

  @classmethod
  def resolve_beneficiaries(
    cls,
    *,
    description: str | None,
    additional_information: str | None,
    additional_description: str | None,
    partner_tax_code: str | None,
    partner_name: str | None,
  ) -> tuple[list[User], PaymentMatchMethod | None, str | None]:
    """
    Returns (users, match_method, hint_used).
    hint_used is the raw token/reference used for matching (for audit).
    """
    door_refs = cls.extract_door_references(
      description, additional_information, additional_description
    )
    if door_refs:
      users, resolved_hints = cls.resolve_users_by_door_references(door_refs)
      if users:
        hint = ",".join(resolved_hints) if resolved_hints else None
        return users, PaymentMatchMethod.DOOR_REFERENCE, hint
      attempted = ",".join(door_refs)
      return [], PaymentMatchMethod.DOOR_REFERENCE, attempted

    return [], None, None

  @classmethod
  def resolve_beneficiary(
    cls,
    *,
    description: str | None,
    additional_information: str | None,
    additional_description: str | None,
    partner_tax_code: str | None,
    partner_name: str | None,
  ) -> tuple[User | None, PaymentMatchMethod | None, str | None]:
    """
    Returns (user, match_method, hint_used).
    hint_used is the raw token or tax code used for matching (for audit).
    """
    if partner_tax_code:
      user = cls.find_user_by_tax_code(partner_tax_code)
      if user:
        return user, PaymentMatchMethod.PARTNER_TAX_CODE, partner_tax_code

    name_id = cls.extract_id_from_partner_name(partner_name)
    if name_id:
      user = cls.find_user_by_tax_code(name_id)
      if user:
        return user, PaymentMatchMethod.PARTNER_NAME_ID, name_id

    return None, None, partner_tax_code or name_id
