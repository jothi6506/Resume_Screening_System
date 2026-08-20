"""Flask application factory."""

import os

from flask import Flask

from app.config import config
from app.extensions import csrf, db, login_manager, migrate


def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Ensure upload directory exists
    upload_path = os.path.join(app.root_path, "..", app.config["UPLOAD_FOLDER"])
    os.makedirs(upload_path, exist_ok=True)

    _init_extensions(app)
    _register_blueprints(app)
    _register_context_processors(app)
    _register_jinja_filters(app)
    _register_error_handlers(app)
    _register_cli(app)

    # Enable WhiteNoise for production static file serving
    try:
        from whitenoise import WhiteNoise
        static_folder = os.path.join(app.root_path, "static")
        app.wsgi_app = WhiteNoise(app.wsgi_app, root=static_folder, prefix="static/")
    except Exception:
        pass

    return app



def _register_jinja_filters(app):
    import json
    app.jinja_env.filters["fromjson"] = lambda s: json.loads(s) if s else {}
    app.jinja_env.filters["pct"] = lambda v: f"{round(v * 100)}%"



def _init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            app.logger.warning(f"Auto DB setup notice: {e}")

    from app.models import (  # noqa: F401 — register all models
        Application,
        Candidate,
        Job,
        Resume,
        Skill,
        User,
    )

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))


def _register_blueprints(app):
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.resumes import resumes_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(resumes_bp)


def _register_context_processors(app):
    from flask import request

    from app.utils.nav import NAV_ITEMS

    @app.context_processor
    def inject_globals():
        active_nav = None
        if request.endpoint:
            for item in NAV_ITEMS:
                if request.endpoint == item["endpoint"]:
                    active_nav = item["id"]
                    break

        return {
            "app_name": "ResumeScreen AI",
            "ai_enabled": app.config.get("AI_ENABLED", False),
            "nav_items": NAV_ITEMS,
            "active_nav": active_nav,
        }


def _register_error_handlers(app):
    from flask import render_template

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500


def _register_cli(app):
    from app.cli import register_commands

    register_commands(app)
