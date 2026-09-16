#!/usr/bin/env bash
# Keep trying to create an Ampere A1 instance until Oracle has capacity.
#
# "Out of capacity for shape VM.Standard.A1.Flex" is the single most common obstacle to
# using Oracle's free tier. Capacity is released continuously as other people's instances
# are terminated, so the reliable approach is to keep asking. Most people succeed within a
# few hours; sometimes it takes a day or two.
#
# Setup (once):
#   1. Install the OCI CLI:  bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)"
#   2. Configure it:         oci setup config
#   3. Fill in the values below, or pass them as environment variables.
#
# Then:
#   ./deploy/oracle/retry-create.sh
#
# Leave it running. It stops as soon as an instance is created.
set -uo pipefail

# ── Required: get these from the OCI console ────────────────────────────────────────────
# Compartment OCID:  Identity > Compartments  (the root compartment is your tenancy OCID)
# Subnet OCID:       Networking > VCN > Subnets
# Image OCID:        region-specific; see the lookup command in the notes below
COMPARTMENT_OCID="${COMPARTMENT_OCID:-}"
SUBNET_OCID="${SUBNET_OCID:-}"
IMAGE_OCID="${IMAGE_OCID:-}"
SSH_PUBLIC_KEY="${SSH_PUBLIC_KEY:-$HOME/.ssh/oracle-cmblab.pub}"

DISPLAY_NAME="${DISPLAY_NAME:-cmb-lab}"
SHAPE="${SHAPE:-VM.Standard.A1.Flex}"
OCPUS="${OCPUS:-4}"
MEMORY_GB="${MEMORY_GB:-24}"
BOOT_VOLUME_GB="${BOOT_VOLUME_GB:-100}"
INTERVAL="${INTERVAL:-60}"           # seconds between attempts
MAX_ATTEMPTS="${MAX_ATTEMPTS:-0}"    # 0 = unlimited

die() { printf '\033[31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

command -v oci >/dev/null || die "OCI CLI not installed. See the header of this script."
[[ -n "$COMPARTMENT_OCID" ]] || die "Set COMPARTMENT_OCID (Identity > Compartments)."
[[ -n "$SUBNET_OCID"      ]] || die "Set SUBNET_OCID (Networking > VCN > Subnets)."
[[ -n "$IMAGE_OCID"       ]] || die "Set IMAGE_OCID. To list Oracle Linux 9 ARM images:
  oci compute image list --compartment-id \$COMPARTMENT_OCID \\
      --operating-system 'Oracle Linux' --operating-system-version '9' \\
      --shape VM.Standard.A1.Flex --query 'data[0].id' --raw-output"
[[ -f "$SSH_PUBLIC_KEY"   ]] || die "SSH public key not found at $SSH_PUBLIC_KEY.
  Generate one with:  ssh-keygen -t ed25519 -f ${SSH_PUBLIC_KEY%.pub} -C cmb-lab"

# Every availability domain in the region. Trying all of them materially improves the odds:
# capacity is tracked per-AD, so AD-1 being full says nothing about AD-2.
mapfile -t ADS < <(oci iam availability-domain list \
  --compartment-id "$COMPARTMENT_OCID" --query 'data[].name' --raw-output 2>/dev/null \
  | tr -d '[]", ' | grep -v '^$')
(( ${#ADS[@]} )) || die "Could not list availability domains. Is the OCI CLI configured?"

cat <<EOF

  Requesting ${OCPUS} OCPU / ${MEMORY_GB} GB ${SHAPE}
  Availability domains: ${ADS[*]}
  Retrying every ${INTERVAL}s. Ctrl-C to stop.

  Tip: if this runs for hours without luck, try OCPUS=1 MEMORY_GB=6 — a smaller
  request is far easier to place, and A1.Flex can be resized upward later.

EOF

attempt=0
while :; do
  attempt=$((attempt + 1))
  (( MAX_ATTEMPTS > 0 && attempt > MAX_ATTEMPTS )) && { echo "Gave up after $MAX_ATTEMPTS attempts."; exit 1; }

  for ad in "${ADS[@]}"; do
    printf '[%s] attempt %d — %s ... ' "$(date +%H:%M:%S)" "$attempt" "$ad"

    output=$(oci compute instance launch \
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
      --wait-for-state RUNNING \
      2>&1)
    rc=$?

    if (( rc == 0 )); then
      instance_id=$(grep -o 'ocid1\.instance\.[a-z0-9.\-]*' <<<"$output" | head -1)
      ip=$(oci compute instance list-vnics --instance-id "$instance_id" \
             --query 'data[0]."public-ip"' --raw-output 2>/dev/null)
      cat <<EOF

  ✓ Instance created.

    OCID:  $instance_id
    IP:    $ip

  Next:
    ssh -i ${SSH_PUBLIC_KEY%.pub} opc@$ip
    sudo dnf install -y git
    git clone https://github.com/spaceman-dev/cmb-lab.git /tmp/cmb-lab
    sudo /tmp/cmb-lab/deploy/oracle/bootstrap.sh

  Then open TCP 80/443 in the VCN security list.

EOF
      exit 0
    fi

    if grep -qi 'out of capacity\|OutOfCapacity\|InternalError' <<<"$output"; then
      echo "no capacity"
    elif grep -qi 'LimitExceeded\|QuotaExceeded' <<<"$output"; then
      echo
      echo "$output" | head -5
      die "Service limit hit. You may already have Always Free instances using the quota
  (4 OCPU / 24 GB total). Check Compute > Instances, or lower OCPUS/MEMORY_GB."
    else
      echo "failed"
      echo "$output" | head -8
      die "Unexpected error — not a capacity problem. See above."
    fi
  done

  sleep "$INTERVAL"
done
