"""Large-angle isotropy anomaly models — the research contribution."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnomalyStatistic(StrEnum):
    #: Alignment of the quadrupole and octupole planes, the "Axis of Evil".
    QUAD_OCT_ALIGNMENT = "quad_oct_alignment"
    #: North/south power asymmetry, modelled as a dipole modulation of the temperature field.
    HEMISPHERICAL_ASYMMETRY = "hemispherical_asymmetry"
    #: The Eridanus supervoid direction cold region, found with SMHW wavelets.
    COLD_SPOT = "cold_spot"
    #: Deficit of power in C_2 relative to the LCDM prediction.
    LOW_QUADRUPOLE = "low_quadrupole"


class SimulationBatch(BaseModel):
    """A set of Gaussian isotropic realizations forming the null distribution."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    n_sims: int
    nside: int
    lmax: int
    theory_cl_id: UUID | None = None
    seed: int
    mask_slug: str | None = None
    storage_uri: str | None = None
    created_at: datetime | None = None


class AnomalyResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    map_artifact_id: UUID
    batch_id: UUID | None = None
    statistic: AnomalyStatistic
    observed_value: float
    sim_mean: float | None = None
    sim_std: float | None = None
    p_value: float | None = None
    #: p-value after look-elsewhere correction. This is the number that actually matters.
    p_value_corrected: float | None = None
    n_sims: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None

    @property
    def significance_sigma(self) -> float | None:
        """Two-tailed Gaussian-equivalent significance of the observed value."""
        if self.sim_mean is None or not self.sim_std:
            return None
        return abs(self.observed_value - self.sim_mean) / self.sim_std
