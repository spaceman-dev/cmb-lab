#!/usr/bin/env bash
# Pull the latest code and restart cmb-lab in place.
#
#   sudo /opt/cmb-lab/deploy/oracle/update.sh
#
# Rebuilds only what changed. Data in data/ is never touched.
set -euo pipefail

APP_DIR="/opt/cmb-lab"
APP_USER="cmblab"

log() { printf '\n\033[36m==> %s\033[0m\n' "$*"; }
[[ $EUID -eq 0 ]] || { echo "Run with sudo." >&2; exit 1; }

cd "$APP_DIR"
BEFORE="$(sudo -u "$APP_USER" git rev-parse HEAD)"

log "Fetching"
sudo -u "$APP_USER" git pull --ff-only
AFTER="$(sudo -u "$APP_USER" git rev-parse HEAD)"

if [[ "$BEFORE" == "$AFTER" ]]; then
  log "Already up to date ($AFTER)"
  exit 0
fi

CHANGED="$(git diff --name-only "$BEFORE" "$AFTER")"

if grep -qE '^(libs|services)/.*\.(py|toml)$' <<<"$CHANGED"; then
  log "Python changed — reinstalling packages"
  sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install --quiet -e libs/cmblab-core
  for s in ingest catalog spectrum cosmology anomaly skymap tutor chat playground; do
    sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install --quiet -e "services/$s"
  done
fi

if grep -qE '^services/gateway/.*\.go$' <<<"$CHANGED"; then
  log "Gateway changed — rebuilding"
  sudo -u "$APP_USER" env CGO_ENABLED=0 GOCACHE=/tmp/gocache \
    go build -C "$APP_DIR/services/gateway" -o bin/gateway ./cmd/gateway
fi

if grep -qE '^web/' <<<"$CHANGED"; then
  log "Frontend changed — rebuilding"
  sudo -u "$APP_USER" npm --prefix "$APP_DIR/web" ci --silent
  sudo -u "$APP_USER" npm --prefix "$APP_DIR/web" run build
fi

log "Restarting services"
systemctl restart cmblab.target
sleep 8

log "Health"
curl -fsS localhost:8080/health | python3 -m json.tool || echo "Gateway not responding yet"
log "Updated $BEFORE -> $AFTER"
