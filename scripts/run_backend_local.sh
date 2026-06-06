#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export DATABASE_URL="${DATABASE_URL:-postgresql://atc:atc@127.0.0.1:55432/atc_platform}"
export ATC_DEV_AUTH="${ATC_DEV_AUTH:-1}"
export ATC_DEV_USER_EMAIL="${ATC_DEV_USER_EMAIL:-dev@local}"

HOST="${ATC_API_HOST:-127.0.0.1}"
PORT="${ATC_API_PORT:-8000}"

exec "$ROOT/backend/.venv/bin/python" -m uvicorn backend.app.main:app --host "$HOST" --port "$PORT"
