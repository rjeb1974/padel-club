from datetime import datetime, timedelta
from urllib.parse import urlsplit

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from . import db
from .models import User

bp = Blueprint("auth", __name__)

MIN_PASSWORD = 8

# Simple brute-force protection: lock a username after repeated failures.
MAX_FAILURES = 5
LOCKOUT = timedelta(minutes=10)
_failures = {}  # username -> (count, first_failure_time)


def _locked(username):
    count, since = _failures.get(username, (0, None))
    if since and datetime.now() - since > LOCKOUT:
        _failures.pop(username, None)
        return False
    return count >= MAX_FAILURES


def _record_failure(username):
    count, since = _failures.get(username, (0, datetime.now()))
    _failures[username] = (count + 1, since)


def _safe_next(target):
    """Only allow redirects to paths on this site."""
    if target and not urlsplit(target).netloc and target.startswith("/"):
        return target
    return url_for("main.index")


@bp.route("/register", methods=["GET", "POST"])
def register():
    first_user = db.session.scalar(db.select(db.func.count(User.id))) == 0
    if not current_app.config["ALLOW_REGISTRATION"] and not first_user:
        flash("Registration is closed. Ask an admin to create your account.", "error")
        return redirect(url_for("auth.login"))
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        error = None
        if not username or not name:
            error = "Username and name are required."
        elif not username.replace("_", "").replace(".", "").isalnum():
            error = "Username may only contain letters, numbers, dots and underscores."
        elif len(password) < MIN_PASSWORD:
            error = f"Password must be at least {MIN_PASSWORD} characters."
        elif password != confirm:
            error = "Passwords do not match."
        elif db.session.scalar(db.select(User).filter_by(username=username)):
            error = "That username is taken."

        if error:
            flash(error, "error")
        else:
            user = User(username=username, name=name, is_admin=first_user)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            msg = "Welcome! You are the first user, so you are the admin." if first_user else "Welcome!"
            flash(msg, "success")
            return redirect(url_for("main.index"))

    return render_template("register.html", first_user=first_user)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        if _locked(username):
            flash("Too many failed attempts. Try again in 10 minutes.", "error")
            return render_template("login.html"), 429
        user = db.session.scalar(db.select(User).filter_by(username=username))
        if user and user.check_password(password):
            _failures.pop(username, None)
            login_user(user, remember=bool(request.form.get("remember")))
            return redirect(_safe_next(request.args.get("next")))
        _record_failure(username)
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        current = request.form.get("current", "")
        new = request.form.get("new", "")
        if name and name != current_user.name:
            current_user.name = name
            flash("Name updated.", "success")
        if new:
            if not current_user.check_password(current):
                flash("Current password is wrong.", "error")
            elif len(new) < MIN_PASSWORD:
                flash(f"New password must be at least {MIN_PASSWORD} characters.", "error")
            else:
                current_user.set_password(new)
                flash("Password changed.", "success")
        db.session.commit()
        return redirect(url_for("auth.account"))
    return render_template("account.html")
