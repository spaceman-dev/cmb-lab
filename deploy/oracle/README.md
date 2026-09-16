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
| Image | **Ubuntu 22.04** or 24.04 | Scripts assume apt and `netfilter-persistent` |
| Shape | **VM.Standard.A1.Flex** | The Ampere ARM shape. *Not* E2.1.Micro — 1 GB will not run CAMB |
| OCPUs | **4** | Full free allowance |
| Memory | **24 GB** | Full free allowance |
| Boot volume | **100 GB** | Free tier allows 200 GB total |
| SSH key | Upload your public key | You will need the private key to connect |

> **"Out of host capacity"** is the single most common problem with Ampere instances — the
> free ARM shape is heavily oversubscribed in popular regions. If you hit it, try a
> different availability domain, or a different region, or retry periodically. It is not
> something the deployment scripts can work around.

> If your account was upgraded to Pay As You Go, confirm the shape is still tagged
> **Always Free** before creating it, or you will be billed.

## 2. Connect

```bash
chmod 600 ~/.ssh/your-oracle-key
ssh -i ~/.ssh/your-oracle-key ubuntu@<INSTANCE_PUBLIC_IP>
```

The default user is `ubuntu` for Ubuntu images, `opc` for Oracle Linux.

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

### 3b. The instance's own iptables

**This is the step people miss.** Oracle's Ubuntu images ship with an iptables `REJECT`
rule that drops everything except SSH, regardless of what the security list says.

`bootstrap.sh` handles this automatically. If you are doing it manually:

```bash
sudo iptables -I INPUT 6 -p tcp --dport 80  -m state --state NEW,ESTABLISHED -j ACCEPT
sudo iptables -I INPUT 6 -p tcp --dport 443 -m state --state NEW,ESTABLISHED -j ACCEPT
sudo netfilter-persistent save
```

Note `-I INPUT 6` (insert) rather than `-A INPUT` (append) — appending puts the rule *after*
the catch-all REJECT, where it has no effect.

## 4. Run the bootstrap

```bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/spaceman-dev/cmb-lab.git /tmp/cmb-lab
sudo /tmp/cmb-lab/deploy/oracle/bootstrap.sh \
     https://github.com/spaceman-dev/cmb-lab.git \
     cmb.example.com          # omit the domain to serve plain HTTP on the IP
```

It will:

1. Install Python 3.12, Node 20, Go, Caddy, gfortran, and the HEALPix/BLAS libraries
2. Fix the iptables rules
3. Create a `cmblab` system user and check out to `/opt/cmb-lab`
4. Build the Python environment — **CAMB compiles Fortran, so expect 10–15 minutes**
5. Build the Go gateway and the React frontend
6. Download ~170 MB of WMAP/Planck data
7. Install systemd units and start everything
8. Configure Caddy, which obtains a Let's Encrypt certificate automatically if you gave a
   domain

Total: roughly 30–45 minutes on a fresh instance, most of it CAMB and the data download.

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
security list *and* `sudo iptables -L INPUT -n --line-numbers`. Confirm your ACCEPT rules
appear above the REJECT.

**Caddy cannot get a certificate.** Let's Encrypt must reach port 80. Verify the DNS A
record points at the instance IP (`dig +short your-domain`) and that port 80 is open.

**A service keeps restarting.** `journalctl -u cmblab@<name> -n 100`. Usually missing data —
run `sudo -u cmblab /opt/cmb-lab/.venv/bin/cmblab-ingest bootstrap`.

**CAMB fails to build.** Needs `gfortran`, installed by the bootstrap. On Oracle Linux
rather than Ubuntu, use `dnf install gcc-gfortran` and adapt the package names.

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
