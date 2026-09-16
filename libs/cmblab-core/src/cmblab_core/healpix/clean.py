"""The cleaning pipeline: raw archive map -> analysis-ready temperature anisotropy map.

Order matters. The canonical sequence is:

    1. unit normalisation      K_CMB -> uK, so every downstream number is in uK or uK^2
    2. monopole + dipole fit   measured *before* removal, because those values are
                               validation gate G2 and must be recorded
    3. monopole + dipole removal
    4. mask application        Galactic plane and point sources -> UNSEEN
    5. optional degrading      high-resolution maps -> N_side 64 for Monte Carlo work

Fitting the dipole *after* masking the Galactic plane matters: synchrotron and dust
emission near the plane are far brighter than the 3.4 mK dipole and will bias the fit.
That is what ``gal_cut`` is for.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import healpy as hp
import numpy as np

from ..constants import (
    DIPOLE_AMPLITUDE_UK,
    DIPOLE_GALACTIC_LAT_DEG,
    DIPOLE_GALACTIC_LON_DEG,
)
from .io import UNSEEN

#: Multiplicative factor to convert a map's native unit into microkelvin.
_UNIT_TO_UK: dict[str, float] = {
    "k": 1.0e6,
    "k_cmb": 1.0e6,
    "kcmb": 1.0e6,
    "mk": 1.0e3,
    "mk_cmb": 1.0e3,
    "uk": 1.0,
    "uk_cmb": 1.0,
    "muk": 1.0,
    "ukcmb": 1.0,
    "microk": 1.0,
}


@dataclass(slots=True)
class DipoleFit:
    """Result of a joint monopole + dipole fit, in microkelvin."""

    monopole_uk: float
    amplitude_uk: float
    lon_deg: float
    lat_deg: float
    vector_uk: tuple[float, float, float]

    def angular_separation_from_cmb_dipole(self) -> float:
        """Great-circle angle, in degrees, between this fit and the published CMB dipole."""
        return _angular_separation(
            self.lon_deg, self.lat_deg, DIPOLE_GALACTIC_LON_DEG, DIPOLE_GALACTIC_LAT_DEG
        )

    def matches_cmb_dipole(self, amp_tol_uk: float = 150.0, angle_tol_deg: float = 5.0) -> bool:
        """Validation gate G2."""
        amp_ok = abs(self.amplitude_uk - DIPOLE_AMPLITUDE_UK) < amp_tol_uk
        return amp_ok and self.angular_separation_from_cmb_dipole() < angle_tol_deg


@dataclass(slots=True)
class MapStatistics:
    monopole_uk: float
    dipole_amp_uk: float
    dipole_lon_deg: float
    dipole_lat_deg: float
    mean_uk: float
    std_uk: float
    min_uk: float
    max_uk: float
    masked_fraction: float
    n_valid_pixels: int


@dataclass(slots=True)
class CleaningReport:
    """Everything that happened to a map, for the provenance record."""

    nside_in: int
    nside_out: int
    unit_in: str
    unit_out: str = "uK"
    ops: list[dict[str, Any]] = field(default_factory=list)
    dipole_fit: DipoleFit | None = None
    stats: MapStatistics | None = None

    def record(self, op: str, **params: Any) -> None:
        self.ops.append({"op": op, **params})

    def to_dict(self) -> dict[str, Any]:
        return {
            "nside_in": self.nside_in,
            "nside_out": self.nside_out,
            "unit_in": self.unit_in,
            "unit_out": self.unit_out,
            "ops": self.ops,
            "dipole_fit": asdict(self.dipole_fit) if self.dipole_fit else None,
            "stats": asdict(self.stats) if self.stats else None,
        }


# ----------------------------------------------------------------------------------
# primitives
# ----------------------------------------------------------------------------------


def _valid(sky: np.ndarray) -> np.ndarray:
    return sky != UNSEEN


def _angular_separation(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle separation in degrees between two (lon, lat) points."""
    p1, p2 = np.radians([lat1, lat2])
    dlon = np.radians(lon1 - lon2)
    cos_sep = np.sin(p1) * np.sin(p2) + np.cos(p1) * np.cos(p2) * np.cos(dlon)
    return float(np.degrees(np.arccos(np.clip(cos_sep, -1.0, 1.0))))


def to_microkelvin(sky: np.ndarray, unit: str) -> tuple[np.ndarray, float]:
    """Scale a map into microkelvin, preserving UNSEEN pixels.

    Raises on brightness units (MJy/sr) because converting those requires the channel
    bandpass, which is a per-frequency calibration problem, not a unit multiply.
    """
    key = unit.strip().lower().replace(" ", "").replace("-", "_")
    if key not in _UNIT_TO_UK:
        raise ValueError(
            f"Cannot convert unit {unit!r} to uK. Known units: {sorted(_UNIT_TO_UK)}. "
            "Brightness units such as MJy/sr need a bandpass-dependent conversion."
        )
    factor = _UNIT_TO_UK[key]
    if factor == 1.0:
        return sky.copy(), 1.0

    out = sky.copy()
    good = _valid(out)
    out[good] *= factor
    return out, factor


def fit_dipole(sky: np.ndarray, *, gal_cut_deg: float = 30.0) -> DipoleFit:
    """Fit monopole and dipole, excluding |b| < gal_cut_deg.

    The Galactic cut is not optional in practice — foreground emission in the plane is
    orders of magnitude brighter than the dipole and will drag the fit off-axis.
    """
    monopole, vector = hp.fit_dipole(sky, gal_cut=gal_cut_deg, bad=UNSEEN)
    vector = np.asarray(vector, dtype=np.float64)
    amplitude = float(np.linalg.norm(vector))
    lon, lat = hp.vec2ang(vector, lonlat=True)

    return DipoleFit(
        monopole_uk=float(monopole),
        amplitude_uk=amplitude,
        lon_deg=float(np.atleast_1d(lon)[0]),
        lat_deg=float(np.atleast_1d(lat)[0]),
        vector_uk=(float(vector[0]), float(vector[1]), float(vector[2])),
    )


def remove_monopole_dipole(sky: np.ndarray, *, gal_cut_deg: float = 30.0) -> np.ndarray:
    """Subtract the best-fit monopole and dipole, leaving the primordial anisotropies.

    The dipole is kinematic — our motion through the CMB rest frame — so it carries no
    primordial information and would otherwise swamp C_1 and leak into low multipoles.

    healpy returns a MaskedArray here. We flatten it back to a plain array with UNSEEN
    sentinels, because a masked array silently changes the meaning of ``sky != UNSEEN``
    everywhere downstream.
    """
    result = hp.remove_dipole(sky, gal_cut=gal_cut_deg, bad=UNSEEN, copy=True)
    if isinstance(result, np.ma.MaskedArray):
        result = result.filled(UNSEEN)
    return np.asarray(result, dtype=np.float64)


def apply_mask(sky: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Set pixels where ``mask == 0`` to UNSEEN.

    HEALPix convention: 1 = keep, 0 = reject. Masks are resampled to the map resolution
    with a conservative threshold so partially-masked coarse pixels are rejected.
    """
    if mask.size != sky.size:
        nside = hp.npix2nside(sky.size)
        mask = hp.ud_grade(mask.astype(np.float64), nside_out=nside)
        mask = (mask > 0.9).astype(np.float64)

    out = sky.copy()
    out[mask < 0.5] = UNSEEN
    return out


def degrade(sky: np.ndarray, nside_out: int) -> np.ndarray:
    """Reduce map resolution. Used to make Monte Carlo studies tractable.

    ``pess=True`` makes any output pixel containing a bad input pixel bad, which avoids
    smearing masked Galactic emission into clean regions.
    """
    nside_in = hp.npix2nside(sky.size)
    if nside_out == nside_in:
        return sky.copy()
    if nside_out > nside_in:
        raise ValueError(f"Refusing to upgrade {nside_in} -> {nside_out}: invents information")
    return hp.ud_grade(sky, nside_out=nside_out, pess=True, order_in="RING")


def compute_stats(sky: np.ndarray, *, gal_cut_deg: float = 30.0) -> MapStatistics:
    """Summary statistics over valid pixels only."""
    good = _valid(sky)
    values = sky[good]
    fit = fit_dipole(sky, gal_cut_deg=gal_cut_deg)

    return MapStatistics(
        monopole_uk=fit.monopole_uk,
        dipole_amp_uk=fit.amplitude_uk,
        dipole_lon_deg=fit.lon_deg,
        dipole_lat_deg=fit.lat_deg,
        mean_uk=float(values.mean()) if values.size else float("nan"),
        std_uk=float(values.std()) if values.size else float("nan"),
        min_uk=float(values.min()) if values.size else float("nan"),
        max_uk=float(values.max()) if values.size else float("nan"),
        masked_fraction=float(1.0 - good.sum() / sky.size),
        n_valid_pixels=int(good.sum()),
    )


# ----------------------------------------------------------------------------------
# orchestrator
# ----------------------------------------------------------------------------------


def clean_map(
    sky: np.ndarray,
    *,
    unit: str = "K_CMB",
    mask: np.ndarray | None = None,
    remove_dipole: bool = True,
    gal_cut_deg: float = 30.0,
    nside_out: int | None = None,
) -> tuple[np.ndarray, CleaningReport]:
    """Run the full cleaning sequence and return the map plus a provenance report.

    This is the single entry point the ingest worker calls. Step 5 of the build plan.
    """
    nside_in = hp.npix2nside(sky.size)
    report = CleaningReport(nside_in=nside_in, nside_out=nside_in, unit_in=unit)

    out, factor = to_microkelvin(sky, unit)
    report.record("to_microkelvin", unit_in=unit, factor=factor)

    # Measure before removing — these values are the validation gate.
    fit = fit_dipole(out, gal_cut_deg=gal_cut_deg)
    report.dipole_fit = fit
    report.record(
        "fit_dipole",
        gal_cut_deg=gal_cut_deg,
        monopole_uk=fit.monopole_uk,
        amplitude_uk=fit.amplitude_uk,
        lon_deg=fit.lon_deg,
        lat_deg=fit.lat_deg,
        separation_from_published_deg=fit.angular_separation_from_cmb_dipole(),
    )

    if remove_dipole:
        out = remove_monopole_dipole(out, gal_cut_deg=gal_cut_deg)
        report.record("remove_monopole_dipole", gal_cut_deg=gal_cut_deg)

    if mask is not None:
        out = apply_mask(out, mask)
        report.record("apply_mask", masked_fraction=float(1.0 - _valid(out).sum() / out.size))

    if nside_out is not None and nside_out != nside_in:
        out = degrade(out, nside_out)
        report.nside_out = nside_out
        report.record("degrade", nside_in=nside_in, nside_out=nside_out)

    report.stats = compute_stats(out, gal_cut_deg=gal_cut_deg)
    return out, report
