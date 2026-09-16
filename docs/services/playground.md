# playground

**Path:** `services/playground/` · **Port:** 8010

Turn a knob, watch the spectrum move. This is where the physics stops being a set of
equations and becomes something you have a feel for.

## Responsibility

Expose the analysis choices and the cosmological parameters as interactive controls, and
recompute the spectrum, the theory curve, and χ² fast enough for it to feel live.

## Modules

### `experiments.py`

**Seven spectrum knobs** — the analysis choices:

| Knob | Effect |
| --- | --- |
| Map pair | Which detectors to cross-correlate |
| Mask | KQ75 vs KQ85, or none |
| ℓ range | Where the measurement starts and stops |
| Binning | `linear:N`, `log:N`, or `planck` |
| Beam deconvolution | On/off — off shows the spectrum collapsing at high ℓ |
| Point-source subtraction | On/off — off shows the ℓ²-growing residual |
| Noise in the variance | On/off — off shows χ²/dof exploding to ~198 |

Those last three each reproduce a real bug from this project's own history. Toggling them is
the fastest way to understand why the pipeline is built the way it is.

**Five theory knobs** — H₀, Ω_b h², Ω_c h², n_s, τ. Each carries an `explain` string
describing what should happen.

> **Corrected physics:** raising H₀ *shrinks* D_A, so the fixed-length ruler subtends a
> *larger* angle and the peaks move to **lower** ℓ — from ℓ = 225 at H₀ = 60 to ℓ = 213 at
> H₀ = 80. This is an easy sign to get backwards, and an earlier version of this text had it
> wrong. The degeneracy is also visible: raising H₀ requires lowering Ω_c h² (0.136 → 0.094)
> to keep Ω_m h³ roughly constant.

**Eight guided experiments**, each a named scenario with a question, a suggested knob
setting, and what to look for.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/knobs` | All knobs, ranges, defaults, explanations |
| GET | `/experiments` | Guided experiments |
| GET | `/experiments/{experiment_id}` | One experiment |
| POST | `/experiments/{experiment_id}/run` | Run it |
| POST | `/spectrum` | Recompute with given analysis settings |
| POST | `/theory` | Theory curve for given parameters |
| POST | `/compare/spectra` | Two analysis settings side by side |
| POST | `/compare/theory` | Two parameter sets side by side |

## Performance

Theory curves come from the cosmology service's cached CAMB wrapper (~60 ms), and the
gateway caches responses, so repeated settings are instant. Spectrum recomputation is
heavier — it re-runs the estimator — so the UI debounces slider input.

## Running

```bash
make dev-playground
```
