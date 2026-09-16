"""Angular power spectrum domain models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SpectrumMethod(StrEnum):
    #: Pseudo-C_l with a simple 1/f_sky correction. Fast, approximate, good for a first look.
    ANAFAST_FSKY = "anafast_fsky"
    #: Full MASTER mode-coupling deconvolution via NaMaster. Correct for masked skies.
    MASTER = "master"


class Bandpower(BaseModel):
    """One binned point of the power spectrum.

    D_l = l(l+1)C_l / 2pi, in uK^2 — the convention every CMB paper plots.
    """

    ell_min: int
    ell_max: int
    ell_eff: float
    dl_uk2: float
    dl_err_uk2: float | None = None


class SpectrumResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    map_artifact_id: UUID
    mask_product_id: UUID | None = None
    beam_product_id: UUID | None = None
    method: SpectrumMethod
    lmax: int
    binning: str = "linear:30"
    f_sky: float | None = None
    beam_corrected: bool = False
    pixwin_corrected: bool = False

    # Gate G3
    peak1_ell: int | None = None
    peak1_dl_uk2: float | None = None

    # Gate G4
    chi2_vs_published: float | None = None
    dof: int | None = None

    bandpowers: list[Bandpower] = Field(default_factory=list)
    storage_uri: str | None = None
    created_at: datetime | None = None

    @property
    def chi2_per_dof(self) -> float | None:
        if self.chi2_vs_published is None or not self.dof:
            return None
        return self.chi2_vs_published / self.dof


class SpectrumComparison(BaseModel):
    """Our bandpowers against a published reference spectrum."""

    result_id: UUID
    reference_slug: str
    ell_eff: list[float]
    ours_dl: list[float]
    ours_err: list[float]
    reference_dl: list[float]
    residual: list[float]
    residual_sigma: list[float]
    chi2: float
    dof: int

    @property
    def chi2_per_dof(self) -> float:
        return self.chi2 / self.dof if self.dof else float("nan")
