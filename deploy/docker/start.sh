#!/usr/bin/env bash
# Start every cmb-lab service inside one container.
#
# The gateway is the only listener on the exposed port; the Python services bind to
# loopback. If any service dies, the container exits so the platform restarts it rather
# than leaving a half-working site up.
set -uo pipefail

PORT="${GATEWAY_PORT:-7860}"
export DATA_DIR="${DATA_DIR:-/app/data}"

log() { printf '[start] %s\n' "$*"; }

# The image normally ships with the archive data baked in. If the build could not reach
# the network, fetch it now — the site is unusable without it.
if [[ -z "$(ls -A "$DATA_DIR/clean" 2>/dev/null)" ]]; then
  log "no archive data found; downloading (~170 MB, 10-20 min)"
  cmblab-ingest bootstrap || log "WARNING: download failed — the site will run, but the
  analysis tabs will report that nothing has been measured yet"
fi

declare -A PORTS=(
  [catalog]=8001 [spectrum]=8003 [cosmology]=8004 [anomaly]=8005
  [skymap]=8007  [tutor]=8008    [chat]=8009      [playground]=8010
)

pids=()
for name in "${!PORTS[@]}"; do
  log "starting $name on ${PORTS[$name]}"
  uvicorn "cmblab_${name}.main:app" \
    --host 127.0.0.1 --port "${PORTS[$name]}" --log-level warning &
  pids+=($!)
done

# Wait for the services to bind before the gateway starts advertising itself as healthy.
for name in "${!PORTS[@]}"; do
  for _ in $(seq 1 60); do
    curl -fsS "http://127.0.0.1:${PORTS[$name]}/health" >/dev/null 2>&1 && break
    sleep 1
  done
done
log "all services up"

log "starting gateway on :$PORT"
gateway &
pids+=($!)

# Exit as soon as anything dies, so the platform's restart policy takes over.
trap 'kill "${pids[@]}" 2>/dev/null' EXIT INT TERM
wait -n "${pids[@]}"
log "a service exited; shutting down"
exit 1
