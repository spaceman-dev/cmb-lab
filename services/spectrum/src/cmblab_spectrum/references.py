"""Loaders for published reference power spectra.

The two archives use different column layouts, both documented only in file headers. These
loaders encode those layouts once so nothing downstream has to care.

WMAP 9-year binned TT (7 columns)
    0 mean l   1 l_min   2 l_max   3 D_l   4 total error   5 measurement error
    6 cosmic variance

Planck 2018 binned TT (5 columns)
    0 l   1 D_l   2 -dD_l   3 +dD_l   4 best-fit LCDM
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from cmblab_core.config import get_settings


@dataclass(slots=True)
class ReferenceSpectrum:
    slug: str
    mission: str
    ell: np.ndarray
    dl: np.ndarray
    err_lo: np.ndarray
    err_hi: np.ndarray
    ell_min: np.ndarray | None = None
    ell_max: np.ndarray | None = None
    best_fit: np.ndarray | None = None
    reference: str = ""

    @property
    def err(self) -> np.ndarray:
        return 0.5 * (self.err_lo + self.err_hi)

    def first_peak(self, search_min: int = 100, search_max: int = 350) -> tuple[float, float]:
        window = (self.ell >= search_min) & (self.ell <= search_max)
        index = int(np.argmax(self.dl[window]))
        return float(self.ell[window][index]), float(self.dl[window][index])

    def interpolate(self, target_ell: np.ndarray) -> np.ndarray:
        return np.interp(target_ell, self.ell, self.dl, left=np.nan, right=np.nan)


def load_wmap9_binned(path: str | Path) -> ReferenceSpectrum:
    data = np.loadtxt(path, comments="#")
    return ReferenceSpectrum(
        slug="wmap9-TT-binned",
        mission="WMAP",
        ell=data[:, 0],
        ell_min=data[:, 1],
        ell_max=data[:, 2],
        dl=data[:, 3],
        err_lo=data[:, 4],
        err_hi=data[:, 4],
        reference="2013ApJS..208...19H",
    )


def load_planck18_binned(path: str | Path) -> ReferenceSpectrum:
    data = np.loadtxt(path, comments="#")
    return ReferenceSpectrum(
        slug="planck18-TT-binned",
        mission="Planck",
        ell=data[:, 0],
        dl=data[:, 1],
        err_lo=data[:, 2],
        err_hi=data[:, 3],
        best_fit=data[:, 4] if data.shape[1] > 4 else None,
        reference="2020A&A...641A...6P",
    )


#: slug -> (relative path under data/raw, loader)
REFERENCES: dict[str, tuple[str, str]] = {
    "wmap9-TT-binned": ("wmap9/wmap_binned_tt_spectrum_9yr_v5.txt", "wmap9"),
    "planck18-TT-binned": ("planck-pr3/COM_PowerSpect_CMB-TT-binned_R3.01.txt", "planck18"),
}

_LOADERS = {"wmap9": load_wmap9_binned, "planck18": load_planck18_binned}


def load_reference(slug: str) -> ReferenceSpectrum:
    if slug not in REFERENCES:
        raise KeyError(f"Unknown reference {slug!r}. Known: {sorted(REFERENCES)}")

    relative, loader_key = REFERENCES[slug]
    path = Path(get_settings().data_dir) / "raw" / relative
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `make data-bootstrap` to download reference spectra."
        )
    return _LOADERS[loader_key](path)


def available_references() -> list[str]:
    return sorted(REFERENCES)
