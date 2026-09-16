"""Reading HEALPix sky maps from FITS and persisting them compactly.

Archive FITS files carry unit and ordering conventions in their headers that differ between
WMAP and Planck. Everything here normalises those differences away so the rest of the
pipeline only ever sees RING-ordered float64 arrays.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import healpy as hp
import numpy as np
from astropy.io import fits

#: HEALPix sentinel for a masked/invalid pixel.
UNSEEN = hp.UNSEEN

#: Anything more negative than this is treated as UNSEEN. Guards against float32 rounding
#: of the sentinel value, which bites when reading Planck maps stored as single precision.
_BAD_THRESHOLD = -1.0e30


@dataclass(slots=True)
class FitsInspection:
    """What a FITS file claims about itself, before we trust any of it."""

    path: Path
    n_hdus: int
    nside: int | None
    ordering: str | None
    coord_system: str | None
    n_columns: int
    column_names: list[str] = field(default_factory=list)
    column_units: list[str] = field(default_factory=list)
    header: dict[str, Any] = field(default_factory=dict)

    @property
    def npix(self) -> int | None:
        return hp.nside2npix(self.nside) if self.nside else None


def inspect_fits(path: str | Path) -> FitsInspection:
    """Read FITS metadata without loading pixel data.

    Always do this before ingesting an unfamiliar product: it tells you the field layout,
    so you know whether field 0 is temperature or a hit-count map.
    """
    path = Path(path)
    with fits.open(path, memmap=True) as hdul:
        n_hdus = len(hdul)
        # HEALPix payload lives in the first binary table extension.
        bin_hdu = next(
            (h for h in hdul[1:] if isinstance(h, fits.BinTableHDU)),
            hdul[1] if n_hdus > 1 else hdul[0],
        )
        hdr = bin_hdu.header
        columns = getattr(bin_hdu, "columns", None)
        names = list(columns.names) if columns is not None else []
        units = [u or "" for u in (columns.units if columns is not None else [])]

        return FitsInspection(
            path=path,
            n_hdus=n_hdus,
            nside=hdr.get("NSIDE"),
            ordering=hdr.get("ORDERING"),
            coord_system=hdr.get("COORDSYS"),
            n_columns=len(names),
            column_names=names,
            column_units=units,
            header={k: hdr[k] for k in hdr if k not in ("COMMENT", "HISTORY")},
        )


def read_healpix_map(
    path: str | Path,
    field: int | tuple[int, ...] = 0,
    *,
    dtype: type = np.float64,
) -> np.ndarray:
    """Load a HEALPix map as a RING-ordered array with UNSEEN normalised.

    healpy reorders NESTED files to RING for us; we additionally coerce every flavour of
    "bad pixel" (NaN, huge negatives, float32-rounded sentinels) to a single UNSEEN value so
    downstream masking logic has exactly one case to handle.
    """
    sky = hp.read_map(str(path), field=field, dtype=dtype, nest=False)
    sky = np.atleast_2d(sky) if isinstance(field, tuple) else np.asarray(sky)

    bad = ~np.isfinite(sky) | (sky < _BAD_THRESHOLD)
    if bad.any():
        sky = sky.copy()
        sky[bad] = UNSEEN
    return sky


def save_npz_map(
    path: str | Path,
    sky: np.ndarray,
    *,
    nside: int | None = None,
    unit: str = "uK",
    coord_system: str = "G",
    metadata: dict[str, Any] | None = None,
) -> Path:
    """Persist a cleaned map compressed, with its physical metadata attached.

    We deliberately do not write FITS here: these are derived products, and npz round-trips
    faster and keeps arbitrary JSON-ish metadata alongside the array.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    nside = nside or hp.npix2nside(sky.size)

    np.savez_compressed(
        path,
        sky=sky.astype(np.float64, copy=False),
        nside=np.int64(nside),
        unit=unit,
        coord_system=coord_system,
        metadata=np.array(str(metadata or {})),
    )
    return path


def load_npz_map(path: str | Path) -> tuple[np.ndarray, dict[str, Any]]:
    """Inverse of :func:`save_npz_map`."""
    with np.load(path, allow_pickle=False) as data:
        sky = data["sky"]
        meta = {
            "nside": int(data["nside"]),
            "unit": str(data["unit"]),
            "coord_system": str(data["coord_system"]),
        }
    return sky, meta
