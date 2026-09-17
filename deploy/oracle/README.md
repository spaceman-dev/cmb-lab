# Deploying to Oracle Cloud Always Free

Oracle's Always Free tier gives **4 Ampere ARM cores and 24 GB RAM, permanently**, which is
comparable to the machine this project was developed on. Everything works, including
multi-core MCMC. It is by far the most capable free tier available.

The trade-off is that it is a plain VM: you manage the OS, the firewall, and TLS. These
scripts do that for you.

---

## The short version

Open **Cloud Shell** — the `>_` icon in the OCI console's top bar.

```bash
git clone https://github.com/spaceman-dev/cmb-lab.git && cd cmb-lab
./deploy/oracle/deploy.sh
```

That one script inventories existing instances and offers to remove any too small to run
the app, creates a public subnet if there isn't one, and then loops instance creation until
Ampere capacity frees up.

When it reports an IP, SSH in and run the bootstrap:

```bash
ssh -i ~/.ssh/oracle-cmblab opc@<IP>
sudo dnf install -y git
git clone https://github.com/spaceman-dev/cmb-lab.git /tmp/cmb-lab
sudo /tmp/cmb-lab/deploy/oracle/bootstrap.sh
```

> **Use Cloud Shell, not your laptop.** The CLI is pre-authenticated there, and it runs
> inside Oracle's network. Corporate TLS inspection (Zscaler and similar) breaks the OCI
> CLI's Python HTTP stack in ways that look like certificate errors but are not — `curl`
> and `openssl` will both succeed while the CLI hangs indefinitely.

**Order matters.** The network has to exist before the instance: an instance created on a
private subnet cannot be given a public IP, and that is not fixable afterwards.

### Always Free safety

`retry-create.sh` refuses to create anything billable. It checks the shape is on the Always
Free list, caps Ampere at 4 OCPU / 24 GB with the 6 GB-per-OCPU ratio enforced, caps the
boot volume at 200 GB, and sums existing instances first — the allowance is tenancy-wide, so
a forgotten instance silently consumes it.

Defaults are the smallest thing that actually works: **1 OCPU / 6 GB, 50 GB boot volume**.

The rest of this document explains each step and what to do when it goes wrong.


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
you have done wrong — Ampere is heavily oversubscribed, so Oracle has none free in that
availability domain at that moment. Capacity is released continuously as other people
terminate instances, so the reliable approach is to keep asking.

**The easy way — OCI Cloud Shell.** Click the `>_` icon in the console's top bar. The CLI
is already authenticated there, so there is nothing to configure:

```bash
git clone https://github.com/spaceman-dev/cmb-lab.git
cd cmb-lab && ./deploy/oracle/retry-create.sh
```

It discovers your tenancy, the newest Oracle Linux 9 ARM image, a public subnet, and every
availability domain, then loops until one succeeds. Leave the tab open.

Tune it if needed:

```bash
OCPUS=1 MEMORY_GB=6 INTERVAL=30 ./deploy/oracle/retry-create.sh
```

What actually helps, in order:

1. **Ask for less.** 1 OCPU / 6 GB places far more easily than 4 / 24, and A1.Flex can be
   resized upward later without rebuilding. 6 GB builds and runs everything, just slower.
2. **Try every availability domain.** Capacity is per-AD — AD-1 being full says nothing
   about AD-2. The script does this automatically. (Some regions have only one AD.)
3. **Retry on a loop.** Hours, sometimes a day. This is normal and not a sign of a problem.
4. **Do not pin a fault domain.** Letting Oracle choose gives it more placement options.
5. **Different region.** Effective, but your home region is fixed at signup.

Upgrading to Pay As You Go also lifts the capacity restriction — Always Free shapes stay
free, but you leave the lowest-priority queue. Only do this if you are comfortable that a
misconfigured non-free resource could incur charges.

> **While you wait:** the [static showcase](../../docs/deployment.md#strategy-a--static-showcase-recommended)
> deploys to Vercel or Netlify in minutes, free and permanently. It serves the full Learn
> tab, the glossary, the curated assistant, and all pre-computed results — everything
> except live recomputation. Worth having up regardless.



## 2. Connect

```bash
chmod 600 ~/.ssh/oracle-cmblab
ssh -i ~/.ssh/oracle-cmblab opc@<INSTANCE_PUBLIC_IP>      # Oracle Linux
ssh -i ~/.ssh/oracle-cmblab ubuntu@<INSTANCE_PUBLIC_IP>   # Ubuntu
```

The default user is **`opc`** on Oracle Linux and **`ubuntu`** on Ubuntu images.

## 3. Networking: you need a **public** subnet

If the console greys out the public IP option and says:

> *You must select a public subnet to assign a public IPv4 address*

— then the subnet OCI auto-created for you is **private**, and no checkbox will fix it. A
VNIC in a private subnet cannot hold a public IP.

A public subnet needs three things that must all agree: an Internet Gateway, a route table
sending `0.0.0.0/0` to it, and `prohibit-public-ip-on-vnic = false`.

The script builds all of it, plus the security list rules:

```bash
./deploy/oracle/setup-network.sh
```

Or in the console: **Networking → Virtual Cloud Networks → Create VCN → "VCN with Internet
Connectivity"**, which produces a public subnet alongside a private one. Select the
**public** one when creating the instance.

### The two firewall layers

Oracle filters traffic in two independent places. Missing either gives the same symptom:
the port simply times out.

**3a. VCN security list** (cloud-side) — created by `setup-network.sh`. Manually:
Networking → VCN → Security Lists → default → **Add Ingress Rules**:

| Source CIDR | Protocol | Destination port |
| :-- | :-- | :-- |
| `0.0.0.0/0` | TCP | 22 |
| `0.0.0.0/0` | TCP | 80 |
| `0.0.0.0/0` | TCP | 443 |

**3b. The instance's own firewall** — handled by `bootstrap.sh`. **This is the step people
miss.** OCI images filter locally too, regardless of the security list.

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

Oracle Linux also runs SELinux enforcing, which blocks Caddy from proxying to the local
gateway. That surfaces as a **502, not a timeout**:

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
