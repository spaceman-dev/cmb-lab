#!/usr/bin/env bash
# Create a VCN with a public subnet suitable for cmb-lab, and open the ports it needs.
#
# Oracle's "create instance" flow sometimes auto-creates a PRIVATE subnet, and a VNIC in a
# private subnet cannot be given a public IP — which is what produces:
#
#     "You must select a public subnet to assign a public IPv4 address"
#
# A public subnet needs three things that must all line up: an Internet Gateway, a route
# table sending 0.0.0.0/0 to it, and prohibit-public-ip-on-vnic set to false. This script
# creates all of them, plus security list rules for SSH, HTTP and HTTPS.
#
# EASIEST WAY TO RUN — OCI Cloud Shell (the '>_' icon in the console top bar):
#   git clone https://github.com/spaceman-dev/cmb-lab.git
#   cd cmb-lab && ./deploy/oracle/setup-network.sh
#
# Everything it creates is free. To undo: delete the VCN in the console, which removes the
# gateway, route table, security list and subnet with it.
set -uo pipefail

VCN_NAME="${VCN_NAME:-cmb-lab-vcn}"
VCN_CIDR="${VCN_CIDR:-10.0.0.0/16}"
SUBNET_NAME="${SUBNET_NAME:-cmb-lab-public}"
SUBNET_CIDR="${SUBNET_CIDR:-10.0.1.0/24}"

log()  { printf '\033[36m==> %s\033[0m\n' "$*"; }
ok()   { printf '\033[32m    %s\033[0m\n' "$*"; }
die()  { printf '\n\033[31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

command -v oci >/dev/null || die "OCI CLI not found. Use Cloud Shell ('>_' in the console),
  or install locally: brew install oci-cli && oci setup config"

OCI_ARGS=()
if [[ -n "${OCI_CLI_CLOUD_SHELL:-}" ]] || [[ -f /etc/oci-cloud-shell ]] || [[ -n "${OCI_CS_USER_OCID:-}" ]]; then
  OCI_ARGS+=(--auth instance_obo_user)
  log "Cloud Shell detected — using the delegation token"
fi

# The root compartment's OCID *is* the tenancy OCID. Cloud Shell exports it for us.
COMPARTMENT_OCID="${COMPARTMENT_OCID:-${OCI_TENANCY:-}}"
if [[ -z "$COMPARTMENT_OCID" ]]; then
  COMPARTMENT_OCID=$(awk -F= '/^tenancy=/{print $2; exit}' ~/.oci/config 2>/dev/null || true)
fi
[[ -n "$COMPARTMENT_OCID" ]] || die "Could not determine the compartment OCID.

  Note: a compartment NAME (e.g. 'dhruvbhat') is not an OCID. An OCID looks like
    ocid1.tenancy.oc1..aaaaaaaa...

  In Cloud Shell:  echo \$OCI_TENANCY
  In the console:  Identity > Compartments > click the compartment > copy OCID
  Then:            export COMPARTMENT_OCID=ocid1.tenancy.oc1..xxxxx"

log "Compartment: ${COMPARTMENT_OCID:0:32}..."

# ── Reuse an existing public subnet if there already is one ─────────────────────────────
existing=$(oci network subnet list "${OCI_ARGS[@]}" \
  --compartment-id "$COMPARTMENT_OCID" --all \
  --query 'data[?"prohibit-public-ip-on-vnic"==`false`]|[0].id' --raw-output 2>/dev/null)
if [[ -n "$existing" && "$existing" != "null" ]]; then
  ok "A public subnet already exists: $existing"
  echo
  echo "  export SUBNET_OCID=$existing"
  echo "  ./deploy/oracle/retry-create.sh"
  echo
  exit 0
fi

# ── VCN ─────────────────────────────────────────────────────────────────────────────────
log "Creating VCN $VCN_NAME ($VCN_CIDR)"
VCN_ID=$(oci network vcn create "${OCI_ARGS[@]}" \
  --compartment-id "$COMPARTMENT_OCID" \
  --display-name "$VCN_NAME" --cidr-blocks "[\"$VCN_CIDR\"]" \
  --dns-label cmblab \
  --wait-for-state AVAILABLE \
  --query 'data.id' --raw-output 2>&1) || die "VCN creation failed:
$VCN_ID"
ok "$VCN_ID"

# ── Internet Gateway ────────────────────────────────────────────────────────────────────
log "Creating Internet Gateway"
IGW_ID=$(oci network internet-gateway create "${OCI_ARGS[@]}" \
  --compartment-id "$COMPARTMENT_OCID" --vcn-id "$VCN_ID" \
  --display-name "${VCN_NAME}-igw" --is-enabled true \
  --wait-for-state AVAILABLE \
  --query 'data.id' --raw-output 2>&1) || die "Internet Gateway creation failed:
$IGW_ID"
ok "$IGW_ID"

# ── Route table: send everything not local to the gateway ───────────────────────────────
log "Creating route table (0.0.0.0/0 -> Internet Gateway)"
RT_ID=$(oci network route-table create "${OCI_ARGS[@]}" \
  --compartment-id "$COMPARTMENT_OCID" --vcn-id "$VCN_ID" \
  --display-name "${VCN_NAME}-rt" \
  --route-rules "[{\"destination\":\"0.0.0.0/0\",\"destinationType\":\"CIDR_BLOCK\",\"networkEntityId\":\"$IGW_ID\"}]" \
  --wait-for-state AVAILABLE \
  --query 'data.id' --raw-output 2>&1) || die "Route table creation failed:
$RT_ID"
ok "$RT_ID"

# ── Security list: SSH, HTTP, HTTPS in; everything out ──────────────────────────────────
# This is the cloud-side firewall. The instance ALSO has its own (firewalld on Oracle
# Linux) which bootstrap.sh handles separately — both must allow the traffic.
log "Creating security list (ingress 22, 80, 443)"
INGRESS='[
  {"protocol":"6","source":"0.0.0.0/0","isStateless":false,"tcpOptions":{"destinationPortRange":{"min":22,"max":22}}},
  {"protocol":"6","source":"0.0.0.0/0","isStateless":false,"tcpOptions":{"destinationPortRange":{"min":80,"max":80}}},
  {"protocol":"6","source":"0.0.0.0/0","isStateless":false,"tcpOptions":{"destinationPortRange":{"min":443,"max":443}}}
]'
EGRESS='[{"protocol":"all","destination":"0.0.0.0/0","isStateless":false}]'

SL_ID=$(oci network security-list create "${OCI_ARGS[@]}" \
  --compartment-id "$COMPARTMENT_OCID" --vcn-id "$VCN_ID" \
  --display-name "${VCN_NAME}-sl" \
  --ingress-security-rules "$INGRESS" --egress-security-rules "$EGRESS" \
  --wait-for-state AVAILABLE \
  --query 'data.id' --raw-output 2>&1) || die "Security list creation failed:
$SL_ID"
ok "$SL_ID"

# ── Public subnet ───────────────────────────────────────────────────────────────────────
# prohibit-public-ip-on-vnic=false is the flag that makes this subnet "public".
log "Creating public subnet $SUBNET_NAME ($SUBNET_CIDR)"
SUBNET_ID=$(oci network subnet create "${OCI_ARGS[@]}" \
  --compartment-id "$COMPARTMENT_OCID" --vcn-id "$VCN_ID" \
  --display-name "$SUBNET_NAME" --cidr-block "$SUBNET_CIDR" \
  --route-table-id "$RT_ID" --security-list-ids "[\"$SL_ID\"]" \
  --prohibit-public-ip-on-vnic false \
  --dns-label public \
  --wait-for-state AVAILABLE \
  --query 'data.id' --raw-output 2>&1) || die "Subnet creation failed:
$SUBNET_ID"
ok "$SUBNET_ID"

cat <<EOF

  ✓ Network ready. Instances here can receive a public IP, and ports 22/80/443 are open.

    VCN:    $VCN_ID
    Subnet: $SUBNET_ID

  Now create the instance:

    export SUBNET_OCID=$SUBNET_ID
    ./deploy/oracle/retry-create.sh

  Or in the console, pick VCN "$VCN_NAME" / subnet "$SUBNET_NAME" and the
  "Assign a public IPv4 address" option will no longer be greyed out.

EOF
