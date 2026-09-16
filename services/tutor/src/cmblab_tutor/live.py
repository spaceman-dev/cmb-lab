"""Live values: splice real pipeline results into the lesson text.

A lesson that says "the first peak sits at ℓ ≈ 220" is fine. A lesson that says "the first
peak sits at ℓ = 220, and here is the number *your* pipeline just measured from NASA data"
is a different experience entirely. Every ``live`` key a section declares is resolved here.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from cmblab_core.constants import H0_MEASUREMENTS, PLANCK_2018


@lru_cache(maxsize=1)
def _spectrum_run():
    from cmblab_spectrum.pipeline import run_cross_spectrum

    return run_cross_spectrum(
        "wmap9",
        "da-v1",
        "da-v2",
        mask_dataset="wmap9",
        mask_product="mask-kq75",
        lmax=800,
    )


def _fmt(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}"


RESOLVERS: dict[str, Any] = {}


def resolver(key: str):
    def decorate(fn):
        RESOLVERS[key] = fn
        return fn

    return decorate


@resolver("first_peak_ell")
def _first_peak_ell() -> dict[str, Any]:
    run = _spectrum_run()
    return {
        "label": "First acoustic peak (measured here)",
        "value": run.peak1_ell,
        "display": f"ℓ = {run.peak1_ell}",
        "context": "Published value: ℓ ≈ 220",
        "source": "your pipeline, WMAP V1 × V2",
    }


@resolver("first_peak_dl")
def _first_peak_dl() -> dict[str, Any]:
    run = _spectrum_run()
    return {
        "label": "Peak amplitude (measured here)",
        "value": round(run.peak1_dl, 1),
        "display": f"𝒟ℓ = {_fmt(run.peak1_dl, 0)} µK²",
        "context": "Published value: ≈ 5,750 µK²",
        "source": "your pipeline, WMAP V1 × V2",
    }


@resolver("theory_peak_ell")
def _theory_peak_ell() -> dict[str, Any]:
    from cmblab_cosmology.theory import theory_spectrum

    theory = theory_spectrum({}, lmax=1000)
    ell, dl = theory.first_peak()
    return {
        "label": "CAMB prediction for Planck 2018 parameters",
        "value": ell,
        "display": f"ℓ = {ell}, 𝒟ℓ = {_fmt(dl, 0)} µK²",
        "context": "Solved from the Boltzmann equations, not fitted to our data",
        "source": "CAMB",
    }


@resolver("f_sky")
def _f_sky() -> dict[str, Any]:
    run = _spectrum_run()
    return {
        "label": "Sky fraction after masking",
        "value": round(run.spectrum.f_sky, 4),
        "display": f"f_sky = {run.spectrum.f_sky:.3f}",
        "context": "WMAP KQ75 temperature analysis mask",
        "source": "your pipeline",
    }


@resolver("n_bandpowers")
def _n_bandpowers() -> dict[str, Any]:
    run = _spectrum_run()
    return {
        "label": "Bandpowers measured",
        "value": len(run.bandpowers),
        "display": f"{len(run.bandpowers)} bandpowers, ℓ = 2–{run.spectrum.usable_lmax}",
        "context": "Cut where signal-to-noise collapses",
        "source": "your pipeline",
    }


@resolver("chi2_per_dof")
def _chi2() -> dict[str, Any]:
    run = _spectrum_run()
    comparison = run.comparisons.get("wmap9-TT-binned")
    if not comparison:
        return {"label": "χ²/dof", "value": None, "display": "not available"}
    return {
        "label": "Agreement with WMAP's published spectrum",
        "value": round(comparison.chi2_per_dof, 3),
        "display": f"χ²/dof = {comparison.chi2_per_dof:.2f}",
        "context": f"{comparison.n_compared} bandpowers compared; 1.0 is perfect",
        "source": "your pipeline vs NASA published TT",
    }


@resolver("beam_labels")
def _beams() -> dict[str, Any]:
    run = _spectrum_run()
    beams = run.spectrum.meta.get("beams", [])
    return {
        "label": "Beam transfer functions used",
        "value": beams,
        "display": ", ".join(beams) if beams else "none",
        "context": "Measured by WMAP from observations of Jupiter",
        "source": "NASA LAMBDA",
    }


@resolver("map_rms")
def _map_rms() -> dict[str, Any]:
    from pathlib import Path

    import numpy as np
    from cmblab_core.config import get_settings
    from cmblab_core.healpix import UNSEEN, load_npz_map

    path = Path(get_settings().data_dir) / "clean" / "wmap9" / "ilc-map.npz"
    if not path.exists():
        return {"label": "Map RMS", "value": None, "display": "map not downloaded"}

    sky, _ = load_npz_map(path)
    valid = sky[(sky != UNSEEN) & np.isfinite(sky)]
    rms = float(valid.std())
    return {
        "label": "Temperature fluctuation amplitude",
        "value": round(rms, 2),
        "display": f"{rms:.1f} µK RMS",
        "context": f"Against a 2.7255 K background — that is 1 part in {2.7255e6 / rms:,.0f}",
        "source": "WMAP 9-year ILC map",
    }


@resolver("map_nside")
def _map_nside() -> dict[str, Any]:
    import healpy as hp

    return {
        "label": "Map resolution",
        "value": 512,
        "display": f"N_side = 512 → {hp.nside2npix(512):,} pixels",
        "context": f"Each pixel is about {hp.nside2resol(512, arcmin=True):.1f} arcmin across",
        "source": "HEALPix pixelisation",
    }


@resolver("posterior_H0")
def _posterior_h0() -> dict[str, Any]:
    published = PLANCK_2018["H0"]
    return {
        "label": "H₀ from the CMB",
        "value": published.value,
        "display": f"H₀ = {published.value} ± {published.err} km/s/Mpc",
        "context": "Run an MCMC fit in the Inference tab to measure this yourself",
        "source": published.source,
    }


@resolver("posterior_ombh2")
def _posterior_ombh2() -> dict[str, Any]:
    published = PLANCK_2018["ombh2"]
    return {
        "label": "Baryon density",
        "value": published.value,
        "display": f"Ω_b h² = {published.value} ± {published.err}",
        "context": "Independently confirmed by Big Bang nucleosynthesis",
        "source": published.source,
    }


@resolver("tension_H0")
def _tension_h0() -> dict[str, Any]:
    cmb = H0_MEASUREMENTS["planck2018_cmb"]
    local = H0_MEASUREMENTS["sh0es_cepheid"]
    return {
        "label": "The Hubble tension",
        "value": round(local.tension_sigma(cmb), 2),
        "display": (
            f"CMB: {cmb.value} ± {cmb.err}   vs   Cepheids: {local.value} ± {local.err}   "
            f"→ {local.tension_sigma(cmb):.1f}σ"
        ),
        "context": "The biggest unresolved discrepancy in cosmology",
        "source": "Planck 2018 vs SH0ES 2022",
    }


@resolver("alignment_angle")
def _alignment_angle() -> dict[str, Any]:
    return {
        "label": "Quadrupole–octupole angle",
        "value": None,
        "display": "run the anomaly analysis to measure it",
        "context": "Isotropy predicts a typical angle of 60°; published analyses find ~10°",
        "source": "Anomaly tab",
    }


@resolver("alignment_p")
def _alignment_p() -> dict[str, Any]:
    return {
        "label": "Alignment p-value",
        "value": None,
        "display": "run the Monte Carlo to measure it",
        "context": "Remember to read the look-elsewhere corrected value",
        "source": "Anomaly tab",
    }


@resolver("anomaly_summary")
def _anomaly_summary() -> dict[str, Any]:
    return {
        "label": "Anomaly statistics tested",
        "value": 4,
        "display": "4 statistics → Šidák correction with n = 4",
        "context": "Alignment, hemispherical asymmetry, Cold Spot, low quadrupole",
        "source": "Anomaly tab",
    }


def resolve(keys: list[str]) -> dict[str, Any]:
    """Resolve live values, degrading gracefully when data is missing."""
    out: dict[str, Any] = {}
    for key in keys:
        resolver_fn = RESOLVERS.get(key)
        if resolver_fn is None:
            continue
        try:
            out[key] = resolver_fn()
        except Exception as exc:  # noqa: BLE001 - a lesson must render without data
            out[key] = {
                "label": key,
                "value": None,
                "display": "unavailable",
                "context": f"{type(exc).__name__}: {exc}",
                "source": "",
            }
    return out
