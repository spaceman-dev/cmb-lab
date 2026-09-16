# Deploying to Oracle Cloud Always Free

Oracle's Always Free tier gives **4 Ampere ARM cores and 24 GB RAM, permanently**, which is
comparable to the machine this project was developed on. Everything works, including
multi-core MCMC. It is by far the most capable free tier available.

The trade-off is that it is a plain VM: you manage the OS, the firewall, and TLS. These
scripts do that for you.

---

## 1. Create the instance

In the OCI Console → **Compute → Instances → Create instance**:

| Setting | Value | Why |
| :-- | :-- | :-- |
| Image | **Oracle Linux 9** or **Ubuntu 22.04/24.04** | The bootstrap script handles both |
| Shape | **VM.Standard.A1.Flex** | The Ampere ARM shape. *Not* E2.1.Micro — 1 GB will not run CAMB |
| OCPUs / Memory | **4 OCPU / 24 GB**, or **1 / 6** if capacity is tight | Free allowance is 4 OCPU + 24 GB total |
| Boot volume | **100 GB** | Free tier allows 200 GB total |
| **Public IPv4 address** | **Assign a public IPv4 address** | ⚠️ Defaults to *No* on new VCNs. Without it the instance is unreachable |
| **SSH keys** | **Upload your public key** | ⚠️ Oracle Linux disables password login. No key = no access, ever |

> ### The two settings people get wrong
>
> **Public IP.** If the subnet is private, or you leave "Assign a public IPv4 address"
> unchecked, you get an instance with no internet-facing address. You cannot SSH to it and
> nobody can reach the site. Adding one later means attaching a new VNIC or reserving an IP
> — far easier to get right at creation.
>
> **SSH key.** There is no password fallback. An instance created without a key is
> permanently inaccessible; the only fix is to terminate it and start again.
>
> Generate one first if you have none:
> ```bash
> ssh-keygen -t ed25519 -f ~/.ssh/oracle-cmblab -C cmb-lab
> cat ~/.ssh/oracle-cmblab.pub        # paste this into the console
> ```

### "Out of capacity for shape VM.Standard.A1.Flex"

This is the single most common obstacle to using the free tier, and it is not something
you have done wrong — Ampere capacity is heavily oversubscribed, so Oracle simply has none
free in that availability domain right now.

What actually works, roughly in order of effectiveness:

1. **Ask for less.** A 1 OCPU / 6 GB request is far easier to place than 4 / 24. A1.Flex
   can be resized upward later without rebuilding, so this costs you nothing permanent.
   6 GB is enough to build and run everything, just more slowly.
2. **Try every availability domain.** Capacity is tracked per-AD. AD-1 being full tells you
   nothing about AD-2 or AD-3. (Note: many regions have only one AD.)
3. **Retry on a loop.** Capacity is released continuously as other people terminate
   instances. Scripted retrying is the standard approach and usually succeeds within a few
   hours:
   ```bash
   export COMPARTMENT_OCID=ocid1.tenancy.oc1..xxxxx
   export SUBNET_OCID=ocid1.subnet.oc1..xxxxx
   export IMAGE_OCID=ocid1.image.oc1..xxxxx
   ./deploy/oracle/retry-create.sh          # add OCPUS=1 MEMORY_GB=6 if needed
   ```
4. **Do not specify a fault domain.** Letting Oracle choose gives it more placement options.
5. **Different region.** Effective, but your home region is fixed at signup, and moving
   means a new account.

Upgrading to Pay As You Go also removes the capacity restriction on Always Free shapes —
they stay free, but you are no longer in the lowest-priority queue. Only do this if you are
comfortable that a misconfigured non-free resource could incur charges.


## 2. Connect

```bash
chmod 600 ~/.ssh/oracle-cmblab
ssh -i ~/.ssh/oracle-cmblab opc@<INSTANCE_PUBLIC_IP>      # Oracle Linux
ssh -i ~/.ssh/oracle-cmblab ubuntu@<INSTANCE_PUBLIC_IP>   # Ubuntu
```

The default user is **`opc`** on Oracle Linux and **`ubuntu`** on Ubuntu images.

## 3. Open the ports — **both** layers

Oracle blocks traffic in two independent places. Missing either one produces the same
symptom: the port simply times out.

### 3a. VCN security list (the cloud firewall)

Console → **Networking → Virtual Cloud Networks →** your VCN **→ Security Lists →** default
→ **Add Ingress Rules**:

| Source CIDR | Protocol | Destination port | Purpose |
| :-- | :-- | :-- | :-- |
| `0.0.0.0/0` | TCP | 80 | HTTP, and Let's Encrypt validation |
| `0.0.0.0/0` | TCP | 443 | HTTPS |

### 3b. The instance's own firewall

**This is the step people miss.** OCI images filter traffic locally as well, regardless of
what the security list says — `firewalld` on Oracle Linux, a baked-in iptables `REJECT`
rule on Ubuntu.

`bootstrap.sh` handles this automatically. Manually:

```bash
# Oracle Linux (firewalld)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload

# Ubuntu (iptables)
sudo iptables -I INPUT 6 -p tcp --dport 80  -m state --state NEW,ESTABLISHED -j ACCEPT
sudo iptables -I INPUT 6 -p tcp --dport 443 -m state --state NEW,ESTABLISHED -j ACCEPT
sudo netfilter-persistent save
```

Note `-I INPUT 6` (insert) rather than `-A INPUT` (append) — appending puts the rule *after*
the catch-all REJECT, where it has no effect.

Oracle Linux also runs SELinux in enforcing mode, which blocks Caddy from proxying to the
local gateway. The script sets `httpd_can_network_connect`; manually it is:

```bash
sudo setsebool -P httpd_can_network_connect 1
```

## 4. Run the bootstrap

```bash
# Oracle Linux
sudo dnf install -y git
# Ubuntu
# sudo apt-get update && sudo apt-get install -y git

git clone https://github.com/spaceman-dev/cmb-lab.git /tmp/cmb-lab
sudo /tmp/cmb-lab/deploy/oracle/bootstrap.sh \
     https://github.com/spaceman-dev/cmb-lab.git \
     cmb.example.com          # omit the domain to serve plain HTTP on the IP
```

It detects the distribution and then:

1. Installs Python 3.12, Node 20, Go, Caddy, gfortran, and the HEALPix/BLAS libraries
2. Fixes the local firewall and SELinux
3. Creates a `cmblab` system user and checks out to `/opt/cmb-lab`
4. Builds the Python environment — **CAMB compiles Fortran, so expect 10–15 minutes**
5. Builds the Go gateway and the React frontend
6. Downloads ~170 MB of WMAP/Planck data
7. Installs systemd units and starts everything
8. Configures Caddy, which obtains a Let's Encrypt certificate automatically if you gave a
   domain

Total: roughly 30–45 minutes on 4 OCPU, longer on 1. Most of it is CAMB and the download.

## 5. Add the Gemini key (optional)

The site is fully functional without it — the assistant falls back to 29 curated answers.

```bash
sudo -u cmblab nano /opt/cmb-lab/.env      # set GEMINI_API_KEY=...
sudo systemctl restart cmblab.target       # settings are cached; a restart is required
```

## 6. Verify

```bash
systemctl --plain list-units 'cmblab*'
curl -s localhost:8080/health | python3 -m json.tool
journalctl -u cmblab-spectrum -n 50
```

Then open `https://your-domain` or `http://<INSTANCE_IP>`.

---

## Operating it

| Task | Command |
| :-- | :-- |
| Update to latest `main` | `sudo /opt/cmb-lab/deploy/oracle/update.sh` |
| Restart everything | `sudo systemctl restart cmblab.target` |
| Restart one service | `sudo systemctl restart cmblab@spectrum` |
| Follow logs | `sudo journalctl -u cmblab@spectrum -f` |
| All service logs | `sudo journalctl -u 'cmblab*' -f` |
| Caddy logs | `sudo journalctl -u caddy -f` |
| Stop everything | `sudo systemctl stop cmblab.target` |

### Layout on the server

```
/opt/cmb-lab/              source, owned by the cmblab user
  .venv/                   Python environment
  data/                    archive + cleaned maps (the only writable path)
  web/dist/                built frontend, served by Caddy
  services/gateway/bin/    compiled gateway
/etc/caddy/Caddyfile       reverse proxy config
/etc/systemd/system/cmblab*  units
```

### How requests flow

```
Internet :443
   └─ Caddy (TLS, static files)
        ├─ /            → /opt/cmb-lab/web/dist
        └─ /api/v1/*    → 127.0.0.1:8080  (Go gateway)
                              └─ 127.0.0.1:8001-8010  (Python services)
```

Only Caddy listens publicly. Every backend binds to loopback, and the systemd units add
`ProtectSystem=strict` with `data/` as the sole writable path.

---

## Troubleshooting

**Page times out.** Almost always the firewall. Check both layers from section 3 — the VCN
security list *and* the instance's own filter: `sudo firewall-cmd --list-all` on Oracle
Linux, `sudo iptables -L INPUT -n --line-numbers` on Ubuntu (ACCEPT rules must appear
*above* the REJECT). Also confirm the instance actually has a public IP — run
`curl -s ifconfig.me` on the box, and check **Instance details → Public IP** in the console.

**Caddy returns 502.** On Oracle Linux this is SELinux blocking the local proxy:
`sudo setsebool -P httpd_can_network_connect 1`.

**Caddy cannot get a certificate.** Let's Encrypt must reach port 80. Verify the DNS A
record points at the instance IP (`dig +short your-domain`) and that port 80 is open.

**A service keeps restarting.** `journalctl -u cmblab@<name> -n 100`. Usually missing data —
run `sudo -u cmblab /opt/cmb-lab/.venv/bin/cmblab-ingest bootstrap`.

**CAMB fails to build.** Needs a Fortran compiler — `gcc-gfortran` on Oracle Linux,
`gfortran` on Ubuntu. Both are installed by the bootstrap.

**Out of memory during the npm build.** Rare with 24 GB, but if you provisioned a smaller
shape: `NODE_OPTIONS=--max-old-space-size=2048 npm run build`.

**MCMC is slow.** Expected — 4 ARM cores versus the 14 this was developed on. Reduce walkers
or steps in the Inference tab. The thread-pinning environment variables in the unit file are
important; without them oversubscription makes it far worse.

---

## Cost

Everything here fits in Always Free: 4 OCPU + 24 GB Ampere, 100 GB of the 200 GB block
volume allowance, and 10 TB/month egress. Caddy's certificates are free.

The one thing to watch is that Oracle reclaims **idle** Always Free compute instances. A
publicly reachable site with occasional traffic is not idle, but an instance you provision
and never visit may be reclaimed.
