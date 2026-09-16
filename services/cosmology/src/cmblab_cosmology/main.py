"""HTTP API for the cosmology service."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import numpy as np
from cmblab_core.constants import H0_MEASUREMENTS, PLANCK_2018
from cmblab_core.jobs import JobManager
from cmblab_core.service import create_app
from pydantic import BaseModel, Field

from .pipeline import build_likelihood, run_inference
from .sampler import model_curve, scan_parameter
from .theory import PARAM_BOUNDS, PARAM_LABELS, cache_info, theory_spectrum

app = create_app(
    service_name="cosmology",
    description="CAMB theory spectra, LCDM likelihood, and MCMC parameter inference.",
)

jobs = JobManager(max_workers=2)
_runs: dict[str, Any] = {}


@lru_cache(maxsize=8)
def _likelihood(free_params: tuple[str, ...], lmax: int, ell_min: int):
    return build_likelihood(free_params=free_params, lmax=lmax, ell_min=ell_min)


class TheoryRequest(BaseModel):
    H0: float = Field(default=67.36, ge=20, le=120)
    ombh2: float = Field(default=0.02237, ge=0.005, le=0.1)
    omch2: float = Field(default=0.1200, ge=0.01, le=0.99)
    tau: float = Field(default=0.0544, ge=0.01, le=0.4)
    ns: float = Field(default=0.9649, ge=0.8, le=1.2)
    As: float = Field(default=2.1e-9, gt=0)
    lmax: int = Field(default=2500, ge=64, le=3000)
    lensed: bool = True


class InferenceRequest(BaseModel):
    dataset: str = "wmap9"
    product_a: str = "da-v1"
    product_b: str = "da-v2"
    free_params: list[str] = Field(default_factory=lambda: ["H0", "ombh2", "omch2"])
    n_walkers: int = Field(default=24, ge=8, le=128)
    n_steps: int = Field(default=1200, ge=100, le=20000)
    lmax: int = Field(default=800, ge=200, le=2000)
    ell_min: int = Field(default=30, ge=2, le=200)


class ScanRequest(BaseModel):
    parameter: str = "H0"
    n_points: int = Field(default=25, ge=5, le=80)
    span: float = Field(default=1.0, gt=0, le=1.0, description="Fraction of the prior box")
    free_params: list[str] = Field(default_factory=lambda: ["H0", "ombh2", "omch2"])
    lmax: int = 800
    ell_min: int = 30


class ModelRequest(BaseModel):
    values: dict[str, float] = Field(default_factory=dict)
    free_params: list[str] = Field(default_factory=lambda: ["H0", "ombh2", "omch2"])
    lmax: int = 1200
    ell_min: int = 30


@app.get("/parameters", tags=["theory"])
async def parameter_metadata() -> dict[str, Any]:
    """Sampling bounds, labels, and published values — everything a UI needs."""
    return {
        "bounds": {k: {"min": v[0], "max": v[1]} for k, v in PARAM_BOUNDS.items()},
        "labels": PARAM_LABELS,
        "planck2018": {
            name: {"value": m.value, "err": m.err, "source": m.source}
            for name, m in PLANCK_2018.items()
        },
        "h0_measurements": {
            name: {"value": m.value, "err": m.err, "source": m.source}
            for name, m in H0_MEASUREMENTS.items()
        },
        "camb_cache": cache_info(),
    }


@app.post("/theory", tags=["theory"])
async def compute_theory(request: TheoryRequest) -> dict[str, Any]:
    """A LCDM theory spectrum for arbitrary parameters. Fast enough for a slider."""
    payload = request.model_dump()
    lmax = payload.pop("lmax")
    lensed = payload.pop("lensed")

    theory = theory_spectrum(payload, lmax=lmax, lensed=lensed)
    peak_ell, peak_dl = theory.first_peak()

    # Drop the monopole and dipole: they carry no primordial information.
    keep = theory.ell >= 2
    return {
        "params": theory.params,
        "derived": {
            k: (None if not np.isfinite(v) else round(v, 6)) for k, v in theory.derived.items()
        },
        "first_peak": {"ell": peak_ell, "dl_uk2": round(peak_dl, 1)},
        "ell": theory.ell[keep].tolist(),
        "dl_tt": np.round(theory.dl_tt[keep], 4).tolist(),
        "dl_ee": np.round(theory.dl_ee[keep], 6).tolist(),
        "dl_te": np.round(theory.dl_te[keep], 5).tolist(),
    }


@app.post("/inference/jobs", tags=["inference"])
async def start_inference(request: InferenceRequest) -> dict[str, Any]:
    """Launch an MCMC fit. Returns immediately; poll /jobs/{id}."""

    def task(progress):
        run = run_inference(
            dataset=request.dataset,
            product_a=request.product_a,
            product_b=request.product_b,
            free_params=tuple(request.free_params),
            n_walkers=request.n_walkers,
            n_steps=request.n_steps,
            lmax=request.lmax,
            ell_min=request.ell_min,
            progress=progress,
        )
        _runs[job_id] = run
        return run.public()

    job_id = jobs.submit("mcmc", task, params=request.model_dump())
    estimate = request.n_walkers * request.n_steps * 0.06 / 2
    return {
        "job_id": job_id,
        "state": "pending",
        "estimated_seconds": round(estimate),
        "poll": f"/inference/jobs/{job_id}",
    }


@app.get("/inference/jobs/{job_id}", tags=["inference"])
async def inference_status(job_id: str) -> dict[str, Any]:
    record = jobs.get(job_id)
    payload = record.public()
    if record.state == "succeeded":
        payload["result"] = record.result
    return payload


@app.get("/inference/jobs/{job_id}/corner", tags=["inference"])
async def inference_corner(job_id: str) -> dict[str, Any]:
    if job_id not in _runs:
        raise KeyError(f"No completed inference run with id {job_id}")
    return _runs[job_id].corner_data()


@app.get("/inference/jobs", tags=["inference"])
async def list_inference_jobs(limit: int = 20) -> dict[str, Any]:
    return {"jobs": [r.public() for r in jobs.list(limit=limit)]}


@app.post("/scan", tags=["exploration"])
async def scan(request: ScanRequest) -> dict[str, Any]:
    """Profile chi-squared along one parameter. Drives the playground sliders."""
    if request.parameter not in PARAM_BOUNDS:
        raise KeyError(f"Unknown parameter {request.parameter}")

    likelihood, label = _likelihood(tuple(request.free_params), request.lmax, request.ell_min)
    if request.parameter not in likelihood.free_params:
        raise ValueError(
            f"{request.parameter} is not free in this configuration: {likelihood.free_params}"
        )

    lo, hi = PARAM_BOUNDS[request.parameter]
    centre = 0.5 * (lo + hi)
    half = 0.5 * (hi - lo) * request.span
    values = np.linspace(centre - half, centre + half, request.n_points)

    payload = scan_parameter(likelihood, request.parameter, values)
    payload["spectrum"] = label
    return payload


@app.post("/model", tags=["exploration"])
async def model(request: ModelRequest) -> dict[str, Any]:
    """Theory curve plus residuals against our measured bandpowers."""
    likelihood, label = _likelihood(tuple(request.free_params), request.lmax, request.ell_min)
    payload = model_curve(likelihood, request.values, lmax=request.lmax)
    payload["spectrum"] = label
    payload["data"] = {
        "ell": likelihood.data.ell_eff.tolist(),
        "dl": likelihood.data.dl.tolist(),
        "sigma": likelihood.data.sigma.tolist(),
    }
    return payload


@app.get("/tension/H0", tags=["exploration"])
async def hubble_tension() -> dict[str, Any]:
    """The headline disagreement in modern cosmology, as a ready-to-plot table."""
    cmb = H0_MEASUREMENTS["planck2018_cmb"]
    rows = []
    for name, m in H0_MEASUREMENTS.items():
        rows.append(
            {
                "key": name,
                "value": m.value,
                "err": m.err,
                "source": m.source,
                "probe": "early universe" if "cmb" in name or "bao" in name else "late universe",
                "tension_vs_planck_sigma": round(m.tension_sigma(cmb), 2),
            }
        )
    return {"parameter": "H0", "unit": "km/s/Mpc", "measurements": rows}
