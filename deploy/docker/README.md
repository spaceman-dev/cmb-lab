# Container deployment

Everything runs behind **one port** — eight Python services, the Go gateway, and the built
frontend. The gateway serves `web/dist` directly when `STATIC_DIR` is set, so there is no
separate web server to configure.

That makes the image portable to any container platform: Hugging Face Spaces, Cloud Run,
Fly.io, Render, or plain Docker.

## Build and run locally

```bash
docker build -t cmb-lab .
docker run -p 7860:7860 cmb-lab
```

Then open http://localhost:7860.

The build takes a while — CAMB compiles Fortran, and ~170 MB of archive data is downloaded
and baked into the image so the container starts ready to use.

### Resource requirements

Measured, not estimated:

| | |
| :-- | :-- |
| Per Python service (imports only) | **~131 MB** |
| Eight services | **~1.05 GB** |
| Plus OS, gateway, and working data | **~1.5–2 GB** |
| Peak during build (CAMB + npm) | **~4 GB** |

**Minimum practical runtime: 2 GB. Recommended: 4 GB+.**

A 1 GB instance cannot run this — the imports alone exceed the total memory. This rules out
Oracle's `VM.Standard.E2.1.Micro` and similar micro shapes.

---

## Hugging Face Spaces — recommended free option

Free Spaces give **2 vCPU and 16 GB RAM** with Docker, no sleep, and no credit card. It is
the only mainstream free tier with enough memory for the scientific Python stack.

1. Create a Space at https://huggingface.co/new-space — choose **Docker** → **Blank**.

2. Push the repo to it:

   ```bash
   git remote add hf https://huggingface.co/spaces/<your-username>/cmb-lab
   git push hf main
   ```

3. Replace the Space's `README.md` with [README-huggingface.md](README-huggingface.md) —
   Spaces requires YAML frontmatter declaring `sdk: docker` and `app_port: 7860`:

   ```bash
   cp deploy/docker/README-huggingface.md README.md
   git add README.md && git commit -m "HF Spaces frontmatter" && git push hf main
   ```

   Keep this on a separate branch if you do not want it overwriting the GitHub README.

4. Optionally add `GEMINI_API_KEY` under **Settings → Variables and secrets** to enable
   open-ended assistant questions. Everything else works without it.

**Build time is the main risk.** Compiling CAMB plus downloading the archive data can
approach the Space build limit. If it times out, host the cleaned `.npz` files as a HF
Dataset and fetch those in the Dockerfile instead of the raw FITS — they are much smaller
and need no processing.

---

## Other platforms

| Platform | Free tier | Verdict |
| :-- | :-- | :-- |
| **Hugging Face Spaces** | 2 vCPU / 16 GB | ✅ Best fit |
| **Google Cloud Run** | 2 GB, scales to zero | ⚠️ Works, but cold starts are slow and the image is large |
| **Fly.io** | 256 MB on the free allowance | ❌ Needs a paid 2 GB machine |
| **Render** | 512 MB, ephemeral disk, sleeps | ❌ Too little memory; data would not persist |
| **Oracle A1.Flex** | 4 OCPU / 24 GB | ✅ Best overall — see [../oracle/README.md](../oracle/README.md) |
| **Oracle E2.1.Micro** | 1 GB | ❌ Cannot run this |

### Cloud Run

```bash
gcloud run deploy cmb-lab \
  --source . --port 7860 \
  --memory 4Gi --cpu 2 \
  --timeout 300 --allow-unauthenticated
```

Set `--min-instances 1` to avoid cold starts, which costs money but makes it usable.

---

## Making the image smaller

| Action | Saves |
| :-- | :-- |
| Ship cleaned `.npz` rather than raw FITS | ~60% of the data |
| Pre-compute a CAMB grid and interpolate | Removes gfortran and the build toolchain |
| Degrade maps to N_side 512 | 4× smaller; fine to ℓ ≈ 1000 |
| Drop `matplotlib`, pre-render the sky maps | ~100 MB and a chunk of per-service RSS |

Removing CAMB is the biggest single win if you only need fixed theory curves.

---

## Environment variables

| Variable | Default | Purpose |
| :-- | :-- | :-- |
| `GATEWAY_PORT` | `7860` | The single exposed port |
| `STATIC_DIR` | `/app/web/dist` | Frontend location. Unset it to run API-only |
| `DATA_DIR` | `/app/data` | Archive and cleaned maps |
| `GEMINI_API_KEY` | — | Optional; enables open-ended assistant answers |
| `OMP_NUM_THREADS` | `1` | One thread per service; the process pools do the real parallelism |
