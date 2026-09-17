#!/usr/bin/env bash
# One command to get cmb-lab onto Oracle Cloud Always Free.
#
#   1. Shows what exists and offers to terminate instances that cannot run the app
#   2. Makes sure there is a public subnet (a private one cannot hold a public IP)
#   3. Loops instance creation until Ampere capacity appears
#
# RUN THIS IN OCI CLOUD SHELL — the '>_' icon in the console's top bar. The CLI is already
# authenticated there, and it runs inside Oracle's network, which avoids corporate TLS
# inspection that can block the API from a laptop.
#
#   git clone https://github.com/spaceman-dev/cmb-lab.git
#   cd cmb-lab && ./deploy/oracle/deploy.sh
#
# Everything it creates is Always Free. Pass --yes to skip confirmations.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSUME_YES=0
[[ "${1:-}" == "--yes" || "${1:-}" == "-y" ]] && ASSUME_YES=1

log()  { printf '\n\033[36m==> %s\033[0m\n' "$*"; }
ok()   { printf '\033[32m    %s\033[0m\n' "$*"; }
warn() { printf '\033[33m  ! %s\033[0m\n' "$*"; }
die()  { printf '\n\033[31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

confirm() {
  (( ASSUME_YES )) && return 0
  read -r -p "    $1 [y/N] " reply
  [[ "$reply" =~ ^[Yy] ]]
}

command -v oci >/dev/null || die "OCI CLI not found.
  Use Cloud Shell: click the '>_' icon in the OCI Console top bar."

# Cloud Shell authenticates with a delegation token; elsewhere the CLI uses ~/.oci/config.
# Wrapped in a function because macOS ships bash 3.2, where expanding an empty array under
# `set -u` is an error.
OCI_AUTH=""
if [[ -n "${OCI_CLI_CLOUD_SHELL:-}" ]] || [[ -f /etc/oci-cloud-shell ]] || [[ -n "${OCI_CS_USER_OCID:-}" ]]; then
  OCI_AUTH="instance_obo_user"
fi

oci_call() { oci ${OCI_AUTH:+--auth "$OCI_AUTH"} "$@"; }

COMPARTMENT_OCID="${COMPARTMENT_OCID:-${OCI_TENANCY:-}}"
[[ -n "$COMPARTMENT_OCID" ]] || COMPARTMENT_OCID=$(awk -F= '/^tenancy=/{print $2; exit}' ~/.oci/config 2>/dev/null)
[[ -n "$COMPARTMENT_OCID" ]] || die "Could not determine the compartment OCID.
  export COMPARTMENT_OCID=ocid1.tenancy.oc1..xxxxx"

# ── 1. Inventory, and clear out anything that cannot run the app ────────────────────────
log "Existing instances"
rows=$(oci_call compute instance list  \
  --compartment-id "$COMPARTMENT_OCID" --all \
  --query 'data[?"lifecycle-state"!=`TERMINATED`].[id,"display-name",shape,"shape-config"."memory-in-gbs","lifecycle-state"]' \
  --output json 2>/dev/null)

if [[ -z "$rows" || "$rows" == "null" || "$rows" == "[]" ]]; then
  ok "none"
else
  python3 - "$rows" <<'PY'
import json, sys
for oid, name, shape, mem, state in json.loads(sys.argv[1]):
    mem = mem or 0
    flag = "  <- too small for cmb-lab" if mem < 2 else ""
    print(f"    {name:30s} {shape:24s} {mem:g} GB  {state}{flag}")
PY

  # 1 GB shapes cannot run this: the Python imports alone need ~1.05 GB across the eight
  # services. Leaving one running also consumes part of the Always Free allowance.
  doomed=$(python3 -c "
import json,sys
print('\n'.join(f\"{r[0]}\t{r[1]}\" for r in json.loads(sys.argv[1]) if (r[3] or 0) < 2))
" "$rows")

  if [[ -n "$doomed" ]]; then
    echo
    warn "These have under 2 GB RAM and cannot run cmb-lab (measured need: ~1.05 GB of"
    warn "imports across eight services, plus the OS). They also use up free-tier quota."
    while IFS=$'\t' read -r oid name; do
      [[ -z "$oid" ]] && continue
      if confirm "Terminate '$name'?"; then
        oci_call compute instance terminate  \
          --instance-id "$oid" --force --wait-for-state TERMINATED >/dev/null 2>&1 \
          && ok "terminated $name" || warn "could not terminate $name"
      else
        warn "keeping $name — it will count against the free allowance"
      fi
    done <<<"$doomed"
  fi
fi

# ── 2. Network ──────────────────────────────────────────────────────────────────────────
log "Checking for a public subnet"
subnet=$(oci_call network subnet list  \
  --compartment-id "$COMPARTMENT_OCID" --all \
  --query 'data[?"prohibit-public-ip-on-vnic"==`false`]|[0].id' --raw-output 2>/dev/null)

if [[ -n "$subnet" && "$subnet" != "null" ]]; then
  ok "found $subnet"
else
  warn "none found — an instance without one cannot have a public IP"
  "$HERE/setup-network.sh" || die "network setup failed"
  subnet=$(oci_call network subnet list  \
    --compartment-id "$COMPARTMENT_OCID" --all \
    --query 'data[?"prohibit-public-ip-on-vnic"==`false`]|[0].id' --raw-output 2>/dev/null)
  [[ -n "$subnet" && "$subnet" != "null" ]] || die "still no public subnet"
fi
export SUBNET_OCID="$subnet"

# ── 3. SSH key ──────────────────────────────────────────────────────────────────────────
if [[ -z "${SSH_PUBLIC_KEY:-}" ]]; then
  for c in ~/.ssh/oracle-cmblab.pub ~/.ssh/id_ed25519.pub ~/.ssh/id_rsa.pub; do
    [[ -f "$c" ]] && { SSH_PUBLIC_KEY="$c"; break; }
  done
fi
if [[ ! -f "${SSH_PUBLIC_KEY:-/nonexistent}" ]]; then
  log "Generating an SSH key (none found)"
  ssh-keygen -t ed25519 -f ~/.ssh/oracle-cmblab -N "" -C cmb-lab -q
  SSH_PUBLIC_KEY=~/.ssh/oracle-cmblab.pub
  ok "created ~/.ssh/oracle-cmblab"
  warn "Download the PRIVATE key before closing Cloud Shell, or you lose access:"
  warn "  Cloud Shell menu -> Download -> ~/.ssh/oracle-cmblab"
fi
export SSH_PUBLIC_KEY

# ── 4. Create ───────────────────────────────────────────────────────────────────────────
log "Creating the instance (Always Free: 1 OCPU / 6 GB Ampere)"
echo "    Capacity in Hyderabad is scarce, so this retries until it succeeds."
echo "    Leave it running. Ctrl-C to stop."
echo
exec "$HERE/retry-create.sh"
