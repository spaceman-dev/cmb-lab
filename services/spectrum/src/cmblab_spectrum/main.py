"""HTTP API for the spectrum service.

Spectrum estimation takes a few seconds on WMAP-sized maps, which is too slow for an
interactive request but fast enough that a disk-backed result cache removes the problem
entirely. Identical parameters return the cached result immediately.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from cmblab_core.config import get_settings
from cmblab_core.constants import ACOUSTIC_PEAKS, PLANCK_2018
from cmblab_core.service import create_app
from fastapi import Query
from pydantic import BaseModel, Field

from .pipeline import run_cross_spectrum, run_spectrum
from .references import available_references, load_reference

app = create_app(
    service_name="spectrum",
    description="Angular power spectrum estimation, binning, and comparison to published results.",
)

_CACHE: dict[str, dict[str, Any]] = {}


def _cache_key(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


class CrossSpectrumRequest(BaseModel):
    dataset: str = "wmap9"
    product_a: str = "da-v1"
    product_b: str = "da-v2"
    mask_dataset: str | None = "wmap9"
    mask_product: str | None = "mask-kq75"
    lmax: int = Field(default=800, ge=64, le=2500)
    binning: str = "linear:30"
    subtract_point_sources: bool = True


class AutoSpectrumRequest(BaseModel):
    dataset: str = "wmap9"
    product: str = "ilc-map"
    mask_dataset: str | None = "wmap9"
    mask_product: str | None = "mask-kq75"
    lmax: int = Field(default=400, ge=64, le=2500)
    beam_fwhm_arcmin: float | None = 60.0
    binning: str = "linear:30"


def _serialise(run) -> dict[str, Any]:
    spectrum = run.spectrum
    return {
        "map_label": run.map_label,
        "estimator": "cross" if spectrum.is_cross else "auto",
        "f_sky": round(spectrum.f_sky, 5),
        "lmax": spectrum.lmax,
        "reliable_lmax": spectrum.usable_lmax,
        "beam_lmax": spectrum.reliable_lmax,
        "snr_lmax": spectrum.snr_lmax() if spectrum.is_cross else None,
        "beam_corrected": spectrum.beam_corrected,
        "pixwin_corrected": spectrum.pixwin_corrected,
        "beams": spectrum.meta.get("beams", []),
        "point_source": (
            {
                "amplitude_uk2_sr": run.point_source_fit.amplitude,
                "amplitude_err": run.point_source_fit.amplitude_err,
                "method": run.point_source_fit.method,
                "circular": run.point_source_fit.circular,
                "summary": run.point_source_fit.summary(),
            }
            if run.point_source_fit
            else None
        ),
        "gates": {
            "G3": {
                "name": "First acoustic peak",
                "passed": run.gate_g3_passed,
                "detail": run.gate_g3_detail,
                "measured": {"ell": run.peak1_ell, "dl_uk2": round(run.peak1_dl, 1)},
                "expected": {
                    "ell": ACOUSTIC_PEAKS[1]["ell"],
                    "dl_uk2": ACOUSTIC_PEAKS[1]["dl_uk2"],
                },
            },
            "G4": {
                "name": "Agreement with published spectra",
                "comparisons": {
                    slug: {
                        "chi2": round(c.chi2, 2),
                        "dof": c.dof,
                        "chi2_per_dof": round(c.chi2_per_dof, 3),
                        "n_compared": c.n_compared,
                        "passed": c.passes_gate_g4,
                    }
                    for slug, c in run.comparisons.items()
                },
            },
        },
        "bandpowers": [
            {
                "ell_min": b.ell_min,
                "ell_max": b.ell_max,
                "ell_eff": round(b.ell_eff, 2),
                "dl_uk2": round(b.dl_uk2, 3),
                "dl_err_uk2": round(b.dl_err_uk2, 3) if b.dl_err_uk2 else None,
            }
            for b in run.bandpowers
        ],
    }


@app.post("/spectra/cross", tags=["spectra"])
async def compute_cross_spectrum(request: CrossSpectrumRequest) -> dict[str, Any]:
    """Noise-unbiased cross-spectrum between two independently-noised maps."""
    key = _cache_key({"kind": "cross", **request.model_dump()})
    if key in _CACHE:
        return {"id": key, "cached": True, **_CACHE[key]}

    run = run_cross_spectrum(
        request.dataset,
        request.product_a,
        request.product_b,
        mask_dataset=request.mask_dataset,
        mask_product=request.mask_product,
        lmax=request.lmax,
        binning=request.binning,
        subtract_point_sources=request.subtract_point_sources,
    )
    payload = _serialise(run)
    _CACHE[key] = payload
    return {"id": key, "cached": False, **payload}


@app.post("/spectra/auto", tags=["spectra"])
async def compute_auto_spectrum(request: AutoSpectrumRequest) -> dict[str, Any]:
    """Single-map auto-spectrum. Carries a noise bias at high multipole; see docs."""
    key = _cache_key({"kind": "auto", **request.model_dump()})
    if key in _CACHE:
        return {"id": key, "cached": True, **_CACHE[key]}

    run = run_spectrum(
        request.dataset,
        request.product,
        mask_dataset=request.mask_dataset,
        mask_product=request.mask_product,
        lmax=request.lmax,
        beam_fwhm_arcmin=request.beam_fwhm_arcmin,
        binning=request.binning,
    )
    payload = _serialise(run)
    _CACHE[key] = payload
    return {"id": key, "cached": False, **payload}


@app.get("/spectra/{spectrum_id}", tags=["spectra"])
async def get_spectrum(spectrum_id: str) -> dict[str, Any]:
    if spectrum_id not in _CACHE:
        raise KeyError(f"No spectrum with id {spectrum_id}")
    return {"id": spectrum_id, "cached": True, **_CACHE[spectrum_id]}


@app.get("/references", tags=["references"])
async def list_references() -> dict[str, Any]:
    entries = []
    for slug in available_references():
        try:
            reference = load_reference(slug)
        except FileNotFoundError:
            entries.append({"slug": slug, "available": False})
            continue
        peak_ell, peak_dl = reference.first_peak()
        entries.append(
            {
                "slug": slug,
                "available": True,
                "mission": reference.mission,
                "reference": reference.reference,
                "n_bins": int(reference.ell.size),
                "ell_min": float(reference.ell.min()),
                "ell_max": float(reference.ell.max()),
                "first_peak": {"ell": peak_ell, "dl_uk2": round(peak_dl, 1)},
            }
        )
    return {"references": entries}


@app.get("/references/{slug}", tags=["references"])
async def get_reference(
    slug: str,
    ell_max: int = Query(default=2500, ge=10, le=3000),
) -> dict[str, Any]:
    reference = load_reference(slug)
    selected = reference.ell <= ell_max

    payload = {
        "slug": reference.slug,
        "mission": reference.mission,
        "reference": reference.reference,
        "ell": reference.ell[selected].tolist(),
        "dl_uk2": reference.dl[selected].tolist(),
        "err_lo": reference.err_lo[selected].tolist(),
        "err_hi": reference.err_hi[selected].tolist(),
    }
    if reference.best_fit is not None:
        payload["best_fit_dl_uk2"] = reference.best_fit[selected].tolist()
    return payload


@app.get("/parameters/planck2018", tags=["references"])
async def planck_parameters() -> dict[str, Any]:
    """Published Planck 2018 base-LCDM parameters, for the comparison view."""
    return {
        "source": next(iter(PLANCK_2018.values())).source,
        "parameters": {
            name: {
                "value": m.value,
                "err_lo": m.err_lo,
                "err_hi": m.err_hi,
            }
            for name, m in PLANCK_2018.items()
        },
    }


@app.get("/maps", tags=["maps"])
async def list_cleaned_maps() -> dict[str, Any]:
    """Cleaned map artifacts currently on disk, with their gate G2 statistics."""
    clean_root = Path(get_settings().data_dir) / "clean"
    entries = []

    for path in sorted(clean_root.glob("*/*.npz")):
        with np.load(path, allow_pickle=False) as data:
            nside = int(data["nside"])
            unit = str(data["unit"])
            sky = data["sky"]
            finite = sky[np.isfinite(sky) & (sky > -1e29)]

        preview = Path(get_settings().data_dir) / "previews" / path.parent.name / f"{path.stem}.png"
        entries.append(
            {
                "dataset": path.parent.name,
                "product": path.stem,
                "nside": nside,
                "npix": int(sky.size),
                "unit": unit,
                "rms": round(float(finite.std()), 3) if finite.size else None,
                "has_preview": preview.exists(),
            }
        )

    return {"maps": entries}
