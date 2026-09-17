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
MEMORY_GB="${MEMORY_GB:-6}"          # free tier allows 24 total; 6 is the A1 minimum
BOOT_VOLUME_GB="${BOOT_VOLUME_GB:-50}"
DISPLAY_NAME="${DISPLAY_NAME:-cmb-lab}"
# Oracle rate-limits launch_instance. Polling hard gets you 429s, which wastes the attempt
# and helps nobody, so the default gap is deliberately unhurried.
INTERVAL="${INTERVAL:-300}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-0}"    # 0 = unlimited

log()  { printf '\033[36m%s\033[0m\n' "$*"; }
warn() { printf '\033[33m  ! %s\033[0m\n' "$*"; }
die()  { printf '\n\033[31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

# ── Always Free guard rails ─────────────────────────────────────────────────────────────
# This script must never be able to create a billable resource. Oracle bills silently the
# moment you step outside the Always Free envelope, so the limits are enforced here rather
# than trusted to the caller. Numbers from Oracle's Always Free resource list.
FREE_SHAPES="VM.Standard.A1.Flex VM.Standard.E2.1.Micro"
FREE_MAX_OCPUS_A1=4        # 4 OCPU of Ampere across all instances
FREE_MAX_MEMORY_A1=24      # 24 GB of Ampere across all instances
FREE_MAX_BOOT_GB=200       # 200 GB of block volume in total

grep -qw -- "$SHAPE" <<<"$FREE_SHAPES" || die "Refusing to create shape '$SHAPE'.
  It is not in the Always Free list and would be billed.
  Allowed: $FREE_SHAPES"

if [[ "$SHAPE" == "VM.Standard.A1.Flex" ]]; then
  (( OCPUS >= 1 && OCPUS <= FREE_MAX_OCPUS_A1 )) \
    || die "OCPUS=$OCPUS is outside the Always Free range (1-$FREE_MAX_OCPUS_A1)."
  (( MEMORY_GB >= 6 && MEMORY_GB <= FREE_MAX_MEMORY_A1 )) \
    || die "MEMORY_GB=$MEMORY_GB is outside the Always Free range (6-$FREE_MAX_MEMORY_A1)."
  # Ampere allocates 6 GB per OCPU; asking for more than that ratio leaves the free tier.
  (( MEMORY_GB <= OCPUS * 6 )) \
    || die "MEMORY_GB=$MEMORY_GB exceeds 6 GB per OCPU for $OCPUS OCPU.
  Always Free gives 6 GB per Ampere core. Use MEMORY_GB=$(( OCPUS * 6 )) or fewer OCPUs."
fi

(( BOOT_VOLUME_GB >= 47 && BOOT_VOLUME_GB <= FREE_MAX_BOOT_GB )) \
  || die "BOOT_VOLUME_GB=$BOOT_VOLUME_GB is outside the Always Free range (47-$FREE_MAX_BOOT_GB)."

# Ampere is heavily contended. E2.1.Micro usually has capacity, and measurement shows the
# full stack does fit in 1 GB: 693 MiB steady state, all endpoints healthy at a 768 MB cap
# (it only starts OOM-killing at 640 MB). It is tight and slow, but it works — so it is
# worth falling back to rather than waiting indefinitely for Ampere.
FALLBACK_SHAPE="${FALLBACK_SHAPE:-VM.Standard.E2.1.Micro}"
FALLBACK_AFTER="${FALLBACK_AFTER:-12}"   # passes before also trying the fallback; 0 disables

command -v oci >/dev/null || die "OCI CLI not found.
  In the OCI Console, click the '>_' Cloud Shell icon — it is pre-installed there.
  Locally: brew install oci-cli && oci setup config"

# Cloud Shell authenticates with a delegation token; elsewhere the CLI uses ~/.oci/config.
# Wrapped in a function because macOS ships bash 3.2, where expanding an empty array under
# `set -u` is an error.
OCI_AUTH=""
if [[ -n "${OCI_CLI_CLOUD_SHELL:-}" ]] || [[ -f /etc/oci-cloud-shell ]] || [[ -n "${OCI_CS_USER_OCID:-}" ]]; then
  OCI_AUTH="instance_obo_user"
  log "Running in Cloud Shell — using the delegation token."
fi

oci_call() { oci ${OCI_AUTH:+--auth "$OCI_AUTH"} "$@"; }

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
  IMAGE_OCID=$(oci_call compute image list  \
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
  SUBNET_OCID=$(oci_call network subnet list  \
    --compartment-id "$COMPARTMENT_OCID" --all \
    --query 'data[?"prohibit-public-ip-on-vnic"==`false`]|[0].id' \
    --raw-output 2>/dev/null)
fi
[[ -n "${SUBNET_OCID:-}" && "$SUBNET_OCID" != "null" ]] || die "No public subnet found.
  Every existing subnet forbids public IPs, so an instance there would be unreachable.
  This is also what causes the console warning:
      'You must select a public subnet to assign a public IPv4 address'

  Create one:  ./deploy/oracle/setup-network.sh
  Or pass:     export SUBNET_OCID=ocid1.subnet.oc1..xxxxx"

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
# them on each pass materially improves the odds. (Some regions, Hyderabad included, have
# only one AD — then this is just a single attempt per pass.)
#
# Built with a read loop rather than mapfile, which is bash 4+ and absent on macOS.
ADS=""
while IFS= read -r ad; do
  [[ -n "$ad" ]] && ADS="${ADS}${ad} "
done < <(oci_call iam availability-domain list \
  --compartment-id "$COMPARTMENT_OCID" --query 'data[].name' --raw-output 2>/dev/null \
  | tr -d '[]", ' | grep -v '^$')

[[ -n "$ADS" ]] || die "Could not list availability domains. Is the CLI authenticated?
  Session tokens expire after an hour: oci session authenticate --profile-name \$OCI_CLI_PROFILE"

# ── Do not exceed the Always Free quota with what already exists ────────────────────────
# The allowance is tenancy-wide, not per-instance, so a forgotten instance silently eats
# into it. Anything beyond the envelope starts billing.
used=$(oci_call compute instance list  \
  --compartment-id "$COMPARTMENT_OCID" --all \
  --query 'data[?"lifecycle-state"!=`TERMINATED`].{s:shape,o:"shape-config".ocpus,m:"shape-config"."memory-in-gbs",n:"display-name",id:id}' \
  --output json 2>/dev/null)

if [[ -n "$used" && "$used" != "null" && "$used" != "[]" ]]; then
  log "Existing (non-terminated) instances:"
  python3 - "$used" <<'PY' || true
import json, sys
rows = json.loads(sys.argv[1])
a1o = a1m = 0.0
for r in rows:
    print(f"    {r.get('n','?'):32s} {r.get('s','?'):24s} "
          f"{r.get('o') or 0:g} OCPU / {r.get('m') or 0:g} GB")
    if r.get('s') == 'VM.Standard.A1.Flex':
        a1o += r.get('o') or 0
        a1m += r.get('m') or 0
if a1o or a1m:
    print(f"    -> Ampere already in use: {a1o:g} OCPU / {a1m:g} GB of 4 / 24")
PY

  a1_used_ocpu=$(python3 -c "
import json,sys
print(sum(r.get('o') or 0 for r in json.loads(sys.argv[1]) if r.get('s')=='VM.Standard.A1.Flex'))
" "$used" 2>/dev/null || echo 0)
  a1_used_mem=$(python3 -c "
import json,sys
print(sum(r.get('m') or 0 for r in json.loads(sys.argv[1]) if r.get('s')=='VM.Standard.A1.Flex'))
" "$used" 2>/dev/null || echo 0)

  if [[ "$SHAPE" == "VM.Standard.A1.Flex" ]]; then
    total_o=$(python3 -c "print($a1_used_ocpu + $OCPUS)")
    total_m=$(python3 -c "print($a1_used_mem + $MEMORY_GB)")
    over=$(python3 -c "print(1 if ($total_o > $FREE_MAX_OCPUS_A1 or $total_m > $FREE_MAX_MEMORY_A1) else 0)")
    if [[ "$over" == "1" ]]; then
      die "Creating this instance would take Ampere usage to ${total_o} OCPU / ${total_m} GB,
  over the Always Free limit of ${FREE_MAX_OCPUS_A1} OCPU / ${FREE_MAX_MEMORY_A1} GB, and the excess would be billed.
  Terminate an existing instance first, or lower OCPUS / MEMORY_GB."
    fi
  fi
fi

cat <<EOF

  Requesting ${OCPUS} OCPU / ${MEMORY_GB} GB  ${SHAPE}   (Always Free)
  Boot volume: ${BOOT_VOLUME_GB} GB
  Image:   ${IMAGE_OCID:0:40}...
  Subnet:  ${SUBNET_OCID:0:40}...  (public IPs enabled)
  Key:     $SSH_PUBLIC_KEY
  ADs:     ${ADS}

  Retrying every ${INTERVAL}s across every AD. Ctrl-C to stop.
  Keep this running — capacity frees up unpredictably.

EOF

attempt=0
last_refresh=$(date +%s)
backoff=0

# Session tokens last an hour. Refreshing well inside that keeps an unattended loop alive
# for days instead of dying quietly ~60 minutes in. Cloud Shell's delegation token is
# managed for us, so only refresh when using a local profile.
refresh_token_if_due() {
  [[ -n "$OCI_AUTH" ]] && return 0                 # Cloud Shell: nothing to do
  [[ -n "${OCI_CLI_PROFILE:-}" ]] || return 0
  local now elapsed
  now=$(date +%s)
  elapsed=$(( now - last_refresh ))
  (( elapsed < 1800 )) && return 0                 # every 30 minutes
  if oci session refresh --profile "$OCI_CLI_PROFILE" >/dev/null 2>&1; then
    last_refresh=$now
    log "session token refreshed"
  else
    warn "token refresh failed; re-authenticate with:"
    warn "  oci session authenticate --profile-name $OCI_CLI_PROFILE"
  fi
}

while :; do
  attempt=$((attempt + 1))
  if (( MAX_ATTEMPTS > 0 && attempt > MAX_ATTEMPTS )); then
    die "Gave up after $MAX_ATTEMPTS passes."
  fi

  refresh_token_if_due

  for ad in $ADS; do
    # After enough failed passes, also try the smaller always-available shape. Ampere in
    # a single-AD region can stay full for days.
    shapes="$SHAPE"
    if [[ -n "$FALLBACK_SHAPE" ]] && (( FALLBACK_AFTER > 0 && attempt > FALLBACK_AFTER )); then
      shapes="$SHAPE $FALLBACK_SHAPE"
    fi

    for shape in $shapes; do
      if [[ "$shape" == "VM.Standard.E2.1.Micro" ]]; then
        shape_cfg=""                       # fixed 1 OCPU / 1 GB, not configurable
      else
        shape_cfg="{\"ocpus\":${OCPUS},\"memoryInGBs\":${MEMORY_GB}}"
      fi

      printf '[%s] pass %-4d %-22s %-24s ' "$(date +%H:%M:%S)" "$attempt" "${ad##*:}" "$shape"

      if [[ -n "$shape_cfg" ]]; then
        output=$(oci_call compute instance launch \
          --compartment-id "$COMPARTMENT_OCID" \
          --availability-domain "$ad" \
          --display-name "$DISPLAY_NAME" \
          --shape "$shape" \
          --shape-config "$shape_cfg" \
          --image-id "$IMAGE_OCID" \
          --subnet-id "$SUBNET_OCID" \
          --assign-public-ip true \
          --boot-volume-size-in-gbs "$BOOT_VOLUME_GB" \
          --ssh-authorized-keys-file "$SSH_PUBLIC_KEY" \
          --wait-for-state RUNNING 2>&1)
      else
        output=$(oci_call compute instance launch \
          --compartment-id "$COMPARTMENT_OCID" \
          --availability-domain "$ad" \
          --display-name "$DISPLAY_NAME" \
          --shape "$shape" \
          --image-id "$IMAGE_OCID" \
          --subnet-id "$SUBNET_OCID" \
          --assign-public-ip true \
          --boot-volume-size-in-gbs "$BOOT_VOLUME_GB" \
          --ssh-authorized-keys-file "$SSH_PUBLIC_KEY" \
          --wait-for-state RUNNING 2>&1)
      fi
      rc=$?

      if (( rc == 0 )); then
        instance_id=$(grep -oE 'ocid1\.instance\.[a-z0-9.-]+' <<<"$output" | head -1)
        ip=$(oci_call compute instance list-vnics --instance-id "$instance_id" \
               --query 'data[0]."public-ip"' --raw-output 2>/dev/null)
        cat <<EOF
CREATED

  ✓ Instance is running.

    Shape: $shape
    OCID:  $instance_id
    IP:    $ip

  Next:
    1. Open TCP 80 and 443 in the VCN security list
       (Networking > VCN > Security Lists > Default > Add Ingress Rules,
        source 0.0.0.0/0, TCP, destination port 80 then 443)

    2. ssh -i ${SSH_PUBLIC_KEY%.pub} opc@$ip
       sudo dnf install -y git
       git clone https://github.com/spaceman-dev/cmb-lab.git /tmp/cmb-lab
       sudo /tmp/cmb-lab/deploy/oracle/bootstrap.sh

EOF
        if [[ "$shape" == "VM.Standard.E2.1.Micro" ]]; then
          cat <<'EOF'
  Note: this is the 1 GB shape. Measured steady state is ~693 MiB, which fits, but
  leaves little headroom. Before running the bootstrap, add swap:

    sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
    sudo mkswap /swapfile && sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

  Expect MCMC and the anomaly Monte Carlo to be slow; reduce walkers and steps.

EOF
        fi
        exit 0
      fi

      if grep -qiE 'out of capacity|outofcapacity|internalerror' <<<"$output"; then
        echo "no capacity"
        backoff=0
      elif grep -qiE 'toomanyrequests|too many requests|"status": 429' <<<"$output"; then
        # Oracle throttled us. Backing off is the only correct response: retrying
        # sooner just extends the throttle.
        backoff=$(( backoff == 0 ? 300 : backoff * 2 ))
        (( backoff > 3600 )) && backoff=3600
        echo "rate limited — backing off ${backoff}s"
        sleep "$backoff"
      elif grep -qiE 'limitexceeded|quotaexceeded' <<<"$output"; then
        echo "QUOTA"
        die "Service limit reached. Always Free allows 4 OCPU / 24 GB of Ampere in total,
  so an existing instance may be consuming it. Check Compute > Instances, or lower
  OCPUS / MEMORY_GB."
      elif grep -qiE 'notauthenticated|expired|invalid.*token|401' <<<"$output"; then
        # Recoverable: refresh and let the next pass retry rather than aborting a loop
        # that may have been running for hours.
        echo "auth expired"
        if oci session refresh --profile "${OCI_CLI_PROFILE:-DEFAULT}" >/dev/null 2>&1; then
          last_refresh=$(date +%s)
          log "session token refreshed, continuing"
        else
          die "Session expired and could not be refreshed. Run:
  oci session authenticate --profile-name ${OCI_CLI_PROFILE:-DEFAULT}"
        fi
      else
        echo "FAILED"
        sed 's/^/    /' <<<"$output" | head -12
        die "Not a capacity problem — see the message above."
      fi
    done
  done

  sleep "$INTERVAL"
done
