---
title: cmb-lab
emoji: 🌌
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Measure the cosmic microwave background from raw NASA data
---

# cmb-lab

An independent reproduction of the cosmic microwave background power spectrum, measured
from raw NASA WMAP and ESA Planck archive data — not copied from published tables.

**Source:** https://github.com/spaceman-dev/cmb-lab

## What it measured

| Result | Value | Published |
| :-- | :-- | :-- |
| First acoustic peak | **ℓ = 220** | ℓ = 220 ± 8 |
| Agreement with WMAP | **χ²/dof = 0.57** | — |
| H₀ | 66.38 ± 1.07 | 67.36 ± 0.54 (0.81σ) |
| Age of the universe | 14.006 ± 0.093 Gyr | 13.797 ± 0.023 |

All four classic large-angle anomalies are calibrated against 500 simulated isotropic
universes. After correcting for the look-elsewhere effect, none exceeds 2.1σ.

## Using it

- **Spectrum** — cross-correlate two WMAP detectors and watch ℓ = 220 emerge
- **Sky Map** — the real microwave sky in four projections, filterable by angular scale
- **Inference** — run MCMC against CAMB and compare to Planck 2018
- **Anomalies** — measure them, then calibrate the significance honestly
- **Playground** — break the pipeline deliberately to see why each step matters
- **Learn** — six lessons at three reading depths, from plain English to full derivations

## Notes on this hosted copy

Runs on 2 vCPU. MCMC and the Monte Carlo anomaly calibration are CPU-bound and will be
noticeably slower than on a workstation — reduce the walker and step counts if a run is
taking too long.

The physics assistant answers from a curated knowledge base of 29 questions plus live
pipeline values. Open-ended questions need a `GEMINI_API_KEY` secret, which this Space may
not have set; without it the assistant still works, it just cannot improvise.
