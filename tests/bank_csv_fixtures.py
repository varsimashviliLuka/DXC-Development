"""Sample Georgian bank CSV for tests."""

import csv
import io

ENGLISH_HEADERS = [
  "Date",
  "Description",
  "Transaction Type",
  "Amount",
  "Currency",
  "Account Number",
  "Account Name",
  "Additional Information",
  "Document Date",
  "Document Number",
  "Partner's Account",
  "Partner's Name",
  "Partner's Tax Code",
  "Partner's Bank Code",
  "Partner's Bank",
  "Intermediary Bank Code",
  "Intermediary Bank",
  "Charge Details",
  "Taxpayer Code",
  "Taxpayer Name",
  "Treasury Code",
  "Op.Code",
  "Additional Description",
  "Transaction ID",
]

GEORGIAN_HEADERS = [
  "თარიღი",
  "დანიშნულება",
  "ტრანზაქციის ტიპი",
  "თანხა",
  "ვალუტა",
  "ანგარიშის ნომერი",
  "ანგარიშის დასახელება",
  "დამატებითი ინფორმაცია",
  "საბუთის თარიღი",
  "საბუთის №",
  "პარტნიორის ანგარიში",
  "პარტნიორი",
  "პარტნიორის საგადასახადო კოდი",
  "პარტნიორის ბანკის კოდი",
  "პარტნიორის ბანკი",
  "შუამავალი ბანკის კოდი",
  "შუამავალი ბანკი",
  "ხარჯის ტიპი",
  "გადასახადის გადამხდელის კოდი",
  "გადასახადის გადამხდელის დასახელება",
  "სახაზინო კოდი",
  "ოპ.კოდი",
  "დამატებითი დანიშნულება",
  "ტრანზაქციის ID",
]


def make_bank_csv_row(
  *,
  date="11/02/2026",
  description="Test payment",
  amount="100.0",
  partner_tax="01010018012",
  partner_name="Test User",
  additional_description="",
  transaction_id="18705073767.20",
  transaction_type="Income",
):
  values = {
    "Date": date,
    "Description": description,
    "Transaction Type": transaction_type,
    "Amount": amount,
    "Currency": "GEL",
    "Account Number": "GE91TB7473634050100001",
    "Account Name": "Test Account",
    "Additional Information": "",
    "Document Date": date,
    "Document Number": "840013",
    "Partner's Account": "GE21BG0000000184586000",
    "Partner's Name": partner_name,
    "Partner's Tax Code": partner_tax,
    "Partner's Bank Code": "BAGAGE22",
    "Partner's Bank": "Test Bank",
    "Additional Description": additional_description,
    "Transaction ID": transaction_id,
  }
  return [values.get(h, "") for h in ENGLISH_HEADERS]


def build_bank_csv(*data_rows: list[str]) -> str:
  buffer = io.StringIO()
  writer = csv.writer(buffer)
  writer.writerow(GEORGIAN_HEADERS)
  writer.writerow(ENGLISH_HEADERS)
  for row in data_rows:
    writer.writerow(row)
  return buffer.getvalue()
