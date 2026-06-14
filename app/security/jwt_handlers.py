"""Flask-JWT-Extended error callbacks."""

from flask import jsonify


def register_jwt_handlers(jwt):
  @jwt.unauthorized_loader
  def missing_token(reason):
    return jsonify({"message": reason or "Missing Authorization Header"}), 401

  @jwt.invalid_token_loader
  def invalid_token(reason):
    return jsonify({"message": reason or "Invalid token"}), 401

  @jwt.expired_token_loader
  def expired_token(_jwt_header, _jwt_payload):
    return jsonify({"message": "Token has expired"}), 401

  @jwt.revoked_token_loader
  def revoked_token(_jwt_header, _jwt_payload):
    return jsonify({"message": "Token has been revoked"}), 401

  @jwt.needs_fresh_token_loader
  def needs_fresh_token(_jwt_header, _jwt_payload):
    return jsonify({"message": "Fresh token required"}), 401
