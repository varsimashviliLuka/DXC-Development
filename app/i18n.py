"""Two-language support (Georgian / English). Language is stored in a cookie."""

from flask import current_app, g, request

from app.translations import MESSAGES

LANGUAGES = {"ka": "ქართული", "en": "English"}
LANGUAGE_COOKIE = "lang"
LANGUAGE_COOKIE_MAX_AGE = 365 * 24 * 3600


def get_locale() -> str:
  if "lang" not in g:
    lang = request.cookies.get(LANGUAGE_COOKIE)
    g.lang = lang if lang in LANGUAGES else current_app.config["DEFAULT_LANGUAGE"]
  return g.lang


def t(key: str, **params):
  """Translate a key into the current language; lists (bullet points) are returned as-is."""
  entry = MESSAGES.get(key)
  if entry is None:
    current_app.logger.warning("Missing translation key %s", key)
    return key
  value = entry.get(get_locale()) or entry["en"]
  if params and isinstance(value, str):
    return value.format(**params)
  return value


def localized(values: dict) -> str:
  """Pick the current language from a {"en": ..., "ka": ...} mapping such as company address."""
  return values.get(get_locale()) or values.get("en") or ""


def init_i18n(app) -> None:
  app.jinja_env.globals.update(t=t, localized=localized, LANGUAGES=LANGUAGES)

  @app.context_processor
  def inject_locale():
    return {"lang": get_locale()}
