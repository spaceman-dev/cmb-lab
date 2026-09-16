# Deploying cmb-lab for free

Honest summary first: **this is a heavy application.** CAMB compiles Fortran, healpy pulls
in a C++ HEALPix stack, and a full analysis wants ~270 MB of archive data plus multiple CPU
cores. Most free tiers are built for a small Node app, not this.

So there are two realistic strategies, and the right one depends on what you want the
deployment to *do*.

| Strategy | Cost | Interactive? | Best for |
| :-- | :-- | :-- | :-- |
| **A. Static showcase** | Free, forever | No — pre-computed results | Portfolios, sharing results, the Learn tab |
| **B. Full application** | Free tier, with caveats | Yes | Demos where people run their own analysis |

If you want the full interactive app, go straight to
**[Oracle Cloud Always Free](../deploy/oracle/README.md)** — it is the only free tier with
enough CPU and RAM to run this comfortably, and the deployment is scripted end to end.

---

## Strategy A — static showcase (recommended)

Pre-compute every result, export it as JSON and PNG, and ship only the frontend. The Learn
tab, the glossary, the curated assistant, all charts, and all sky maps keep working. Only
live recomputation is lost.

This deploys to Vercel, Netlify, Cloudflare Pages, or GitHub Pages for free with no
time limits and no cold starts.

### 1. Export the results

With services running locally:

```bash
mkdir -p web/public/snapshot

# core results
curl -s localhost:8080/api/v1/spectrum/spectra/latest        > web/public/snapshot/spectrum.json
curl -s localhost:8080/api/v1/cosmology/inference/jobs       > web/public/snapshot/inference.json
curl -s localhost:8080/api/v1/anomaly/jobs                   > web/public/snapshot/anomaly.json
curl -s localhost:8080/api/v1/spectrum/references            > web/public/snapshot/references.json

# the teaching layer is fully static already
curl -s localhost:8080/api/v1/tutor/curriculum               > web/public/snapshot/curriculum.json
for l in origin harmonics peaks estimator inference anomalies; do
  curl -s "localhost:8080/api/v1/tutor/lessons/$l"           > "web/public/snapshot/lesson-$l.json"
done
curl -s localhost:8080/api/v1/tutor/glossary                 > web/public/snapshot/glossary.json
curl -s localhost:8080/api/v1/chat/capabilities              > web/public/snapshot/chat.json

# pre-render the sky maps
mkdir -p web/public/snapshot/maps
for p in quadrupole octupole low-multipoles acoustic damping; do
  curl -s "localhost:8080/api/v1/skymap/preset/wmap9/ilc-map/$p.png?width=1100" \
       -o "web/public/snapshot/maps/$p.png"
done
curl -s "localhost:8080/api/v1/skymap/render/wmap9/ilc-map.png?projection=mollweide&width=1600" \
     -o web/public/snapshot/maps/full.png
```

### 2. Point the client at the snapshot

Add a build-time switch in `web/src/api/client.ts`:

```ts
const STATIC = import.meta.env.VITE_STATIC_MODE === "true";

async function request<T>(path: string): Promise<T> {
  if (STATIC) {
    const file = SNAPSHOT_ROUTES[path];
    if (!file) throw new Error(`No snapshot for ${path}. Run the export script.`);
    return (await fetch(`/snapshot/${file}`)).json();
  }
  return liveRequest<T>(path);
}
```

Disable the Recompute buttons when `STATIC` is set, with a note linking to this file so
visitors know the local version is interactive.

### 3. Deploy

```bash
VITE_STATIC_MODE=true npm --prefix web run build
```

<details>
<summary><b>Vercel</b></summary>

```bash
npm i -g vercel
cd web && vercel --prod
```
Build command `npm run build`, output `dist`, env `VITE_STATIC_MODE=true`.
</details>

<details>
<summary><b>Netlify</b></summary>

```bash
npm i -g netlify-cli
cd web && netlify deploy --prod --dir=dist
```
</details>

<details>
<summary><b>GitHub Pages</b></summary>

Set `base: "/cmb-lab/"` in `vite.config.ts`, then use the workflow in
`.github/workflows/pages.yml`.
</details>

---

## Strategy B — full application

### Option 1: Hugging Face Spaces — best fit

Free Spaces give **16 GB RAM and 2 vCPU** with Docker, no sleep, and no credit card. This is
the only mainstream free tier that comfortably fits the scientific Python stack.

Create `Dockerfile` at the repo root:

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      gfortran build-essential curl git && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -e libs/cmblab-core \
    && for s in ingest catalog spectrum cosmology anomaly skymap tutor chat playground; do \
         pip install --no-cache-dir -e "services/$s"; done

# Frontend
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm --prefix web ci && npm --prefix web run build

# Data: fetch at build time so the image is self-contained
RUN python -m cmblab_ingest.cli bootstrap

EXPOSE 7860
CMD ["./scripts/serve.sh"]
```

Spaces expects one port, so run the gateway on 7860 and have it serve `web/dist` as static
files. Then:

```bash
git remote add hf https://huggingface.co/spaces/<user>/cmb-lab
git push hf main
```

> **Watch out:** the free tier has a 50 GB image limit but builds time out after ~1 hour.
> `make data-bootstrap` takes 10–20 minutes on a good connection. If the build times out,
> host the cleaned `.npz` files as a HF Dataset and download those instead of the raw FITS —
> they are much smaller and need no processing.

### Option 2: Fly.io

Free allowance covers ~3 shared-cpu-1x machines with 256 MB RAM, which is **not enough** —
CAMB alone wants more. Scale to 1 GB and you leave the free tier. Usable if you are willing
to spend a few dollars a month.

```bash
fly launch --no-deploy
fly volumes create cmblab_data --size 3    # data must persist
fly deploy
```

Set `auto_stop_machines = true` so it sleeps when idle.

### Option 3: Render

Free web services get 512 MB and **spin down after 15 minutes idle**, with a ~50 second cold
start. The filesystem is ephemeral, so `data/` disappears on every restart — you would need
to re-download 170 MB each time, which will exceed the startup timeout.

Only workable if you bake the data into the image and accept cold starts.

### Option 4: Oracle Cloud Always Free — **the main deployment**

The most generous free tier that exists: **4 ARM cores and 24 GB RAM**, permanently free.
That is comparable to the machine this project was developed on, so everything works
including multi-core MCMC.

This is fully automated. See **[deploy/oracle/README.md](../deploy/oracle/README.md)** for
the full walkthrough.

```bash
# on a fresh Ubuntu 22.04 VM.Standard.A1.Flex instance
git clone https://github.com/spaceman-dev/cmb-lab.git /tmp/cmb-lab
sudo /tmp/cmb-lab/deploy/oracle/bootstrap.sh \
     https://github.com/spaceman-dev/cmb-lab.git \
     your-domain.com
```

The script installs every dependency, fixes Oracle's iptables rules, builds the gateway and
frontend, downloads the data, installs systemd units, and configures Caddy with automatic
Let's Encrypt TLS.

Two Oracle-specific traps the script handles for you:

- **Two firewalls.** Opening the VCN security list is not enough; OCI images also ship an
  iptables `REJECT` rule. The rule must be *inserted* above it, not appended after.
- **"Out of host capacity".** The free ARM shape is heavily oversubscribed. Try another
  availability domain or region, or retry — no script can work around this one.

---

## Making it lighter

Whichever route you take:

| Action | Saves |
| :-- | :-- |
| Ship only `BOOTSTRAP_PRODUCTS` | ~100 MB vs the full archive |
| Ship cleaned `.npz`, not raw FITS | ~60% of the data size |
| Pre-render sky map PNGs | Removes matplotlib from the request path |
| Pre-compute a CAMB grid and interpolate | Removes the Fortran dependency entirely |
| Degrade maps to N_side 512 | 4× smaller; fine up to ℓ ≈ 1000 |
| `--no-cache-dir` on every pip install | ~300 MB of image layers |

Dropping CAMB is the single biggest win if you only need fixed theory curves: pre-compute
spectra on a parameter grid, save as `.npz`, and interpolate. That removes gfortran, the
build toolchain, and most of the memory requirement.

---

## What each strategy actually gives you

| Feature | Static | Full |
| :-- | :-: | :-: |
| Learn tab, all six lessons | ✅ | ✅ |
| Glossary and curated assistant | ✅ | ✅ |
| Pre-computed spectrum, corner plots, anomalies | ✅ | ✅ |
| Sky map presets | ✅ | ✅ |
| Interactive sky map filtering | ❌ | ✅ |
| Recompute the spectrum | ❌ | ✅ |
| Run your own MCMC | ❌ | ✅ |
| Playground knobs | ❌ | ✅ |
| Gemini assistant | ❌ | ✅ |
| Cost | $0 | $0–5/mo |
| Cold starts | None | Likely |

For a portfolio or for sharing results, static is genuinely the better product: it is
instant, it never falls over, and the science on display is identical.
