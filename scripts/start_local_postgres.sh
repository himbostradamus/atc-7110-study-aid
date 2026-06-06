#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PGROOT="$ROOT/.local-pg"
BINDIR="$PGROOT/extract/usr/lib/postgresql/16/bin"
DATADIR="$PGROOT/data"
RUNDIR="$PGROOT/run"
LOGDIR="$PGROOT/logs"

PORT="${ATC_PGPORT:-55432}"
HOST="${ATC_PGHOST:-127.0.0.1}"
SOCKETDIR="${ATC_PGSOCKETDIR:-/tmp/atc_pg_${UID}_${PORT}}"

if [[ ! -x "$BINDIR/postgres" ]]; then
  echo "Postgres binaries not found at $BINDIR" >&2
  exit 1
fi

mkdir -p "$DATADIR" "$RUNDIR" "$LOGDIR" "$SOCKETDIR"

if [[ ! -f "$DATADIR/PG_VERSION" ]]; then
  "$BINDIR/initdb" -D "$DATADIR" -U postgres -A trust --no-locale --encoding=UTF8
fi

if "$BINDIR/pg_ctl" -D "$DATADIR" status >/dev/null 2>&1; then
  echo "Local Postgres already running on $HOST:$PORT"
  exit 0
fi

"$BINDIR/pg_ctl" \
  -D "$DATADIR" \
  -l "$LOGDIR/postgres.log" \
  -o "-p $PORT -k $SOCKETDIR -h $HOST" \
  start

echo "Local Postgres started on $HOST:$PORT"
