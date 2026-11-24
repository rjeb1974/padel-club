from datetime import date
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import db
from .auth import MIN_PASSWORD
from .models import Attendance, GameDay, Match, User, format_score, parse_score, player_stats

bp = Blueprint("main", __name__)


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def _all_users():
    return db.session.scalars(db.select(User).order_by(db.func.lower(User.name))).all()


def _get_gameday(gameday_id):
    return db.get_or_404(GameDay, gameday_id)


# ---------------------------------------------------------------- dashboard

@bp.route("/")
@login_required
def index():
    today = date.today()
    upcoming = db.session.scalars(
        db.select(GameDay).where(GameDay.date >= today).order_by(GameDay.date).limit(5)
    ).all()
    recent = db.session.scalars(
        db.select(GameDay).where(GameDay.date < today).order_by(GameDay.date.desc()).limit(5)
    ).all()
    rows = _leaderboard_rows()[:5]
    return render_template("index.html", upcoming=upcoming, recent=recent, rows=rows)


def _leaderboard_rows(year=None):
    gd_query = db.select(GameDay)
    if year:
        gd_query = gd_query.where(db.extract("year", GameDay.date) == year)
    gamedays = db.session.scalars(gd_query).all()
    matches = [m for gd in gamedays for m in gd.matches]
    return player_stats(_all_users(), matches, gamedays)


@bp.route("/leaderboard")
@login_required
def leaderboard():
    year = request.args.get("year", type=int)
    years = sorted(
        {d.year for d in db.session.scalars(db.select(GameDay.date))}, reverse=True
    )
    return render_template("leaderboard.html", rows=_leaderboard_rows(year),
                           years=years, year=year)


# ---------------------------------------------------------------- game days

@bp.route("/gamedays")
@login_required
def gamedays():
    days = db.session.scalars(db.select(GameDay).order_by(GameDay.date.desc())).all()
    return render_template("gamedays.html", days=days, today=date.today())


@bp.route("/gamedays/new", methods=["GET", "POST"])
@admin_required
def new_gameday():
    if request.method == "POST":
        gd = GameDay()
        if _fill_gameday(gd):
            db.session.add(gd)
            db.session.commit()
            flash("Game day created.", "success")
            return redirect(url_for("main.gameday", gameday_id=gd.id))
    return render_template("gameday_form.html", gd=None, today=date.today())


@bp.route("/gamedays/<int:gameday_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_gameday(gameday_id):
    gd = _get_gameday(gameday_id)
    if request.method == "POST":
        if _fill_gameday(gd):
            db.session.commit()
            flash("Game day updated.", "success")
            return redirect(url_for("main.gameday", gameday_id=gd.id))
    return render_template("gameday_form.html", gd=gd, today=date.today())


def _fill_gameday(gd):
    try:
        gd.date = date.fromisoformat(request.form.get("date", ""))
    except ValueError:
        flash("Please enter a valid date.", "error")
        return False
    gd.location = request.form.get("location", "").strip()
    gd.notes = request.form.get("notes", "").strip()
    return True


@bp.route("/gamedays/<int:gameday_id>/delete", methods=["POST"])
@admin_required
def delete_gameday(gameday_id):
    gd = _get_gameday(gameday_id)
    db.session.delete(gd)
    db.session.commit()
    flash("Game day deleted.", "info")
    return redirect(url_for("main.gamedays"))


@bp.route("/gamedays/<int:gameday_id>")
@login_required
def gameday(gameday_id):
    gd = _get_gameday(gameday_id)
    return render_template("gameday.html", gd=gd, users=_all_users())


@bp.route("/gamedays/<int:gameday_id>/attendance", methods=["POST"])
@login_required
def toggle_attendance(gameday_id):
    """Players mark themselves present/absent; admins can do it for anyone."""
    gd = _get_gameday(gameday_id)
    user_id = request.form.get("user_id", type=int) or current_user.id
    if user_id != current_user.id and not current_user.is_admin:
        abort(403)
    user = db.get_or_404(User, user_id)

    existing = db.session.scalar(
        db.select(Attendance).filter_by(gameday_id=gd.id, user_id=user.id)
    )
    if existing:
        db.session.delete(existing)
        flash(f"{user.name} marked absent.", "info")
    else:
        db.session.add(Attendance(gameday_id=gd.id, user_id=user.id))
        flash(f"{user.name} marked present.", "success")
    db.session.commit()
    return redirect(url_for("main.gameday", gameday_id=gd.id))


# ---------------------------------------------------------------- matches

@bp.route("/gamedays/<int:gameday_id>/matches", methods=["POST"])
@login_required
def add_match(gameday_id):
    gd = _get_gameday(gameday_id)
    ids = [request.form.get(k, type=int) for k in ("a1", "a2", "b1", "b2")]
    back = redirect(url_for("main.gameday", gameday_id=gd.id))

    if None in ids:
        flash("Choose all four players.", "error")
        return back
    if len(set(ids)) != 4:
        flash("Each player can only appear once in a match.", "error")
        return back
    players = [db.session.get(User, i) for i in ids]
    if None in players:
        flash("Unknown player.", "error")
        return back
    try:
        sets, winner = parse_score(request.form.get("score", ""))
    except ValueError as e:
        flash(str(e), "error")
        return back

    db.session.add(Match(
        gameday=gd, a1_id=ids[0], a2_id=ids[1], b1_id=ids[2], b2_id=ids[3],
        score=format_score(sets), winner=winner, created_by_id=current_user.id,
    ))
    # Anyone who played was obviously present.
    for p in players:
        if not gd.is_present(p):
            db.session.add(Attendance(gameday=gd, user_id=p.id))
    db.session.commit()
    flash("Match recorded.", "success")
    return back


@bp.route("/matches/<int:match_id>/delete", methods=["POST"])
@login_required
def delete_match(match_id):
    m = db.get_or_404(Match, match_id)
    if not (current_user.is_admin or m.created_by_id == current_user.id):
        abort(403)
    gameday_id = m.gameday_id
    db.session.delete(m)
    db.session.commit()
    flash("Match deleted.", "info")
    return redirect(url_for("main.gameday", gameday_id=gameday_id))


# ---------------------------------------------------------------- players

@bp.route("/players")
@login_required
def players():
    return render_template("players.html", users=_all_users())


@bp.route("/players/<int:user_id>")
@login_required
def player(user_id):
    user = db.get_or_404(User, user_id)
    matches = db.session.scalars(
        db.select(Match).join(GameDay)
        .where(db.or_(Match.a1_id == user.id, Match.a2_id == user.id,
                      Match.b1_id == user.id, Match.b2_id == user.id))
        .order_by(GameDay.date.desc(), Match.id.desc())
    ).all()
    gamedays = db.session.scalars(
        db.select(GameDay).join(Attendance).where(Attendance.user_id == user.id)
        .order_by(GameDay.date.desc())
    ).all()
    stats = player_stats([user], matches, gamedays)[0]
    return render_template("player.html", user=user, matches=matches,
                           gamedays=gamedays, s=stats)


# ---------------------------------------------------------------- admin

@bp.route("/admin/users", methods=["GET", "POST"])
@admin_required
def admin_users():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            username = request.form.get("username", "").strip().lower()
            name = request.form.get("name", "").strip()
            password = request.form.get("password", "")
            if not username or not name or len(password) < MIN_PASSWORD:
                flash(f"Username, name and a password of {MIN_PASSWORD}+ characters are required.", "error")
            elif db.session.scalar(db.select(User).filter_by(username=username)):
                flash("That username is taken.", "error")
            else:
                u = User(username=username, name=name)
                u.set_password(password)
                db.session.add(u)
                db.session.commit()
                flash(f"Created account for {name}.", "success")
        else:
            user = db.get_or_404(User, request.form.get("user_id", type=int))
            if action == "toggle_admin":
                if user.id == current_user.id:
                    flash("You cannot remove your own admin rights.", "error")
                else:
                    user.is_admin = not user.is_admin
                    db.session.commit()
                    flash(f"Updated {user.name}.", "success")
            elif action == "reset_password":
                password = request.form.get("password", "")
                if len(password) < MIN_PASSWORD:
                    flash(f"Password must be at least {MIN_PASSWORD} characters.", "error")
                else:
                    user.set_password(password)
                    db.session.commit()
                    flash(f"Password reset for {user.name}.", "success")
        return redirect(url_for("main.admin_users"))
    return render_template("admin_users.html", users=_all_users())
