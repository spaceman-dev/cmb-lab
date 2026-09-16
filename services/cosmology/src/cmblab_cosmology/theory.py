"""Theory spectra from CAMB.

CAMB solves the coupled Boltzmann-Einstein system for the photon, baryon, dark matter and
neutrino fluids in a perturbed FRW universe, and returns the predicted angular power
spectrum. Everything here is a thin, cached wrapper: the physics lives in CAMB.

Performance note: one evaluation at lmax=700 costs about 60 ms, so an MCMC chain of tens of
thousands of samples is a few minutes on this machine rather than a few hours. That is why
the sampler runs as a background job and not a batch script.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import camb
import numpy as np
from cmblab_core.models import CosmoParams

#: Parameters the sampler is allowed to vary, with sensible uniform bounds.
PARAM_BOUNDS: dict[str, tuple[float, float]] = {
    "H0": (55.0, 85.0),
    "ombh2": (0.017, 0.027),
    "omch2": (0.09, 0.15),
    "ns": (0.88, 1.05),
    "logA": (2.7, 3.4),  # ln(10^10 As)
    "tau": (0.01, 0.15),
}

#: Human-readable labels used by the API and the frontend.
PARAM_LABELS: dict[str, str] = {
    "H0": "H₀  [km/s/Mpc]",
    "ombh2": "Ω_b h²",
    "omch2": "Ω_c h²",
    "ns": "n_s",
    "logA": "ln(10¹⁰ A_s)",
    "tau": "τ",
    "omega_m": "Ω_m",
    "sigma8": "σ₈",
    "age_gyr": "age  [Gyr]",
    "theta_star": "100 θ*",
    "z_star": "z*",
}


@dataclass(slots=True)
class TheoryResult:
    ell: np.ndarray
    dl_tt: np.ndarray
    dl_ee: np.ndarray
    dl_te: np.ndarray
    params: dict[str, float]
    derived: dict[str, float] = field(default_factory=dict)

    def first_peak(self, lo: int = 100, hi: int = 350) -> tuple[int, float]:
        window = (self.ell >= lo) & (self.ell <= hi)
        index = int(np.argmax(self.dl_tt[window]))
        return int(self.ell[window][index]), float(self.dl_tt[window][index])


def logA_to_As(log_a: float) -> float:
    """ln(10^10 A_s) -> A_s. The log form is what samplers should explore."""
    return float(np.exp(log_a) * 1e-10)


def As_to_logA(a_s: float) -> float:
    return float(np.log(a_s * 1e10))


@lru_cache(maxsize=4096)
def _compute(
    H0: float,
    ombh2: float,
    omch2: float,
    tau: float,
    ns: float,
    As: float,
    mnu: float,
    omk: float,
    lmax: int,
    lensed: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, float]]:
    """Raw CAMB call. Cached because MCMC revisits nearby points constantly."""
    pars = camb.set_params(
        H0=H0,
        ombh2=ombh2,
        omch2=omch2,
        tau=tau,
        ns=ns,
        As=As,
        mnu=mnu,
        omk=omk,
        lmax=lmax,
        lens_potential_accuracy=1 if lensed else 0,
        WantTransfer=True,
    )
    results = camb.get_results(pars)

    key = "total" if lensed else "unlensed_scalar"
    spectra = results.get_cmb_power_spectra(pars, CMB_unit="muK", raw_cl=False)[key]

    derived_raw = results.get_derived_params()
    derived = {
        "omega_m": float(results.get_Omega("cdm") + results.get_Omega("baryon")),
        "omega_lambda": float(results.get_Omega("de")),
        "sigma8": float(results.get_sigma8_0()),
        "age_gyr": float(results.physical_time(0.0)),
        "theta_star": float(derived_raw.get("thetastar", np.nan)),
        "z_star": float(derived_raw.get("zstar", np.nan)),
        "z_drag": float(derived_raw.get("zdrag", np.nan)),
        "r_star_mpc": float(derived_raw.get("rstar", np.nan)),
    }
    derived["S8"] = derived["sigma8"] * np.sqrt(derived["omega_m"] / 0.3)

    return spectra[:, 0].copy(), spectra[:, 1].copy(), spectra[:, 3].copy(), derived


def theory_spectrum(
    params: CosmoParams | dict[str, float],
    *,
    lmax: int = 2500,
    lensed: bool = True,
) -> TheoryResult:
    """Compute D_l for a set of cosmological parameters."""
    if isinstance(params, dict):
        payload = dict(params)
        if "logA" in payload:
            payload["As"] = logA_to_As(payload.pop("logA"))
        params = CosmoParams(**payload)

    tt, ee, te, derived = _compute(
        round(params.H0, 6),
        round(params.ombh2, 8),
        round(params.omch2, 8),
        round(params.tau, 6),
        round(params.ns, 6),
        float(f"{params.As:.8e}"),
        round(params.mnu, 4),
        round(params.omk, 6),
        lmax,
        lensed,
    )

    return TheoryResult(
        ell=np.arange(tt.size),
        dl_tt=tt,
        dl_ee=ee,
        dl_te=te,
        params={
            "H0": params.H0,
            "ombh2": params.ombh2,
            "omch2": params.omch2,
            "tau": params.tau,
            "ns": params.ns,
            "As": params.As,
            "logA": As_to_logA(params.As),
        },
        derived=derived,
    )


def bin_theory(
    theory: TheoryResult,
    edges: list[tuple[int, int]],
) -> np.ndarray:
    """Average theory D_l into the same bandpowers as the data.

    Weighting by 2l+1 matches how the data were binned. Comparing an unbinned theory curve
    against binned data at the bin centre is a subtle but real bias, especially in the wide
    bins where the spectrum has curvature.
    """
    out = np.empty(len(edges))
    for i, (lo, hi) in enumerate(edges):
        selected = (theory.ell >= lo) & (theory.ell <= hi)
        if not selected.any():
            out[i] = np.nan
            continue
        ell = theory.ell[selected]
        weights = 2.0 * ell + 1.0
        out[i] = float(np.sum(weights * theory.dl_tt[selected]) / weights.sum())
    return out


def cache_info() -> dict[str, Any]:
    info = _compute.cache_info()
    return {
        "hits": info.hits,
        "misses": info.misses,
        "size": info.currsize,
        "maxsize": info.maxsize,
    }
