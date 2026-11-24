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
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python run.py
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
pip install -r requirements-dev.txt
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

## Hosting: Render (app) + Supabase (database)

```
players' browsers  ->  Render (runs the Python app, HTTPS)  ->  Supabase (PostgreSQL)
```

**1. Supabase (database)**
1. Create a project at https://supabase.com (free plan). Choose a strong database password and save it.
2. Click **Connect** (top of the project page) → **Session pooler** → copy the URI, e.g.
   `postgresql://postgres.abcd1234:[YOUR-PASSWORD]@aws-0-eu-west-1.pooler.supabase.com:5432/postgres`
3. Replace `[YOUR-PASSWORD]` with your database password.

Use the *Session pooler* string, not "Direct connection": the direct one is IPv6-only and Render can't reach it.
The app creates its tables automatically on first start.

**2. GitHub (code)**: push this repository to a (private) GitHub repo.

**3. Render (app)**
1. Sign up at https://render.com with your GitHub account.
2. **New → Blueprint** → pick the repo. Render reads `render.yaml`.
3. When asked for `DATABASE_URL`, paste the Supabase string from step 1. Click **Apply**.
4. After the first deploy (a few minutes) open `https://padel-club-xxxx.onrender.com` and register. The first account becomes the admin.

**Updating**: `git push`. Render redeploys automatically; data lives in Supabase and is kept.

**Closing registration**: Render dashboard → the service → *Environment* → set `ALLOW_REGISTRATION` to `0` → save (it redeploys).

**Free-plan limits**
- Render: the app sleeps after ~15 minutes without visitors; the next visit takes 30–60 s to wake it.
- Supabase: a project with no activity for a week is paused; restore it with one click in the dashboard. Regular use of the app keeps it active.
- Data can be viewed and exported in Supabase's *Table editor*.