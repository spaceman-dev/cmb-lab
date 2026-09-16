"""Gaussian bandpower likelihood and parameter inference.

Given bandpowers D_b with uncertainties sigma_b, and a theory prediction D_b(theta) binned
the same way, the log-likelihood for a diagonal covariance is

    -2 ln L  =  sum_b  [ (D_b - D_b(theta)) / sigma_b ]^2

Two honest caveats:

* **The covariance is diagonal.** Masking couples neighbouring multipoles, so the true
  bandpower covariance has off-diagonal terms. Ignoring them makes the likelihood slightly
  over-confident. For a 20-bandpower WMAP measurement this is a modest effect, but it means
  quoted errors should be read as approximate.
* **TT alone cannot separate tau from A_s.** Reionization suppresses the spectrum by
  e^(-2 tau) at every multipole above the reionization bump, which is degenerate with the
  primordial amplitude. Polarization at low multipole breaks it. With TT-only data we
  impose a Gaussian prior on tau from the published measurement and say so.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
from cmblab_core.constants import PLANCK_2018

from .theory import PARAM_BOUNDS, bin_theory, theory_spectrum

#: Gaussian priors applied to parameters the data cannot constrain on their own.
DEFAULT_PRIORS: dict[str, tuple[float, float]] = {
    "tau": (PLANCK_2018["tau"].value, PLANCK_2018["tau"].err),
}

#: Fixed unless explicitly sampled.
DEFAULT_FIXED: dict[str, float] = {
    "tau": PLANCK_2018["tau"].value,
    "logA": 3.044,
    "ns": PLANCK_2018["ns"].value,
}


@dataclass(slots=True)
class BandpowerData:
    """Observed bandpowers plus the bin edges needed to bin theory identically."""

    ell_eff: np.ndarray
    dl: np.ndarray
    sigma: np.ndarray
    edges: list[tuple[int, int]]

    @classmethod
    def from_bandpowers(cls, bandpowers: Sequence, ell_min: int = 30) -> BandpowerData:
        """Build from cmblab_core Bandpower models, dropping unusable bins.

        Bins below ell_min are excluded by default: at large angles cosmic variance
        dominates, the f_sky approximation is least accurate, and the low-l anomalies we
        study separately would leak into the parameter fit.
        """
        rows = [b for b in bandpowers if b.dl_err_uk2 and b.dl_err_uk2 > 0 and b.ell_eff >= ell_min]
        if len(rows) < 4:
            raise ValueError(f"Only {len(rows)} usable bandpowers above l={ell_min}")

        return cls(
            ell_eff=np.array([b.ell_eff for b in rows]),
            dl=np.array([b.dl_uk2 for b in rows]),
            sigma=np.array([b.dl_err_uk2 for b in rows]),
            edges=[(b.ell_min, b.ell_max) for b in rows],
        )

    @property
    def lmax(self) -> int:
        return int(max(hi for _, hi in self.edges))

    def __len__(self) -> int:
        return int(self.dl.size)


@dataclass(slots=True)
class LikelihoodConfig:
    free_params: list[str] = field(default_factory=lambda: ["H0", "ombh2", "omch2"])
    fixed: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_FIXED))
    priors: dict[str, tuple[float, float]] = field(default_factory=lambda: dict(DEFAULT_PRIORS))
    lmax_pad: int = 100
    lensed: bool = True

    def validate(self) -> None:
        unknown = [p for p in self.free_params if p not in PARAM_BOUNDS]
        if unknown:
            raise ValueError(f"Unknown parameters {unknown}. Allowed: {sorted(PARAM_BOUNDS)}")
        if not self.free_params:
            raise ValueError("At least one free parameter is required")


class BandpowerLikelihood:
    """Callable log-posterior over the free parameters."""

    def __init__(self, data: BandpowerData, config: LikelihoodConfig | None = None) -> None:
        self.data = data
        self.config = config or LikelihoodConfig()
        self.config.validate()
        self._lmax = data.lmax + self.config.lmax_pad
        self._inv_var = 1.0 / data.sigma**2

    @property
    def free_params(self) -> list[str]:
        return self.config.free_params

    @property
    def ndim(self) -> int:
        return len(self.config.free_params)

    def start_point(self) -> np.ndarray:
        """Planck 2018 best fit, used to seed the walkers."""
        defaults = {
            "H0": 67.36,
            "ombh2": 0.02237,
            "omch2": 0.1200,
            "ns": 0.9649,
            "logA": 3.044,
            "tau": 0.0544,
        }
        return np.array([defaults[p] for p in self.free_params])

    def _assemble(self, vector: np.ndarray) -> dict[str, float]:
        values = dict(self.config.fixed)
        values.update(dict(zip(self.free_params, vector, strict=True)))
        return values

    def log_prior(self, vector: np.ndarray) -> float:
        total = 0.0
        for name, value in zip(self.free_params, vector, strict=True):
            lo, hi = PARAM_BOUNDS[name]
            if not (lo <= value <= hi):
                return -np.inf
            if name in self.config.priors:
                mu, sigma = self.config.priors[name]
                total += -0.5 * ((value - mu) / sigma) ** 2
        return total

    def chi2(self, vector: np.ndarray) -> float:
        values = self._assemble(vector)
        theory = theory_spectrum(values, lmax=self._lmax, lensed=self.config.lensed)
        model = bin_theory(theory, self.data.edges)
        if not np.all(np.isfinite(model)):
            return np.inf
        return float(np.sum((self.data.dl - model) ** 2 * self._inv_var))

    def log_likelihood(self, vector: np.ndarray) -> float:
        try:
            return -0.5 * self.chi2(vector)
        except Exception:  # noqa: BLE001 - CAMB rejects unphysical corners of the box
            return -np.inf

    def __call__(self, vector: np.ndarray) -> float:
        prior = self.log_prior(vector)
        if not np.isfinite(prior):
            return -np.inf
        likelihood = self.log_likelihood(vector)
        return prior + likelihood if np.isfinite(likelihood) else -np.inf

    def best_fit_model(self, vector: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
        values = self._assemble(vector)
        theory = theory_spectrum(values, lmax=self._lmax, lensed=self.config.lensed)
        return bin_theory(theory, self.data.edges), theory.derived
