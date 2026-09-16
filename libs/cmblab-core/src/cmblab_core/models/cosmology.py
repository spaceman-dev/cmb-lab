"""Cosmological theory and inference models."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CosmoParams(BaseModel):
    """Base six-parameter flat LCDM. Defaults are the Planck 2018 best fit."""

    H0: float = Field(default=67.36, ge=20.0, le=120.0, description="km/s/Mpc")
    ombh2: float = Field(default=0.02237, ge=0.005, le=0.1, description="Baryon density")
    omch2: float = Field(default=0.1200, ge=0.01, le=0.99, description="Cold dark matter density")
    tau: float = Field(default=0.0544, ge=0.01, le=0.4, description="Reionization optical depth")
    ns: float = Field(default=0.9649, ge=0.8, le=1.2, description="Scalar spectral index")
    As: float = Field(default=2.1e-9, gt=0, description="Scalar amplitude at k=0.05/Mpc")

    # Fixed by default; expose for extensions to LCDM.
    mnu: float = Field(default=0.06, ge=0.0, description="Sum of neutrino masses, eV")
    omk: float = Field(default=0.0, description="Curvature density")

    def cache_key(self) -> str:
        parts = (
            f"{self.H0:.6f}",
            f"{self.ombh2:.8f}",
            f"{self.omch2:.8f}",
            f"{self.tau:.6f}",
            f"{self.ns:.6f}",
            f"{self.As:.6e}",
            f"{self.mnu:.4f}",
            f"{self.omk:.6f}",
        )
        return "|".join(parts)


class DerivedParams(BaseModel):
    omega_m: float | None = None
    omega_lambda: float | None = None
    sigma8: float | None = None
    S8: float | None = None
    age_gyr: float | None = None
    z_star: float | None = None
    theta_star: float | None = None
    z_reion: float | None = None


class TheorySpectrum(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    params: CosmoParams
    lmax: int = 2500
    ell: list[int] = Field(default_factory=list)
    dl_tt_uk2: list[float] = Field(default_factory=list)
    dl_ee_uk2: list[float] = Field(default_factory=list)
    dl_te_uk2: list[float] = Field(default_factory=list)
    derived: DerivedParams | None = None
    created_at: datetime | None = None


class PosteriorSummary(BaseModel):
    param: str
    mean: float
    std: float
    median: float | None = None
    q16: float | None = None
    q84: float | None = None

    def format(self, precision: int = 4) -> str:
        return f"{self.mean:.{precision}f} +/- {self.std:.{precision}f}"


class InferenceRun(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    spectrum_result_id: UUID | None = None
    likelihood: str = "gaussian_bandpower"
    sampler: str = "emcee"
    free_params: list[str] = Field(default_factory=lambda: ["H0", "ombh2", "omch2", "ns"])
    n_walkers: int = 32
    n_steps: int = 2000
    burn_in: int | None = None
    acceptance_frac: float | None = None
    autocorr_time: float | None = None
    max_log_like: float | None = None
    chain_uri: str | None = None
    state: str = "pending"
    summaries: list[PosteriorSummary] = Field(default_factory=list)
    created_at: datetime | None = None
