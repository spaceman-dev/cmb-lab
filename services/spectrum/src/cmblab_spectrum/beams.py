"""Beam transfer functions.

A telescope with a finite beam smooths the sky, suppressing power at small angular scales
by a factor b_l. Recovering the true spectrum means dividing it back out — so an inaccurate
b_l produces an error that grows exponentially with multipole.

WMAP publishes tabulated b_l per differencing assembly, measured from observations of
Jupiter. Always prefer those over a Gaussian approximation: the real beams have extended
sidelobes that a Gaussian does not capture.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import healpy as hp
import numpy as np
from cmblab_core.config import get_settings


@dataclass(slots=True)
class BeamTransfer:
    """Tabulated beam transfer function b_l, normalised to 1 at l=1."""

    label: str
    ell: np.ndarray
    bl: np.ndarray
    bl_frac_err: np.ndarray | None = None

    def at(self, lmax: int) -> np.ndarray:
        """Resample onto 0..lmax, holding the last tabulated value past the end."""
        out = np.ones(lmax + 1)
        n = min(self.bl.size, lmax + 1)
        out[:n] = self.bl[:n]
        if n <= lmax:
            out[n:] = self.bl[-1]
        return out

    def effective_fwhm_arcmin(self, fit_lmax: int = 400) -> float:
        """Best-fit Gaussian FWHM, useful as a sanity check and for reporting."""
        selected = (self.ell >= 2) & (self.ell <= fit_lmax) & (self.bl > 0)
        ell = self.ell[selected].astype(float)
        slope = np.polyfit(ell * (ell + 1.0) / 2.0, np.log(self.bl[selected]), 1)[0]
        sigma = np.sqrt(max(-slope, 0.0))
        return float(np.degrees(sigma) * np.sqrt(8.0 * np.log(2.0)) * 60.0)


def load_wmap_beam(path: str | Path, label: str = "") -> BeamTransfer:
    """Load a ``wmap_ampl_bl_*.txt`` file: columns are l, b_l, fractional error."""
    data = np.loadtxt(path, comments="#")
    return BeamTransfer(
        label=label or Path(path).stem,
        ell=data[:, 0].astype(int),
        bl=data[:, 1],
        bl_frac_err=data[:, 2] if data.shape[1] > 2 else None,
    )


def load_beam(dataset_slug: str, beam_slug: str) -> BeamTransfer:
    """Load a beam product that the ingest service has already downloaded."""
    from cmblab_ingest.registry import get_product

    product = get_product(dataset_slug, beam_slug)
    path = Path(get_settings().data_dir) / "raw" / dataset_slug / product.filename
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `cmblab-ingest fetch {dataset_slug} {beam_slug}` first."
        )
    return load_wmap_beam(path, label=beam_slug)


def gaussian_beam(fwhm_arcmin: float, lmax: int) -> BeamTransfer:
    bl = hp.gauss_beam(np.radians(fwhm_arcmin / 60.0), lmax=lmax)
    return BeamTransfer(
        label=f"gaussian-{fwhm_arcmin:.1f}arcmin",
        ell=np.arange(lmax + 1),
        bl=bl,
    )
