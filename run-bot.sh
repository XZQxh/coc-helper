#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
if [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
fi
exec "$PY" bot.py
