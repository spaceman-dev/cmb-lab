#!/usr/bin/env bash
# Provision a fresh Oracle Cloud Always Free instance to run cmb-lab.
#
# Target: VM.Standard.A1.Flex (Ampere ARM), 4 OCPU / 24 GB, Ubuntu 22.04 or 24.04.
# Run once on a brand new instance:
#
#   curl -fsSL https://raw.githubusercontent.com/<user>/cmb-lab/main/deploy/oracle/bootstrap.sh | bash -s -- <repo-url> [domain]
#
# or, if you have already cloned:
#
#   sudo ./deploy/oracle/bootstrap.sh <repo-url> [domain]
#
# Idempotent: safe to re-run.
set -euo pipefail

REPO_URL="${1:-https://github.com/spaceman-dev/cmb-lab.git}"
DOMAIN="${2:-}"                      # optional; without it, serves plain HTTP on :80
APP_USER="cmblab"
APP_DIR="/opt/cmb-lab"

log() { printf '\n\033[36m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Run with sudo."

ARCH="$(uname -m)"
log "Architecture: $ARCH"
[[ "$ARCH" == "aarch64" ]] || log "WARNING: expected aarch64 (Ampere A1). Continuing anyway."

# ── 1. System packages ──────────────────────────────────────────────────────────────────
log "Installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  build-essential gfortran git curl wget pkg-config \
  python3.12 python3.12-venv python3.12-dev \
  libcfitsio-dev libopenblas-dev \
  nginx-common debian-keyring debian-archive-keyring apt-transport-https

# Node 20 for the frontend build
if ! command -v node >/dev/null || [[ "$(node -v | cut -c2-3)" -lt 20 ]]; then
  log "Installing Node 20"
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y -qq nodejs
fi

# Go, for the gateway. Ubuntu's package lags, so fetch upstream.
GO_VERSION="1.23.4"
if ! command -v go >/dev/null || [[ "$(go version | awk '{print $3}')" != "go${GO_VERSION}" ]]; then
  log "Installing Go ${GO_VERSION} (arm64)"
  curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-arm64.tar.gz" -o /tmp/go.tgz
  rm -rf /usr/local/go && tar -C /usr/local -xzf /tmp/go.tgz && rm /tmp/go.tgz
  ln -sf /usr/local/go/bin/go /usr/local/bin/go
fi

# Caddy for automatic TLS
if ! command -v caddy >/dev/null; then
  log "Installing Caddy"
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -qq && apt-get install -y -qq caddy
fi

# ── 2. THE ORACLE GOTCHA: iptables ──────────────────────────────────────────────────────
# OCI Ubuntu images ship with a REJECT rule that drops everything except SSH. Opening the
# VCN security list in the console is NOT enough — this is the step everyone misses and
# then spends an hour wondering why the port is unreachable.
log "Opening ports 80 and 443 in iptables"
for port in 80 443; do
  if ! iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null; then
    # Insert BEFORE the catch-all REJECT rather than appending after it.
    iptables -I INPUT 6 -p tcp --dport "$port" -m state --state NEW,ESTABLISHED -j ACCEPT
  fi
done
apt-get install -y -qq iptables-persistent >/dev/null 2>&1 || true
netfilter-persistent save >/dev/null 2>&1 || iptables-save > /etc/iptables/rules.v4

# ── 3. Application user and checkout ────────────────────────────────────────────────────
id -u "$APP_USER" >/dev/null 2>&1 || useradd --system --create-home --shell /bin/bash "$APP_USER"

log "Fetching source into $APP_DIR"
if [[ -d "$APP_DIR/.git" ]]; then
  sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only
else
  mkdir -p "$APP_DIR" && chown "$APP_USER:$APP_USER" "$APP_DIR"
  sudo -u "$APP_USER" git clone --depth 1 "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

# ── 4. Python environment ───────────────────────────────────────────────────────────────
log "Building Python environment (CAMB compiles Fortran — this takes a while)"
sudo -u "$APP_USER" python3.12 -m venv "$APP_DIR/.venv"
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install --quiet --upgrade pip wheel
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install --quiet -e libs/cmblab-core
for s in ingest catalog spectrum cosmology anomaly skymap tutor chat playground; do
  sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install --quiet -e "services/$s"
done

# ── 5. Gateway and frontend ─────────────────────────────────────────────────────────────
log "Building Go gateway"
sudo -u "$APP_USER" env CGO_ENABLED=0 GOCACHE=/tmp/gocache \
  go build -C "$APP_DIR/services/gateway" -o bin/gateway ./cmd/gateway

log "Building frontend"
sudo -u "$APP_USER" npm --prefix "$APP_DIR/web" ci --silent
sudo -u "$APP_USER" npm --prefix "$APP_DIR/web" run build

# ── 6. Data ─────────────────────────────────────────────────────────────────────────────
if [[ ! -d "$APP_DIR/data/clean" ]] || [[ -z "$(ls -A "$APP_DIR/data/clean" 2>/dev/null)" ]]; then
  log "Downloading archive data (~170 MB from NASA/ESA — 10-20 min)"
  sudo -u "$APP_USER" "$APP_DIR/.venv/bin/cmblab-ingest" bootstrap
else
  log "Archive data already present, skipping download"
fi

# ── 7. Environment file ─────────────────────────────────────────────────────────────────
if [[ ! -f "$APP_DIR/.env" ]]; then
  sudo -u "$APP_USER" cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  log "Created $APP_DIR/.env — add GEMINI_API_KEY there if you want the AI assistant"
fi
chmod 600 "$APP_DIR/.env" && chown "$APP_USER:$APP_USER" "$APP_DIR/.env"

# ── 8. systemd ──────────────────────────────────────────────────────────────────────────
log "Installing systemd units"
cp "$APP_DIR/deploy/oracle/systemd/"*.service /etc/systemd/system/
cp "$APP_DIR/deploy/oracle/systemd/"*.target  /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now cmblab.target

# ── 9. Caddy ────────────────────────────────────────────────────────────────────────────
log "Configuring Caddy"
if [[ -n "$DOMAIN" ]]; then
  sed "s|{{DOMAIN}}|$DOMAIN|g" "$APP_DIR/deploy/oracle/Caddyfile" > /etc/caddy/Caddyfile
else
  # No domain: serve plain HTTP so the instance IP works immediately.
  sed "s|{{DOMAIN}}|:80|g" "$APP_DIR/deploy/oracle/Caddyfile" > /etc/caddy/Caddyfile
fi
systemctl restart caddy

# ── 10. Report ──────────────────────────────────────────────────────────────────────────
sleep 8
log "Service status"
systemctl --no-pager --plain list-units 'cmblab-*.service' || true

PUBLIC_IP="$(curl -fsS --max-time 5 https://ifconfig.me 2>/dev/null || echo 'your-instance-ip')"
cat <<EOF

  cmb-lab is deployed.

    URL:      ${DOMAIN:+https://$DOMAIN}${DOMAIN:-http://$PUBLIC_IP}
    Source:   $APP_DIR
    Logs:     journalctl -u cmblab-spectrum -f
    Restart:  systemctl restart cmblab.target
    Health:   curl -s localhost:8080/health | python3 -m json.tool

  If the page does not load, the VCN security list still needs ingress rules for
  TCP 80 and 443. See deploy/oracle/README.md section 3.

EOF
