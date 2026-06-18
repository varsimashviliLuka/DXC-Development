"""Display formatting helpers."""

from urllib.parse import urlparse

_MAP_LINK_HINTS = (
  "maps.google.",
  "google.com/maps",
  "goo.gl/maps",
  "maps.app.goo.gl",
)


def external_url(value: str | None) -> str | None:
  """
  Return a safe external URL if the value looks like a web/map link.

  Plain street addresses return None so callers can render text instead.
  """
  text = (value or "").strip()
  if not text:
    return None

  if text.startswith(("http://", "https://")):
    parsed = urlparse(text)
    if parsed.scheme in ("http", "https") and parsed.netloc:
      return text
    return None

  lower = text.lower()
  if lower.startswith("www.") or any(hint in lower for hint in _MAP_LINK_HINTS):
    return f"https://{text.lstrip('/')}"

  return None
