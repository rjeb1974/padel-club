import re

import pytest

from app import create_app, db
from app.models import Attendance, GameDay, Match, User, parse_score


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "test.db"),
    })
    from app import auth
    auth._failures.clear()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def register(client, username, name=None, password="password123"):
    return client.post("/register", data={
        "username": username, "name": name or username.title(),
        "password": password, "confirm": password,
    }, follow_redirects=True)


def login(client, username, password="password123"):
    return client.post("/login", data={"username": username, "password": password},
                       follow_redirects=True)


def logout(client):
    return client.post("/logout", follow_redirects=True)


# ------------------------------------------------------------ score parsing

def test_parse_score():
    assert parse_score("6-4 3-6 7-5") == ([(6, 4), (3, 6), (7, 5)], 1)
    assert parse_score("4/6, 2/6") == ([(4, 6), (2, 6)], 2)
    for bad in ["", "abc", "6-6", "6-4 4-6"]:
        with pytest.raises(ValueError):
            parse_score(bad)


# ------------------------------------------------------------ auth

def test_requires_login(client):
    r = client.get("/")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_first_user_is_admin(client, app):
    register(client, "alice")
    logout(client)
    register(client, "bob")
    with app.app_context():
        assert db.session.scalar(db.select(User).filter_by(username="alice")).is_admin
        assert not db.session.scalar(db.select(User).filter_by(username="bob")).is_admin


def test_login_wrong_password(client):
    register(client, "alice")
    logout(client)
    r = login(client, "alice", "nope-nope")
    assert b"Invalid username or password" in r.data


def test_login_lockout(client):
    register(client, "alice")
    logout(client)
    for _ in range(5):
        login(client, "alice", "wrong-pass")
    r = login(client, "alice")  # even the right password is refused while locked
    assert b"Too many failed attempts" in r.data


def test_registration_closed(app, client):
    register(client, "alice")
    logout(client)
    app.config["ALLOW_REGISTRATION"] = False
    r = register(client, "bob")
    assert b"Registration is closed" in r.data


def test_non_admin_cannot_create_gameday(client):
    register(client, "alice")
    logout(client)
    register(client, "bob")
    assert client.post("/gamedays/new", data={"date": "2026-12-01"}).status_code == 403


def test_open_redirect_blocked(client):
    register(client, "alice")
    logout(client)
    r = client.post("/login?next=https://evil.example/", data={
        "username": "alice", "password": "password123"})
    assert r.headers["Location"] == "/"


# ------------------------------------------------------------ main flow

def _setup_players(client):
    for name in ["alice", "bob", "carol", "dave"]:
        register(client, name)
        logout(client)
    login(client, "alice")


def test_full_flow(client, app):
    _setup_players(client)

    r = client.post("/gamedays/new", data={"date": "2026-12-01", "location": "Club"},
                    follow_redirects=True)
    assert b"Game day created" in r.data
    gd_id = int(re.search(rb"/gamedays/(\d+)/attendance", r.data).group(1))

    # alice marks herself present, then admin adds bob
    client.post(f"/gamedays/{gd_id}/attendance")
    client.post(f"/gamedays/{gd_id}/attendance", data={"user_id": 2})

    # record a match alice+bob beat carol+dave; carol and dave get auto-marked present
    r = client.post(f"/gamedays/{gd_id}/matches", data={
        "a1": 1, "a2": 2, "b1": 3, "b2": 4, "score": "6-4, 3-6, 7-5"},
        follow_redirects=True)
    assert b"Match recorded" in r.data
    with app.app_context():
        m = db.session.scalar(db.select(Match))
        assert m.score == "6-4 3-6 7-5" and m.winner == 1
        assert db.session.scalar(db.select(db.func.count(Attendance.id))) == 4

    # invalid matches are rejected
    r = client.post(f"/gamedays/{gd_id}/matches", data={
        "a1": 1, "a2": 1, "b1": 3, "b2": 4, "score": "6-4"}, follow_redirects=True)
    assert b"only appear once" in r.data

    r = client.get("/leaderboard")
    assert r.status_code == 200
    # Alice: 1 win, 2 of 3 sets, games 16-15 -> +1
    assert b"2-1" in r.data and b"+1" in r.data

    assert client.get("/players/1").status_code == 200
    assert client.get("/").status_code == 200


def test_non_admin_cannot_mark_others(client):
    _setup_players(client)
    client.post("/gamedays/new", data={"date": "2026-12-01"})
    logout(client)
    login(client, "bob")
    assert client.post("/gamedays/1/attendance", data={"user_id": 1}).status_code == 403
    assert client.post("/gamedays/1/attendance").status_code == 302


def test_only_creator_or_admin_deletes_match(client):
    _setup_players(client)
    client.post("/gamedays/new", data={"date": "2026-12-01"})
    logout(client)
    login(client, "bob")
    client.post("/gamedays/1/matches", data={"a1": 1, "a2": 2, "b1": 3, "b2": 4, "score": "6-0 6-0"})
    logout(client)
    login(client, "carol")
    assert client.post("/matches/1/delete").status_code == 403
    logout(client)
    login(client, "bob")
    assert client.post("/matches/1/delete").status_code == 302


def test_admin_creates_user(client, app):
    register(client, "alice")
    r = client.post("/admin/users", data={
        "action": "create", "username": "eve", "name": "Eve", "password": "temp12345"},
        follow_redirects=True)
    assert b"Created account for Eve" in r.data
    logout(client)
    r = login(client, "eve", "temp12345")
    assert b"Hi, Eve" in r.data
