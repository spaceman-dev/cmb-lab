"""Unresolved point source correction.

A cross-spectrum between two detectors removes *noise*, because detector noise is
independent. It does not remove anything that is genuinely on the sky in both maps — and
unresolved extragalactic point sources are. Below the detection threshold they form a
Poisson field, which has a flat angular power spectrum:

    C_l^ps = A_ps  (constant)   ->   D_l^ps = l(l+1) A_ps / 2pi  (grows as l^2)

That l^2 growth is why a V1 x V2 spectrum sits increasingly above LCDM past l ~ 350 even
though the noise has cancelled. WMAP applies exactly this correction to their published
spectrum; so do we.

A caveat worth being explicit about: fitting A_ps against a theory curve is mildly
circular, because it assumes the theory is right in order to measure the contaminant. The
non-circular alternative exploits frequency dependence — point sources have a different
spectral index from the CMB, so comparing V x V against V x W and W x W separates them.
:func:`fit_from_frequency_pair` implements that; :func:`fit_against_theory` is the quick
version and reports its own assumption.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class PointSourceFit:
    """A fitted flat-C_l contaminant amplitude, in uK^2 sr."""

    amplitude: float
    amplitude_err: float
    ell_min: int
    ell_max: int
    method: str
    circular: bool

    def cl_template(self, ell: np.ndarray) -> np.ndarray:
        return np.full(ell.shape, self.amplitude, dtype=np.float64)

    def dl_template(self, ell: np.ndarray) -> np.ndarray:
        return ell * (ell + 1.0) * self.amplitude / (2.0 * np.pi)

    def summary(self) -> str:
        flag = " (assumes the reference theory is correct)" if self.circular else ""
        return (
            f"A_ps = {self.amplitude:.4e} +/- {self.amplitude_err:.1e} uK^2 sr "
            f"fitted over l={self.ell_min}-{self.ell_max} via {self.method}{flag}"
        )


def fit_against_theory(
    ell: np.ndarray,
    cl: np.ndarray,
    theory_cl: np.ndarray,
    variance: np.ndarray | None = None,
    *,
    ell_min: int = 400,
    ell_max: int = 800,
) -> PointSourceFit:
    """Fit a constant C_l excess over a theory curve, inverse-variance weighted.

    Restricted to high multipoles where the CMB is damping away and any flat component
    dominates the residual.
    """
    selected = (ell >= ell_min) & (ell <= ell_max) & np.isfinite(theory_cl) & np.isfinite(cl)
    if selected.sum() < 3:
        raise ValueError(f"Not enough multipoles in [{ell_min}, {ell_max}] to fit")

    excess = cl[selected] - theory_cl[selected]

    if variance is not None:
        weights = 1.0 / np.maximum(variance[selected], np.finfo(float).tiny)
    else:
        weights = 2.0 * ell[selected] + 1.0

    amplitude = float(np.sum(weights * excess) / np.sum(weights))
    error = float(np.sqrt(1.0 / np.sum(weights)))

    return PointSourceFit(
        amplitude=amplitude,
        amplitude_err=error,
        ell_min=ell_min,
        ell_max=ell_max,
        method="flat-Cl excess over theory",
        circular=True,
    )


def fit_from_frequency_pair(
    ell: np.ndarray,
    cl_low: np.ndarray,
    cl_high: np.ndarray,
    freq_low_ghz: float,
    freq_high_ghz: float,
    *,
    spectral_index: float = -2.0,
    ell_min: int = 400,
    ell_max: int = 800,
) -> PointSourceFit:
    """Separate a point source component using its frequency dependence.

    The CMB is identical in thermodynamic units at every frequency, so it cancels in the
    difference of two frequency cross-spectra. A point source population with antenna
    temperature scaling as nu^beta does not, leaving

        C_l^low - C_l^high  =  A_ps(low) * [1 - (nu_high/nu_low)^(2*beta)]

    No theory curve is involved, so this estimate is not circular.
    """
    selected = (ell >= ell_min) & (ell <= ell_max)
    if selected.sum() < 3:
        raise ValueError(f"Not enough multipoles in [{ell_min}, {ell_max}] to fit")

    ratio = (freq_high_ghz / freq_low_ghz) ** (2.0 * spectral_index)
    denominator = 1.0 - ratio
    if abs(denominator) < 1e-6:
        raise ValueError("Frequencies too close to separate a point source component")

    difference = cl_low[selected] - cl_high[selected]
    weights = 2.0 * ell[selected] + 1.0

    amplitude = float(np.sum(weights * difference) / np.sum(weights) / denominator)
    scatter = float(np.std(difference / denominator) / np.sqrt(selected.sum()))

    return PointSourceFit(
        amplitude=amplitude,
        amplitude_err=scatter,
        ell_min=ell_min,
        ell_max=ell_max,
        method=f"{freq_low_ghz:.0f}/{freq_high_ghz:.0f} GHz differencing",
        circular=False,
    )


def subtract(cl: np.ndarray, fit: PointSourceFit) -> np.ndarray:
    """Remove the fitted flat component, clipping at zero."""
    return np.clip(cl - fit.amplitude, 0.0, None)
