"""Cosmological inference pipeline and validation gate G5."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from cmblab_core.constants import PLANCK_2018, Measurement
from cmblab_spectrum.pipeline import run_cross_spectrum

from .likelihood import BandpowerData, BandpowerLikelihood, LikelihoodConfig
from .sampler import SamplerResult, run_mcmc
from .theory import PARAM_LABELS

ProgressFn = Callable[[float, str], None]

#: A recovered parameter passes if it sits within this many sigma of the published value,
#: combining both uncertainties. Three sigma is the conventional "consistent" threshold.
G5_TENSION_LIMIT = 3.0


@dataclass(slots=True)
class ParameterComparison:
    name: str
    label: str
    ours: float
    ours_err: float
    published: float
    published_err: float
    tension_sigma: float
    source: str

    @property
    def consistent(self) -> bool:
        return self.tension_sigma < G5_TENSION_LIMIT

    def public(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "ours": self.ours,
            "ours_err": self.ours_err,
            "published": self.published,
            "published_err": self.published_err,
            "tension_sigma": round(self.tension_sigma, 3),
            "consistent": self.consistent,
            "source": self.source,
        }


@dataclass(slots=True)
class InferenceRun:
    result: SamplerResult
    comparisons: dict[str, ParameterComparison] = field(default_factory=dict)
    gate_g5_passed: bool = False
    gate_g5_detail: str = ""
    spectrum_label: str = ""

    def public(self) -> dict[str, Any]:
        r = self.result
        return {
            "spectrum": self.spectrum_label,
            "free_params": r.free_params,
            "n_walkers": r.n_walkers,
            "n_steps": r.n_steps,
            "burn_in": r.burn_in,
            "n_samples": int(r.chain.shape[0]),
            "acceptance_fraction": round(r.acceptance_fraction, 4),
            "autocorr_time": round(r.autocorr_time, 2) if r.autocorr_time else None,
            "best_fit": r.best_fit,
            "best_chi2": round(r.best_chi2, 3),
            "dof": r.dof,
            "chi2_per_dof": round(r.chi2_per_dof, 3),
            "n_data": r.n_data,
            "posterior": {k: v.public() for k, v in r.summaries.items()},
            "derived": {k: v.public() for k, v in r.derived_summaries.items()},
            "gates": {
                "G5": {
                    "name": "Recover published LCDM parameters",
                    "passed": self.gate_g5_passed,
                    "detail": self.gate_g5_detail,
                    "comparisons": {k: v.public() for k, v in self.comparisons.items()},
                }
            },
        }

    def corner_data(self, max_points: int = 4000) -> dict[str, Any]:
        """Thinned chain for a browser-side corner plot."""
        chain = self.result.chain
        step = max(1, chain.shape[0] // max_points)
        thinned = chain[::step]
        return {
            "params": self.result.free_params,
            "labels": [PARAM_LABELS.get(p, p) for p in self.result.free_params],
            "samples": thinned.T.tolist(),
            "n_samples": int(thinned.shape[0]),
        }


def _compare(name: str, ours_mean: float, ours_err: float) -> ParameterComparison | None:
    published: Measurement | None = PLANCK_2018.get(name)
    if published is None:
        return None

    denominator = np.sqrt(ours_err**2 + published.err**2)
    tension = abs(ours_mean - published.value) / denominator if denominator else 0.0

    return ParameterComparison(
        name=name,
        label=PARAM_LABELS.get(name, name),
        ours=ours_mean,
        ours_err=ours_err,
        published=published.value,
        published_err=published.err,
        tension_sigma=float(tension),
        source=published.source,
    )


def run_inference(
    *,
    dataset: str = "wmap9",
    product_a: str = "da-v1",
    product_b: str = "da-v2",
    mask_dataset: str | None = "wmap9",
    mask_product: str | None = "mask-kq75",
    free_params: tuple[str, ...] = ("H0", "ombh2", "omch2"),
    n_walkers: int = 24,
    n_steps: int = 1200,
    lmax: int = 800,
    ell_min: int = 30,
    workers: int | None = None,
    progress: ProgressFn | None = None,
) -> InferenceRun:
    """Estimate the spectrum, fit LCDM to it, and check gate G5."""

    def report(fraction: float, message: str) -> None:
        if progress:
            progress(fraction, message)

    report(0.02, "estimating power spectrum")
    spectrum_run = run_cross_spectrum(
        dataset,
        product_a,
        product_b,
        mask_dataset=mask_dataset,
        mask_product=mask_product,
        lmax=lmax,
    )

    report(0.08, "building likelihood")
    data = BandpowerData.from_bandpowers(spectrum_run.bandpowers, ell_min=ell_min)
    likelihood = BandpowerLikelihood(data, LikelihoodConfig(free_params=list(free_params)))

    def sampler_progress(fraction: float, message: str) -> None:
        report(0.1 + 0.85 * fraction, message)

    result = run_mcmc(
        likelihood,
        n_walkers=n_walkers,
        n_steps=n_steps,
        workers=workers,
        progress=sampler_progress,
    )

    run = InferenceRun(result=result, spectrum_label=spectrum_run.map_label)

    for name, summary in result.summaries.items():
        if comparison := _compare(name, summary.mean, summary.std):
            run.comparisons[name] = comparison
    for name, summary in result.derived_summaries.items():
        if comparison := _compare(name, summary.mean, summary.std):
            run.comparisons[name] = comparison

    checked = list(run.comparisons.values())
    if checked:
        worst = max(checked, key=lambda c: c.tension_sigma)
        run.gate_g5_passed = all(c.consistent for c in checked)
        run.gate_g5_detail = (
            f"{sum(c.consistent for c in checked)}/{len(checked)} parameters within "
            f"{G5_TENSION_LIMIT:.0f}σ of Planck 2018; "
            f"largest tension {worst.label} at {worst.tension_sigma:.2f}σ"
        )
    else:
        run.gate_g5_detail = "no comparable parameters sampled"

    report(1.0, "complete")
    return run


def build_likelihood(
    *,
    dataset: str = "wmap9",
    product_a: str = "da-v1",
    product_b: str = "da-v2",
    mask_dataset: str | None = "wmap9",
    mask_product: str | None = "mask-kq75",
    free_params: tuple[str, ...] = ("H0", "ombh2", "omch2"),
    lmax: int = 800,
    ell_min: int = 30,
) -> tuple[BandpowerLikelihood, str]:
    """Likelihood only, for fast scans and the playground."""
    spectrum_run = run_cross_spectrum(
        dataset,
        product_a,
        product_b,
        mask_dataset=mask_dataset,
        mask_product=mask_product,
        lmax=lmax,
    )
    data = BandpowerData.from_bandpowers(spectrum_run.bandpowers, ell_min=ell_min)
    return (
        BandpowerLikelihood(data, LikelihoodConfig(free_params=list(free_params))),
        spectrum_run.map_label,
    )
