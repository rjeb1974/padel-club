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

## Hosting on PythonAnywhere

**First time**
1. Create a free account at https://www.pythonanywhere.com.
2. **Web** tab → *Add a new web app* → *Manual configuration* → choose the newest Python version offered (e.g. 3.13).
3. On your PC, build the upload package: `git archive -o dist/padel-app.zip HEAD`
4. **Files** tab → upload `padel-app.zip` into your home directory.
5. Open a **Bash console** (Consoles tab) and run (using the Python version from step 2):
   ```bash
   unzip -o padel-app.zip -d ~/padel
   bash ~/padel/deploy/setup_pythonanywhere.sh 3.13
   ```
6. Back on the **Web** tab: set *Virtualenv* to `/home/<you>/.virtualenvs/padel`, turn on *Force HTTPS*, click **Reload**.
7. Open `https://<you>.pythonanywhere.com` and register. The first account becomes the admin.

**Updating later**: repeat steps 3–5. The database in `~/padel/instance` is kept.

**Closing registration**: once everyone has an account, change `ALLOW_REGISTRATION` to `"0"` in the WSGI file (Web tab → WSGI configuration file) and click Reload.

**Backups**: download `~/padel/instance/padel.db` from the Files tab now and then.

The free plan asks you to click *Run until 3 months from today* on the Web tab every 3 months.
