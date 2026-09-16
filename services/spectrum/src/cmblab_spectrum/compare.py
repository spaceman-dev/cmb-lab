"""Compare an estimated spectrum against a published one — validation gate G4."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from cmblab_core.models import Bandpower

from .references import ReferenceSpectrum


@dataclass(slots=True)
class ComparisonResult:
    reference_slug: str
    ell_eff: np.ndarray
    ours_dl: np.ndarray
    ours_err: np.ndarray
    reference_dl: np.ndarray
    residual: np.ndarray
    residual_sigma: np.ndarray
    chi2: float
    dof: int
    n_compared: int

    @property
    def chi2_per_dof(self) -> float:
        return self.chi2 / self.dof if self.dof else float("nan")

    @property
    def passes_gate_g4(self) -> bool:
        """A chi2/dof anywhere near 1 means the pipeline reproduces the published result."""
        return 0.3 <= self.chi2_per_dof <= 3.0

    def summary(self) -> str:
        return (
            f"vs {self.reference_slug}: chi2/dof = {self.chi2_per_dof:.2f} "
            f"({self.chi2:.1f} / {self.dof}) over {self.n_compared} bandpowers  "
            f"[{'PASS' if self.passes_gate_g4 else 'FAIL'}]"
        )


def compare_to_reference(
    bandpowers: list[Bandpower],
    reference: ReferenceSpectrum,
    *,
    ell_min: int = 2,
    ell_max: int | None = None,
) -> ComparisonResult:
    """Interpolate the reference onto our bandpower centres and compute chi-squared.

    Errors are combined in quadrature from both sides. Bandpowers without an error estimate,
    or outside the reference's multipole coverage, are dropped rather than guessed at.
    """
    ell_eff = np.array([b.ell_eff for b in bandpowers])
    ours = np.array([b.dl_uk2 for b in bandpowers])
    ours_err = np.array([b.dl_err_uk2 if b.dl_err_uk2 else np.nan for b in bandpowers])

    reference_dl = reference.interpolate(ell_eff)
    reference_err = np.interp(ell_eff, reference.ell, reference.err, left=np.nan, right=np.nan)

    upper = ell_max if ell_max is not None else np.inf
    usable = (
        np.isfinite(reference_dl)
        & np.isfinite(ours_err)
        & np.isfinite(reference_err)
        & (ell_eff >= ell_min)
        & (ell_eff <= upper)
        & (ours_err > 0)
    )

    ell_eff, ours, ours_err = ell_eff[usable], ours[usable], ours_err[usable]
    reference_dl, reference_err = reference_dl[usable], reference_err[usable]

    combined_err = np.sqrt(ours_err**2 + reference_err**2)
    residual = ours - reference_dl
    residual_sigma = residual / combined_err

    chi2 = float(np.sum(residual_sigma**2))
    n = int(usable.sum())

    return ComparisonResult(
        reference_slug=reference.slug,
        ell_eff=ell_eff,
        ours_dl=ours,
        ours_err=ours_err,
        reference_dl=reference_dl,
        residual=residual,
        residual_sigma=residual_sigma,
        chi2=chi2,
        dof=max(n - 1, 1),
        n_compared=n,
    )
