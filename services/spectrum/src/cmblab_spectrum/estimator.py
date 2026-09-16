"""Angular power spectrum estimation from a masked HEALPix map.

The measured quantity is the *pseudo* power spectrum: what you get when you spherical-
harmonic transform a map that has had a mask applied. It is biased low, because the mask
threw away sky, and it is biased at high multipole, because the instrument beam and the
finite pixel size both smooth the sky.

Undoing those three effects is the whole job:

    C_l_true  =  C_l_pseudo  /  ( w2 * b_l^2 * p_l^2 )

    w2   mean of the squared mask — the "f_sky correction"
    b_l  beam transfer function — how much the telescope smoothed the sky
    p_l  HEALPix pixel window — how much pixelisation smoothed the sky

The f_sky correction is the leading-order MASTER approximation. It is accurate for large,
smooth masks and multipoles well above the mask's characteristic scale, which covers the
acoustic peaks. Full mode-coupling deconvolution is the ``master`` method.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import healpy as hp
import numpy as np
from cmblab_core.healpix import UNSEEN

#: Below this beam+pixel transfer value, deconvolution amplifies noise catastrophically.
#: A 1 degree beam hits this around l ~ 450. Multipoles past it are reported but flagged.
TRANSFER_FLOOR = 0.02


@dataclass(slots=True)
class PowerSpectrum:
    """An estimated angular power spectrum, unbinned."""

    ell: np.ndarray
    cl: np.ndarray
    dl: np.ndarray
    f_sky: float
    w2: float
    lmax: int
    beam_corrected: bool
    pixwin_corrected: bool
    #: Largest multipole where the transfer function is still trustworthy.
    reliable_lmax: int
    #: True when built from two independent maps, which removes the noise bias.
    is_cross: bool = False
    #: Per-map noise power spectra, estimated as (auto - cross). Only set for cross-spectra.
    nl_a: np.ndarray | None = None
    nl_b: np.ndarray | None = None
    transfer: np.ndarray | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def first_peak(self, search_min: int = 100, search_max: int = 350) -> tuple[int, float]:
        """Locate the first acoustic peak. Validation gate G3."""
        window = (self.ell >= search_min) & (self.ell <= search_max)
        if not window.any():
            raise ValueError(f"No multipoles in search range [{search_min}, {search_max}]")

        # Smooth before peak-finding: the raw spectrum is noisy point to point.
        smoothed = _smooth(self.dl[window], width=15)
        index = int(np.argmax(smoothed))
        return int(self.ell[window][index]), float(smoothed[index])

    def variance(self) -> np.ndarray:
        """Per-multipole variance of C_l, including instrument noise where known.

        For a cross-spectrum between maps A and B the Knox result is

            Var(C_l^AB) = [ (C_l^AB)^2 + (C_l + N_l^A)(C_l + N_l^B) ] / ((2l+1) f_sky)

        Dropping the noise terms — as a pure cosmic-variance estimate does — understates
        the error badly wherever noise is comparable to signal, which then shows up as an
        absurd chi-squared against published spectra.
        """
        modes = (2.0 * self.ell + 1.0) * self.f_sky
        with np.errstate(divide="ignore", invalid="ignore"):
            if self.is_cross and self.nl_a is not None and self.nl_b is not None:
                total_a = self.cl + self.nl_a
                total_b = self.cl + self.nl_b
                var = (self.cl**2 + total_a * total_b) / modes
            else:
                var = 2.0 * self.cl**2 / modes
        return np.nan_to_num(var, nan=0.0, posinf=0.0, neginf=0.0)

    def snr_lmax(self, min_ell: int = 100, threshold: float = 0.1) -> int:
        """Highest multipole where signal still exceeds ``threshold`` times the noise.

        A cross-spectrum stays *unbiased* into the noise-dominated regime, but its variance
        explodes there, producing wildly scattered bandpowers that are formally correct and
        practically useless. Reporting where the data stop carrying information is more
        honest than plotting noise with big error bars.

        The default is deliberately permissive. Cutting at S/N = 1 would discard the second
        acoustic peak, which a single WMAP detector pair still measures perfectly well with
        appropriately large error bars. Cutting at S/N = 0.1 removes only the multipoles
        where the measurement has genuinely collapsed.
        """
        if self.nl_a is None or self.nl_b is None:
            return self.lmax

        noise = _smooth(0.5 * (self.nl_a + self.nl_b), width=21)
        signal = _smooth(np.abs(self.cl), width=21)

        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(noise > 0, signal / noise, np.inf)

        below = np.where((self.ell >= min_ell) & (ratio < threshold))[0]
        return int(self.ell[below[0]]) - 1 if below.size else self.lmax

    @property
    def usable_lmax(self) -> int:
        """The multipole beyond which results should not be reported."""
        return min(self.reliable_lmax, self.snr_lmax())


def _smooth(values: np.ndarray, width: int = 15) -> np.ndarray:
    """Boxcar smoothing that preserves array length."""
    if width <= 1 or values.size < width:
        return values
    kernel = np.ones(width) / width
    return np.convolve(values, kernel, mode="same")


def _to_dl(ell: np.ndarray, cl: np.ndarray) -> np.ndarray:
    """Convert C_l to the D_l = l(l+1)C_l/2pi convention every CMB paper plots."""
    return ell * (ell + 1.0) * cl / (2.0 * np.pi)


def beam_window(
    lmax: int,
    *,
    fwhm_arcmin: float | None = None,
    bl: np.ndarray | None = None,
) -> np.ndarray:
    """Beam transfer function b_l, either Gaussian or supplied from an archive file."""
    if bl is not None:
        out = np.ones(lmax + 1)
        n = min(bl.size, lmax + 1)
        out[:n] = bl[:n]
        # Beyond the tabulated range the beam has effectively closed; hold the last value.
        out[n:] = bl[n - 1] if n else 1.0
        return out

    if fwhm_arcmin:
        return hp.gauss_beam(np.radians(fwhm_arcmin / 60.0), lmax=lmax)

    return np.ones(lmax + 1)


def _build_mask(sky: np.ndarray, mask: np.ndarray | None, nside: int) -> np.ndarray:
    """Combine the supplied mask with pixels the map itself flagged as bad."""
    working = np.ones(sky.size) if mask is None else np.asarray(mask, dtype=np.float64)
    if working.size != sky.size:
        working = hp.ud_grade(working, nside_out=nside)
        working = (working > 0.9).astype(np.float64)
    working = working.copy()
    working[sky == UNSEEN] = 0.0
    return working


def _apodised(sky: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Zero the masked pixels and weight by the mask.

    map2alm has no concept of UNSEEN: those pixels must be zeroed, not left at -1.6e30.
    """
    return np.where(mask > 0, sky, 0.0) * mask


def _transfer_function(
    nside: int,
    lmax: int,
    size: int,
    *,
    beam_fwhm_arcmin: float | None,
    bl: np.ndarray | None,
    apply_pixwin: bool,
) -> tuple[np.ndarray, bool]:
    transfer = np.ones(size)
    beam_used = beam_fwhm_arcmin is not None or bl is not None
    if beam_used:
        transfer *= beam_window(lmax, fwhm_arcmin=beam_fwhm_arcmin, bl=bl)[:size]
    if apply_pixwin:
        transfer *= hp.pixwin(nside, lmax=lmax)[:size]
    return transfer, beam_used


def _reliable_lmax(transfer: np.ndarray, lmax: int) -> int:
    below = np.where(transfer < TRANSFER_FLOOR)[0]
    return int(below[0] - 1) if below.size else lmax


def estimate_spectrum(
    sky: np.ndarray,
    *,
    mask: np.ndarray | None = None,
    lmax: int | None = None,
    beam_fwhm_arcmin: float | None = None,
    bl: np.ndarray | None = None,
    apply_pixwin: bool = True,
    iterations: int = 3,
) -> PowerSpectrum:
    """Estimate the auto power spectrum of a single map.

    Beware: an auto-spectrum contains the map's own noise, N_l, which deconvolution
    amplifies without bound. Above the multipole where noise overtakes signal the result
    turns upward and is meaningless. For an unbiased estimate use
    :func:`estimate_cross_spectrum` with two independently-noised maps.

    ``iterations`` controls healpy's iterative ``map2alm`` refinement. Three iterations is
    the usual compromise: it substantially reduces harmonic leakage at modest cost.
    """
    sky = np.asarray(sky, dtype=np.float64)
    nside = hp.npix2nside(sky.size)
    lmax = lmax or min(3 * nside - 1, 2500)

    working_mask = _build_mask(sky, mask, nside)
    f_sky = float((working_mask > 0).mean())
    w2 = float(np.mean(working_mask**2))
    if w2 <= 0:
        raise ValueError("Mask removes the entire sky")

    alm = hp.map2alm(
        _apodised(sky, working_mask), lmax=lmax, iter=iterations, use_pixel_weights=False
    )
    cl_pseudo = hp.alm2cl(alm)
    ell = np.arange(cl_pseudo.size)

    transfer, beam_used = _transfer_function(
        nside,
        lmax,
        cl_pseudo.size,
        beam_fwhm_arcmin=beam_fwhm_arcmin,
        bl=bl,
        apply_pixwin=apply_pixwin,
    )

    safe = np.maximum(transfer, TRANSFER_FLOOR / 10.0)
    cl = cl_pseudo / (w2 * safe**2)

    return PowerSpectrum(
        ell=ell,
        cl=cl,
        dl=_to_dl(ell, cl),
        f_sky=f_sky,
        w2=w2,
        lmax=lmax,
        beam_corrected=beam_used,
        pixwin_corrected=apply_pixwin,
        reliable_lmax=_reliable_lmax(transfer, lmax),
        is_cross=False,
        transfer=transfer,
        meta={
            "nside": nside,
            "iterations": iterations,
            "beam_fwhm_arcmin": beam_fwhm_arcmin,
        },
    )


def estimate_cross_spectrum(
    sky_a: np.ndarray,
    sky_b: np.ndarray,
    *,
    mask: np.ndarray | None = None,
    lmax: int | None = None,
    bl_a: np.ndarray | None = None,
    bl_b: np.ndarray | None = None,
    apply_pixwin: bool = True,
    iterations: int = 3,
) -> PowerSpectrum:
    """Cross-spectrum of two maps of the same sky with independent noise.

    This is the standard trick behind every published CMB spectrum. Writing each map as
    signal plus noise, the expectation of the cross-spectrum is

        <a_lm^A a_lm^B*>  =  C_l b_l^A b_l^B  +  <n^A n^B*>

    and the noise term vanishes because the two detectors' noise is uncorrelated. The
    result is unbiased at every multipole, with no noise model required — which is why the
    spectrum keeps its shape into the damping tail instead of turning upward.

    The two maps must cover the same sky at the same N_side; they may have different beams.
    """
    sky_a = np.asarray(sky_a, dtype=np.float64)
    sky_b = np.asarray(sky_b, dtype=np.float64)
    if sky_a.size != sky_b.size:
        raise ValueError(f"Maps differ in size: {sky_a.size} vs {sky_b.size}")

    nside = hp.npix2nside(sky_a.size)
    lmax = lmax or min(3 * nside - 1, 2500)

    # A pixel bad in either map must be excluded from both, or the cross-spectrum is
    # computed over mismatched sky.
    working_mask = _build_mask(sky_a, mask, nside)
    working_mask[sky_b == UNSEEN] = 0.0

    f_sky = float((working_mask > 0).mean())
    w2 = float(np.mean(working_mask**2))
    if w2 <= 0:
        raise ValueError("Mask removes the entire sky")

    alm_a = hp.map2alm(
        _apodised(sky_a, working_mask), lmax=lmax, iter=iterations, use_pixel_weights=False
    )
    alm_b = hp.map2alm(
        _apodised(sky_b, working_mask), lmax=lmax, iter=iterations, use_pixel_weights=False
    )
    cl_pseudo = hp.alm2cl(alm_a, alm_b)
    ell = np.arange(cl_pseudo.size)

    size = cl_pseudo.size
    pixel_window = hp.pixwin(nside, lmax=lmax)[:size] if apply_pixwin else np.ones(size)
    beam_a = beam_window(lmax, bl=bl_a)[:size] if bl_a is not None else np.ones(size)
    beam_b = beam_window(lmax, bl=bl_b)[:size] if bl_b is not None else np.ones(size)

    # Each map contributes its own beam once, and the pixel window once.
    transfer = np.sqrt(np.abs(beam_a * beam_b)) * pixel_window
    floor = (TRANSFER_FLOOR / 10.0) ** 2
    divisor = np.maximum(beam_a * beam_b * pixel_window**2, floor)
    cl = cl_pseudo / (w2 * divisor)

    # Each auto-spectrum is signal + that map's own noise, so subtracting the (noise-free)
    # cross-spectrum leaves a purely empirical estimate of each map's noise power. No noise
    # model, no instrument simulation — just the data.
    cl_aa = hp.alm2cl(alm_a) / (w2 * np.maximum(beam_a**2 * pixel_window**2, floor))
    cl_bb = hp.alm2cl(alm_b) / (w2 * np.maximum(beam_b**2 * pixel_window**2, floor))
    nl_a = np.clip(cl_aa - cl, 0.0, None)
    nl_b = np.clip(cl_bb - cl, 0.0, None)

    return PowerSpectrum(
        ell=ell,
        cl=cl,
        dl=_to_dl(ell, cl),
        f_sky=f_sky,
        w2=w2,
        lmax=lmax,
        beam_corrected=bl_a is not None or bl_b is not None,
        pixwin_corrected=apply_pixwin,
        reliable_lmax=_reliable_lmax(transfer, lmax),
        is_cross=True,
        nl_a=nl_a,
        nl_b=nl_b,
        transfer=transfer,
        meta={"nside": nside, "iterations": iterations},
    )


def cosmic_variance_error(
    ell: np.ndarray,
    cl: np.ndarray,
    f_sky: float,
    *,
    delta_ell: np.ndarray | float = 1.0,
) -> np.ndarray:
    """Knox formula for the sample-variance limited uncertainty on C_l.

        sigma(C_l) = sqrt( 2 / ((2l+1) * f_sky * delta_l) ) * C_l

    This is a *lower bound* on the error: it omits instrument noise, so at high multipole
    where noise dominates it will be optimistic. Good enough to sanity-check the peaks.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        modes = (2.0 * ell + 1.0) * f_sky * delta_ell
        sigma = np.sqrt(2.0 / modes) * np.abs(cl)
    return np.nan_to_num(sigma, nan=0.0, posinf=0.0)
