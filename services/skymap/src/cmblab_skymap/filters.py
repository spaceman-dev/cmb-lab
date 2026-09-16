"""Harmonic filtering — the most pedagogically useful thing you can do to a sky map.

A CMB map is a sum of spherical harmonics. Isolating a band of multipoles and transforming
back shows you *exactly* what that angular scale contributes. Displaying the quadrupole
alone, then the octupole alone, then their sum, makes the "Axis of Evil" alignment visible
rather than merely tabulated — the two patterns visibly share a plane.
"""

from __future__ import annotations

from dataclasses import dataclass

import healpy as hp
import numpy as np
from cmblab_core.healpix import UNSEEN


@dataclass(slots=True)
class FilterResult:
    sky: np.ndarray
    ell_min: int
    ell_max: int
    rms: float
    description: str


def multipole_band(
    sky: np.ndarray,
    ell_min: int,
    ell_max: int,
    *,
    lmax: int | None = None,
) -> FilterResult:
    """Keep only multipoles in [ell_min, ell_max] and transform back to a map."""
    nside = hp.npix2nside(sky.size)
    lmax = lmax or min(3 * nside - 1, 512)
    ell_max = min(ell_max, lmax)

    clean = np.where(sky == UNSEEN, 0.0, sky)
    alm = hp.map2alm(clean, lmax=lmax, iter=1, use_pixel_weights=False)

    window = np.zeros(lmax + 1)
    window[ell_min : ell_max + 1] = 1.0
    filtered = hp.alm2map(hp.almxfl(alm, window), nside, lmax=lmax)

    angular_scale = 180.0 / max(ell_min, 1)
    return FilterResult(
        sky=filtered,
        ell_min=ell_min,
        ell_max=ell_max,
        rms=float(filtered.std()),
        description=(f"multipoles {ell_min}–{ell_max}, angular scales around {angular_scale:.1f}°"),
    )


def smooth(sky: np.ndarray, fwhm_deg: float, *, lmax: int | None = None) -> FilterResult:
    """Gaussian smoothing. Suppresses small scales without touching large ones."""
    nside = hp.npix2nside(sky.size)
    lmax = lmax or min(3 * nside - 1, 512)

    clean = np.where(sky == UNSEEN, 0.0, sky)
    smoothed = hp.smoothing(clean, fwhm=np.radians(fwhm_deg), lmax=lmax)

    return FilterResult(
        sky=smoothed,
        ell_min=0,
        ell_max=int(180.0 / max(fwhm_deg, 1e-3)),
        rms=float(smoothed.std()),
        description=f"smoothed with a {fwhm_deg:.2f}° FWHM Gaussian beam",
    )


#: Named views that tell a story, exposed directly in the UI.
PRESETS: dict[str, dict] = {
    "full": {
        "label": "Full map",
        "ell_min": 2,
        "ell_max": 512,
        "explain": (
            "Everything the instrument measured, with the monopole and dipole removed. "
            "The mottled pattern is the sound of the primordial plasma, frozen in place "
            "380,000 years after the Big Bang."
        ),
    },
    "quadrupole": {
        "label": "Quadrupole only (ℓ=2)",
        "ell_min": 2,
        "ell_max": 2,
        "explain": (
            "The largest possible anisotropy pattern: five independent numbers describing "
            "the whole sky. Its observed amplitude is lower than ΛCDM predicts, which is "
            "one of the long-standing large-angle anomalies."
        ),
    },
    "octupole": {
        "label": "Octupole only (ℓ=3)",
        "ell_min": 3,
        "ell_max": 3,
        "explain": (
            "The next pattern up. Compare its orientation to the quadrupole: in an "
            "isotropic universe they should point in unrelated directions, yet they appear "
            "to share a plane. That is the 'Axis of Evil'."
        ),
    },
    "quad_oct": {
        "label": "Quadrupole + octupole",
        "ell_min": 2,
        "ell_max": 3,
        "explain": (
            "The two lowest multipoles together. The combined pattern looks planar, which "
            "is the visual statement of the alignment anomaly."
        ),
    },
    "large_scale": {
        "label": "Large scales (ℓ ≤ 30)",
        "ell_min": 2,
        "ell_max": 30,
        "explain": (
            "The Sachs–Wolfe plateau. These fluctuations were larger than the horizon at "
            "recombination, so they never had time to oscillate: you are seeing the "
            "primordial gravitational potential almost unprocessed."
        ),
    },
    "acoustic": {
        "label": "Acoustic scales (ℓ = 100–500)",
        "ell_min": 100,
        "ell_max": 500,
        "explain": (
            "The range containing the acoustic peaks. This is the standing-wave pattern of "
            "photon-baryon fluid sloshing in dark matter potential wells — the actual "
            "sound of the early universe."
        ),
    },
    "first_peak": {
        "label": "First acoustic peak (ℓ = 180–260)",
        "ell_min": 180,
        "ell_max": 260,
        "explain": (
            "Modes that had exactly enough time to compress once before recombination "
            "froze them. The angular size of these blobs, about one degree, is what tells "
            "us the universe is spatially flat."
        ),
    },
    "damping_tail": {
        "label": "Damping tail (ℓ > 800)",
        "ell_min": 800,
        "ell_max": 2048,
        "explain": (
            "Silk damping. Recombination was not instantaneous, so photons random-walked "
            "out of the smallest overdensities and washed them out."
        ),
    },
}
