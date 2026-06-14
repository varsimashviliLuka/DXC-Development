import io

from app.utils.georgian_names import parse_georgian_partner_name


def test_strips_im_prefix_and_splits_name():
  parsed = parse_georgian_partner_name("ი/მ დავით მაღლაკელიძე")
  assert parsed.first_name == "დავით"
  assert parsed.last_name == "მაღლაკელიძე"
  assert parsed.display_name == "დავით მაღლაკელიძე"
  assert parsed.id_suffix is None


def test_strips_im_prefix_with_trailing_id():
  parsed = parse_georgian_partner_name("ი/მ ზურაბ ოქროცვარიძე, 01010015553")
  assert parsed.first_name == "ზურაბ"
  assert parsed.last_name == "ოქროცვარიძე"
  assert parsed.id_suffix == "01010015553"


def test_name_without_im_prefix():
  parsed = parse_georgian_partner_name("ალექსი ნოზაძე, 01010017857")
  assert parsed.first_name == "ალექსი"
  assert parsed.last_name == "ნოზაძე"
  assert parsed.id_suffix == "01010017857"


def test_empty_name():
  parsed = parse_georgian_partner_name("")
  assert parsed.first_name is None
  assert parsed.last_name is None


def test_bank_import_parses_georgian_partner_name(client, admin_headers):
  from tests.bank_csv_fixtures import build_bank_csv, make_bank_csv_row
  from app.models import BankImport

  csv_content = build_bank_csv(
    make_bank_csv_row(
      partner_name="ი/მ დავით მაღლაკელიძე, 01010015553",
      partner_tax="01010015553",
      transaction_id="18709999999.20",
    )
  )
  response = client.post(
    "/api/v1/transactions/import",
    data={"file": (io.BytesIO(csv_content.encode("utf-8")), "bank.csv")},
    headers=admin_headers,
    content_type="multipart/form-data",
  )
  assert response.status_code == 200

  with client.application.app_context():
    record = BankImport.query.filter_by(bank_transaction_id="18709999999.20").first()
    assert record is not None
    assert record.partner_first_name == "დავით"
    assert record.partner_last_name == "მაღლაკელიძე"
    assert record.partner_name == "დავით მაღლაკელიძე"
    assert record.partner_name_raw.startswith("ი/მ")
