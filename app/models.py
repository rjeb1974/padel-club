import re
from datetime import date, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class GameDay(db.Model):
    """A scheduled padel session that players attend."""

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    location = db.Column(db.String(120), default="")
    notes = db.Column(db.Text, default="")

    attendances = db.relationship(
        "Attendance", back_populates="gameday", cascade="all, delete-orphan"
    )
    matches = db.relationship(
        "Match", back_populates="gameday", cascade="all, delete-orphan",
        order_by="Match.id",
    )

    @property
    def players_present(self):
        return sorted((a.user for a in self.attendances), key=lambda u: u.name.lower())

    def is_present(self, user):
        return any(a.user_id == user.id for a in self.attendances)


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gameday_id = db.Column(db.Integer, db.ForeignKey("game_day.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    gameday = db.relationship("GameDay", back_populates="attendances")
    user = db.relationship("User")

    __table_args__ = (db.UniqueConstraint("gameday_id", "user_id"),)


class Match(db.Model):
    """A doubles match: team 1 (a1, a2) vs team 2 (b1, b2)."""

    id = db.Column(db.Integer, primary_key=True)
    gameday_id = db.Column(db.Integer, db.ForeignKey("game_day.id"), nullable=False)
    a1_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    a2_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    b1_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    b2_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    score = db.Column(db.String(60), nullable=False)  # normalised, e.g. "6-4 3-6 7-5"
    winner = db.Column(db.Integer, nullable=False)  # 1 or 2
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=datetime.now)

    gameday = db.relationship("GameDay", back_populates="matches")
    a1 = db.relationship("User", foreign_keys=[a1_id])
    a2 = db.relationship("User", foreign_keys=[a2_id])
    b1 = db.relationship("User", foreign_keys=[b1_id])
    b2 = db.relationship("User", foreign_keys=[b2_id])
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    @property
    def team1(self):
        return [self.a1, self.a2]

    @property
    def team2(self):
        return [self.b1, self.b2]

    def team_of(self, user):
        if user.id in (self.a1_id, self.a2_id):
            return 1
        if user.id in (self.b1_id, self.b2_id):
            return 2
        return None

    @property
    def sets(self):
        return parse_score(self.score)[0]


def parse_score(text):
    """Parse a score like "6-4, 3-6, 7-5".

    Returns (sets, winner) where sets is a list of (team1_games, team2_games).
    Raises ValueError with a user-facing message if the score is invalid.
    """
    pairs = re.findall(r"(\d+)\s*[-/:]\s*(\d+)", text or "")
    if not pairs:
        raise ValueError('Enter the score as sets, e.g. "6-4 3-6 7-5".')
    sets = [(int(a), int(b)) for a, b in pairs]
    for a, b in sets:
        if a == b:
            raise ValueError(f"A set cannot end tied ({a}-{b}).")
        if a > 99 or b > 99:
            raise ValueError("Set scores look too large.")
    won1 = sum(1 for a, b in sets if a > b)
    won2 = len(sets) - won1
    if won1 == won2:
        raise ValueError("Sets are tied; there must be a winning team.")
    return sets, (1 if won1 > won2 else 2)


def format_score(sets):
    return " ".join(f"{a}-{b}" for a, b in sets)


def player_stats(users, matches, gamedays):
    """Compute per-player totals for the leaderboard."""
    stats = {
        u.id: {"user": u, "presences": 0, "played": 0, "wins": 0, "losses": 0,
               "sets_won": 0, "sets_lost": 0, "games_won": 0, "games_lost": 0}
        for u in users
    }
    for gd in gamedays:
        for a in gd.attendances:
            if a.user_id in stats:
                stats[a.user_id]["presences"] += 1
    for m in matches:
        sets = m.sets
        for uid, team in ((m.a1_id, 1), (m.a2_id, 1), (m.b1_id, 2), (m.b2_id, 2)):
            s = stats.get(uid)
            if s is None:
                continue
            s["played"] += 1
            if m.winner == team:
                s["wins"] += 1
            else:
                s["losses"] += 1
            for g1, g2 in sets:
                mine, theirs = (g1, g2) if team == 1 else (g2, g1)
                s["games_won"] += mine
                s["games_lost"] += theirs
                if mine > theirs:
                    s["sets_won"] += 1
                else:
                    s["sets_lost"] += 1
    rows = list(stats.values())
    for r in rows:
        r["win_pct"] = round(100 * r["wins"] / r["played"]) if r["played"] else 0
        r["game_diff"] = r["games_won"] - r["games_lost"]
    rows.sort(key=lambda r: (-r["wins"], -r["win_pct"], -r["game_diff"],
                             -r["presences"], r["user"].name.lower()))
    return rows
