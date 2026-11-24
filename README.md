# Padel Club

A small web app for a group of padel players to track **presences** at game days and **match scores**, with a leaderboard. Each player has their own login.

Built with Python, Flask, SQLAlchemy and SQLite.

## Features

- **Accounts**: each player registers with their own username and password. The first account created becomes the admin.
- **Game days**: the admin schedules sessions (date, location, notes).
- **Presences**: players mark themselves "I'm in" or "I can't make it". The admin can mark anyone.
- **Matches**: anyone can record a 2v2 match with its set scores (e.g. `6-4 3-6 7-5`). The winner is worked out automatically, and the four players are marked present.
- **Leaderboard**: presences, matches, wins and losses, win %, sets and game difference. Shown all-time or per season (year).
- **Player pages**: personal stats, match history and presence history.
- **Admin → Users**: create accounts, reset passwords, grant admin rights.

## Setup (Windows / PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:5000 and register. The first account becomes the admin.

The database is created automatically at `instance/padel.db`.

## Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | generated, saved in `instance/secret_key` | Signs login sessions |
| `DATABASE_URL` | `sqlite:///instance/padel.db` | Any SQLAlchemy URL, e.g. PostgreSQL |
| `ALLOW_REGISTRATION` | `1` | Set to `0` to close sign-ups; the admin then creates accounts |

Make an existing user an admin from the command line:

```powershell
flask --app run make-admin <username>
```

## Tests

```powershell
python -m pytest
```

## Project layout

```
app/
  __init__.py     app factory, config, CLI command
  models.py       User, GameDay, Attendance, Match + score parsing and stats
  auth.py         register / login / logout / account
  views.py        game days, presences, matches, leaderboard, players, admin
  templates/      Jinja2 HTML pages
  static/style.css
run.py            entry point
tests/            pytest suite
```

## Going online

`python run.py` starts a development server. To let the group use the app from their phones:
- Use a production server, e.g. `pip install waitress` and then `waitress-serve --port=8000 run:app`.
- Set a fixed `SECRET_KEY`.
- Put it behind HTTPS, or deploy to a host such as PythonAnywhere, Render or Fly.io.
