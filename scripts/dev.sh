#!/usr/bin/env bash
# Start, stop, and check every cmb-lab backend service.
#
#   scripts/dev.sh up       start all Python services + the Go gateway
#   scripts/dev.sh down     stop everything
#   scripts/dev.sh status   health-check every service
#   scripts/dev.sh logs     tail all service logs
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/.venv/bin"
LOGS="$ROOT/data/logs"
export DATA_DIR="$ROOT/data"

# Load .env so keys like GEMINI_API_KEY reach the service processes.
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
  export DATA_DIR="$ROOT/data"   # always absolute, whatever .env says
fi

mkdir -p "$LOGS"

# name:port pairs. Order matters only for readability.
SERVICES=(
  "catalog:8001"
  "spectrum:8003"
  "cosmology:8004"
  "anomaly:8005"
  "skymap:8007"
  "tutor:8008"
  "chat:8009"
  "playground:8010"
)

GATEWAY_BIN="$ROOT/services/gateway/bin/gateway"
GATEWAY_PORT="${GATEWAY_PORT:-8080}"

start() {
  for entry in "${SERVICES[@]}"; do
    name="${entry%%:*}"
    port="${entry##*:}"
    pkill -f "cmblab_${name}.main:app" >/dev/null 2>&1
    nohup "$VENV/uvicorn" "cmblab_${name}.main:app" --port "$port" --log-level warning \
      > "$LOGS/${name}.log" 2>&1 &
    echo "  started ${name} on :${port}"
  done

  if [[ -x "$GATEWAY_BIN" ]]; then
    pkill -f "services/gateway/bin/gateway" >/dev/null 2>&1
    nohup "$GATEWAY_BIN" > "$LOGS/gateway.log" 2>&1 &
    echo "  started gateway on :${GATEWAY_PORT}"
  else
    echo "  gateway binary missing — run: make gateway-build"
  fi

  echo "waiting for services to come up..."
  sleep 10
  status
}

stop() {
  for entry in "${SERVICES[@]}"; do
    name="${entry%%:*}"
    pkill -f "cmblab_${name}.main:app" >/dev/null 2>&1 && echo "  stopped ${name}"
  done
  pkill -f "services/gateway/bin/gateway" >/dev/null 2>&1 && echo "  stopped gateway"

  # pkill only signals; the kernel releases the listening socket a moment later. Without
  # waiting, `restart` can relaunch into "address already in use" and the service dies.
  for entry in "${SERVICES[@]}" "gateway:${GATEWAY_PORT}"; do
    port="${entry##*:}"
    for _ in $(seq 1 40); do
      lsof -ti tcp:"$port" -sTCP:LISTEN >/dev/null 2>&1 || break
      sleep 0.25
    done
    # Anything still holding the port after 10s is a stray from an earlier run.
    if lsof -ti tcp:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      lsof -ti tcp:"$port" -sTCP:LISTEN | xargs kill -9 >/dev/null 2>&1
      echo "  force-freed port ${port}"
    fi
  done
  true
}

status() {
  printf "%-12s %-6s %s\n" "SERVICE" "PORT" "STATUS"
  for entry in "${SERVICES[@]}"; do
    name="${entry%%:*}"
    port="${entry##*:}"
    if curl -sf --max-time 4 "localhost:${port}/health" >/dev/null 2>&1; then
      printf "%-12s %-6s \033[32mok\033[0m\n" "$name" "$port"
    else
      printf "%-12s %-6s \033[31mdown\033[0m  (tail %s)\n" "$name" "$port" "$LOGS/${name}.log"
    fi
  done

  if curl -sf --max-time 4 "localhost:${GATEWAY_PORT}/api/v1/health" >/dev/null 2>&1; then
    printf "%-12s %-6s \033[32mok\033[0m\n" "gateway" "$GATEWAY_PORT"
  else
    printf "%-12s %-6s \033[31mdown\033[0m\n" "gateway" "$GATEWAY_PORT"
  fi
}

logs() {
  tail -n 30 -f "$LOGS"/*.log
}

case "${1:-status}" in
  up|start)   start ;;
  down|stop)  stop ;;
  restart)    stop; start ;;
  status)     status ;;
  logs)       logs ;;
  *)          echo "usage: $0 {up|down|restart|status|logs}"; exit 1 ;;
esac
