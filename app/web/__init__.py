"""Web blueprint registration."""

from app.web.admin.routes import admin_bp
from app.web.admin.api_routes import admin_api_bp
from app.web.auth.routes import auth_bp
from app.web.main.routes import main_bp
from app.web.user.routes import user_bp


def register_web_blueprints(app):
  app.register_blueprint(main_bp)
  app.register_blueprint(auth_bp, url_prefix="/auth")
  app.register_blueprint(admin_bp, url_prefix="/admin")
  app.register_blueprint(admin_api_bp, url_prefix="/admin/api")
  app.register_blueprint(user_bp, url_prefix="/dashboard")
