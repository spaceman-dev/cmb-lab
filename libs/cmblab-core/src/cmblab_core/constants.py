"""Published physical constants and reference values.

Every number here is a *validation target*: the pipeline is considered correct when it
reproduces these within the quoted uncertainty. Sources are cited inline so any value can
be challenged.
"""

from __future__ import annotations

from typing import NamedTuple


class Measurement(NamedTuple):
    """A published value with symmetric or asymmetric uncertainty."""

    value: float
    err_lo: float
    err_hi: float
    source: str

    @property
    def err(self) -> float:
        return 0.5 * (self.err_lo + self.err_hi)

    def contains(self, x: float, n_sigma: float = 1.0) -> bool:
        return self.value - n_sigma * self.err_lo <= x <= self.value + n_sigma * self.err_hi

    def tension_sigma(self, other: Measurement) -> float:
        """Naive tension between two measurements, in sigma."""
        denom = (self.err**2 + other.err**2) ** 0.5
        return abs(self.value - other.value) / denom if denom else 0.0


def _sym(value: float, err: float, source: str) -> Measurement:
    return Measurement(value, err, err, source)


# ----------------------------------------------------------------------------------
# CMB monopole and dipole  (Gate G2)
# ----------------------------------------------------------------------------------

#: CMB monopole temperature. COBE/FIRAS, Fixsen 2009 (ApJ 707, 916).
T_CMB_K = 2.72548
T_CMB_ERR_K = 0.00057

#: Conventional rounded value used throughout the Planck/WMAP literature.
T_CMB_NOMINAL_K = 2.7255

#: Solar-system CMB dipole amplitude, Planck 2018 (A&A 641, A1).
DIPOLE_AMPLITUDE_UK = 3362.08
DIPOLE_AMPLITUDE_ERR_UK = 0.99

#: Dipole direction in Galactic coordinates (degrees), Planck 2018.
DIPOLE_GALACTIC_LON_DEG = 264.021
DIPOLE_GALACTIC_LAT_DEG = 48.253


# ----------------------------------------------------------------------------------
# Acoustic peak positions  (Gate G3)
# ----------------------------------------------------------------------------------
# D_l = l(l+1)C_l / 2pi, in uK^2. Approximate peak locations in the TT spectrum.

ACOUSTIC_PEAKS: dict[int, dict[str, float]] = {
    1: {"ell": 220.0, "ell_tol": 8.0, "dl_uk2": 5750.0, "dl_tol": 400.0},
    2: {"ell": 537.0, "ell_tol": 15.0, "dl_uk2": 2520.0, "dl_tol": 300.0},
    3: {"ell": 810.0, "ell_tol": 20.0, "dl_uk2": 2450.0, "dl_tol": 300.0},
}

#: Below this multipole the spectrum is dominated by the Sachs-Wolfe plateau.
SACHS_WOLFE_ELL_MAX = 30

#: Above this multipole Silk damping suppresses power.
SILK_DAMPING_ELL_MIN = 1000


# ----------------------------------------------------------------------------------
# Planck 2018 base-LCDM  (Gate G5)
# TT,TE,EE+lowE+lensing. Planck 2018 results VI, A&A 641, A6, Table 2.
# ----------------------------------------------------------------------------------

PLANCK18 = "Planck 2018 TT,TE,EE+lowE+lensing (A&A 641, A6)"

PLANCK_2018: dict[str, Measurement] = {
    # Sampled parameters
    "ombh2": _sym(0.02237, 0.00015, PLANCK18),
    "omch2": _sym(0.1200, 0.0012, PLANCK18),
    "theta_mc_100": _sym(1.04092, 0.00031, PLANCK18),
    "tau": _sym(0.0544, 0.0073, PLANCK18),
    "ln10As": _sym(3.044, 0.014, PLANCK18),
    "ns": _sym(0.9649, 0.0042, PLANCK18),
    # Derived parameters
    "H0": _sym(67.36, 0.54, PLANCK18),
    "omega_m": _sym(0.3153, 0.0073, PLANCK18),
    "omega_lambda": _sym(0.6847, 0.0073, PLANCK18),
    "sigma8": _sym(0.8111, 0.0060, PLANCK18),
    "S8": _sym(0.832, 0.013, PLANCK18),
    "age_gyr": _sym(13.797, 0.023, PLANCK18),
    "z_star": _sym(1089.92, 0.25, PLANCK18),
    "z_reion": _sym(7.67, 0.73, PLANCK18),
}

#: Convenient starting point for MCMC and theory calls.
PLANCK_2018_BESTFIT: dict[str, float] = {
    "H0": 67.36,
    "ombh2": 0.02237,
    "omch2": 0.1200,
    "tau": 0.0544,
    "ns": 0.9649,
    "As": 2.1e-9,
}


# ----------------------------------------------------------------------------------
# WMAP 9-year  (WMAP-only LCDM). Hinshaw et al. 2013, ApJS 208, 19, Table 3.
# ----------------------------------------------------------------------------------

WMAP9_SRC = "WMAP 9-year (ApJS 208, 19)"

WMAP_9YEAR: dict[str, Measurement] = {
    "ombh2": _sym(0.02264, 0.00050, WMAP9_SRC),
    "omch2": _sym(0.1138, 0.0045, WMAP9_SRC),
    "ns": _sym(0.972, 0.013, WMAP9_SRC),
    "tau": _sym(0.089, 0.014, WMAP9_SRC),
    "H0": _sym(70.0, 2.2, WMAP9_SRC),
    "omega_m": _sym(0.279, 0.025, WMAP9_SRC),
    "sigma8": _sym(0.821, 0.023, WMAP9_SRC),
}


# ----------------------------------------------------------------------------------
# The Hubble tension — the headline result for the tension dashboard.
# ----------------------------------------------------------------------------------

H0_MEASUREMENTS: dict[str, Measurement] = {
    "planck2018_cmb": _sym(67.36, 0.54, PLANCK18),
    "wmap9_cmb": _sym(70.0, 2.2, WMAP9_SRC),
    "act_dr4_cmb": _sym(67.9, 1.5, "ACT DR4 (JCAP 12, 047)"),
    "sh0es_cepheid": _sym(73.04, 1.04, "SH0ES Riess et al. 2022 (ApJL 934, L7)"),
    "trgb": _sym(69.8, 1.9, "CCHP TRGB Freedman 2021 (ApJ 919, 16)"),
    "bao_bbn": _sym(67.6, 1.1, "BOSS BAO+BBN (MNRAS 480, 3879)"),
}


# ----------------------------------------------------------------------------------
# Instrument descriptors
# ----------------------------------------------------------------------------------

#: Planck frequency channels in GHz (LFI 30-70, HFI 100-857).
PLANCK_FREQUENCIES_GHZ = (30, 44, 70, 100, 143, 217, 353, 545, 857)

#: Planck component-separation pipelines producing full-sky CMB maps.
PLANCK_COMPONENT_METHODS = ("COMMANDER", "NILC", "SEVEM", "SMICA")

#: WMAP differencing-assembly bands, GHz.
WMAP_BANDS_GHZ = {"K": 22.8, "Ka": 33.0, "Q": 40.7, "V": 60.8, "W": 93.5}

#: Native HEALPix resolutions of the delivered maps.
NSIDE_PLANCK = 2048
NSIDE_WMAP = 512

#: Resolution used for Monte Carlo isotropy studies. Large-angle anomalies live at low l,
#: so degrading here costs nothing scientifically and saves ~1000x compute.
NSIDE_ANOMALY = 64
