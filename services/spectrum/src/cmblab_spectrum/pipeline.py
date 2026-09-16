"""Orchestration for the spectrum service: cleaned map in, validated bandpowers out."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from cmblab_core.config import get_settings
from cmblab_core.constants import ACOUSTIC_PEAKS
from cmblab_core.healpix import load_npz_map
from cmblab_core.models import Bandpower

from .beams import load_beam
from .binning import bin_spectrum
from .compare import ComparisonResult, compare_to_reference
from .estimator import PowerSpectrum, estimate_cross_spectrum, estimate_spectrum
from .pointsources import PointSourceFit, fit_against_theory, subtract
from .references import load_reference


@dataclass(slots=True)
class SpectrumRun:
    map_label: str
    spectrum: PowerSpectrum
    bandpowers: list[Bandpower]
    peak1_ell: int
    peak1_dl: float
    gate_g3_passed: bool
    gate_g3_detail: str
    comparisons: dict[str, ComparisonResult] = field(default_factory=dict)
    point_source_fit: PointSourceFit | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "map_label": self.map_label,
            "f_sky": self.spectrum.f_sky,
            "lmax": self.spectrum.lmax,
            "reliable_lmax": self.spectrum.reliable_lmax,
            "beam_corrected": self.spectrum.beam_corrected,
            "pixwin_corrected": self.spectrum.pixwin_corrected,
            "peak1_ell": self.peak1_ell,
            "peak1_dl_uk2": self.peak1_dl,
            "gate_g3_passed": self.gate_g3_passed,
            "gate_g3_detail": self.gate_g3_detail,
            "bandpowers": [b.model_dump() for b in self.bandpowers],
            "comparisons": {
                slug: {
                    "chi2": c.chi2,
                    "dof": c.dof,
                    "chi2_per_dof": c.chi2_per_dof,
                    "n_compared": c.n_compared,
                    "passed": c.passes_gate_g4,
                }
                for slug, c in self.comparisons.items()
            },
        }


def _clean_path(dataset_slug: str, product_slug: str) -> Path:
    return Path(get_settings().data_dir) / "clean" / dataset_slug / f"{product_slug}.npz"


def _check_gate_g3(peak_ell: int, peak_dl: float) -> tuple[bool, str]:
    """The first acoustic peak must sit at l ~ 220 with D_l ~ 5750 uK^2."""
    expected = ACOUSTIC_PEAKS[1]
    ell_ok = abs(peak_ell - expected["ell"]) <= expected["ell_tol"]
    dl_ok = abs(peak_dl - expected["dl_uk2"]) <= expected["dl_tol"]

    detail = (
        f"first peak at l={peak_ell} (expected {expected['ell']:.0f}"
        f"+/-{expected['ell_tol']:.0f}), "
        f"D_l={peak_dl:.0f} uK^2 (expected {expected['dl_uk2']:.0f}"
        f"+/-{expected['dl_tol']:.0f})"
    )
    return ell_ok and dl_ok, detail


def run_spectrum(
    dataset_slug: str,
    product_slug: str,
    *,
    mask_dataset: str | None = None,
    mask_product: str | None = None,
    lmax: int = 600,
    beam_fwhm_arcmin: float | None = None,
    binning: str = "linear:30",
    compare_with: tuple[str, ...] = ("wmap9-TT-binned", "planck18-TT-binned"),
    apply_pixwin: bool = True,
) -> SpectrumRun:
    """Estimate, bin, and validate the power spectrum of an already-cleaned map."""
    map_path = _clean_path(dataset_slug, product_slug)
    if not map_path.exists():
        raise FileNotFoundError(
            f"{map_path} not found. Run `cmblab-ingest fetch {dataset_slug} {product_slug}` first."
        )

    sky, _ = load_npz_map(map_path)

    mask = None
    if mask_dataset and mask_product:
        mask_path = _clean_path(mask_dataset, mask_product)
        if not mask_path.exists():
            raise FileNotFoundError(f"{mask_path} not found. Ingest the mask first.")
        mask, _ = load_npz_map(mask_path)

    spectrum = estimate_spectrum(
        sky,
        mask=mask,
        lmax=lmax,
        beam_fwhm_arcmin=beam_fwhm_arcmin,
        apply_pixwin=apply_pixwin,
    )

    bandpowers = bin_spectrum(
        spectrum, scheme=binning, lmin=2, lmax=min(lmax, spectrum.reliable_lmax)
    )

    peak_ell, peak_dl = spectrum.first_peak()
    passed, detail = _check_gate_g3(peak_ell, peak_dl)

    run = SpectrumRun(
        map_label=f"{dataset_slug}/{product_slug}",
        spectrum=spectrum,
        bandpowers=bandpowers,
        peak1_ell=peak_ell,
        peak1_dl=peak_dl,
        gate_g3_passed=passed,
        gate_g3_detail=detail,
    )

    for slug in compare_with:
        try:
            reference = load_reference(slug)
        except (FileNotFoundError, KeyError):
            continue
        run.comparisons[slug] = compare_to_reference(
            bandpowers, reference, ell_max=spectrum.reliable_lmax
        )

    return run


def save_bandpowers(run: SpectrumRun, path: str | Path) -> Path:
    """Persist bandpowers as a compressed archive for the API layer to serve."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        ell_eff=np.array([b.ell_eff for b in run.bandpowers]),
        ell_min=np.array([b.ell_min for b in run.bandpowers]),
        ell_max=np.array([b.ell_max for b in run.bandpowers]),
        dl=np.array([b.dl_uk2 for b in run.bandpowers]),
        dl_err=np.array([b.dl_err_uk2 or 0.0 for b in run.bandpowers]),
        f_sky=run.spectrum.f_sky,
        peak1_ell=run.peak1_ell,
        peak1_dl=run.peak1_dl,
    )
    return path


def _theory_cl(ell: np.ndarray, reference_slug: str = "planck18-TT-binned") -> np.ndarray:
    """Interpolate a reference best-fit LCDM curve onto integer multipoles, as C_l."""
    reference = load_reference(reference_slug)
    if reference.best_fit is None:
        raise ValueError(f"{reference_slug} carries no best-fit column")

    dl = np.interp(ell, reference.ell, reference.best_fit, left=np.nan, right=np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        cl = 2.0 * np.pi * dl / (ell * (ell + 1.0))
    cl[~np.isfinite(cl)] = np.nan
    return cl


def _apply_point_source_correction(
    spectrum: PowerSpectrum, ell_min: int, ell_max: int
) -> PointSourceFit:
    """Fit and remove the flat unresolved-source component, in place."""
    theory = _theory_cl(spectrum.ell)
    fit = fit_against_theory(
        spectrum.ell,
        spectrum.cl,
        theory,
        spectrum.variance(),
        ell_min=ell_min,
        ell_max=ell_max,
    )
    spectrum.cl = subtract(spectrum.cl, fit)
    spectrum.dl = spectrum.ell * (spectrum.ell + 1.0) * spectrum.cl / (2.0 * np.pi)
    return fit


def run_cross_spectrum(
    dataset_slug: str,
    product_a: str,
    product_b: str,
    *,
    mask_dataset: str | None = None,
    mask_product: str | None = None,
    lmax: int = 800,
    binning: str = "linear:30",
    compare_with: tuple[str, ...] = ("wmap9-TT-binned", "planck18-TT-binned"),
    apply_pixwin: bool = True,
    subtract_point_sources: bool = True,
    ps_fit_range: tuple[int, int] = (500, 800),
) -> SpectrumRun:
    """Cross-spectrum between two independently-noised maps. The unbiased estimator.

    Beam transfer functions are resolved automatically from each product's registered
    ``beam_product``, so the archive's measured beams are used rather than a Gaussian
    approximation.

    ``subtract_point_sources`` removes the flat C_l contribution of unresolved
    extragalactic sources. Cross-spectra cancel detector noise but not real sky signal, and
    at V band that residual dominates the error budget above l ~ 350.
    """
    from cmblab_ingest.registry import get_product

    sky_a, _ = load_npz_map(_require(_clean_path(dataset_slug, product_a), dataset_slug, product_a))
    sky_b, _ = load_npz_map(_require(_clean_path(dataset_slug, product_b), dataset_slug, product_b))

    mask = None
    if mask_dataset and mask_product:
        mask, _ = load_npz_map(
            _require(_clean_path(mask_dataset, mask_product), mask_dataset, mask_product)
        )

    bl_a = bl_b = None
    beam_labels = []
    for product_slug, setter in ((product_a, "a"), (product_b, "b")):
        spec = get_product(dataset_slug, product_slug)
        if not spec.beam_product:
            continue
        beam = load_beam(dataset_slug, spec.beam_product)
        beam_labels.append(f"{spec.beam_product} (FWHM~{beam.effective_fwhm_arcmin():.1f}')")
        if setter == "a":
            bl_a = beam.at(lmax)
        else:
            bl_b = beam.at(lmax)

    spectrum = estimate_cross_spectrum(
        sky_a,
        sky_b,
        mask=mask,
        lmax=lmax,
        bl_a=bl_a,
        bl_b=bl_b,
        apply_pixwin=apply_pixwin,
    )
    spectrum.meta["beams"] = beam_labels

    point_source_fit = None
    if subtract_point_sources:
        try:
            point_source_fit = _apply_point_source_correction(spectrum, *ps_fit_range)
        except (FileNotFoundError, KeyError, ValueError):
            point_source_fit = None

    bandpowers = bin_spectrum(
        spectrum, scheme=binning, lmin=2, lmax=min(lmax, spectrum.usable_lmax)
    )

    peak_ell, peak_dl = spectrum.first_peak()
    passed, detail = _check_gate_g3(peak_ell, peak_dl)

    run = SpectrumRun(
        map_label=f"{dataset_slug}/{product_a} x {product_b}",
        spectrum=spectrum,
        bandpowers=bandpowers,
        peak1_ell=peak_ell,
        peak1_dl=peak_dl,
        gate_g3_passed=passed,
        gate_g3_detail=detail,
        point_source_fit=point_source_fit,
    )

    for slug in compare_with:
        try:
            reference = load_reference(slug)
        except (FileNotFoundError, KeyError):
            continue
        run.comparisons[slug] = compare_to_reference(
            bandpowers, reference, ell_max=spectrum.usable_lmax
        )

    return run


def _require(path: Path, dataset_slug: str, product_slug: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `cmblab-ingest fetch {dataset_slug} {product_slug}` first."
        )
    return path
