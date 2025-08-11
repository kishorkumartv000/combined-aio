#!/usr/bin/env bash
set -euo pipefail

PYTHON="python3"
PIP="$PYTHON -m pip"
VENV_DIR=".venv"

setup_with_venv() {
  "$PYTHON" -m venv "$VENV_DIR" 2>/dev/null || return 1
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
  pip install --upgrade pip --quiet
  pip install -r requirements.txt --quiet
  exec python -m bot
}

setup_without_venv() {
  # Try user install first (PEP 668 compliant), then fallback to break-system-packages
  if ! $PIP install -r requirements.txt --user --quiet; then
    $PIP install -r requirements.txt --break-system-packages --quiet
  fi
  exec $PYTHON -m bot
}

if ! setup_with_venv; then
  echo "Venv unavailable; falling back to system Python with user/site packages" >&2
  setup_without_venv
fi