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


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_mapping(
        SECRET_KEY=_load_secret_key(app.instance_path),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL",
            "sqlite:///" + os.path.join(app.instance_path, "padel.db"),
        ),
        # Set ALLOW_REGISTRATION=0 to close sign-ups once everyone has an account.
        ALLOW_REGISTRATION=os.environ.get("ALLOW_REGISTRATION", "1") == "1",
    )
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
