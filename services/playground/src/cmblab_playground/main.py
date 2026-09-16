"""HTTP API for the playground: run controlled comparisons and see what changes."""

from __future__ import annotations

from typing import Any

import numpy as np
from cmblab_core.service import create_app
from cmblab_cosmology.theory import theory_spectrum
from cmblab_spectrum.pipeline import run_cross_spectrum
from pydantic import BaseModel, Field

from .experiments import (
    EXPERIMENTS,
    SPECTRUM_KNOBS,
    THEORY_KNOBS,
    get_experiment,
)

app = create_app(
    service_name="playground",
    description="Interactive experimentation with the CMB analysis pipeline.",
)

_CACHE: dict[str, dict[str, Any]] = {}


class SpectrumConfig(BaseModel):
    product_a: str = "da-v1"
    product_b: str = "da-v2"
    mask_product: str | None = "mask-kq75"
    lmax: int = Field(default=800, ge=100, le=1500)
    binning: str = "linear:30"
    subtract_point_sources: bool = True
    apply_pixwin: bool = True


class TheoryConfig(BaseModel):
    H0: float = Field(default=67.36, ge=55, le=85)
    ombh2: float = Field(default=0.02237, ge=0.017, le=0.027)
    omch2: float = Field(default=0.1200, ge=0.09, le=0.15)
    ns: float = Field(default=0.9649, ge=0.88, le=1.05)
    tau: float = Field(default=0.0544, ge=0.01, le=0.15)
    lmax: int = Field(default=1200, ge=200, le=2500)


class CompareSpectraRequest(BaseModel):
    baseline: SpectrumConfig = Field(default_factory=SpectrumConfig)
    variant: SpectrumConfig
    label_baseline: str = "baseline"
    label_variant: str = "variant"


class CompareTheoryRequest(BaseModel):
    baseline: TheoryConfig = Field(default_factory=TheoryConfig)
    variant: TheoryConfig
    label_baseline: str = "baseline"
    label_variant: str = "variant"


def _run_spectrum(config: SpectrumConfig) -> dict[str, Any]:
    key = config.model_dump_json()
    if key in _CACHE:
        return {**_CACHE[key], "cached": True}

    mask = config.mask_product if config.mask_product not in (None, "none", "") else None

    run = run_cross_spectrum(
        "wmap9",
        config.product_a,
        config.product_b,
        mask_dataset="wmap9" if mask else None,
        mask_product=mask,
        lmax=config.lmax,
        binning=config.binning,
        subtract_point_sources=config.subtract_point_sources,
        apply_pixwin=config.apply_pixwin,
    )

    comparison = run.comparisons.get("wmap9-TT-binned")
    payload = {
        "label": f"{config.product_a} × {config.product_b}",
        "is_auto_spectrum": config.product_a == config.product_b,
        "config": config.model_dump(),
        "f_sky": round(run.spectrum.f_sky, 4),
        "usable_lmax": run.spectrum.usable_lmax,
        "peak1_ell": run.peak1_ell,
        "peak1_dl": round(run.peak1_dl, 1),
        "gate_g3_passed": run.gate_g3_passed,
        "chi2_per_dof": round(comparison.chi2_per_dof, 3) if comparison else None,
        "gate_g4_passed": comparison.passes_gate_g4 if comparison else None,
        "point_source_amplitude": (
            run.point_source_fit.amplitude if run.point_source_fit else None
        ),
        "bandpowers": [
            {
                "ell": round(b.ell_eff, 2),
                "dl": round(b.dl_uk2, 2),
                "err": round(b.dl_err_uk2, 2) if b.dl_err_uk2 else None,
            }
            for b in run.bandpowers
        ],
        "cached": False,
    }
    _CACHE[key] = payload
    return payload


def _run_theory(config: TheoryConfig) -> dict[str, Any]:
    values = config.model_dump()
    lmax = values.pop("lmax")
    theory = theory_spectrum(values, lmax=lmax)
    peak_ell, peak_dl = theory.first_peak()

    keep = theory.ell >= 2
    # Thin for transport: a curve sampled every 2 multipoles is visually identical.
    step = 2 if lmax > 800 else 1

    return {
        "config": config.model_dump(),
        "peak1_ell": peak_ell,
        "peak1_dl": round(peak_dl, 1),
        "ell": theory.ell[keep][::step].tolist(),
        "dl_tt": np.round(theory.dl_tt[keep][::step], 2).tolist(),
        "derived": {
            k: (None if not np.isfinite(v) else round(v, 5)) for k, v in theory.derived.items()
        },
    }


@app.get("/knobs", tags=["meta"])
async def knobs() -> dict[str, Any]:
    """Everything that can be changed, with the physics behind each control."""
    return {
        "spectrum": [k.public() for k in SPECTRUM_KNOBS],
        "theory": [k.public() for k in THEORY_KNOBS],
    }


@app.get("/experiments", tags=["experiments"])
async def experiments() -> dict[str, Any]:
    """Curated before/after experiments, each with a prediction to check."""
    return {
        "experiments": [
            {
                "id": e["id"],
                "title": e["title"],
                "question": e["question"],
                "difficulty": e["difficulty"],
                "kind": e.get("kind", "spectrum"),
                "lesson": e.get("lesson"),
            }
            for e in EXPERIMENTS
        ]
    }


@app.get("/experiments/{experiment_id}", tags=["experiments"])
async def experiment(experiment_id: str) -> dict[str, Any]:
    return get_experiment(experiment_id)


@app.post("/experiments/{experiment_id}/run", tags=["experiments"])
async def run_experiment(experiment_id: str) -> dict[str, Any]:
    """Execute both arms of a curated experiment and return them side by side."""
    config = get_experiment(experiment_id)
    is_theory = config.get("kind") == "theory"

    if is_theory:
        baseline = _run_theory(TheoryConfig(**config["baseline"]))
        variant = _run_theory(TheoryConfig(**{**config["baseline"], **config["variant"]}))
        delta = {
            "peak1_ell": variant["peak1_ell"] - baseline["peak1_ell"],
            "peak1_dl": round(variant["peak1_dl"] - baseline["peak1_dl"], 1),
        }
    else:
        base_config = SpectrumConfig(**config["baseline"])
        baseline = _run_spectrum(base_config)
        variant = _run_spectrum(SpectrumConfig(**{**base_config.model_dump(), **config["variant"]}))
        delta = {
            "peak1_ell": variant["peak1_ell"] - baseline["peak1_ell"],
            "chi2_per_dof": (
                round(variant["chi2_per_dof"] - baseline["chi2_per_dof"], 3)
                if variant["chi2_per_dof"] and baseline["chi2_per_dof"]
                else None
            ),
        }

    return {
        "experiment": config,
        "kind": "theory" if is_theory else "spectrum",
        "baseline": baseline,
        "variant": variant,
        "delta": delta,
    }


@app.post("/spectrum", tags=["sandbox"])
async def sandbox_spectrum(config: SpectrumConfig) -> dict[str, Any]:
    """Run the pipeline with any configuration you like."""
    return _run_spectrum(config)


@app.post("/theory", tags=["sandbox"])
async def sandbox_theory(config: TheoryConfig) -> dict[str, Any]:
    """A ΛCDM theory curve for any parameters. Fast enough to drive sliders."""
    return _run_theory(config)


@app.post("/compare/spectra", tags=["compare"])
async def compare_spectra(request: CompareSpectraRequest) -> dict[str, Any]:
    baseline = _run_spectrum(request.baseline)
    variant = _run_spectrum(request.variant)

    changed = {
        key: {"from": value, "to": getattr(request.variant, key)}
        for key, value in request.baseline.model_dump().items()
        if getattr(request.variant, key) != value
    }

    return {
        "baseline": {**baseline, "label": request.label_baseline},
        "variant": {**variant, "label": request.label_variant},
        "changed": changed,
        "delta": {
            "peak1_ell": variant["peak1_ell"] - baseline["peak1_ell"],
            "chi2_per_dof": (
                round(variant["chi2_per_dof"] - baseline["chi2_per_dof"], 3)
                if variant["chi2_per_dof"] and baseline["chi2_per_dof"]
                else None
            ),
        },
    }


@app.post("/compare/theory", tags=["compare"])
async def compare_theory(request: CompareTheoryRequest) -> dict[str, Any]:
    baseline = _run_theory(request.baseline)
    variant = _run_theory(request.variant)

    changed = {
        key: {"from": value, "to": getattr(request.variant, key)}
        for key, value in request.baseline.model_dump().items()
        if getattr(request.variant, key) != value
    }

    return {
        "baseline": {**baseline, "label": request.label_baseline},
        "variant": {**variant, "label": request.label_variant},
        "changed": changed,
        "delta": {
            "peak1_ell": variant["peak1_ell"] - baseline["peak1_ell"],
            "peak1_dl": round(variant["peak1_dl"] - baseline["peak1_dl"], 1),
        },
    }
