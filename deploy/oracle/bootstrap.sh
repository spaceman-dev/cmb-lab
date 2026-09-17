#!/usr/bin/env bash
# Provision a fresh Oracle Cloud Always Free instance to run cmb-lab.
#
# Supports both OCI base images:
#   - Oracle Linux 9      (dnf, firewalld, SELinux)
#   - Ubuntu 22.04/24.04  (apt, iptables)
#
# Target shape: VM.Standard.A1.Flex (Ampere ARM). 1 OCPU/6 GB works; 4 OCPU/24 GB is better.
#
#   sudo ./deploy/oracle/bootstrap.sh <repo-url> [domain]
#
# Idempotent: safe to re-run.
set -euo pipefail

REPO_URL="${1:-https://github.com/spaceman-dev/cmb-lab.git}"
DOMAIN="${2:-}"                      # optional; without it, serves plain HTTP on :80
APP_USER="cmblab"
APP_DIR="/opt/cmb-lab"

log()  { printf '\n\033[36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[33m  ! %s\033[0m\n' "$*"; }
die()  { printf '\n\033[31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Run with sudo."

# ── Detect the distribution ─────────────────────────────────────────────────────────────
# shellcheck disable=SC1091
. /etc/os-release
case "${ID}${VERSION_ID%%.*}" in
  ol9|ol8|rhel9|centos9|rocky9|almalinux9) OS_FAMILY=rhel ;;
  ubuntu22|ubuntu24)                       OS_FAMILY=debian ;;
  *) die "Unsupported OS: $PRETTY_NAME. Use Oracle Linux 9 or Ubuntu 22.04/24.04." ;;
esac

log "Detected $PRETTY_NAME ($OS_FAMILY family) on $(uname -m)"
[[ "$(uname -m)" == "aarch64" ]] || warn "Expected aarch64 (Ampere A1). Continuing anyway."

# Work in MB: integer-dividing to GB reports 0 on a 1 GB box and fails the check below.
MEM_MB=$(( $(awk '/MemTotal/ {print $2}' /proc/meminfo) / 1024 ))
SWAP_MB=$(( $(awk '/SwapTotal/ {print $2}' /proc/meminfo) / 1024 ))
USABLE_MB=$(( MEM_MB + SWAP_MB ))
log "Resources: $(nproc) vCPU, ${MEM_MB} MB RAM + ${SWAP_MB} MB swap = ${USABLE_MB} MB usable"

# Measured: the full stack is healthy at a 768 MB cap and only OOM-kills at 640 MB.
# Swap counts, because the build peaks are transient and the steady state is ~693 MB.
(( USABLE_MB >= 1400 )) || die "Only ${USABLE_MB} MB usable (RAM + swap).
  cmb-lab needs ~693 MB steady state, and the CAMB/npm builds peak well above that.
  Add swap before re-running:
    sudo dd if=/dev/zero of=/swapfile bs=1M count=3072
    sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab"

(( MEM_MB >= 1800 )) && LOW_MEM=0 || LOW_MEM=1
(( LOW_MEM )) && warn "Under 2 GB of RAM — builds will lean on swap and be slow."

# ── 1. System packages ──────────────────────────────────────────────────────────────────
log "Installing system packages (a few minutes)"
if [[ $OS_FAMILY == rhel ]]; then
  # Only gfortran is genuinely required: CAMB builds from source, while numpy, scipy,
  # healpy and astropy all ship manylinux wheels. Installing the "Development Tools"
  # group instead would drag in valgrind and desktop-portal packages — hundreds of MB
  # of nothing useful on a headless 1 GB box.
  dnf install -y -q gcc gcc-c++ make gcc-gfortran git curl wget pkgconf-pkg-config \
    python3.12 python3.12-devel python3.12-pip \
    || die "Could not install build prerequisites."

  # Optional: only needed if pip has to build healpy from source rather than use a wheel.
  dnf install -y -q oracle-epel-release-el9 >/dev/null 2>&1 \
    || dnf install -y -q epel-release >/dev/null 2>&1 || true
  dnf install -y -q cfitsio-devel openblas-devel >/dev/null 2>&1 \
    || warn "cfitsio/openblas headers unavailable — fine, pip will use prebuilt wheels."
else
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq \
    build-essential gfortran git curl wget pkg-config \
    python3.12 python3.12-venv python3.12-dev \
    libcfitsio-dev libopenblas-dev \
    debian-keyring debian-archive-keyring apt-transport-https
fi

PYTHON_BIN=python3.12
command -v "$PYTHON_BIN" >/dev/null || die "$PYTHON_BIN not found after install."

# Node 20 for the frontend build
if ! command -v node >/dev/null || (( $(node -v | sed 's/v\([0-9]*\).*/\1/') < 20 )); then
  log "Installing Node 20"
  if [[ $OS_FAMILY == rhel ]]; then
    curl -fsSL https://rpm.nodesource.com/setup_20.x | bash - >/dev/null
    dnf install -y -q nodejs
  else
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >/dev/null
    apt-get install -y -qq nodejs
  fi
fi

# Go, for the gateway. Distro packages lag, so fetch upstream. Must satisfy the `go`
# directive in services/gateway/go.mod, or the build fails with "go.mod requires go >= ...".
GO_VERSION="1.24.4"
if ! command -v go >/dev/null || [[ "$(go version 2>/dev/null | awk '{print $3}')" != "go${GO_VERSION}" ]]; then
  log "Installing Go ${GO_VERSION}"
  GOARCH=$([[ "$(uname -m)" == "aarch64" ]] && echo arm64 || echo amd64)
  curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-${GOARCH}.tar.gz" -o /tmp/go.tgz
  rm -rf /usr/local/go && tar -C /usr/local -xzf /tmp/go.tgz && rm /tmp/go.tgz
  ln -sf /usr/local/go/bin/go /usr/local/bin/go
fi

# Caddy for automatic TLS
if ! command -v caddy >/dev/null; then
  log "Installing Caddy"
  if [[ $OS_FAMILY == rhel ]]; then
    dnf install -y -q 'dnf-command(copr)' >/dev/null 2>&1 || true
    dnf copr enable -y @caddy/caddy "epel-9-$(uname -m)" >/dev/null 2>&1 || true
    if ! dnf install -y -q caddy 2>/dev/null; then
      warn "COPR unavailable; installing the static Caddy binary instead"
      CADDY_ARCH=$([[ "$(uname -m)" == "aarch64" ]] && echo arm64 || echo amd64)
      curl -fsSL "https://caddyserver.com/api/download?os=linux&arch=${CADDY_ARCH}" \
        -o /usr/bin/caddy
      chmod +x /usr/bin/caddy
      useradd --system --home /var/lib/caddy --shell /sbin/nologin caddy 2>/dev/null || true
      mkdir -p /etc/caddy /var/lib/caddy
      curl -fsSL https://raw.githubusercontent.com/caddyserver/dist/master/init/caddy.service \
        -o /etc/systemd/system/caddy.service
      systemctl daemon-reload
    fi
  else
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
      | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
      > /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -qq && apt-get install -y -qq caddy
  fi
fi

# ── 2. THE ORACLE GOTCHA: the instance's own firewall ───────────────────────────────────
# Opening the VCN security list in the console is NOT enough. OCI images also filter
# locally — firewalld on Oracle Linux, a baked-in iptables REJECT on Ubuntu. Missing this
# gives an unexplained connection timeout that looks exactly like a cloud-side problem.
log "Opening ports 80 and 443 on the instance firewall"
if systemctl is-active --quiet firewalld 2>/dev/null; then
  firewall-cmd --permanent --add-service=http  >/dev/null
  firewall-cmd --permanent --add-service=https >/dev/null
  firewall-cmd --reload >/dev/null
  log "firewalld: http/https allowed"
else
  for port in 80 443; do
    if ! iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null; then
      # Insert BEFORE the catch-all REJECT rather than appending after it.
      iptables -I INPUT 6 -p tcp --dport "$port" -m state --state NEW,ESTABLISHED -j ACCEPT
    fi
  done
  if [[ $OS_FAMILY == debian ]]; then
    apt-get install -y -qq iptables-persistent >/dev/null 2>&1 || true
    netfilter-persistent save >/dev/null 2>&1 || iptables-save > /etc/iptables/rules.v4
  else
    mkdir -p /etc/sysconfig && iptables-save > /etc/sysconfig/iptables
  fi
  log "iptables: ports 80/443 allowed and persisted"
fi

# SELinux (Oracle Linux default) blocks Caddy from proxying to the local gateway.
if command -v getenforce >/dev/null && [[ "$(getenforce)" == "Enforcing" ]]; then
  log "SELinux enforcing — permitting local proxy connections"
  setsebool -P httpd_can_network_connect 1
fi

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
log "Building Python environment (CAMB compiles Fortran — 10-15 minutes)"
sudo -u "$APP_USER" "$PYTHON_BIN" -m venv "$APP_DIR/.venv"
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install --quiet --upgrade pip wheel
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install --quiet -e libs/cmblab-core
for s in ingest catalog spectrum cosmology anomaly skymap tutor chat playground; do
  sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install --quiet -e "services/$s"
done

# ── 5. Gateway and frontend ─────────────────────────────────────────────────────────────
log "Building Go gateway"
# Absolute path: sudo's secure_path is /sbin:/bin:/usr/sbin:/usr/bin on Oracle Linux, so
# /usr/local/bin/go is not resolvable from a sudo'd shell.
GO_BIN="$(command -v go || echo /usr/local/go/bin/go)"
[[ -x "$GO_BIN" ]] || die "Go not found at $GO_BIN after installation."
sudo -u "$APP_USER" env CGO_ENABLED=0 GOCACHE=/tmp/gocache "HOME=/home/$APP_USER" \
  "$GO_BIN" build -C "$APP_DIR/services/gateway" -o bin/gateway ./cmd/gateway

# Building via GOCACHE=/tmp leaves the binary labelled user_tmp_t, which systemd refuses
# to execute (203/EXEC, "Permission denied") even though the file mode is correct.
if command -v restorecon >/dev/null && [[ "$(getenforce 2>/dev/null)" == "Enforcing" ]]; then
  dnf install -y -q policycoreutils-python-utils >/dev/null 2>&1 || true
  semanage fcontext -a -t bin_t "$APP_DIR/services/gateway/bin(/.*)?" >/dev/null 2>&1 || true
  restorecon -R "$APP_DIR/services/gateway/bin" >/dev/null 2>&1 || true
fi

log "Building frontend"
NODE_OPTS=""
# Vite's build is the peak memory moment. On a small box cap the heap so it spills to swap
# instead of being OOM-killed.
(( LOW_MEM )) && NODE_OPTS="--max-old-space-size=1024"
sudo -u "$APP_USER" npm --prefix "$APP_DIR/web" ci --silent
sudo -u "$APP_USER" env NODE_OPTIONS="$NODE_OPTS" npm --prefix "$APP_DIR/web" run build

# ── 6. Data ─────────────────────────────────────────────────────────────────────────────
if [[ -z "$(ls -A "$APP_DIR/data/clean" 2>/dev/null)" ]]; then
  log "Downloading archive data (~170 MB from NASA/ESA — 10-20 min)"
  sudo -u "$APP_USER" "$APP_DIR/.venv/bin/cmblab-ingest" bootstrap
else
  log "Archive data already present, skipping download"
fi

# ── 7. Environment file ─────────────────────────────────────────────────────────────────
# astropy and matplotlib write config under $HOME on first import. The systemd units set
# ProtectHome, so they are pointed here instead — it must exist and be writable.
mkdir -p "$APP_DIR/data/home/.config" "$APP_DIR/data/home/.cache/matplotlib"
chown -R "$APP_USER:$APP_USER" "$APP_DIR/data/home"

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
mkdir -p /etc/caddy /var/log/caddy
chown -R caddy:caddy /var/log/caddy 2>/dev/null || true
if [[ -n "$DOMAIN" ]]; then
  sed "s|{{DOMAIN}}|$DOMAIN|g" "$APP_DIR/deploy/oracle/Caddyfile" > /etc/caddy/Caddyfile
else
  # No domain: serve plain HTTP so the instance IP works immediately.
  sed "s|{{DOMAIN}}|:80|g" "$APP_DIR/deploy/oracle/Caddyfile" > /etc/caddy/Caddyfile
fi
systemctl enable caddy >/dev/null 2>&1 || true
systemctl restart caddy

# ── 10. Report ──────────────────────────────────────────────────────────────────────────
sleep 8
log "Service status"
systemctl --no-pager --plain list-units 'cmblab*' || true

PUBLIC_IP="$(curl -fsS --max-time 5 https://ifconfig.me 2>/dev/null || echo 'your-instance-ip')"
cat <<EOF

  cmb-lab is deployed.

    URL:      ${DOMAIN:+https://$DOMAIN}${DOMAIN:-http://$PUBLIC_IP}
    Source:   $APP_DIR
    Logs:     journalctl -u 'cmblab*' -f
    Restart:  systemctl restart cmblab.target
    Health:   curl -s localhost:8080/health

  If the page does not load, add ingress rules for TCP 80 and 443 to the VCN
  security list in the OCI console. See deploy/oracle/README.md section 3.

EOF
