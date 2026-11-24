import os
import secrets

import click
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def _load_secret_key(instance_path):
    """Use SECRET_KEY from the environment, or a key persisted in the instance folder."""
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    key_file = os.path.join(instance_path, "secret_key")
    if not os.path.exists(key_file):
        with open(key_file, "w") as f:
            f.write(secrets.token_hex(32))
    with open(key_file) as f:
        return f.read().strip()


def _database_url(instance_path):
    """DATABASE_URL from the environment (e.g. Supabase), or a local SQLite file."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        return "sqlite:///" + os.path.join(instance_path, "padel.db")
    # Supabase/Heroku-style URLs -> use the psycopg 3 driver.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def _engine_options(url):
    if not url.startswith("postgresql"):
        return {}
    return {
        "pool_pre_ping": True,   # survive connections dropped by the pooler/idle DB
        "pool_recycle": 300,
        # Server-side prepared statements break with Supabase's transaction pooler.
        "connect_args": {"prepare_threshold": None},
    }


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    db_url = _database_url(app.instance_path)
    app.config.from_mapping(
        SECRET_KEY=_load_secret_key(app.instance_path),
        SQLALCHEMY_DATABASE_URI=db_url,
        SQLALCHEMY_ENGINE_OPTIONS=_engine_options(db_url),
        # Set ALLOW_REGISTRATION=0 to close sign-ups once everyone has an account.
        ALLOW_REGISTRATION=os.environ.get("ALLOW_REGISTRATION", "1") == "1",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SAMESITE="Lax",
    )
    # PRODUCTION=1 when served over HTTPS behind a host's proxy.
    if os.environ.get("PRODUCTION") == "1":
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
        app.config.update(SESSION_COOKIE_SECURE=True, REMEMBER_COOKIE_SECURE=True,
                          PREFERRED_URL_SCHEME="https")
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    from . import models  # noqa: F401  (register models)
    from .auth import bp as auth_bp
    from .views import bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()

    @app.cli.command("make-admin")
    @click.argument("username")
    def make_admin(username):
        """Give admin rights to an existing user."""
        user = db.session.scalar(db.select(models.User).filter_by(username=username))
        if user is None:
            raise click.ClickException(f"No user named {username!r}")
        user.is_admin = True
        db.session.commit()
        click.echo(f"{username} is now an admin.")

    return app
