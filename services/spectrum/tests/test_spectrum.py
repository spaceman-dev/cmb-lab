"""Validation gates for power spectrum estimation.

The synthetic tests prove the estimator is unbiased on data whose answer we know exactly.
The real-data tests (marked ``slow``) prove the whole pipeline reproduces published CMB
results, and are skipped when the archive files have not been downloaded.
"""

from __future__ import annotations

from pathlib import Path

import healpy as hp
import numpy as np
import pytest
from cmblab_core.config import get_settings
from cmblab_core.constants import ACOUSTIC_PEAKS
from cmblab_spectrum.binning import make_edges
from cmblab_spectrum.estimator import estimate_cross_spectrum, estimate_spectrum
from cmblab_spectrum.pointsources import fit_against_theory, subtract

NSIDE = 128
LMAX = 256


def toy_cl(lmax: int = LMAX) -> np.ndarray:
    """A smooth, positive spectrum with a bump — enough structure to be a real test."""
    ell = np.arange(lmax + 1, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        base = 1000.0 * 2.0 * np.pi / np.maximum(ell * (ell + 1.0), 1.0)
    base[:2] = 0.0
    bump = 1.0 + 1.5 * np.exp(-(((ell - 120.0) / 40.0) ** 2))
    return base * bump


def galactic_mask(nside: int, cut_deg: float = 20.0) -> np.ndarray:
    _, lat = hp.pix2ang(nside, np.arange(hp.nside2npix(nside)), lonlat=True)
    return (np.abs(lat) > cut_deg).astype(np.float64)


# ------------------------------------------------------------------ binning


def test_linear_edges_have_requested_width():
    edges = make_edges("linear:30", 2, 300)
    assert np.all(np.diff(edges) == 30)


def test_log_edges_increase_monotonically():
    edges = make_edges("log:10", 2, 1000)
    assert np.all(np.diff(edges) > 0)


def test_unknown_scheme_is_rejected():
    with pytest.raises(ValueError, match="Unknown binning scheme"):
        make_edges("fibonacci", 2, 100)


# ------------------------------------------------- estimator on a known sky


@pytest.mark.physics
def test_full_sky_estimate_recovers_input_spectrum():
    """With no mask and no beam, the estimator must be unbiased."""
    cl_in = toy_cl()
    sky = hp.synfast(cl_in, NSIDE, lmax=LMAX, pixwin=False, new=True)

    result = estimate_spectrum(sky, lmax=LMAX, apply_pixwin=False)

    band = (result.ell >= 30) & (result.ell <= 200)
    ratio = np.mean(result.cl[band] / cl_in[band])
    assert ratio == pytest.approx(1.0, abs=0.15)


@pytest.mark.physics
def test_fsky_correction_restores_masked_power():
    """Masking removes power; dividing by w2 must put the amplitude back."""
    cl_in = toy_cl()
    sky = hp.synfast(cl_in, NSIDE, lmax=LMAX, pixwin=False, new=True)
    mask = galactic_mask(NSIDE)

    result = estimate_spectrum(sky, mask=mask, lmax=LMAX, apply_pixwin=False)
    assert result.f_sky < 0.8

    band = (result.ell >= 40) & (result.ell <= 200)
    ratio = np.mean(result.cl[band] / cl_in[band])
    assert ratio == pytest.approx(1.0, abs=0.2)


@pytest.mark.physics
def test_beam_deconvolution_undoes_smoothing():
    cl_in = toy_cl()
    fwhm_arcmin = 40.0
    sky = hp.synfast(cl_in, NSIDE, lmax=LMAX, fwhm=np.radians(fwhm_arcmin / 60.0), new=True)

    uncorrected = estimate_spectrum(sky, lmax=LMAX, apply_pixwin=False)
    corrected = estimate_spectrum(sky, lmax=LMAX, beam_fwhm_arcmin=fwhm_arcmin, apply_pixwin=False)

    band = (corrected.ell >= 60) & (corrected.ell <= 200)
    # Smoothing suppresses power, so the corrected estimate must be larger and closer to truth.
    assert np.mean(corrected.cl[band]) > np.mean(uncorrected.cl[band])
    assert np.mean(corrected.cl[band] / cl_in[band]) == pytest.approx(1.0, abs=0.2)


# --------------------------------------------- the point of cross-spectra


@pytest.mark.physics
def test_auto_spectrum_is_biased_by_noise():
    """Demonstrates the problem cross-spectra exist to solve."""
    cl_in = toy_cl()
    signal = hp.synfast(cl_in, NSIDE, lmax=LMAX, pixwin=False, new=True)
    rng = np.random.default_rng(7)
    noise_rms = 60.0

    noisy = signal + rng.normal(0, noise_rms, signal.size)
    result = estimate_spectrum(noisy, lmax=LMAX, apply_pixwin=False)

    band = (result.ell >= 150) & (result.ell <= 240)
    # The noise floor lifts the auto-spectrum well above the truth at high l.
    assert np.mean(result.cl[band] / cl_in[band]) > 1.5


@pytest.mark.physics
def test_cross_spectrum_cancels_independent_noise():
    """Two maps of one sky with independent noise give an unbiased cross-spectrum."""
    cl_in = toy_cl()
    signal = hp.synfast(cl_in, NSIDE, lmax=LMAX, pixwin=False, new=True)
    rng = np.random.default_rng(11)
    noise_rms = 60.0

    map_a = signal + rng.normal(0, noise_rms, signal.size)
    map_b = signal + rng.normal(0, noise_rms, signal.size)

    result = estimate_cross_spectrum(map_a, map_b, lmax=LMAX, apply_pixwin=False)

    band = (result.ell >= 150) & (result.ell <= 240)
    assert np.mean(result.cl[band] / cl_in[band]) == pytest.approx(1.0, abs=0.3)
    assert result.is_cross


@pytest.mark.physics
def test_cross_spectrum_measures_the_noise_it_removed():
    """The auto-minus-cross difference should recover the injected noise level."""
    cl_in = toy_cl()
    signal = hp.synfast(cl_in, NSIDE, lmax=LMAX, pixwin=False, new=True)
    rng = np.random.default_rng(13)
    noise_rms = 50.0

    map_a = signal + rng.normal(0, noise_rms, signal.size)
    map_b = signal + rng.normal(0, noise_rms, signal.size)

    result = estimate_cross_spectrum(map_a, map_b, lmax=LMAX, apply_pixwin=False)

    # White noise of RMS sigma over pixels of solid angle Omega has C_l = sigma^2 * Omega.
    expected = noise_rms**2 * hp.nside2pixarea(NSIDE)
    band = (result.ell >= 100) & (result.ell <= 240)
    assert np.mean(result.nl_a[band]) == pytest.approx(expected, rel=0.35)


# ------------------------------------------------------- point sources


@pytest.mark.physics
def test_point_source_fit_recovers_injected_amplitude():
    ell = np.arange(LMAX + 1)
    theory = toy_cl()
    injected = 3.0e-3
    observed = theory + injected

    fit = fit_against_theory(ell, observed, theory, ell_min=150, ell_max=250)

    assert fit.amplitude == pytest.approx(injected, rel=0.05)
    assert fit.circular is True
    assert np.allclose(subtract(observed, fit)[150:250], theory[150:250], atol=1e-4)


def test_point_source_fit_needs_enough_multipoles():
    ell = np.arange(20)
    with pytest.raises(ValueError, match="Not enough multipoles"):
        fit_against_theory(ell, np.ones(20), np.ones(20), ell_min=15, ell_max=16)


# ------------------------------------------------- real data, if present


def _has_wmap_data() -> bool:
    clean = Path(get_settings().data_dir) / "clean" / "wmap9"
    return all((clean / f"{name}.npz").exists() for name in ("da-v1", "da-v2", "mask-kq75"))


requires_data = pytest.mark.skipif(
    not _has_wmap_data(), reason="WMAP data not downloaded; run `make data-bootstrap`"
)


@pytest.mark.physics
@pytest.mark.slow
@requires_data
def test_gate_g3_first_acoustic_peak_from_real_wmap_data():
    """The headline result: recover the first acoustic peak from NASA flight data."""
    from cmblab_spectrum.pipeline import run_cross_spectrum

    run = run_cross_spectrum(
        "wmap9",
        "da-v1",
        "da-v2",
        mask_dataset="wmap9",
        mask_product="mask-kq75",
        lmax=800,
    )

    expected = ACOUSTIC_PEAKS[1]
    assert abs(run.peak1_ell - expected["ell"]) <= expected["ell_tol"]
    assert abs(run.peak1_dl - expected["dl_uk2"]) <= expected["dl_tol"]
    assert run.gate_g3_passed


@pytest.mark.physics
@pytest.mark.slow
@requires_data
def test_gate_g4_agrees_with_published_spectra():
    """Our bandpowers must be statistically consistent with WMAP's own published TT."""
    from cmblab_spectrum.pipeline import run_cross_spectrum

    run = run_cross_spectrum(
        "wmap9",
        "da-v1",
        "da-v2",
        mask_dataset="wmap9",
        mask_product="mask-kq75",
        lmax=800,
    )

    comparison = run.comparisons["wmap9-TT-binned"]
    assert comparison.n_compared > 20
    assert comparison.passes_gate_g4, comparison.summary()


@pytest.mark.physics
@pytest.mark.slow
@requires_data
def test_point_source_correction_is_required_for_agreement():
    """Without the correction the high-l excess should blow the chi-squared up."""
    from cmblab_spectrum.pipeline import run_cross_spectrum

    corrected = run_cross_spectrum(
        "wmap9",
        "da-v1",
        "da-v2",
        mask_dataset="wmap9",
        mask_product="mask-kq75",
        lmax=800,
        subtract_point_sources=True,
    )
    uncorrected = run_cross_spectrum(
        "wmap9",
        "da-v1",
        "da-v2",
        mask_dataset="wmap9",
        mask_product="mask-kq75",
        lmax=800,
        subtract_point_sources=False,
    )

    better = corrected.comparisons["wmap9-TT-binned"].chi2_per_dof
    worse = uncorrected.comparisons["wmap9-TT-binned"].chi2_per_dof
    assert better < worse / 5.0
