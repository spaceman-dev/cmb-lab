# spectrum

**Path:** `services/spectrum/` · **Port:** 8003

Turns cleaned sky maps into an angular power spectrum, and compares it to published
results. This is the heart of the project, and it owns gates **G3** and **G4**.

## Result

| Gate | Assertion | Measured |
| --- | --- | --- |
| G3 | First acoustic peak at ℓ = 220 ± 8 | **ℓ = 220**, 𝒟ℓ = 5949 µK² |
| G4 | χ²/dof against published spectra ≈ 1 | **0.57** (WMAP), **0.87** (Planck) |

Cross-checks: V1×V2 → ℓ = 220 (χ²/dof 0.57); W1×W2 → ℓ = 218 (χ²/dof 0.76).

## The central design decision

**Auto-spectra do not work.** Squaring one map squares its noise along with the signal, and
deconvolving the beam then amplifies that noise exponentially. Our first attempt on the ILC
map put the peak at ℓ = 343 with χ²/dof = 1669 — a wall of noise, no peaks.

Cross-correlating two detectors that observed the same sky with independent noise makes the
noise term vanish in expectation:

$$\langle a^A_{\ell m} a^{B*}_{\ell m}\rangle = C_\ell B^A_\ell B^B_\ell + \underbrace{\langle n^A n^{B*}\rangle}_{=\,0}$$

No noise model, no instrument simulation. Full reasoning in
[why-cross-spectra](../why-cross-spectra.md).

## Modules

### `estimator.py`

- `estimate_cross_spectrum` — the default path. Two maps, two beams, one mask.
- `estimate_spectrum` — auto-spectrum, kept for demonstrating the failure mode.
- `PowerSpectrum.variance()` — Knox formula **including** the noise term.
- `snr_lmax(threshold=0.1)`, `usable_lmax` — where the measurement stops being meaningful.
- `TRANSFER_FLOOR = 0.02` — refuse to divide by a beam below 2%, which is where
  deconvolution becomes numerically meaningless.

> **Hard-won detail:** omitting the noise term from the variance made our error bars far too
> small and produced χ²/dof = 198 from a perfectly good spectrum. Noise is measured
> empirically as auto minus cross, not modelled.

### `beams.py`

`load_beam`, `BeamTransfer.at(lmax)`, `effective_fwhm_arcmin()`. Uses WMAP's tabulated
beam transfer functions measured from observations of Jupiter, not a Gaussian
approximation — real beams have sidelobes a Gaussian misses.

### `binning.py`

`make_edges` supports `linear:N`, `log:N`, and `planck` (matching the published Planck bin
edges). `bin_spectrum` weights by 2ℓ+1, which is the number of modes per multipole.

### `pointsources.py`

Unresolved radio sources add a flat-in-C_ℓ component that grows as ℓ² in 𝒟ℓ. Left in, it
produced a rising residual and χ²/dof ≈ 5.

- `fit_against_theory` — default. Fits the amplitude against a ΛCDM theory curve. This is
  mildly circular, and the API says so.
- `fit_from_frequency_pair` — non-circular alternative using the frequency dependence. Not
  the default because it needs two frequency bands.

### `compare.py`

`compare_to_reference` computes χ²/dof against WMAP or Planck binned spectra. Gate G4
requires `0.3 ≤ χ²/dof ≤ 3.0` — bounded on both sides, because a suspiciously low χ² means
overestimated errors, which is just as wrong as a high one.

### `references.py`

Parses the published files. Column layouts differ: WMAP binned has 7 columns (mean ℓ, ℓmin,
ℓmax, 𝒟ℓ, total error, measurement error, cosmic variance); Planck binned has 5 (ℓ, 𝒟ℓ,
−dD, +dD, best fit).

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/spectra/cross` | Cross-spectrum from two detector maps. The main entry point |
| POST | `/spectra/auto` | Auto-spectrum, for demonstrating why it fails |
| GET | `/spectra/{spectrum_id}` | Retrieve a computed spectrum |
| GET | `/references` | Available published spectra |
| GET | `/references/{slug}` | One published spectrum |
| GET | `/parameters/planck2018` | Planck 2018 parameter table, with sources |
| GET | `/maps` | Maps usable as spectrum inputs |

## Running

```bash
make spectrum          # full pipeline from the CLI
make dev-spectrum      # service with autoreload
.venv/bin/python -m pytest services/spectrum/tests -q
```
