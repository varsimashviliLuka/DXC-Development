"""Georgian bank CSV import and payment matching."""

import csv
import io
import logging
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.enums import ImportMatchStatus, PaymentMatchMethod, TransactionStatus, TransactionType
from app.extensions import db
from app.models import BankImport, Transaction, User
from app.utils.georgian_names import parse_georgian_partner_name
from app.utils.payment_matching import PaymentMatcher

logger = logging.getLogger(__name__)

# English column names from TBC/BoG export (row 2 in file)
BANK_CSV_COLUMNS = {
  "date": "Date",
  "description": "Description",
  "transaction_type": "Transaction Type",
  "amount": "Amount",
  "currency": "Currency",
  "account_number": "Account Number",
  "account_name": "Account Name",
  "additional_information": "Additional Information",
  "document_date": "Document Date",
  "document_number": "Document Number",
  "partner_account": "Partner's Account",
  "partner_name": "Partner's Name",
  "partner_tax_code": "Partner's Tax Code",
  "partner_bank_code": "Partner's Bank Code",
  "partner_bank": "Partner's Bank",
  "intermediary_bank_code": "Intermediary Bank Code",
  "intermediary_bank": "Intermediary Bank",
  "charge_details": "Charge Details",
  "taxpayer_code": "Taxpayer Code",
  "taxpayer_name": "Taxpayer Name",
  "treasury_code": "Treasury Code",
  "op_code": "Op.Code",
  "additional_description": "Additional Description",
  "transaction_id": "Transaction ID",
}


class BankImportService:
  _SPLIT_QUANT = Decimal("0.01")

  @staticmethod
  def import_bank_csv(file_stream) -> dict:
    content = file_stream.read()
    if isinstance(content, bytes):
      content = content.decode("utf-8-sig")

    rows = list(csv.reader(io.StringIO(content)))
    if len(rows) < 2:
      raise ValueError("CSV file is empty or missing header rows")

    header_row_index = BankImportService._find_english_header_row(rows)
    if header_row_index is None:
      raise ValueError(
        "Could not find English header row (expected columns like 'Transaction ID', 'Amount')"
      )

    headers = [h.strip() for h in rows[header_row_index]]
    batch_id = str(uuid.uuid4())

    matched = 0
    unmatched = 0
    skipped = 0
    duplicates = 0
    errors: list[dict] = []

    for row_num, row in enumerate(rows[header_row_index + 1 :], start=header_row_index + 2):
      if not row or all(not (cell or "").strip() for cell in row):
        continue

      record = dict(zip(headers, row))
      try:
        outcome = BankImportService._process_row(record, batch_id, row_num)
        if outcome == "matched":
          matched += 1
        elif outcome == "unmatched":
          unmatched += 1
        elif outcome == "skipped":
          skipped += 1
        elif outcome == "duplicate":
          duplicates += 1
      except Exception as exc:
        db.session.rollback()
        errors.append({"row": row_num, "error": str(exc)})
        logger.warning("Bank CSV row %s failed: %s", row_num, exc)

    logger.info(
      "Bank CSV import batch=%s matched=%s unmatched=%s skipped=%s duplicates=%s",
      batch_id,
      matched,
      unmatched,
      skipped,
      duplicates,
    )
    return {
      "batch_id": batch_id,
      "matched": matched,
      "unmatched": unmatched,
      "skipped": skipped,
      "duplicates": duplicates,
      "errors": errors,
    }

  @staticmethod
  def _find_english_header_row(rows: list[list[str]]) -> int | None:
    for idx, row in enumerate(rows):
      normalized = {cell.strip() for cell in row if cell and cell.strip()}
      if "Transaction ID" in normalized and "Amount" in normalized:
        return idx
    return None

  @staticmethod
  def _parse_date(value: str | None):
    if not value or not value.strip():
      return None
    value = value.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
      try:
        return datetime.strptime(value, fmt).date()
      except ValueError:
        continue
    return None

  @staticmethod
  def _process_row(record: dict, batch_id: str, row_num: int) -> str:
    bank_txn_id = (record.get(BANK_CSV_COLUMNS["transaction_id"]) or "").strip()
    if not bank_txn_id:
      raise ValueError("Missing Transaction ID")

    existing = BankImport.query.filter_by(bank_transaction_id=bank_txn_id).first()
    if existing:
      return "duplicate"

    txn_type = (record.get(BANK_CSV_COLUMNS["transaction_type"]) or "").strip()
    try:
      amount = Decimal((record.get(BANK_CSV_COLUMNS["amount"]) or "0").replace(",", ""))
    except InvalidOperation as exc:
      raise ValueError("Invalid amount") from exc

    description = (record.get(BANK_CSV_COLUMNS["description"]) or "").strip()
    additional_info = (record.get(BANK_CSV_COLUMNS["additional_information"]) or "").strip()
    additional_desc = (record.get(BANK_CSV_COLUMNS["additional_description"]) or "").strip()
    partner_tax = (record.get(BANK_CSV_COLUMNS["partner_tax_code"]) or "").strip()
    partner_name = (record.get(BANK_CSV_COLUMNS["partner_name"]) or "").strip()

    if txn_type.lower() != "income" or amount <= 0:
      bank_import = BankImportService._create_bank_import(
        record=record,
        batch_id=batch_id,
        bank_txn_id=bank_txn_id,
        amount=amount,
        match_status=ImportMatchStatus.SKIPPED,
        skip_reason=f"Not an incoming payment ({txn_type or 'unknown'})",
      )
      db.session.add(bank_import)
      db.session.commit()
      return "skipped"

    users, multi_method, multi_hint = PaymentMatcher.resolve_beneficiaries(
      description=description,
      additional_information=additional_info,
      additional_description=additional_desc,
      partner_tax_code=partner_tax,
      partner_name=partner_name,
    )
    if users:
      bank_import = BankImportService._create_bank_import(
        record=record,
        batch_id=batch_id,
        bank_txn_id=bank_txn_id,
        amount=amount,
        match_status=ImportMatchStatus.MATCHED,
        match_method=multi_method,
        match_hint=multi_hint,
        user_id=users[0].id,
      )
      db.session.add(bank_import)
      db.session.flush()
      BankImportService._credit_users_split(bank_import, users)
      db.session.commit()
      return "matched"

    user, method, hint = PaymentMatcher.resolve_beneficiary(
      description=description,
      additional_information=additional_info,
      additional_description=additional_desc,
      partner_tax_code=partner_tax,
      partner_name=partner_name,
    )

    if user:
      bank_import = BankImportService._create_bank_import(
        record=record,
        batch_id=batch_id,
        bank_txn_id=bank_txn_id,
        amount=amount,
        match_status=ImportMatchStatus.MATCHED,
        match_method=method,
        match_hint=hint,
        user_id=user.id,
      )
      db.session.add(bank_import)
      db.session.flush()
      BankImportService._credit_user(bank_import, user)
      db.session.commit()
      return "matched"

    bank_import = BankImportService._create_bank_import(
      record=record,
      batch_id=batch_id,
      bank_txn_id=bank_txn_id,
      amount=amount,
      match_status=ImportMatchStatus.UNMATCHED,
      match_hint=hint,
      skip_reason="No registered user matched",
    )
    db.session.add(bank_import)
    db.session.commit()
    return "unmatched"

  @staticmethod
  def _create_bank_import(
    *,
    record: dict,
    batch_id: str,
    bank_txn_id: str,
    amount: Decimal,
    match_status: ImportMatchStatus,
    match_method: PaymentMatchMethod | None = None,
    match_hint: str | None = None,
    user_id: int | None = None,
    skip_reason: str | None = None,
  ) -> BankImport:
    raw_partner_name = (record.get(BANK_CSV_COLUMNS["partner_name"]) or "").strip() or None
    partner_parsed = parse_georgian_partner_name(raw_partner_name)

    return BankImport(
      bank_transaction_id=bank_txn_id,
      import_batch_id=batch_id,
      transaction_date=BankImportService._parse_date(record.get(BANK_CSV_COLUMNS["date"])),
      description=(record.get(BANK_CSV_COLUMNS["description"]) or "").strip() or None,
      bank_transaction_type=(
        record.get(BANK_CSV_COLUMNS["transaction_type"]) or ""
      ).strip()
      or None,
      amount=amount,
      currency=(record.get(BANK_CSV_COLUMNS["currency"]) or "GEL").strip(),
      partner_account=(record.get(BANK_CSV_COLUMNS["partner_account"]) or "").strip() or None,
      partner_name_raw=raw_partner_name,
      partner_name=partner_parsed.display_name,
      partner_first_name=partner_parsed.first_name,
      partner_last_name=partner_parsed.last_name,
      partner_tax_code=(record.get(BANK_CSV_COLUMNS["partner_tax_code"]) or "").strip() or None,
      additional_information=(
        record.get(BANK_CSV_COLUMNS["additional_information"]) or ""
      ).strip()
      or None,
      additional_description=(
        record.get(BANK_CSV_COLUMNS["additional_description"]) or ""
      ).strip()
      or None,
      document_date=BankImportService._parse_date(
        record.get(BANK_CSV_COLUMNS["document_date"])
      ),
      document_number=(record.get(BANK_CSV_COLUMNS["document_number"]) or "").strip() or None,
      op_code=(record.get(BANK_CSV_COLUMNS["op_code"]) or "").strip() or None,
      match_status=match_status,
      match_method=match_method,
      match_hint=match_hint,
      user_id=user_id,
      skip_reason=skip_reason,
    )

  @staticmethod
  def _credit_user(bank_import: BankImport, user: User) -> Transaction:
    user.balance += bank_import.amount
    txn = Transaction(
      user_id=user.id,
      amount=bank_import.amount,
      transaction_type=TransactionType.PAYMENT,
      status=TransactionStatus.COMPLETED,
      description=(bank_import.description or "Bank payment")[:500],
      reference=f"BANK-{bank_import.bank_transaction_id}",
      bank_import_id=bank_import.id,
    )
    db.session.add(txn)

    from app.services.subscription_service import SubscriptionService

    SubscriptionService.reconcile_after_balance_change(user)
    return txn

  @staticmethod
  def _split_amount(total: Decimal, parts: int) -> list[Decimal]:
    if parts <= 0:
      return []
    base = (total / parts).quantize(BankImportService._SPLIT_QUANT)
    splits = [base for _ in range(parts)]
    current_sum = sum(splits, Decimal("0.00"))
    remainder = total - current_sum
    # Keep exact accounting by applying rounding remainder to the first recipient.
    splits[0] += remainder
    return splits

  @staticmethod
  def _credit_users_split(bank_import: BankImport, users: list[User]) -> None:
    if not users:
      return

    if len(users) == 1:
      BankImportService._credit_user(bank_import, users[0])
      return

    amounts = BankImportService._split_amount(bank_import.amount, len(users))
    for idx, (user, amount) in enumerate(zip(users, amounts), start=1):
      user.balance += amount
      txn = Transaction(
        user_id=user.id,
        amount=amount,
        transaction_type=TransactionType.PAYMENT,
        status=TransactionStatus.COMPLETED,
        description=(
          f"{(bank_import.description or 'Bank payment')[:450]} "
          f"(split {idx}/{len(users)})"
        )[:500],
        reference=f"BANK-{bank_import.bank_transaction_id}-SPLIT-{idx}",
        bank_import_id=bank_import.id if idx == 1 else None,
      )
      db.session.add(txn)

      from app.services.subscription_service import SubscriptionService

      SubscriptionService.reconcile_after_balance_change(user)

  @staticmethod
  def list_unmatched(limit: int = 20):
    return (
      BankImport.query.filter_by(match_status=ImportMatchStatus.UNMATCHED)
      .order_by(BankImport.created_at.desc())
      .limit(limit)
      .all()
    )

  @staticmethod
  def count_unmatched() -> int:
    return BankImport.query.filter_by(match_status=ImportMatchStatus.UNMATCHED).count()

  @staticmethod
  def get_by_id(import_id: int) -> BankImport:
    from app.utils.errors import NotFoundError

    record = db.session.get(BankImport, import_id)
    if not record:
      raise NotFoundError("Bank import record not found")
    return record

  @staticmethod
  def assign_to_user(import_id: int, user_id: int) -> BankImport:
    bank_import = BankImportService.get_by_id(import_id)
    if bank_import.match_status != ImportMatchStatus.UNMATCHED:
      raise ValueError("Only unmatched imports can be assigned")

    user = db.session.get(User, user_id)
    if not user:
      raise ValueError("User not found")

    bank_import.match_status = ImportMatchStatus.MATCHED
    bank_import.match_method = PaymentMatchMethod.MANUAL
    bank_import.user_id = user.id
    bank_import.skip_reason = None
    BankImportService._credit_user(bank_import, user)
    db.session.commit()
    logger.info("Manually assigned bank_import_id=%s to user_id=%s", import_id, user_id)
    return bank_import

  @staticmethod
  def create_user_and_assign(
    import_id: int,
    *,
    phone_number: str,
    password: str,
    email: str | None = None,
  ) -> User:
    from app.services.auth_service import AuthService

    bank_import = BankImportService.get_by_id(import_id)
    if bank_import.match_status != ImportMatchStatus.UNMATCHED:
      raise ValueError("Only unmatched imports can be used to create a user")

    id_number = PaymentMatcher.normalize_tax_code(bank_import.partner_tax_code)
    if not id_number:
      raise ValueError("Bank record has no partner tax code for ID number")

    user = AuthService.register_user(
      id_number=id_number,
      password=password,
      phones=[{"phone_number": phone_number, "label": "Personal", "is_primary": True}]
      if phone_number
      else None,
      email=email,
      first_name=bank_import.partner_first_name,
      last_name=bank_import.partner_last_name,
    )
    BankImportService.assign_to_user(import_id, user.id)
    return user
