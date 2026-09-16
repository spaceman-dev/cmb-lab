# anomaly

**Path:** `services/anomaly/` · **Port:** 8005

Measures the four classic large-angle CMB anomalies and — the part that actually matters —
calibrates their significance against simulated isotropic skies. This is gate **G6**.

## Result

500 isotropic ΛCDM simulations at N_side = 64:

| Statistic | Observed | Isotropic null | p (raw) | p (corrected) | σ |
| --- | --- | --- | --- | --- | --- |
| Quadrupole–octupole alignment | 23.56° | 55.52 ± 22.75° | 0.1078 | 0.3663 | 0.90 |
| Hemispherical asymmetry | 0.1774 | 0.1595 ± 0.0477 | 0.3393 | 0.8095 | 0.24 |
| Cold Spot | −4.4155σ | −3.4590 ± 0.3417 | 0.0100 | 0.0393 | 2.06 |
| Low quadrupole | 65.88 µK² | 684.86 ± 445.17 | 0.0120 | 0.0471 | 1.99 |

**Nothing exceeds 2.1σ after correction.** The Cold Spot's raw p = 0.010 looks interesting;
after accounting for having tested four statistics it becomes 0.039, which is not.

This is the honest answer, and reporting it is the point of the service.

## Why calibration is the hard part

Anyone can compute an alignment angle. The difficulty is knowing whether 23.6° is
surprising. Two traps:

1. **The look-elsewhere effect.** Test four statistics and something will look odd by luck.
   Corrected with Šidák: `p_corrected = 1 − (1−p)^n`.
2. **Angles on a sphere.** Two random directions are uniform in cos γ, not in γ, so the
   typical separation is 60°, not 45°. Getting this backwards makes small angles look far
   rarer than they are.

We avoid analytic arguments entirely: generate 500 isotropic skies, measure each one exactly
as we measured the real one, and count.

## Modules

### `statistics.py`

| Statistic | Implementation |
| --- | --- |
| `quadrupole_octupole_alignment` | `preferred_axis` for ℓ=2 and ℓ=3, then the angle between them |
| `hemispherical_asymmetry` | Power ratio between opposing hemispheres, searched over the full sphere |
| `cold_spot` | SMHW (Mexican hat wavelet) at ~5°, with a \|b\| > 15° Galactic cut |
| `low_quadrupole` | C₂ against the ΛCDM expectation |

`preferred_axis(refine=True)` maximises Σ m²|a_ℓm(n̂)|² over directions. Two optimisations
took this from 11.2 s to 1.6 s per sky:

- **Headless axes.** An axis and its antipode are the same axis, so only the northern
  hemisphere of `AXIS_GRID_NSIDE = 8` is searched.
- **Coarse then refine.** A coarse grid, then `REFINE_STEPS = 7` within
  `REFINE_RADIUS_DEG = 12` of the winner.

> The hemispherical asymmetry search uses the **full** sphere, not half — its statistic
> changes sign under reflection, so the symmetry argument does not apply there.

### `simulations.py`

`lcdm_cl(lmax)` requests `lmax + 400` from CAMB to work around lensed-spectrum truncation.

`build_null_distribution` runs simulations in a process pool. `_init_worker` sets five
thread-count environment variables to `"1"`; without it, OpenMP oversubscription across 12
workers slows the run by roughly 20×.

`significance()` applies add-one smoothing:

$$\hat{p} = \frac{N_{\text{more extreme}} + 1}{N_{\text{sims}} + 1}$$

The +1 prevents reporting p = 0, which would claim infinite significance from 500 runs.

### `pipeline.py`

`analyse_statistic`, `calibrate` (gate G6), `run_full_analysis`. G6 passes when p-values on
simulated data are uniform — that is, when the machinery does not manufacture significance.
Measured mean p = 0.462.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/statistics` | Available statistics and descriptions |
| POST | `/measure` | Measure one statistic on a map |
| POST | `/jobs` | Start a full analysis with simulations |
| GET | `/jobs/{job_id}` | Job status and results |
| GET | `/jobs` | All jobs |
| POST | `/calibrate` | Run gate G6 |

## Running

```bash
make dev-anomaly
.venv/bin/python -m pytest services/anomaly/tests -q
```

Simulation runs take minutes and go through `JobManager`.
