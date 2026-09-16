"""Large-angle isotropy statistics — the four classic CMB "anomalies".

Standard cosmology assumes the universe is statistically isotropic: no direction is special.
The CMB largely agrees, but four features at large angular scales have resisted easy
explanation for two decades. Each is implemented here as a single number, so that a Monte
Carlo ensemble of isotropic skies can tell us how unusual it really is.

1. **Quadrupole-octupole alignment** ("Axis of Evil"). The l=2 and l=3 multipoles each have
   a preferred axis. In an isotropic universe those axes should be uncorrelated, so the
   angle between them is uniformly distributed in cos. They are observed to be close.

2. **Hemispherical power asymmetry.** One half of the sky appears to have more large-angle
   power than the other, which no isotropic model predicts.

3. **The Cold Spot.** An unusually cold, unusually large region in the southern sky,
   detected with spherical Mexican-hat wavelets.

4. **The low quadrupole.** C_2 is smaller than LCDM predicts.

The scientific content is not in measuring these numbers — it is in the null distribution.
A statistic chosen *because* it looked odd will always look odd; only simulations with a
look-elsewhere correction can say whether it means anything.
"""

from __future__ import annotations

from dataclasses import dataclass

import healpy as hp
import numpy as np
from cmblab_core.healpix import UNSEEN

#: HEALPix resolution of the coarse grid of candidate axes. Nside=8 gives 768 directions,
#: halved to 384 by the headless-axis symmetry below, then refined locally. The dispersion
#: is a smooth function of direction, so coarse-then-refine beats a single fine grid by an
#: order of magnitude at equal accuracy — which matters when every Monte Carlo realisation
#: repeats the identical search.
AXIS_GRID_NSIDE = 8

#: Angular radius of the local refinement pass, comfortably larger than the coarse spacing.
REFINE_RADIUS_DEG = 12.0
REFINE_STEPS = 7


@dataclass(slots=True)
class AxisResult:
    """A preferred direction on the sky, in Galactic coordinates."""

    lon_deg: float
    lat_deg: float
    value: float

    @property
    def vector(self) -> np.ndarray:
        return np.asarray(hp.ang2vec(self.lon_deg, self.lat_deg, lonlat=True))


def _axis_grid(nside: int = AXIS_GRID_NSIDE) -> tuple[np.ndarray, np.ndarray]:
    """Candidate axes covering the northern hemisphere only.

    An axis is headless: n and -n describe the same plane, and the angular momentum
    dispersion is identical for both. Searching the southern hemisphere as well would
    double the cost for exactly duplicated values.
    """
    npix = hp.nside2npix(nside)
    theta, phi = hp.pix2ang(nside, np.arange(npix))
    northern = theta <= np.pi / 2 + 1e-9
    return theta[northern], phi[northern]


def angular_separation(a: AxisResult, b: AxisResult) -> float:
    """Angle in degrees between two axes, folded to [0, 90].

    Axes are headless: n and -n describe the same axis, so an angle of 170 degrees is
    really an alignment of 10 degrees. Forgetting this fold is the classic way to get the
    alignment statistic wrong.
    """
    cosine = float(np.clip(abs(np.dot(a.vector, b.vector)), -1.0, 1.0))
    return float(np.degrees(np.arccos(cosine)))


def preferred_axis(
    alm: np.ndarray,
    ell: int,
    lmax: int,
    *,
    grid_nside: int = AXIS_GRID_NSIDE,
    refine: bool = True,
) -> AxisResult:
    """Axis maximising the angular momentum dispersion of multipole ``ell``.

    de Oliveira-Costa et al. (2004) define the preferred axis as the one maximising

        sum_m  m^2 |a_lm(n)|^2

    where a_lm(n) are the coefficients in a frame with z along n. A multipole whose power
    sits in high |m| modes is concentrated near the equator of that frame, so the axis
    picks out the plane in which the multipole lives.
    """
    m_values = np.arange(ell + 1)
    weights = m_values.astype(float) ** 2

    # Isolate this multipole: rotating a handful of coefficients is far cheaper than
    # rotating a full-resolution alm array once per candidate axis.
    indices = np.array([hp.Alm.getidx(lmax, ell, m) for m in m_values])
    isolated = np.zeros_like(alm)
    isolated[indices] = alm[indices]

    def dispersion(theta: float, phi: float) -> float:
        rotated = isolated.copy()
        # ZYZ Euler angles that carry (theta, phi) onto the north pole.
        hp.rotate_alm(rotated, 0.0, -theta, -phi)
        power = np.abs(rotated[indices]) ** 2
        # m != 0 coefficients each represent two modes (+m and -m).
        power[1:] *= 2.0
        return float(np.sum(weights * power))

    thetas, phis = _axis_grid(grid_nside)
    values = np.array([dispersion(t, p) for t, p in zip(thetas, phis, strict=True)])
    best = int(np.argmax(values))
    best_theta, best_phi, best_value = thetas[best], phis[best], values[best]

    if refine:
        radius = np.radians(REFINE_RADIUS_DEG)
        offsets = np.linspace(-radius, radius, REFINE_STEPS)
        for dtheta in offsets:
            for dphi in offsets:
                theta = np.clip(best_theta + dtheta, 0.0, np.pi)
                phi = (best_phi + dphi / max(np.sin(theta), 0.1)) % (2 * np.pi)
                value = dispersion(theta, phi)
                if value > best_value:
                    best_value, best_theta, best_phi = value, theta, phi

    return AxisResult(
        lon_deg=float(np.degrees(best_phi)),
        lat_deg=float(90.0 - np.degrees(best_theta)),
        value=float(best_value),
    )


def quadrupole_octupole_alignment(
    sky: np.ndarray, lmax: int = 8, *, grid_nside: int = AXIS_GRID_NSIDE
) -> dict[str, float]:
    """Angle between the l=2 and l=3 preferred axes.

    Under isotropy cos(angle) is uniform on [0, 1], so the expected angle is 60 degrees and
    small angles are rare. The observed CMB gives roughly 10 degrees.
    """
    clean = np.where(sky == UNSEEN, 0.0, sky)
    alm = hp.map2alm(clean, lmax=lmax, iter=1, use_pixel_weights=False)

    quad = preferred_axis(alm, 2, lmax, grid_nside=grid_nside)
    oct_ = preferred_axis(alm, 3, lmax, grid_nside=grid_nside)
    angle = angular_separation(quad, oct_)

    return {
        "angle_deg": angle,
        "cos_angle": float(np.cos(np.radians(angle))),
        "quad_lon": quad.lon_deg,
        "quad_lat": quad.lat_deg,
        "oct_lon": oct_.lon_deg,
        "oct_lat": oct_.lat_deg,
    }


def hemispherical_asymmetry(
    sky: np.ndarray,
    *,
    lmax: int = 64,
    grid_nside: int = AXIS_GRID_NSIDE,
    mask: np.ndarray | None = None,
) -> dict[str, float]:
    """Largest fractional power difference between opposing hemispheres.

        A(n) = (P_north(n) - P_south(n)) / (P_north(n) + P_south(n))

    maximised over axes n, using only multipoles up to ``lmax``. Restricting to large
    scales matters: the reported asymmetry is a low-multipole phenomenon and including
    small scales dilutes it into noise.
    """
    nside = hp.npix2nside(sky.size)
    clean = np.where(sky == UNSEEN, 0.0, sky)

    # Low-pass filter so the statistic measures large-angle power only.
    alm = hp.map2alm(clean, lmax=lmax, iter=1, use_pixel_weights=False)
    filtered = hp.alm2map(alm, nside, lmax=lmax)

    valid = np.ones(sky.size, dtype=bool)
    if mask is not None:
        valid &= mask > 0.5
    valid &= sky != UNSEEN

    pixel_vectors = np.asarray(hp.pix2vec(nside, np.arange(sky.size)))
    squared = filtered**2

    # Full sphere here: unlike the axis statistics, swapping n for -n flips the sign of the
    # asymmetry, so both hemispheres have to be searched to find the maximum.
    npix_grid = hp.nside2npix(grid_nside)
    thetas, phis = hp.pix2ang(grid_nside, np.arange(npix_grid))
    best_value = -np.inf
    best_lon = best_lat = 0.0

    for theta, phi in zip(thetas, phis, strict=True):
        axis = hp.ang2vec(theta, phi)
        north = (pixel_vectors.T @ axis) > 0

        north_sel = north & valid
        south_sel = (~north) & valid
        if north_sel.sum() < 100 or south_sel.sum() < 100:
            continue

        p_north = float(squared[north_sel].mean())
        p_south = float(squared[south_sel].mean())
        total = p_north + p_south
        if total <= 0:
            continue

        asymmetry = (p_north - p_south) / total
        if asymmetry > best_value:
            best_value = asymmetry
            best_lon = float(np.degrees(phi))
            best_lat = float(90.0 - np.degrees(theta))

    return {
        "asymmetry": float(best_value),
        "axis_lon": best_lon,
        "axis_lat": best_lat,
        "lmax": float(lmax),
    }


def smhw_window(ell: np.ndarray, scale_deg: float) -> np.ndarray:
    """Spherical Mexican-hat wavelet window function.

    The Mexican hat is the Laplacian of a Gaussian, which in harmonic space is

        W_l  proportional to  x exp(-x/2),   x = l(l+1) R^2

    It is a compensated filter: it has zero response to a constant offset, so it isolates
    localised features from the large-scale background. That is exactly what you want when
    hunting for an anomalous cold region rather than an overall temperature shift.
    """
    radius = np.radians(scale_deg)
    x = ell * (ell + 1.0) * radius**2
    window = x * np.exp(-0.5 * x)
    peak = window.max()
    return window / peak if peak > 0 else window


def cold_spot(
    sky: np.ndarray,
    *,
    scale_deg: float = 5.0,
    lmax: int = 128,
    mask: np.ndarray | None = None,
) -> dict[str, float]:
    """Most extreme negative excursion after Mexican-hat wavelet filtering.

    The statistic is the minimum of the filtered map in units of its own standard
    deviation, so it is dimensionless and comparable across simulations.
    """
    nside = hp.npix2nside(sky.size)
    clean = np.where(sky == UNSEEN, 0.0, sky)

    alm = hp.map2alm(clean, lmax=lmax, iter=1, use_pixel_weights=False)
    ell = np.arange(lmax + 1)
    filtered_alm = hp.almxfl(alm, smhw_window(ell, scale_deg))
    filtered = hp.alm2map(filtered_alm, nside, lmax=lmax)

    valid = np.ones(sky.size, dtype=bool)
    if mask is not None:
        valid &= mask > 0.5
    valid &= sky != UNSEEN

    # Exclude a Galactic band: wavelet filtering rings around the sharp mask edge and would
    # otherwise manufacture spurious extrema near the cut.
    _, lat = hp.pix2ang(nside, np.arange(sky.size), lonlat=True)
    valid &= np.abs(lat) > 15.0

    values = filtered[valid]
    if values.size < 100:
        return {"coldest_sigma": float("nan"), "lon": 0.0, "lat": 0.0, "scale_deg": scale_deg}

    sigma = float(values.std())
    if sigma <= 0:
        return {"coldest_sigma": float("nan"), "lon": 0.0, "lat": 0.0, "scale_deg": scale_deg}

    normalised = values / sigma
    coldest = float(normalised.min())

    pixel_index = np.arange(sky.size)[valid][int(np.argmin(normalised))]
    lon, lat_deg = hp.pix2ang(nside, int(pixel_index), lonlat=True)

    return {
        "coldest_sigma": coldest,
        "lon": float(lon),
        "lat": float(lat_deg),
        "scale_deg": scale_deg,
    }


def low_quadrupole(sky: np.ndarray, *, mask: np.ndarray | None = None) -> dict[str, float]:
    """Quadrupole power D_2 = 6 C_2 / 2pi, in uK^2.

    Corrected for the sky fraction. With only five independent modes the quadrupole is
    intrinsically noisy, which is precisely why its low value is so hard to interpret.
    """
    clean = np.where(sky == UNSEEN, 0.0, sky)

    f_sky = 1.0
    if mask is not None:
        clean = clean * (mask > 0.5)
        f_sky = float(np.mean((mask > 0.5) ** 2))

    alm = hp.map2alm(clean, lmax=8, iter=1, use_pixel_weights=False)
    cl = hp.alm2cl(alm)

    c2 = float(cl[2] / f_sky) if f_sky > 0 else float("nan")
    c3 = float(cl[3] / f_sky) if f_sky > 0 else float("nan")

    return {
        "c2_uk2": c2,
        "d2_uk2": 2 * 3 * c2 / (2 * np.pi),
        "c3_uk2": c3,
        "d3_uk2": 3 * 4 * c3 / (2 * np.pi),
    }


#: Registry mapping statistic name -> (function, key of the scalar used for p-values,
#: whether small values are the anomaly).
STATISTICS: dict[str, tuple] = {
    "quad_oct_alignment": (quadrupole_octupole_alignment, "angle_deg", True),
    "hemispherical_asymmetry": (hemispherical_asymmetry, "asymmetry", False),
    "cold_spot": (cold_spot, "coldest_sigma", True),
    "low_quadrupole": (low_quadrupole, "d2_uk2", True),
}
