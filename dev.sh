#!/usr/bin/env bash
# Launches backend, frontend, and Postgres (status/log tail, or a start
# attempt if it's not running), each in its own gnome-terminal tab.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v gnome-terminal >/dev/null 2>&1; then
  echo "gnome-terminal not found. Run these manually instead:" >&2
  echo "  cd \"$REPO_ROOT/backend\" && uv run --project .. uvicorn app.main:app --reload --port 8000" >&2
  echo "  cd \"$REPO_ROOT/frontend\" && npm run dev" >&2
  echo "  sudo systemctl start postgresql" >&2
  exit 1
fi

gnome-terminal --tab --title="backend" -- bash -c \
  "cd '$REPO_ROOT/backend' && uv run --project .. uvicorn app.main:app --reload --port 8000; exec bash"

gnome-terminal --tab --title="frontend" -- bash -c \
  "cd '$REPO_ROOT/frontend' && npm run dev; exec bash"

if pg_isready -q; then
  gnome-terminal --tab --title="postgres" -- bash -c \
    "pg_lsclusters; echo; echo 'Tailing postgresql-16-main.log (Ctrl+C to stop tailing, service keeps running):'; tail -f /var/log/postgresql/postgresql-16-main.log; exec bash"
else
  gnome-terminal --tab --title="postgres" -- bash -c \
    "echo 'Postgres not reachable — starting it (may prompt for your sudo password):'; sudo systemctl start postgresql && pg_isready && echo; echo 'Tailing postgresql-16-main.log:'; tail -f /var/log/postgresql/postgresql-16-main.log; exec bash"
fi

echo "Started backend, frontend, and postgres tabs in gnome-terminal."
