"""Validation gates for theory spectra and parameter inference."""

from __future__ import annotations

import numpy as np
import pytest
from cmblab_core.constants import ACOUSTIC_PEAKS, PLANCK_2018
from cmblab_cosmology.likelihood import BandpowerData, BandpowerLikelihood, LikelihoodConfig
from cmblab_cosmology.theory import (
    PARAM_BOUNDS,
    As_to_logA,
    bin_theory,
    logA_to_As,
    theory_spectrum,
)


@pytest.fixture(scope="module")
def planck_theory():
    return theory_spectrum({}, lmax=1200)


# ─────────────────────────────────────────────────────── theory


@pytest.mark.physics
def test_camb_reproduces_the_first_acoustic_peak(planck_theory):
    """CAMB with Planck parameters must put the first peak where it is observed."""
    ell, dl = planck_theory.first_peak()
    expected = ACOUSTIC_PEAKS[1]

    assert abs(ell - expected["ell"]) <= expected["ell_tol"]
    assert abs(dl - expected["dl_uk2"]) <= expected["dl_tol"]


@pytest.mark.physics
def test_derived_parameters_match_published_values(planck_theory):
    """Derived quantities are not fitted — they fall out of the six base parameters."""
    derived = planck_theory.derived

    assert derived["omega_m"] == pytest.approx(PLANCK_2018["omega_m"].value, abs=0.01)
    assert derived["sigma8"] == pytest.approx(PLANCK_2018["sigma8"].value, abs=0.03)
    assert derived["age_gyr"] == pytest.approx(PLANCK_2018["age_gyr"].value, abs=0.2)
    assert derived["z_star"] == pytest.approx(PLANCK_2018["z_star"].value, rel=0.01)


@pytest.mark.physics
def test_sachs_wolfe_plateau_is_flat():
    """A near scale-invariant spectrum makes D_l flat below l ~ 30."""
    theory = theory_spectrum({}, lmax=300)
    plateau = theory.dl_tt[5:26]
    # Flat to within a factor of 1.5 across the plateau, unlike the peak region.
    assert plateau.max() / plateau.min() < 1.5


@pytest.mark.physics
def test_raising_H0_moves_peaks_to_lower_multipole():
    """With the physical densities held fixed, larger H0 means a *closer* last scattering.

    This direction is easy to get backwards. Holding omega_b h^2 and omega_c h^2 fixed,
    raising H0 shrinks the comoving distance to last scattering. A ruler of unchanged length
    at a shorter distance subtends a *larger* angle, so theta_* grows and the peaks move to
    lower multipole. Measured: l = 225 at H0 = 60, l = 213 at H0 = 80.
    """
    low = theory_spectrum({"H0": 62.0}, lmax=800)
    high = theory_spectrum({"H0": 74.0}, lmax=800)

    assert high.first_peak()[0] < low.first_peak()[0]
    assert high.derived["theta_star"] > low.derived["theta_star"]


@pytest.mark.physics
def test_more_baryons_suppress_the_second_peak():
    """Baryon loading deepens compressions (odd peaks) relative to rarefactions."""

    def peak_ratio(ombh2: float) -> float:
        theory = theory_spectrum({"ombh2": ombh2}, lmax=900)
        first = theory.dl_tt[180:260].max()
        second = theory.dl_tt[480:600].max()
        return second / first

    assert peak_ratio(0.026) < peak_ratio(0.019)


def test_logA_roundtrip():
    assert As_to_logA(logA_to_As(3.044)) == pytest.approx(3.044)


def test_theory_results_are_cached():
    """The sampler revisits nearby points constantly; caching is what makes it fast."""
    from cmblab_cosmology.theory import cache_info

    theory_spectrum({"H0": 68.5}, lmax=300)
    before = cache_info()["hits"]
    theory_spectrum({"H0": 68.5}, lmax=300)
    assert cache_info()["hits"] > before


# ─────────────────────────────────────────────────────── binning


def test_bin_theory_averages_within_edges(planck_theory):
    edges = [(30, 59), (60, 89), (200, 259)]
    binned = bin_theory(planck_theory, edges)

    assert binned.shape == (3,)
    assert np.all(np.isfinite(binned))
    # The bin spanning the first peak must be the largest of the three.
    assert binned[2] > binned[1] > binned[0]


def test_bin_theory_weights_by_mode_count(planck_theory):
    """A single-multipole bin must return exactly that multipole's value."""
    binned = bin_theory(planck_theory, [(220, 220)])
    assert binned[0] == pytest.approx(planck_theory.dl_tt[220])


# ─────────────────────────────────────────────────────── likelihood


def _fake_bandpowers(n: int = 12):
    from cmblab_core.models import Bandpower

    theory = theory_spectrum({}, lmax=700)
    rows = []
    for i in range(n):
        lo, hi = 30 + i * 40, 69 + i * 40
        ell = np.arange(lo, hi + 1)
        weights = 2.0 * ell + 1.0
        dl = float(np.sum(weights * theory.dl_tt[lo : hi + 1]) / weights.sum())
        rows.append(
            Bandpower(
                ell_min=lo,
                ell_max=hi,
                ell_eff=float(np.sum(weights * ell) / weights.sum()),
                dl_uk2=dl,
                dl_err_uk2=max(dl * 0.03, 20.0),
            )
        )
    return rows


@pytest.mark.physics
def test_likelihood_is_minimised_at_the_truth():
    """Feeding in noiseless theory bandpowers, chi2 must be ~0 at the true parameters.

    Not exactly zero: the fixture and the likelihood evaluate CAMB at slightly different
    lmax, and CAMB's lensing and sampling accuracy depend weakly on it. The residual is
    chi2 ~ 4e-3 across 12 bandpowers, six orders of magnitude below the offset case.
    """
    data = BandpowerData.from_bandpowers(_fake_bandpowers())
    likelihood = BandpowerLikelihood(data, LikelihoodConfig(free_params=["H0"]))

    at_truth = likelihood.chi2(np.array([67.36]))
    off_truth = likelihood.chi2(np.array([78.0]))

    assert at_truth < 0.1
    assert off_truth > 1000 * max(at_truth, 1e-6)


def test_prior_rejects_out_of_bounds():
    data = BandpowerData.from_bandpowers(_fake_bandpowers())
    likelihood = BandpowerLikelihood(data, LikelihoodConfig(free_params=["H0"]))

    lo, hi = PARAM_BOUNDS["H0"]
    assert np.isneginf(likelihood.log_prior(np.array([hi + 5])))
    assert np.isneginf(likelihood.log_prior(np.array([lo - 5])))
    assert np.isfinite(likelihood.log_prior(np.array([67.0])))


def test_unknown_parameter_is_rejected():
    data = BandpowerData.from_bandpowers(_fake_bandpowers())
    with pytest.raises(ValueError, match="Unknown parameters"):
        BandpowerLikelihood(data, LikelihoodConfig(free_params=["not_a_parameter"]))


def test_bandpower_data_drops_low_multipoles():
    """Below l=30 the f_sky approximation is least reliable, so those bins are excluded."""
    rows = _fake_bandpowers()
    data = BandpowerData.from_bandpowers(rows, ell_min=100)
    assert data.ell_eff.min() >= 100


def test_bandpower_data_needs_enough_bins():
    with pytest.raises(ValueError, match="usable bandpowers"):
        BandpowerData.from_bandpowers(_fake_bandpowers(2), ell_min=30)


# ─────────────────────────────────────────────────────── sampling


@pytest.mark.physics
@pytest.mark.slow
def test_short_mcmc_recovers_an_injected_parameter():
    """End-to-end: sample noiseless theory data and check the chain finds the truth."""
    from cmblab_cosmology.sampler import run_mcmc

    data = BandpowerData.from_bandpowers(_fake_bandpowers())
    likelihood = BandpowerLikelihood(data, LikelihoodConfig(free_params=["H0"]))

    result = run_mcmc(likelihood, n_walkers=8, n_steps=120, workers=1, derived=(), progress=None)

    assert result.summaries["H0"].mean == pytest.approx(67.36, abs=2.0)
    assert 0.1 < result.acceptance_fraction < 0.95
