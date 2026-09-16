"""Spectrum service: angular power spectrum estimation and validation."""

from .binning import bin_spectrum, make_edges
from .compare import ComparisonResult, compare_to_reference
from .estimator import PowerSpectrum, beam_window, cosmic_variance_error, estimate_spectrum
from .pipeline import SpectrumRun, run_spectrum, save_bandpowers
from .references import ReferenceSpectrum, available_references, load_reference

__all__ = [
    "ComparisonResult",
    "PowerSpectrum",
    "ReferenceSpectrum",
    "SpectrumRun",
    "available_references",
    "beam_window",
    "bin_spectrum",
    "compare_to_reference",
    "cosmic_variance_error",
    "estimate_spectrum",
    "load_reference",
    "make_edges",
    "run_spectrum",
    "save_bandpowers",
]
