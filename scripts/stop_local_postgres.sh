#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BINDIR="$ROOT/.local-pg/extract/usr/lib/postgresql/16/bin"
DATADIR="$ROOT/.local-pg/data"

if [[ ! -x "$BINDIR/pg_ctl" || ! -f "$DATADIR/PG_VERSION" ]]; then
  echo "Local Postgres is not initialized." >&2
  exit 1
fi

"$BINDIR/pg_ctl" -D "$DATADIR" stop
