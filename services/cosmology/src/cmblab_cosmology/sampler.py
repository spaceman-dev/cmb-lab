"""MCMC sampling with emcee, plus fast deterministic parameter scans.

The sampler is an affine-invariant ensemble (Goodman & Weare): an ensemble of walkers
proposes moves using the positions of the other walkers, which handles the strong parameter
degeneracies of CMB fits without any hand-tuned proposal matrix. That matters here because
H0, omega_b and omega_c are correlated through the acoustic scale.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field

import emcee
import numpy as np

from .likelihood import BandpowerLikelihood
from .theory import PARAM_LABELS, bin_theory, theory_spectrum

ProgressFn = Callable[[float, str], None]


@dataclass(slots=True)
class ParameterSummary:
    name: str
    label: str
    mean: float
    std: float
    median: float
    q16: float
    q84: float

    def public(self) -> dict[str, float | str]:
        return {
            "name": self.name,
            "label": self.label,
            "mean": self.mean,
            "std": self.std,
            "median": self.median,
            "q16": self.q16,
            "q84": self.q84,
        }


@dataclass(slots=True)
class SamplerResult:
    free_params: list[str]
    chain: np.ndarray  # (nsamples, ndim) post burn-in, flattened
    log_prob: np.ndarray
    summaries: dict[str, ParameterSummary]
    derived_summaries: dict[str, ParameterSummary] = field(default_factory=dict)
    acceptance_fraction: float = 0.0
    autocorr_time: float | None = None
    best_fit: dict[str, float] = field(default_factory=dict)
    best_chi2: float = np.nan
    n_data: int = 0
    n_walkers: int = 0
    n_steps: int = 0
    burn_in: int = 0

    @property
    def dof(self) -> int:
        return max(self.n_data - len(self.free_params), 1)

    @property
    def chi2_per_dof(self) -> float:
        return self.best_chi2 / self.dof


def _summarise(name: str, samples: np.ndarray) -> ParameterSummary:
    q16, q50, q84 = np.percentile(samples, [16, 50, 84])
    return ParameterSummary(
        name=name,
        label=PARAM_LABELS.get(name, name),
        mean=float(np.mean(samples)),
        std=float(np.std(samples)),
        median=float(q50),
        q16=float(q16),
        q84=float(q84),
    )


def run_mcmc(
    likelihood: BandpowerLikelihood,
    *,
    n_walkers: int = 24,
    n_steps: int = 1500,
    burn_in_fraction: float = 0.3,
    seed: int = 42,
    workers: int | None = None,
    derived: tuple[str, ...] = ("omega_m", "sigma8", "age_gyr", "theta_star"),
    progress: ProgressFn | None = None,
) -> SamplerResult:
    """Sample the posterior and summarise it.

    Each likelihood call is one CAMB evaluation at roughly 60 ms, so the chain is entirely
    CPU bound and scales almost linearly across processes.
    """
    ndim = likelihood.ndim
    n_walkers = max(n_walkers, 2 * ndim + 2)
    workers = workers if workers is not None else max(1, min(12, (os.cpu_count() or 4) - 2))

    rng = np.random.default_rng(seed)
    start = likelihood.start_point()

    # Scatter walkers by a small fraction of each parameter's value so the ensemble starts
    # spread out but still inside the prior box.
    scatter = np.abs(start) * 0.01 + 1e-4
    positions = start + scatter * rng.normal(size=(n_walkers, ndim))

    if progress:
        progress(0.0, f"sampling {n_walkers} walkers x {n_steps} steps on {workers} cores")

    report_every = max(1, n_steps // 50)
    pool = ProcessPoolExecutor(max_workers=workers) if workers > 1 else None

    try:
        sampler = emcee.EnsembleSampler(n_walkers, ndim, likelihood, pool=pool)
        for step, _ in enumerate(sampler.sample(positions, iterations=n_steps), start=1):
            if progress and step % report_every == 0:
                progress(0.05 + 0.85 * step / n_steps, f"step {step}/{n_steps}")
    finally:
        if pool is not None:
            pool.shutdown(wait=True)

    burn_in = int(n_steps * burn_in_fraction)
    chain = sampler.get_chain(discard=burn_in, flat=True)
    log_prob = sampler.get_log_prob(discard=burn_in, flat=True)

    if progress:
        progress(0.92, "summarising posterior")

    summaries = {
        name: _summarise(name, chain[:, i]) for i, name in enumerate(likelihood.free_params)
    }

    best_index = int(np.argmax(log_prob))
    best_vector = chain[best_index]
    best_fit = dict(zip(likelihood.free_params, best_vector.tolist(), strict=True))
    best_chi2 = likelihood.chi2(best_vector)

    # Derived parameters are evaluated on a thinned subset: each one costs a CAMB call and
    # the posterior is smooth, so a few hundred samples reproduce the spread faithfully.
    derived_summaries: dict[str, ParameterSummary] = {}
    if derived:
        if progress:
            progress(0.94, "computing derived parameters")
        thin = max(1, chain.shape[0] // 300)
        subset = chain[::thin]
        collected: dict[str, list[float]] = {name: [] for name in derived}

        for vector in subset:
            values = dict(likelihood.config.fixed)
            values.update(dict(zip(likelihood.free_params, vector, strict=True)))
            try:
                result = theory_spectrum(values, lmax=300, lensed=False)
            except Exception:  # noqa: BLE001
                continue
            for name in derived:
                if name in result.derived and np.isfinite(result.derived[name]):
                    collected[name].append(result.derived[name])

        for name, values in collected.items():
            if len(values) > 10:
                derived_summaries[name] = _summarise(name, np.array(values))

    try:
        autocorr = float(np.mean(sampler.get_autocorr_time(quiet=True)))
    except Exception:  # noqa: BLE001
        autocorr = None

    if progress:
        progress(1.0, "done")

    return SamplerResult(
        free_params=list(likelihood.free_params),
        chain=chain,
        log_prob=log_prob,
        summaries=summaries,
        derived_summaries=derived_summaries,
        acceptance_fraction=float(np.mean(sampler.acceptance_fraction)),
        autocorr_time=autocorr,
        best_fit=best_fit,
        best_chi2=best_chi2,
        n_data=len(likelihood.data),
        n_walkers=n_walkers,
        n_steps=n_steps,
        burn_in=burn_in,
    )


def scan_parameter(
    likelihood: BandpowerLikelihood,
    name: str,
    values: np.ndarray,
    *,
    progress: ProgressFn | None = None,
) -> dict[str, list[float]]:
    """Profile chi-squared along one parameter, holding the rest at their start values.

    This is the interactive counterpart to MCMC: a few dozen CAMB calls instead of tens of
    thousands, fast enough to drive a slider in the browser.
    """
    base = likelihood.start_point()
    index = likelihood.free_params.index(name)

    chi2: list[float] = []
    for i, value in enumerate(values):
        vector = base.copy()
        vector[index] = value
        try:
            chi2.append(likelihood.chi2(vector))
        except Exception:  # noqa: BLE001
            chi2.append(float("nan"))
        if progress:
            progress((i + 1) / len(values), f"{name} = {value:.4g}")

    array = np.array(chi2)
    finite = array[np.isfinite(array)]
    best = float(finite.min()) if finite.size else float("nan")

    return {
        "parameter": name,
        "label": PARAM_LABELS.get(name, name),
        "values": [float(v) for v in values],
        "chi2": [float(c) for c in array],
        "delta_chi2": [float(c - best) for c in array],
        "best_value": float(values[int(np.nanargmin(array))]) if finite.size else None,
        "best_chi2": best,
    }


def model_curve(
    likelihood: BandpowerLikelihood, values: dict[str, float], lmax: int = 1200
) -> dict[str, list[float]]:
    """Full theory curve plus its binned form, for overlaying on the data."""
    merged = dict(likelihood.config.fixed)
    merged.update(values)
    theory = theory_spectrum(merged, lmax=lmax, lensed=True)
    binned = bin_theory(theory, likelihood.data.edges)

    residual = (likelihood.data.dl - binned) / likelihood.data.sigma
    chi2 = float(np.nansum(residual**2))

    return {
        "ell": theory.ell[2:].tolist(),
        "dl_tt": theory.dl_tt[2:].tolist(),
        "binned_ell": likelihood.data.ell_eff.tolist(),
        "binned_dl": binned.tolist(),
        "residual_sigma": residual.tolist(),
        "chi2": chi2,
        "dof": max(len(likelihood.data) - len(likelihood.free_params), 1),
        "derived": theory.derived,
    }
