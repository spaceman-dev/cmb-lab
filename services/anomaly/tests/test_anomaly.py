"""Validation gates for the isotropy statistics and their Monte Carlo calibration."""

from __future__ import annotations

import healpy as hp
import numpy as np
import pytest
from cmblab_anomaly.simulations import NullDistribution, significance
from cmblab_anomaly.statistics import (
    STATISTICS,
    AxisResult,
    angular_separation,
    cold_spot,
    hemispherical_asymmetry,
    low_quadrupole,
    preferred_axis,
    quadrupole_octupole_alignment,
    smhw_window,
)

NSIDE = 32
LMAX = 32


def pure_multipole_sky(ell: int, m: int, nside: int = NSIDE) -> np.ndarray:
    """A sky containing exactly one spherical harmonic."""
    alm = np.zeros(hp.Alm.getsize(LMAX), dtype=complex)
    alm[hp.Alm.getidx(LMAX, ell, m)] = 1.0
    return hp.alm2map(alm, nside, lmax=LMAX)


# ─────────────────────────────────────────────────── axis geometry


def test_angular_separation_folds_antipodal_axes():
    """An axis is headless: 170 degrees apart is really 10 degrees of alignment."""
    a = AxisResult(0.0, 0.0, 1.0)
    b = AxisResult(180.0, 0.0, 1.0)
    assert angular_separation(a, b) == pytest.approx(0.0, abs=1e-6)


def test_angular_separation_of_orthogonal_axes():
    a = AxisResult(0.0, 0.0, 1.0)
    b = AxisResult(90.0, 0.0, 1.0)
    assert angular_separation(a, b) == pytest.approx(90.0, abs=1e-6)


@pytest.mark.physics
def test_preferred_axis_finds_the_symmetry_axis():
    """An m=l multipole has all its power at maximum |m|, so its axis is the pole."""
    alm = np.zeros(hp.Alm.getsize(8), dtype=complex)
    alm[hp.Alm.getidx(8, 2, 2)] = 1.0

    axis = preferred_axis(alm, 2, 8)
    # The pattern lives in the equatorial plane of the z axis, so z maximises dispersion.
    assert abs(axis.lat_deg) > 75.0


@pytest.mark.physics
def test_m_zero_multipole_has_minimal_dispersion_along_its_axis():
    """An m=0 multipole is azimuthally symmetric: zero angular momentum about its axis."""
    alm = np.zeros(hp.Alm.getsize(8), dtype=complex)
    alm[hp.Alm.getidx(8, 2, 0)] = 1.0

    axis = preferred_axis(alm, 2, 8)
    # Maximising sum m^2 |a_lm|^2 must move away from the symmetry axis, not towards it.
    assert abs(axis.lat_deg) < 75.0


# ─────────────────────────────────────────────── the four statistics


@pytest.mark.physics
def test_alignment_returns_a_sensible_angle():
    rng = np.random.default_rng(3)
    sky = rng.normal(0, 50, hp.nside2npix(NSIDE))

    result = quadrupole_octupole_alignment(sky)
    assert 0.0 <= result["angle_deg"] <= 90.0
    assert -90.0 <= result["quad_lat"] <= 90.0


@pytest.mark.physics
def test_hemispherical_asymmetry_detects_an_injected_imbalance():
    """Add power to one hemisphere and the statistic must find it."""
    npix = hp.nside2npix(NSIDE)
    rng = np.random.default_rng(5)
    sky = rng.normal(0, 30, npix)

    _, lat = hp.pix2ang(NSIDE, np.arange(npix), lonlat=True)
    boosted = sky.copy()
    boosted[lat > 0] *= 3.0

    plain = hemispherical_asymmetry(sky, lmax=24)["asymmetry"]
    injected = hemispherical_asymmetry(boosted, lmax=24)["asymmetry"]

    assert injected > plain
    assert injected > 0.3
    # And it should point roughly at the north Galactic pole.
    assert hemispherical_asymmetry(boosted, lmax=24)["axis_lat"] > 40.0


@pytest.mark.physics
def test_cold_spot_finds_an_injected_cold_region():
    npix = hp.nside2npix(64)
    rng = np.random.default_rng(7)
    sky = rng.normal(0, 30, npix)

    centre = hp.ang2vec(210.0, -57.0, lonlat=True)
    disc = hp.query_disc(64, centre, np.radians(8.0))
    sky[disc] -= 120.0

    result = cold_spot(sky, scale_deg=5.0, lmax=96)

    assert result["coldest_sigma"] < -3.0
    assert (
        angular_separation(
            AxisResult(result["lon"], result["lat"], 0.0), AxisResult(210.0, -57.0, 0.0)
        )
        < 25.0
    )


@pytest.mark.physics
def test_smhw_window_is_compensated():
    """A Mexican hat has zero response at l=0: it cannot see a constant offset."""
    ell = np.arange(0, 200)
    window = smhw_window(ell, 5.0)

    assert window[0] == pytest.approx(0.0, abs=1e-12)
    assert window.max() == pytest.approx(1.0)
    # Band-pass: it peaks at an intermediate scale, not at either end.
    assert 0 < int(np.argmax(window)) < 199


@pytest.mark.physics
def test_low_quadrupole_measures_injected_power():
    sky = pure_multipole_sky(2, 0, nside=64) * 100.0
    result = low_quadrupole(sky)

    assert result["c2_uk2"] > 0
    assert result["d2_uk2"] == pytest.approx(2 * 3 * result["c2_uk2"] / (2 * np.pi), rel=1e-9)


def test_statistics_registry_is_consistent():
    for name, (function, key, lower) in STATISTICS.items():
        assert callable(function)
        assert isinstance(key, str)
        assert isinstance(lower, bool), name


# ─────────────────────────────────────────────────── significance


def _null(values: np.ndarray, statistic: str = "low_quadrupole") -> NullDistribution:
    from cmblab_anomaly.statistics import STATISTICS as registry

    return NullDistribution(
        statistic=statistic,
        key=registry[statistic][1],
        values=values,
        n_sims=values.size,
        nside=32,
        lmax=32,
        seed=1,
    )


def test_p_value_is_never_exactly_zero():
    """Add-one smoothing: a finite number of simulations cannot prove infinite rarity."""
    null = _null(np.linspace(100.0, 200.0, 500))
    result = significance("low_quadrupole", {"d2_uk2": 1.0}, null)

    assert result.p_value > 0
    assert result.p_value == pytest.approx(1 / 501, rel=1e-6)


def test_p_value_for_a_typical_value_is_near_one_half():
    null = _null(np.linspace(0.0, 100.0, 1001))
    result = significance("low_quadrupole", {"d2_uk2": 50.0}, null)
    assert result.p_value == pytest.approx(0.5, abs=0.02)


def test_sidak_correction_increases_the_p_value():
    null = _null(np.linspace(0.0, 100.0, 1001))
    single = significance("low_quadrupole", {"d2_uk2": 1.0}, null, n_trials_corrected=1)
    multiple = significance("low_quadrupole", {"d2_uk2": 1.0}, null, n_trials_corrected=4)

    assert multiple.p_value_corrected > single.p_value_corrected
    assert multiple.p_value == single.p_value  # the raw value must not change


def test_upper_tail_statistic_uses_the_other_side():
    """Hemispherical asymmetry is anomalous when it is large, not small."""
    null = _null(np.linspace(0.0, 1.0, 1001), statistic="hemispherical_asymmetry")
    high = significance("hemispherical_asymmetry", {"asymmetry": 0.99}, null)
    low = significance("hemispherical_asymmetry", {"asymmetry": 0.01}, null)

    assert high.p_value < 0.05
    assert low.p_value > 0.9


@pytest.mark.physics
@pytest.mark.slow
def test_gate_g6_pipeline_is_calibrated():
    """Gate G6: isotropic input must produce uniformly distributed p-values.

    This is the test that catches the classic anomaly-hunting failure — a pipeline that
    reports small p-values for perfectly ordinary skies.
    """
    from cmblab_anomaly.pipeline import calibrate

    result = calibrate("low_quadrupole", n_checks=20, n_sims=200, nside=16, lmax=32)

    assert result["n_checks"] >= 15
    assert 0.25 <= result["mean_p_value"] <= 0.75, result["detail"]
    assert result["passed"], result["detail"]
