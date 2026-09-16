"""Validation gate G2: the cleaning pipeline must recover a known monopole and dipole.

We inject a dipole with the published CMB amplitude and direction into a synthetic sky,
then assert that the fitter recovers it. If these fail, every downstream number is wrong.
"""

from __future__ import annotations

import healpy as hp
import numpy as np
import pytest

from cmblab_core.constants import (
    DIPOLE_AMPLITUDE_UK,
    DIPOLE_GALACTIC_LAT_DEG,
    DIPOLE_GALACTIC_LON_DEG,
    T_CMB_NOMINAL_K,
)
from cmblab_core.healpix import (
    UNSEEN,
    apply_mask,
    clean_map,
    compute_stats,
    degrade,
    fit_dipole,
    remove_monopole_dipole,
    to_microkelvin,
)

NSIDE = 64


def synthetic_sky(
    nside: int = NSIDE,
    *,
    monopole_uk: float = T_CMB_NOMINAL_K * 1e6,
    dipole_amp_uk: float = DIPOLE_AMPLITUDE_UK,
    lon_deg: float = DIPOLE_GALACTIC_LON_DEG,
    lat_deg: float = DIPOLE_GALACTIC_LAT_DEG,
    anisotropy_rms_uk: float = 70.0,
    seed: int = 42,
) -> np.ndarray:
    """A sky containing exactly a monopole, a dipole, and white anisotropy, in uK."""
    npix = hp.nside2npix(nside)
    direction = hp.ang2vec(lon_deg, lat_deg, lonlat=True)
    pixel_vectors = np.asarray(hp.pix2vec(nside, np.arange(npix)))

    dipole = dipole_amp_uk * (direction @ pixel_vectors)
    noise = np.random.default_rng(seed).normal(0.0, anisotropy_rms_uk, npix)
    return monopole_uk + dipole + noise


# ----------------------------------------------------------------------------- units


def test_kelvin_converts_to_microkelvin():
    sky = np.array([1.0, 2.0, 3.0])
    out, factor = to_microkelvin(sky, "K_CMB")
    assert factor == 1e6
    np.testing.assert_allclose(out, [1e6, 2e6, 3e6])


def test_unit_conversion_preserves_unseen():
    sky = np.array([1.0, UNSEEN, 3.0])
    out, _ = to_microkelvin(sky, "K")
    assert out[1] == UNSEEN


def test_brightness_units_are_rejected():
    with pytest.raises(ValueError, match="MJy/sr|Cannot convert"):
        to_microkelvin(np.zeros(12), "MJy/sr")


# ----------------------------------------------------------------- gate G2: dipole


@pytest.mark.physics
def test_recovers_injected_dipole_amplitude():
    sky = synthetic_sky()
    fit = fit_dipole(sky, gal_cut_deg=0.0)
    assert fit.amplitude_uk == pytest.approx(DIPOLE_AMPLITUDE_UK, rel=0.02)


@pytest.mark.physics
def test_recovers_injected_dipole_direction():
    sky = synthetic_sky()
    fit = fit_dipole(sky, gal_cut_deg=0.0)
    assert fit.angular_separation_from_cmb_dipole() < 2.0


@pytest.mark.physics
def test_recovers_cmb_monopole_temperature():
    sky = synthetic_sky()
    fit = fit_dipole(sky, gal_cut_deg=0.0)
    recovered_kelvin = fit.monopole_uk / 1e6
    assert recovered_kelvin == pytest.approx(T_CMB_NOMINAL_K, abs=1e-3)


@pytest.mark.physics
def test_gate_g2_passes_on_clean_synthetic_sky():
    sky = synthetic_sky()
    fit = fit_dipole(sky, gal_cut_deg=0.0)
    assert fit.matches_cmb_dipole()


@pytest.mark.physics
def test_removal_leaves_no_residual_dipole():
    sky = synthetic_sky()
    residual = remove_monopole_dipole(sky, gal_cut_deg=0.0)
    after = fit_dipole(residual, gal_cut_deg=0.0)

    # Residual dipole should be a tiny fraction of what we removed.
    assert after.amplitude_uk < 0.01 * DIPOLE_AMPLITUDE_UK
    assert abs(after.monopole_uk) < 1.0


@pytest.mark.physics
def test_galactic_cut_protects_fit_from_foregrounds():
    """A bright Galactic plane must not drag the dipole fit off-axis when cut out."""
    sky = synthetic_sky()
    nside = hp.npix2nside(sky.size)
    _, lat = hp.pix2ang(nside, np.arange(sky.size), lonlat=True)

    contaminated = sky.copy()
    contaminated[np.abs(lat) < 10.0] += 5.0e4  # 50 mK of fake synchrotron

    uncut = fit_dipole(contaminated, gal_cut_deg=0.0)
    cut = fit_dipole(contaminated, gal_cut_deg=30.0)

    assert cut.angular_separation_from_cmb_dipole() < uncut.angular_separation_from_cmb_dipole()
    assert cut.angular_separation_from_cmb_dipole() < 5.0


# ------------------------------------------------------------------------ masking


def test_mask_sets_rejected_pixels_to_unseen():
    sky = np.ones(hp.nside2npix(16))
    mask = np.ones_like(sky)
    mask[:100] = 0

    masked = apply_mask(sky, mask)
    assert np.all(masked[:100] == UNSEEN)
    assert np.all(masked[100:] == 1.0)


def test_mask_is_resampled_to_map_resolution():
    sky = np.ones(hp.nside2npix(32))
    coarse_mask = np.ones(hp.nside2npix(16))
    coarse_mask[:50] = 0

    masked = apply_mask(sky, coarse_mask)
    assert masked.size == sky.size
    assert np.any(masked == UNSEEN)


# ---------------------------------------------------------------------- degrading


def test_degrade_reduces_pixel_count():
    sky = synthetic_sky(nside=64)
    out = degrade(sky, 16)
    assert out.size == hp.nside2npix(16)


def test_degrade_refuses_to_upgrade():
    sky = synthetic_sky(nside=16)
    with pytest.raises(ValueError, match="invents information"):
        degrade(sky, 64)


@pytest.mark.physics
def test_degrading_preserves_the_dipole():
    """Degrading is only safe for large-angle work if it leaves low multipoles intact."""
    sky = synthetic_sky(nside=128)
    coarse = degrade(sky, 32)

    fine_fit = fit_dipole(sky, gal_cut_deg=0.0)
    coarse_fit = fit_dipole(coarse, gal_cut_deg=0.0)

    assert coarse_fit.amplitude_uk == pytest.approx(fine_fit.amplitude_uk, rel=0.01)
    assert coarse_fit.angular_separation_from_cmb_dipole() < 2.0


# ----------------------------------------------------------------------- pipeline


@pytest.mark.physics
def test_clean_map_end_to_end_in_kelvin():
    """The realistic path: archive map arrives in K_CMB, leaves as uK anisotropies."""
    sky_kelvin = synthetic_sky() * 1e-6

    cleaned, report = clean_map(sky_kelvin, unit="K_CMB", gal_cut_deg=0.0)

    assert report.unit_in == "K_CMB"
    assert report.dipole_fit is not None
    assert report.dipole_fit.amplitude_uk == pytest.approx(DIPOLE_AMPLITUDE_UK, rel=0.02)
    assert report.dipole_fit.matches_cmb_dipole()

    # Monopole and dipole gone, anisotropies survive.
    assert abs(float(cleaned.mean())) < 1.0
    assert 50.0 < float(cleaned.std()) < 100.0


def test_clean_map_records_every_operation():
    sky = synthetic_sky() * 1e-6
    mask = np.ones(sky.size)
    mask[:500] = 0

    _, report = clean_map(sky, unit="K_CMB", mask=mask, nside_out=32, gal_cut_deg=0.0)
    ops = [entry["op"] for entry in report.ops]

    assert ops == [
        "to_microkelvin",
        "fit_dipole",
        "remove_monopole_dipole",
        "apply_mask",
        "degrade",
    ]
    assert report.nside_out == 32


def test_stats_ignore_masked_pixels():
    sky = synthetic_sky()
    sky[:1000] = UNSEEN

    stats = compute_stats(sky, gal_cut_deg=0.0)
    assert stats.n_valid_pixels == sky.size - 1000
    assert stats.masked_fraction == pytest.approx(1000 / sky.size)
    assert np.isfinite(stats.mean_uk)
