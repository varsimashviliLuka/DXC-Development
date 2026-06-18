"""Tests for address/link formatting."""

from app.utils.formatting import external_url


def test_external_url_accepts_https_map_link():
  url = "https://maps.google.com/?q=41.7151,44.8271"
  assert external_url(url) == url


def test_external_url_accepts_map_link_without_scheme():
  assert external_url("maps.google.com/?q=Tbilisi") == "https://maps.google.com/?q=Tbilisi"


def test_external_url_rejects_plain_address():
  assert external_url("12 Rustaveli Ave, Tbilisi") is None


def test_external_url_empty():
  assert external_url("") is None
  assert external_url(None) is None
