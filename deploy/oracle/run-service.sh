#!/usr/bin/env bash
# Launch one cmb-lab Python service under systemd.
#
# The port map lives here rather than in eight separate unit files, so it stays in one
# place and matches scripts/dev.sh. `exec` hands the process straight to systemd, so there
# is no shell sitting between systemd and uvicorn.
set -euo pipefail

NAME="${1:?usage: run-service.sh <service-name>}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

case "$NAME" in
  catalog)    PORT=8001 ;;
  spectrum)   PORT=8003 ;;
  cosmology)  PORT=8004 ;;
  anomaly)    PORT=8005 ;;
  skymap)     PORT=8007 ;;
  tutor)      PORT=8008 ;;
  chat)       PORT=8009 ;;
  playground) PORT=8010 ;;
  *) echo "Unknown service: $NAME" >&2; exit 64 ;;
esac

# Bind to loopback only. Caddy is the sole public listener.
exec "$ROOT/.venv/bin/uvicorn" "cmblab_${NAME}.main:app" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --log-level warning
