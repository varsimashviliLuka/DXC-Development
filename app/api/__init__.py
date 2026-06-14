"""Flask-RESTX API blueprint registration."""

from flask_restx import Api

from app.api.namespaces import (
  auth_ns,
  buildings_ns,
  chips_ns,
  health_ns,
  me_ns,
  subscriptions_ns,
  transactions_ns,
  users_ns,
)


def register_api(blueprint):
  api = Api(
    blueprint,
    version="1.0",
    title="Elevator Chip API",
    description="REST API for elevator chip subscriptions, users, and buildings.",
    doc="/docs",
    security="Bearer",
    authorizations={
      "Bearer": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": 'JWT token. Format: "Bearer <token>"',
      }
    },
  )

  api.add_namespace(health_ns, path="/health")
  api.add_namespace(auth_ns, path="/auth")
  api.add_namespace(users_ns, path="/users")
  api.add_namespace(buildings_ns, path="/buildings")
  api.add_namespace(subscriptions_ns, path="/subscriptions")
  api.add_namespace(chips_ns, path="/chips")
  api.add_namespace(transactions_ns, path="/transactions")
  api.add_namespace(me_ns, path="/me")

  return api
