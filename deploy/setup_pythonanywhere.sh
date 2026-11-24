#!/bin/bash
# One-shot setup / update for PythonAnywhere.
#
# Run in a PythonAnywhere Bash console, after unzipping the app into ~/padel:
#     bash ~/padel/deploy/setup_pythonanywhere.sh 3.13
# The argument is the Python version you chose for the web app on the "Web" tab.
# Safe to re-run when you upload a new version: your database (~/padel/instance) is kept.
set -euo pipefail

PYVER="${1:-}"
APP_DIR="$HOME/padel"
VENV="$HOME/.virtualenvs/padel"

if [ -z "$PYVER" ]; then
    echo "Usage: bash ~/padel/deploy/setup_pythonanywhere.sh <python-version>   e.g. 3.13"
    exit 1
fi
if ! command -v "python$PYVER" >/dev/null; then
    echo "python$PYVER is not available here. Pick another version (e.g. 3.12, 3.13)."
    exit 1
fi
if [ ! -f "$APP_DIR/run.py" ]; then
    echo "Could not find $APP_DIR/run.py. Unzip the app with:  unzip -o padel-app.zip -d ~/padel"
    exit 1
fi

# Virtualenv: rebuild it if it was made with a different Python version.
if [ -x "$VENV/bin/python" ] && ! "$VENV/bin/python" --version 2>&1 | grep -q "Python $PYVER"; then
    echo "==> Existing virtualenv uses a different Python; recreating it"
    rm -rf "$VENV"
fi
if [ ! -x "$VENV/bin/python" ]; then
    echo "==> Creating virtualenv with Python $PYVER"
    "python$PYVER" -m venv "$VENV"
fi
echo "==> Installing packages"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo "==> Creating the database (if it doesn't exist yet)"
mkdir -p "$APP_DIR/instance"
chmod 700 "$APP_DIR/instance"
(cd "$APP_DIR" && "$VENV/bin/python" -c "from run import app; print('    database ready')")

# Find the web app's WSGI file (create the web app on the Web tab first).
shopt -s nullglob
WSGI_FILES=(/var/www/*_wsgi.py)
if [ ${#WSGI_FILES[@]} -ne 1 ]; then
    echo
    echo "!! Expected exactly one WSGI file in /var/www, found ${#WSGI_FILES[@]}."
    echo "   Create the web app on the Web tab first (Manual configuration, Python $PYVER), then re-run."
    exit 1
fi
WSGI="${WSGI_FILES[0]}"

if ! grep -q "padel-club" "$WSGI"; then
    cp "$WSGI" "$WSGI.orig"
    echo "==> Original WSGI file backed up to $WSGI.orig"
fi
cat > "$WSGI" <<EOF
# padel-club WSGI entry point (written by deploy/setup_pythonanywhere.sh)
import os
import sys

APP_DIR = "$APP_DIR"
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

os.environ["PRODUCTION"] = "1"
# Change to "0" once all players have registered, to close sign-ups.
os.environ["ALLOW_REGISTRATION"] = "1"

from run import app as application  # noqa: E402
EOF
echo "==> WSGI file written: $WSGI"

# Touching the WSGI file reloads the web app.
touch "$WSGI"
SITE="$(basename "$WSGI" _wsgi.py | tr '_' '.')"

echo
echo "Done. If this is the first setup, on the Web tab:"
echo "  1. Virtualenv:  $VENV"
echo "  2. Security:    turn on 'Force HTTPS'"
echo "  3. Click the green 'Reload' button"
echo
echo "Then open: https://$SITE"
