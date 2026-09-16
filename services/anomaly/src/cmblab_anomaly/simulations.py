"""Monte Carlo null distributions for the isotropy statistics.

The logic of the whole exercise:

1. Assume the null hypothesis — the sky is a statistically isotropic Gaussian random field
   drawn from the LCDM power spectrum.
2. Generate many such skies, and put each one through **exactly** the same analysis as the
   real data: same mask, same resolution, same maximisation over axes.
3. Ask what fraction of them produce a statistic at least as extreme as the observed one.

Step 2 is where analyses usually go wrong. If the observed statistic was obtained by
searching over thousands of candidate axes for the most extreme value, the simulations must
search too — otherwise the null distribution is of a different quantity entirely and every
result looks significant.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Any

import healpy as hp
import numpy as np

from .statistics import STATISTICS

ProgressFn = Callable[[float, str], None]

_WORKER: dict[str, Any] = {}


@dataclass(slots=True)
class NullDistribution:
    statistic: str
    key: str
    values: np.ndarray
    n_sims: int
    nside: int
    lmax: int
    seed: int
    failures: int = 0

    @property
    def mean(self) -> float:
        return float(np.nanmean(self.values))

    @property
    def std(self) -> float:
        return float(np.nanstd(self.values))

    def percentiles(self, qs: tuple[float, ...] = (1, 5, 16, 50, 84, 95, 99)) -> dict[str, float]:
        finite = self.values[np.isfinite(self.values)]
        if finite.size == 0:
            return {}
        return {f"p{q:g}": float(np.percentile(finite, q)) for q in qs}

    def histogram(self, bins: int = 40) -> dict[str, list[float]]:
        finite = self.values[np.isfinite(self.values)]
        counts, edges = np.histogram(finite, bins=bins)
        centres = 0.5 * (edges[:-1] + edges[1:])
        return {"centres": centres.tolist(), "counts": counts.tolist()}


@dataclass(slots=True)
class SignificanceResult:
    statistic: str
    observed: float
    details: dict[str, float]
    null: NullDistribution
    p_value: float
    p_value_corrected: float
    n_more_extreme: int
    lower_tail: bool
    n_trials_corrected: int = 1
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def sigma_equivalent(self) -> float:
        """Gaussian-equivalent significance of the *corrected* p-value."""
        from scipy.stats import norm

        p = min(max(self.p_value_corrected, 1e-12), 1 - 1e-12)
        return float(abs(norm.ppf(p / 2.0)))

    def public(self) -> dict[str, Any]:
        return {
            "statistic": self.statistic,
            "observed": self.observed,
            "details": self.details,
            "p_value": round(self.p_value, 5),
            "p_value_corrected": round(self.p_value_corrected, 5),
            "sigma_equivalent": round(self.sigma_equivalent, 3),
            "n_more_extreme": self.n_more_extreme,
            "n_sims": self.null.n_sims,
            "lower_tail": self.lower_tail,
            "n_trials_corrected": self.n_trials_corrected,
            "null": {
                "mean": self.null.mean,
                "std": self.null.std,
                "percentiles": self.null.percentiles(),
                "histogram": self.null.histogram(),
                "failures": self.null.failures,
            },
            **self.extra,
        }


def lcdm_cl(lmax: int, params: dict[str, float] | None = None) -> np.ndarray:
    """Theory C_l in uK^2 for generating isotropic realisations.

    The null hypothesis is LCDM, so the simulations must be drawn from the LCDM spectrum,
    not from the data's own spectrum. Using the measured spectrum would bake any real
    anomaly into the null and hide it.

    CAMB truncates lensed spectra a few hundred multipoles below the requested lmax, so we
    ask for headroom and then slice to exactly what we need.
    """
    from cmblab_cosmology.theory import theory_spectrum

    theory = theory_spectrum(params or {}, lmax=lmax + 400, lensed=True)

    cl = np.zeros(lmax + 1)
    usable = min(theory.dl_tt.size, lmax + 1)
    ell = np.arange(usable, dtype=float)

    with np.errstate(divide="ignore", invalid="ignore"):
        cl[2:usable] = 2.0 * np.pi * theory.dl_tt[2:usable] / (ell[2:] * (ell[2:] + 1.0))

    return np.nan_to_num(cl, nan=0.0, posinf=0.0, neginf=0.0)


def _init_worker(
    cl: np.ndarray,
    nside: int,
    lmax: int,
    mask: np.ndarray | None,
    statistic: str,
    kwargs: dict[str, Any],
) -> None:
    # healpy's spherical harmonic transforms are OpenMP-threaded. With one process per core
    # each spawning its own thread pool, the machine ends up with cores² threads competing
    # for cores¹ cores and throughput collapses — measured here as a 20x slowdown. One
    # thread per process is correct: the parallelism already comes from the process pool.
    for variable in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ):
        os.environ[variable] = "1"

    _WORKER.update(cl=cl, nside=nside, lmax=lmax, mask=mask, statistic=statistic, kwargs=kwargs)


def _run_one(seed: int) -> float:
    """Generate one isotropic sky and evaluate the statistic on it."""
    np.random.seed(seed)
    sky = hp.synfast(_WORKER["cl"], _WORKER["nside"], lmax=_WORKER["lmax"], pixwin=False, new=True)

    mask = _WORKER["mask"]
    function, key, _ = STATISTICS[_WORKER["statistic"]]

    kwargs = dict(_WORKER["kwargs"])
    if mask is not None and _WORKER["statistic"] != "quad_oct_alignment":
        kwargs["mask"] = mask
    elif mask is not None:
        from cmblab_core.healpix import UNSEEN

        sky = np.where(mask > 0.5, sky, UNSEEN)

    try:
        return float(function(sky, **kwargs)[key])
    except Exception:  # noqa: BLE001 - a single failed realisation must not kill the batch
        return float("nan")


def build_null_distribution(
    statistic: str,
    *,
    n_sims: int = 1000,
    nside: int = 64,
    lmax: int = 128,
    mask: np.ndarray | None = None,
    seed: int = 20240101,
    params: dict[str, float] | None = None,
    workers: int | None = None,
    statistic_kwargs: dict[str, Any] | None = None,
    progress: ProgressFn | None = None,
) -> NullDistribution:
    """Evaluate ``statistic`` on ``n_sims`` isotropic Gaussian realisations."""
    if statistic not in STATISTICS:
        raise KeyError(f"Unknown statistic {statistic!r}. Known: {sorted(STATISTICS)}")

    workers = workers or max(1, min(12, (os.cpu_count() or 4) - 2))
    cl = lcdm_cl(lmax, params)
    seeds = list(range(seed, seed + n_sims))

    if progress:
        progress(0.0, f"{n_sims} realisations on {workers} workers")

    values = np.empty(n_sims)
    completed = 0

    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=_init_worker,
        initargs=(cl, nside, lmax, mask, statistic, statistic_kwargs or {}),
    ) as pool:
        chunk = max(1, n_sims // (workers * 8))
        for index, value in enumerate(pool.map(_run_one, seeds, chunksize=chunk)):
            values[index] = value
            completed += 1
            if progress and completed % max(1, n_sims // 40) == 0:
                progress(completed / n_sims, f"{completed}/{n_sims} realisations")

    if progress:
        progress(1.0, "null distribution complete")

    _, key, _ = STATISTICS[statistic]
    return NullDistribution(
        statistic=statistic,
        key=key,
        values=values,
        n_sims=n_sims,
        nside=nside,
        lmax=lmax,
        seed=seed,
        failures=int(np.sum(~np.isfinite(values))),
    )


def significance(
    statistic: str,
    observed_details: dict[str, float],
    null: NullDistribution,
    *,
    n_trials_corrected: int = 1,
) -> SignificanceResult:
    """Empirical p-value, plus a look-elsewhere correction.

    The correction is Sidak: if you ran ``n`` effectively independent tests and are quoting
    the most extreme, the probability that *any* of them reached that level under the null
    is ``1 - (1 - p)^n``. This project tests four anomalies, so quoting an uncorrected
    p-value for whichever looked best would overstate the case roughly fourfold.
    """
    _, key, lower_tail = STATISTICS[statistic]
    observed = float(observed_details[key])

    finite = null.values[np.isfinite(null.values)]
    if finite.size == 0:
        raise ValueError("Null distribution contains no finite values")

    n_extreme = int(np.sum(finite <= observed)) if lower_tail else int(np.sum(finite >= observed))

    # Add-one smoothing: with N simulations the smallest measurable p-value is ~1/N, and
    # reporting exactly zero would claim infinite significance from finite sampling.
    p_value = (n_extreme + 1) / (finite.size + 1)
    p_corrected = 1.0 - (1.0 - p_value) ** n_trials_corrected

    return SignificanceResult(
        statistic=statistic,
        observed=observed,
        details=observed_details,
        null=null,
        p_value=float(p_value),
        p_value_corrected=float(min(p_corrected, 1.0)),
        n_more_extreme=n_extreme,
        lower_tail=lower_tail,
        n_trials_corrected=n_trials_corrected,
    )
