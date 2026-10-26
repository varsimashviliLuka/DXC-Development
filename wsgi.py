"""WSGI entry point for gunicorn (`gunicorn wsgi:app`) and the `flask` CLI."""

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402

app = create_app()
