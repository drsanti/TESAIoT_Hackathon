#!/usr/bin/env bash
# Works in Git Bash / macOS / Linux. Uses .venv python directly (avoids PATH aliases).
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -x .venv/Scripts/python.exe && ! -x .venv/bin/python ]]; then
  echo "Creating .venv ..."
  python3 -m venv .venv 2>/dev/null || python -m venv .venv
fi

if [[ -x .venv/Scripts/python.exe ]]; then
  PY=".venv/Scripts/python.exe"
elif [[ -x .venv/bin/python ]]; then
  PY=".venv/bin/python"
else
  echo "No venv python found under .venv/"
  exit 1
fi

echo "Ensuring dependencies ..."
"$PY" -m pip install -q -r requirements.txt

echo "Starting TESAIoT BLE Flet app ..."
exec "$PY" main.py
