"""Shared multi-term text search helpers."""

import re

from sqlalchemy import func
from sqlalchemy.orm import Query
from sqlalchemy.sql.elements import ColumnElement

from app.extensions import db
from app.models import Building, User, UserPhone


def search_terms(query: str | None) -> list[str]:
  if not query:
    return []
  return [part for part in re.split(r"\s+", query.strip()) if part]


def filter_by_terms(
  query: Query,
  terms: list[str],
  *field_exprs: ColumnElement,
) -> Query:
  """Every term must match at least one field (case-insensitive substring)."""
  if not terms:
    return query
  for term in terms:
    pattern = f"%{term}%"
    query = query.filter(db.or_(*[expr.ilike(pattern) for expr in field_exprs]))
  return query


def user_full_name_expr():
  return func.trim(
    func.coalesce(User.first_name, "") + " " + func.coalesce(User.last_name, "")
  )


def user_search_exprs() -> tuple[ColumnElement, ...]:
  return (
    User.id_number,
    User.email,
    User.first_name,
    User.last_name,
    user_full_name_expr(),
    UserPhone.phone_number,
    UserPhone.label,
  )


def building_search_exprs() -> tuple[ColumnElement, ...]:
  number_name = func.trim(
    func.coalesce(Building.building_number, "")
    + " "
    + func.coalesce(Building.name, "")
  )
  name_number = func.trim(
    func.coalesce(Building.name, "")
    + " "
    + func.coalesce(Building.building_number, "")
  )
  return (
    Building.building_number,
    Building.name,
    Building.address,
    number_name,
    name_number,
  )
