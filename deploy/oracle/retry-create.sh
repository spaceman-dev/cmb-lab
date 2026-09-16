#!/usr/bin/env bash
# Keep trying to create an Ampere A1 instance until Oracle has capacity.
#
# "Out of capacity for shape VM.Standard.A1.Flex" is the usual obstacle to using the free
# tier. It is not a misconfiguration: Ampere is oversubscribed, and capacity is released
# continuously as other people terminate instances. Retrying in a loop is the practical
# answer, and most people succeed within a few hours.
#
# EASIEST WAY TO RUN THIS — OCI Cloud Shell:
#   1. Open the OCI Console, click the terminal icon (>_) in the top bar.
#   2. Paste:
#        git clone https://github.com/spaceman-dev/cmb-lab.git
#        cd cmb-lab && ./deploy/oracle/retry-create.sh
#   Cloud Shell already has the CLI authenticated, so there is nothing to configure.
#   It also keeps running for ~20 minutes of inactivity, so keep the tab open.
#
# Locally instead: install the OCI CLI and run `oci setup config` first.
#
# Everything below is auto-discovered when possible. Override any of it with env vars.
set -uo pipefail

SHAPE="${SHAPE:-VM.Standard.A1.Flex}"
OCPUS="${OCPUS:-1}"                  # free tier allows 4 total; 1 places far more easily
MEMORY_GB="${MEMORY_GB:-6}"          # free tier allows 24 total
BOOT_VOLUME_GB="${BOOT_VOLUME_GB:-100}"
DISPLAY_NAME="${DISPLAY_NAME:-cmb-lab}"
INTERVAL="${INTERVAL:-60}"           # seconds between full passes
MAX_ATTEMPTS="${MAX_ATTEMPTS:-0}"    # 0 = unlimited

log()  { printf '\033[36m%s\033[0m\n' "$*"; }
warn() { printf '\033[33m  ! %s\033[0m\n' "$*"; }
die()  { printf '\n\033[31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

command -v oci >/dev/null || die "OCI CLI not found.
  In the OCI Console, click the '>_' Cloud Shell icon — it is pre-installed there.
  Locally: brew install oci-cli && oci setup config"

# Cloud Shell authenticates with a delegation token; a local install uses ~/.oci/config.
OCI_ARGS=()
if [[ -n "${OCI_CLI_CLOUD_SHELL:-}" ]] || [[ -f /etc/oci-cloud-shell ]] || [[ -n "${OCI_CS_USER_OCID:-}" ]]; then
  OCI_ARGS+=(--auth instance_obo_user)
  log "Running in Cloud Shell — using the delegation token."
fi

# ── Discover the tenancy ────────────────────────────────────────────────────────────────
COMPARTMENT_OCID="${COMPARTMENT_OCID:-${OCI_TENANCY:-}}"
if [[ -z "$COMPARTMENT_OCID" ]]; then
  COMPARTMENT_OCID=$(awk -F= '/^tenancy=/{print $2; exit}' ~/.oci/config 2>/dev/null || true)
fi
[[ -n "$COMPARTMENT_OCID" ]] || die "Could not determine the tenancy OCID.
  Set it explicitly:  export COMPARTMENT_OCID=ocid1.tenancy.oc1..xxxxx
  Find it under Identity > Compartments (the root compartment is your tenancy)."

# ── Discover the image: newest Oracle Linux 9 that supports this shape ──────────────────
if [[ -z "${IMAGE_OCID:-}" ]]; then
  log "Finding the latest Oracle Linux 9 image for $SHAPE ..."
  IMAGE_OCID=$(oci compute image list "${OCI_ARGS[@]}" \
    --compartment-id "$COMPARTMENT_OCID" \
    --operating-system "Oracle Linux" --operating-system-version "9" \
    --shape "$SHAPE" --sort-by TIMECREATED --sort-order DESC \
    --query 'data[0].id' --raw-output 2>/dev/null)
fi
[[ -n "${IMAGE_OCID:-}" && "$IMAGE_OCID" != "null" ]] || die "Could not find an Oracle Linux 9 image.
  List them with:
    oci compute image list --compartment-id $COMPARTMENT_OCID \\
        --operating-system 'Oracle Linux' --shape $SHAPE"

# ── Discover a subnet that hands out public IPs ─────────────────────────────────────────
# An instance on a private subnet has no internet-facing address: you cannot SSH to it and
# nobody can reach the site. So we insist on a subnet with public IPs enabled.
if [[ -z "${SUBNET_OCID:-}" ]]; then
  log "Looking for a public subnet ..."
  SUBNET_OCID=$(oci network subnet list "${OCI_ARGS[@]}" \
    --compartment-id "$COMPARTMENT_OCID" --all \
    --query 'data[?"prohibit-public-ip-on-vnic"==`false`]|[0].id' \
    --raw-output 2>/dev/null)
fi
[[ -n "${SUBNET_OCID:-}" && "$SUBNET_OCID" != "null" ]] || die "No public subnet found.
  Every existing subnet forbids public IPs, so an instance there would be unreachable.
  In the console: Networking > Virtual Cloud Networks > Create VCN > 'VCN with Internet
  Connectivity'. That wizard makes a public subnet with a gateway and route table.
  Then re-run, or pass SUBNET_OCID=ocid1.subnet.oc1..xxxxx"

# ── SSH key ─────────────────────────────────────────────────────────────────────────────
SSH_PUBLIC_KEY="${SSH_PUBLIC_KEY:-}"
if [[ -z "$SSH_PUBLIC_KEY" ]]; then
  for candidate in ~/.ssh/oracle-cmblab.pub ~/.ssh/id_ed25519.pub ~/.ssh/id_rsa.pub; do
    [[ -f "$candidate" ]] && { SSH_PUBLIC_KEY="$candidate"; break; }
  done
fi
[[ -f "${SSH_PUBLIC_KEY:-/nonexistent}" ]] || die "No SSH public key found.
  Oracle Linux has no password login, so an instance without a key is unreachable forever.
  Generate one:  ssh-keygen -t ed25519 -f ~/.ssh/oracle-cmblab -C cmb-lab
  Or set:        export SSH_PUBLIC_KEY=/path/to/key.pub"

# ── Availability domains ────────────────────────────────────────────────────────────────
# Capacity is tracked per-AD, so AD-1 being full says nothing about AD-2. Trying all of
# them on each pass materially improves the odds.
mapfile -t ADS < <(oci iam availability-domain list "${OCI_ARGS[@]}" \
  --compartment-id "$COMPARTMENT_OCID" --query 'data[].name' --raw-output 2>/dev/null \
  | tr -d '[]", ' | grep -v '^$')
(( ${#ADS[@]} )) || die "Could not list availability domains. Is the CLI authenticated?"

cat <<EOF

  Requesting ${OCPUS} OCPU / ${MEMORY_GB} GB  ${SHAPE}
  Image:   ${IMAGE_OCID:0:40}...
  Subnet:  ${SUBNET_OCID:0:40}...  (public IPs enabled)
  Key:     $SSH_PUBLIC_KEY
  ADs:     ${ADS[*]}

  Retrying every ${INTERVAL}s across every AD. Ctrl-C to stop.
  Keep this running — capacity frees up unpredictably.

EOF

attempt=0
while :; do
  attempt=$((attempt + 1))
  if (( MAX_ATTEMPTS > 0 && attempt > MAX_ATTEMPTS )); then
    die "Gave up after $MAX_ATTEMPTS passes."
  fi

  for ad in "${ADS[@]}"; do
    printf '[%s] pass %-4d %-28s ' "$(date +%H:%M:%S)" "$attempt" "$ad"

    output=$(oci compute instance launch "${OCI_ARGS[@]}" \
      --compartment-id "$COMPARTMENT_OCID" \
      --availability-domain "$ad" \
      --display-name "$DISPLAY_NAME" \
      --shape "$SHAPE" \
      --shape-config "{\"ocpus\":${OCPUS},\"memoryInGBs\":${MEMORY_GB}}" \
      --image-id "$IMAGE_OCID" \
      --subnet-id "$SUBNET_OCID" \
      --assign-public-ip true \
      --boot-volume-size-in-gbs "$BOOT_VOLUME_GB" \
      --ssh-authorized-keys-file "$SSH_PUBLIC_KEY" \
      --wait-for-state RUNNING 2>&1)
    rc=$?

    if (( rc == 0 )); then
      instance_id=$(grep -oE 'ocid1\.instance\.[a-z0-9.-]+' <<<"$output" | head -1)
      ip=$(oci compute instance list-vnics "${OCI_ARGS[@]}" --instance-id "$instance_id" \
             --query 'data[0]."public-ip"' --raw-output 2>/dev/null)
      cat <<EOF
CREATED

  ✓ Instance is running.

    OCID: $instance_id
    IP:   $ip

  Next:
    1. Open TCP 80 and 443 in the VCN security list
       (Networking > VCN > Security Lists > Default > Add Ingress Rules,
        source 0.0.0.0/0, TCP, destination port 80 then 443)

    2. ssh -i ${SSH_PUBLIC_KEY%.pub} opc@$ip
       sudo dnf install -y git
       git clone https://github.com/spaceman-dev/cmb-lab.git /tmp/cmb-lab
       sudo /tmp/cmb-lab/deploy/oracle/bootstrap.sh

EOF
      exit 0
    fi

    if grep -qiE 'out of capacity|outofcapacity|internalerror' <<<"$output"; then
      echo "no capacity"
    elif grep -qiE 'limitexceeded|quotaexceeded' <<<"$output"; then
      echo "QUOTA"
      die "Service limit reached. Always Free allows 4 OCPU / 24 GB of Ampere in total,
  so an existing instance may be consuming it. Check Compute > Instances, or lower
  OCPUS / MEMORY_GB."
    else
      echo "FAILED"
      sed 's/^/    /' <<<"$output" | head -12
      die "Not a capacity problem — see the message above."
    fi
  done

  sleep "$INTERVAL"
done
