"""Parse payer names from Georgian bank CSV exports."""

import re
from dataclasses import dataclass

# Legal-entity prefix before a natural person's name (not part of the name).
GEORGIAN_LEGAL_PREFIX = re.compile(r"^ი/მ\s+", re.IGNORECASE)
# Personal number appended after comma: ", 01010015553"
PARTNER_NAME_ID_SUFFIX = re.compile(r",\s*(\d{9,11})\s*$")


@dataclass
class ParsedPartnerName:
  first_name: str | None
  last_name: str | None
  display_name: str | None
  id_suffix: str | None
  raw: str | None


def parse_georgian_partner_name(raw: str | None) -> ParsedPartnerName:
  """
  Parse Partner's Name from bank CSV.

  Examples:
    "ი/მ დავით მაღლაკელიძე" -> first=დავით, last=მაღლაკელიძe
    "ი/მ ზურაბ ოქროცვარიძე, 01010015553" -> same + id_suffix
    "ალექსი ნოზაძე, 01010017857" -> first=ალექსი, last=ნოზაძe
  """
  if not raw or not raw.strip():
    return ParsedPartnerName(None, None, None, None, raw)

  text = raw.strip()
  id_suffix = None

  id_match = PARTNER_NAME_ID_SUFFIX.search(text)
  if id_match:
    id_suffix = id_match.group(1)
    text = text[: id_match.start()].strip()

  text = GEORGIAN_LEGAL_PREFIX.sub("", text).strip()

  if not text:
    return ParsedPartnerName(None, None, None, id_suffix, raw)

  parts = text.split()
  if len(parts) == 1:
    return ParsedPartnerName(parts[0], None, parts[0], id_suffix, raw)

  first_name = parts[0]
  last_name = " ".join(parts[1:])
  display_name = f"{first_name} {last_name}".strip()
  return ParsedPartnerName(first_name, last_name, display_name, id_suffix, raw)
