"""Bandpower binning.

Raw per-multipole estimates are far too noisy to plot or compare. Binning averages
neighbouring multipoles, trading angular resolution for signal to noise. Because the number
of independent modes grows as 2l+1, a bin at high l contains far more information than one
at low l — which is why logarithmic binning is often preferred.
"""

from __future__ import annotations

import numpy as np
from cmblab_core.models import Bandpower

from .estimator import PowerSpectrum


def make_edges(scheme: str, lmin: int, lmax: int) -> np.ndarray:
    """Build bin edges from a scheme string.

    ``linear:30``  fixed width of 30 multipoles
    ``log:20``     20 logarithmically spaced bins
    ``planck``     approximately the Planck binning: fine at low l, coarse at high l
    """
    kind, _, argument = scheme.partition(":")

    if kind == "linear":
        width = int(argument or 30)
        return np.arange(lmin, lmax + width + 1, width)

    if kind == "log":
        count = int(argument or 20)
        return np.unique(
            np.round(np.logspace(np.log10(max(lmin, 2)), np.log10(lmax), count + 1)).astype(int)
        )

    if kind == "planck":
        segments = [
            np.arange(lmin, min(30, lmax + 1), 1),
            np.arange(30, min(100, lmax + 1), 5),
            np.arange(100, min(500, lmax + 1), 15),
            np.arange(500, min(1200, lmax + 1), 30),
            np.arange(1200, lmax + 61, 60),
        ]
        edges = np.unique(np.concatenate([s for s in segments if s.size]))
        return edges[edges <= lmax + 60]

    raise ValueError(f"Unknown binning scheme {scheme!r}. Use linear:N, log:N, or planck.")


def bin_spectrum(
    spectrum: PowerSpectrum,
    *,
    scheme: str = "linear:30",
    lmin: int = 2,
    lmax: int | None = None,
    with_errors: bool = True,
) -> list[Bandpower]:
    """Average a power spectrum into bandpowers, weighting by the number of modes.

    Each multipole carries 2l+1 independent modes, so that is the correct weight. Using a
    flat average instead systematically misweights the wide high-l bins.
    """
    lmax = min(lmax or spectrum.lmax, int(spectrum.ell.max()))
    edges = make_edges(scheme, lmin, lmax)

    ell, dl = spectrum.ell, spectrum.dl
    variance = spectrum.variance() if with_errors else None

    bandpowers: list[Bandpower] = []
    for low, high in zip(edges[:-1], edges[1:], strict=False):
        selected = (ell >= low) & (ell < high) & (ell <= lmax) & (ell >= lmin)
        if not selected.any():
            continue

        ells = ell[selected]
        weights = 2.0 * ells + 1.0
        total = weights.sum()

        mean_dl = float(np.sum(weights * dl[selected]) / total)
        ell_eff = float(np.sum(weights * ells) / total)

        error = None
        if variance is not None:
            # Independent multipoles, so variances add in quadrature under the same weights.
            cl_var = float(np.sum(weights**2 * variance[selected]) / total**2)
            cl_err = np.sqrt(max(cl_var, 0.0))
            error = float(cl_err * ell_eff * (ell_eff + 1.0) / (2.0 * np.pi))

        bandpowers.append(
            Bandpower(
                ell_min=int(low),
                ell_max=int(high - 1),
                ell_eff=ell_eff,
                dl_uk2=mean_dl,
                dl_err_uk2=error,
            )
        )

    return bandpowers
