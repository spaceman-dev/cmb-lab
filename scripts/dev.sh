#!/usr/bin/env bash
# Thin wrapper around scripts/dev.py, which is the real, cross-platform implementation.
# Kept so existing habits and docs keep working. Having one implementation means the
# macOS, Linux and Windows paths cannot drift apart.
#
#   scripts/dev.sh up | down | restart | status | logs | setup | build | doctor
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PY="$ROOT/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3.12 || command -v python3 || true)"
fi
if [[ -z "$PY" ]]; then
  echo "error: no Python found. Install 3.12, then run: python3.12 scripts/dev.py setup" >&2
  exit 1
fi

exec "$PY" "$ROOT/scripts/dev.py" "$@"
