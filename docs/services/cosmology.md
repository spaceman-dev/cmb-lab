# cosmology

**Path:** `services/cosmology/` · **Port:** 8004

Fits the ΛCDM model to our measured bandpowers using CAMB and MCMC. This is gate **G5**.

## Result

Six parameters, all within 3σ of Planck 2018:

| Parameter | Ours | Planck 2018 | Tension |
| --- | --- | --- | --- |
| H₀ | 66.38 ± 1.07 | 67.36 ± 0.54 | 0.81σ |
| Ω_b h² | 0.02170 ± 0.00035 | 0.02237 ± 0.00015 | 1.76σ |
| Ω_c h² | 0.11634 ± 0.00116 | 0.1200 ± 0.0012 | 2.19σ |
| Ω_m | 0.3136 ± 0.0116 | 0.3153 ± 0.0073 | 0.13σ |
| σ₈ | 0.7966 ± 0.0035 | 0.8111 ± 0.0060 | 2.09σ |
| Age | 14.006 ± 0.093 Gyr | 13.797 ± 0.023 | 2.19σ |

χ²/dof = 1.067 · acceptance 0.649 · autocorrelation τ = 22.9

## Modules

### `theory.py`

`theory_spectrum()` calls CAMB and is `lru_cache`d with 4096 entries, because MCMC revisits
nearby parameter values constantly. One evaluation costs about 60 ms at ℓmax = 700.

`PARAM_BOUNDS` and `PARAM_LABELS` define the sampled space. `bin_theory` applies the *same*
binning as the data — comparing a bin-averaged measurement to a theory curve evaluated at
the bin centre is a real bias, small but exactly the kind that shifts a parameter by a
fraction of a sigma.

> **Gotcha:** CAMB truncates lensed spectra below the requested ℓmax. We request
> `lmax + 400` and slice back, otherwise the array is short and broadcasting fails.

### `likelihood.py`

`BandpowerData.from_bandpowers(ell_min=30)` — the low-ℓ bandpowers are dropped because the
f_sky approximation is least reliable there.

`BandpowerLikelihood` is a Gaussian likelihood with a **diagonal** covariance. Masking
couples neighbouring bandpowers, so the true covariance has off-diagonal terms we ignore;
this makes our error bars slightly optimistic, and the docs say so rather than hiding it.

A Gaussian prior on τ comes from the published measurement, because temperature data alone
cannot break the τ–A_s degeneracy. That is stated explicitly in the output.

### `sampler.py`

`run_mcmc` uses `emcee` with a `ProcessPoolExecutor`. An ensemble sampler suits this problem
because the posterior has a long, narrow, tilted valley (the geometric degeneracy) that
walkers learn the shape of automatically — a grid scan would waste nearly every point.

`scan_parameter` varies one parameter with the rest fixed, for the teaching views.
`model_curve` returns the best-fit spectrum for plotting.

### `pipeline.py`

`run_inference` orchestrates a full fit. `G5_TENSION_LIMIT = 3.0` — every parameter must
agree with Planck within 3σ or the gate fails.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/parameters` | Sampled parameters, bounds, labels |
| POST | `/theory` | Theory spectrum for given parameters |
| POST | `/inference/jobs` | Start an MCMC run, returns a job id |
| GET | `/inference/jobs/{job_id}` | Job status, progress, results |
| GET | `/inference/jobs/{job_id}/corner` | Corner plot |
| GET | `/inference/jobs` | All jobs |
| POST | `/scan` | Vary one parameter, hold the rest |
| POST | `/model` | Best-fit curve |
| GET | `/tension/H0` | CMB vs distance-ladder H₀ comparison |

MCMC takes minutes, so it runs through `JobManager` and returns immediately.

## Running

```bash
make fit
cmblab-cosmology fit
.venv/bin/python -m pytest services/cosmology/tests -q
```

## Performance note

The process pool sets `OMP_NUM_THREADS` and four other thread-count variables to `1` in its
initialiser. Without this, each of 12 worker processes spawns its own thread pool on a
14-core machine and oversubscription makes the run roughly 20× slower.
