"""Anomaly analysis pipeline and validation gate G6.

Gate G6 is deliberately *not* "the anomalies are significant". That is an open research
question and no test suite can assert it. What can be asserted is that the machinery
producing the p-values is unbiased:

    Feed the pipeline a sky that is isotropic by construction. If the analysis is correct,
    the resulting p-value should be uniformly distributed on [0, 1] — no preference for
    small values. A pipeline that reports p = 0.01 for a perfectly ordinary sky is broken,
    and that is the single most common failure mode in anomaly hunting.

So G6 calibrates the method. The measurement on real data is then reported honestly
alongside it, with the look-elsewhere correction applied.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import healpy as hp
import numpy as np
from cmblab_core.config import get_settings
from cmblab_core.healpix import UNSEEN, load_npz_map

from .simulations import (
    NullDistribution,
    SignificanceResult,
    build_null_distribution,
    lcdm_cl,
    significance,
)
from .statistics import STATISTICS

ProgressFn = Callable[[float, str], None]

#: Resolution for isotropy work. These are large-angle effects, so degrading from 512 to 64
#: costs nothing scientifically and makes 10,000 simulations tractable.
ANOMALY_NSIDE = 64
ANOMALY_LMAX = 128

#: Number of statistics tested, used for the Sidak look-elsewhere correction.
N_TRIALS = len(STATISTICS)

HUMAN_NAMES = {
    "quad_oct_alignment": "Quadrupole–octupole alignment",
    "hemispherical_asymmetry": "Hemispherical power asymmetry",
    "cold_spot": "Cold Spot",
    "low_quadrupole": "Low quadrupole",
}

UNITS = {
    "quad_oct_alignment": "degrees",
    "hemispherical_asymmetry": "dimensionless",
    "cold_spot": "sigma",
    "low_quadrupole": "µK²",
}


@dataclass(slots=True)
class AnomalyReport:
    map_label: str
    nside: int
    n_sims: int
    results: dict[str, SignificanceResult] = field(default_factory=dict)
    calibration: dict[str, Any] = field(default_factory=dict)
    gate_g6_passed: bool = False
    gate_g6_detail: str = ""

    def public(self) -> dict[str, Any]:
        return {
            "map": self.map_label,
            "nside": self.nside,
            "n_sims": self.n_sims,
            "n_trials_corrected": N_TRIALS,
            "statistics": {
                name: {
                    **result.public(),
                    "human_name": HUMAN_NAMES.get(name, name),
                    "unit": UNITS.get(name, ""),
                }
                for name, result in self.results.items()
            },
            "gates": {
                "G6": {
                    "name": "Monte Carlo isotropy analysis is calibrated",
                    "passed": self.gate_g6_passed,
                    "detail": self.gate_g6_detail,
                    "calibration": self.calibration,
                }
            },
        }


def load_anomaly_map(
    dataset: str = "wmap9",
    product: str = "ilc-map",
    *,
    nside: int = ANOMALY_NSIDE,
    mask_product: str | None = "mask-kq75",
) -> tuple[np.ndarray, np.ndarray | None, str]:
    """Load a cleaned map degraded to the isotropy working resolution."""
    root = Path(get_settings().data_dir) / "clean"
    map_path = root / dataset / f"{product}.npz"
    if not map_path.exists():
        raise FileNotFoundError(
            f"{map_path} not found. Run `cmblab-ingest fetch {dataset} {product}` first."
        )

    sky, _ = load_npz_map(map_path)
    if hp.npix2nside(sky.size) != nside:
        sky = hp.ud_grade(sky, nside_out=nside, pess=False, order_in="RING")

    mask = None
    if mask_product:
        mask_path = root / dataset / f"{mask_product}.npz"
        if mask_path.exists():
            raw_mask, _ = load_npz_map(mask_path)
            # Degrade then re-threshold: a coarse pixel only survives if it was mostly
            # unmasked at full resolution.
            coarse = hp.ud_grade(raw_mask.astype(float), nside_out=nside)
            mask = (coarse > 0.9).astype(np.float64)

    return sky, mask, f"{dataset}/{product}"


def measure(
    sky: np.ndarray,
    statistic: str,
    mask: np.ndarray | None = None,
    **kwargs: Any,
) -> dict[str, float]:
    """Evaluate one statistic on a map, applying the mask the same way simulations do."""
    function, _, _ = STATISTICS[statistic]

    if statistic == "quad_oct_alignment":
        working = np.where(mask > 0.5, sky, UNSEEN) if mask is not None else sky
        return function(working, **kwargs)

    return function(sky, mask=mask, **kwargs)


def analyse_statistic(
    statistic: str,
    *,
    dataset: str = "wmap9",
    product: str = "ilc-map",
    mask_product: str | None = "mask-kq75",
    n_sims: int = 1000,
    nside: int = ANOMALY_NSIDE,
    lmax: int = ANOMALY_LMAX,
    seed: int = 20240101,
    workers: int | None = None,
    progress: ProgressFn | None = None,
) -> SignificanceResult:
    """Measure one statistic on the real sky and calibrate it against simulations."""
    sky, mask, label = load_anomaly_map(dataset, product, nside=nside, mask_product=mask_product)

    if progress:
        progress(0.02, f"measuring {statistic} on {label}")
    observed = measure(sky, statistic, mask)

    def sim_progress(fraction: float, message: str) -> None:
        if progress:
            progress(0.05 + 0.93 * fraction, message)

    null = build_null_distribution(
        statistic,
        n_sims=n_sims,
        nside=nside,
        lmax=lmax,
        mask=mask,
        seed=seed,
        workers=workers,
        progress=sim_progress,
    )

    result = significance(statistic, observed, null, n_trials_corrected=N_TRIALS)
    result.extra["map"] = label
    if progress:
        progress(1.0, "complete")
    return result


def calibrate(
    statistic: str,
    *,
    n_checks: int = 24,
    n_sims: int = 300,
    nside: int = 32,
    lmax: int = 64,
    seed: int = 999,
    workers: int | None = None,
    progress: ProgressFn | None = None,
) -> dict[str, Any]:
    """Gate G6: verify the p-values are uniform when the input really is isotropic.

    Draw ``n_checks`` isotropic skies, run each through the same significance machinery,
    and test whether the resulting p-values look uniform. A biased pipeline piles them up
    near zero.
    """
    if progress:
        progress(0.02, "building reference null distribution")

    null = build_null_distribution(
        statistic,
        n_sims=n_sims,
        nside=nside,
        lmax=lmax,
        seed=seed,
        workers=workers,
        progress=lambda f, m: progress(0.02 + 0.5 * f, m) if progress else None,
    )

    cl = lcdm_cl(lmax)
    function, key, lower_tail = STATISTICS[statistic]
    finite = null.values[np.isfinite(null.values)]

    p_values: list[float] = []
    for i in range(n_checks):
        np.random.seed(seed + 500_000 + i)
        sky = hp.synfast(cl, nside, lmax=lmax, pixwin=False, new=True)
        try:
            observed = float(function(sky)[key])
        except Exception:  # noqa: BLE001
            continue

        extreme = np.sum(finite <= observed) if lower_tail else np.sum(finite >= observed)
        p_values.append(float((extreme + 1) / (finite.size + 1)))

        if progress:
            progress(0.55 + 0.43 * (i + 1) / n_checks, f"calibration sky {i + 1}/{n_checks}")

    values = np.array(p_values)
    mean_p = float(values.mean()) if values.size else float("nan")
    fraction_small = float(np.mean(values < 0.05)) if values.size else float("nan")

    # A uniform distribution has mean 0.5 and puts 5% of its mass below 0.05. With only a
    # few dozen checks the tolerances have to be generous; this catches gross bias, which
    # is what actually goes wrong.
    mean_ok = 0.3 <= mean_p <= 0.7
    tail_ok = fraction_small <= 0.25

    if progress:
        progress(1.0, "calibration complete")

    return {
        "statistic": statistic,
        "n_checks": int(values.size),
        "n_sims_reference": int(finite.size),
        "mean_p_value": round(mean_p, 4),
        "fraction_below_0p05": round(fraction_small, 4),
        "p_values": [round(p, 4) for p in values.tolist()],
        "passed": bool(mean_ok and tail_ok),
        "detail": (
            f"mean p = {mean_p:.3f} (expect ~0.5), {fraction_small:.1%} below 0.05 (expect ~5%)"
        ),
    }


def run_full_analysis(
    *,
    dataset: str = "wmap9",
    product: str = "ilc-map",
    mask_product: str | None = "mask-kq75",
    n_sims: int = 1000,
    nside: int = ANOMALY_NSIDE,
    statistics: tuple[str, ...] | None = None,
    calibration_statistic: str = "low_quadrupole",
    workers: int | None = None,
    progress: ProgressFn | None = None,
) -> AnomalyReport:
    """Run every isotropy statistic, then calibrate the machinery."""
    names = statistics or tuple(STATISTICS)
    report = AnomalyReport(map_label=f"{dataset}/{product}", nside=nside, n_sims=n_sims)

    total = len(names) + 1
    for index, name in enumerate(names):

        def scoped(fraction: float, message: str, i: int = index, label: str = name) -> None:
            if progress:
                progress((i + fraction) / total, f"{label}: {message}")

        report.results[name] = analyse_statistic(
            name,
            dataset=dataset,
            product=product,
            mask_product=mask_product,
            n_sims=n_sims,
            nside=nside,
            workers=workers,
            progress=scoped,
        )

    def calib_progress(fraction: float, message: str) -> None:
        if progress:
            progress((len(names) + fraction) / total, f"calibration: {message}")

    report.calibration = calibrate(calibration_statistic, workers=workers, progress=calib_progress)
    report.gate_g6_passed = bool(report.calibration.get("passed"))
    report.gate_g6_detail = (
        f"p-value calibration on {calibration_statistic}: {report.calibration['detail']}"
    )

    return report


__all__ = [
    "ANOMALY_LMAX",
    "ANOMALY_NSIDE",
    "AnomalyReport",
    "NullDistribution",
    "analyse_statistic",
    "calibrate",
    "load_anomaly_map",
    "measure",
    "run_full_analysis",
]
