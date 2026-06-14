"""Parse payment beneficiary hints from bank transfer text fields."""

import re

from app.enums import PaymentMatchMethod
from app.models import User
from app.utils.georgian_names import parse_georgian_partner_name
from app.utils.validators import ValidationError, normalize_phone, validate_id_number

# Credit this account: UID:01010015553  or  UID:+995592159199
# Aliases: FOR:, BENEFICIARY:, ACCOUNT:
UID_TOKEN_PATTERN = re.compile(
  r"(?:UID|FOR|BENEFICIARY|ACCOUNT)\s*:\s*([+\dA-Za-z\-]+)",
  re.IGNORECASE,
)
DIGITS_ONLY = re.compile(r"\d+")


class PaymentMatcher:
  """
  Resolve which user receives a bank payment.

  Priority (first match wins):
    1. UID:/FOR:/BENEFICIARY:/ACCOUNT: token in description fields
    2. Partner's Tax Code matched to user id_number
    3. ID number extracted from end of Partner's Name
  """

  @staticmethod
  def extract_uid_token(*texts: str | None) -> str | None:
    for text in texts:
      if not text:
        continue
      match = UID_TOKEN_PATTERN.search(text)
      if match:
        return match.group(1).strip()
    return None

  @staticmethod
  def normalize_tax_code(value: str | None) -> str | None:
    if not value:
      return None
    digits = "".join(DIGITS_ONLY.findall(value))
    return digits or None

  @staticmethod
  def find_user_by_identifier(identifier: str) -> User | None:
    identifier = identifier.strip()
    if not identifier:
      return None

    if identifier.startswith("+") or identifier.isdigit():
      try:
        phone = normalize_phone(identifier)
        return User.query.filter_by(phone_number=phone).first()
      except ValidationError:
        pass

    try:
      id_num = validate_id_number(identifier)
      user = User.query.filter_by(id_number=id_num).first()
      if user:
        return user
    except ValidationError:
      pass

    tax = PaymentMatcher.normalize_tax_code(identifier)
    if tax:
      return PaymentMatcher.find_user_by_tax_code(tax)
    return None

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
    uid_token = cls.extract_uid_token(
      description, additional_information, additional_description
    )
    if uid_token:
      user = cls.find_user_by_identifier(uid_token)
      if user:
        return user, PaymentMatchMethod.UID_TOKEN, uid_token

    if partner_tax_code:
      user = cls.find_user_by_tax_code(partner_tax_code)
      if user:
        return user, PaymentMatchMethod.PARTNER_TAX_CODE, partner_tax_code

    name_id = cls.extract_id_from_partner_name(partner_name)
    if name_id:
      user = cls.find_user_by_tax_code(name_id)
      if user:
        return user, PaymentMatchMethod.PARTNER_NAME_ID, name_id

    return None, None, uid_token or partner_tax_code or name_id
