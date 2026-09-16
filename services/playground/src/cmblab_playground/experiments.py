"""The playground: change one thing, see what happens, understand why.

Every knob here corresponds to a real decision in the analysis, and each one is documented
with what it does physically and what you should expect to see. The most instructive
experiments are the ones that *break* the result — turning off the beam deconvolution and
watching the acoustic peaks vanish teaches more than reading about beam transfer functions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Knob:
    id: str
    label: str
    kind: str  # select | number | boolean
    default: Any
    options: list[Any] = field(default_factory=list)
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    physics: str = ""
    watch_for: str = ""

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "default": self.default,
            "options": self.options,
            "min": self.minimum,
            "max": self.maximum,
            "step": self.step,
            "physics": self.physics,
            "watch_for": self.watch_for,
        }


SPECTRUM_KNOBS = [
    Knob(
        id="product_a",
        label="Detector A",
        kind="select",
        default="da-v1",
        options=["da-v1", "da-v2", "da-w1", "da-w2", "da-q1", "da-q2"],
        physics=(
            "Which WMAP differencing assembly to use. Q band is 41 GHz, V band 61 GHz, "
            "W band 94 GHz. Lower frequencies carry more Galactic synchrotron; higher "
            "frequencies more dust."
        ),
        watch_for=(
            "Pair two detectors from the same band and the answer barely changes. That "
            "stability across independent instruments is what tells you the signal is "
            "cosmological rather than instrumental."
        ),
    ),
    Knob(
        id="product_b",
        label="Detector B",
        kind="select",
        default="da-v2",
        options=["da-v1", "da-v2", "da-w1", "da-w2", "da-q1", "da-q2"],
        physics=(
            "The second map in the cross-correlation. It must have independent noise — "
            "that is the entire reason the estimator is unbiased."
        ),
        watch_for=(
            "Set A and B to the SAME detector and you get an auto-spectrum. Watch the "
            "high-ℓ end turn upward as the noise stops cancelling."
        ),
    ),
    Knob(
        id="mask_product",
        label="Galactic mask",
        kind="select",
        default="mask-kq75",
        options=["mask-kq75", "mask-kq85", "none"],
        physics=(
            "KQ75 keeps 69% of the sky and is conservative. KQ85 keeps 82% — more modes, "
            "smaller error bars, but more Galactic residual leaks in. 'none' uses the full "
            "sky including the Milky Way."
        ),
        watch_for=(
            "With no mask the Galactic plane dominates completely and the acoustic peaks "
            "disappear under foreground power. This is why 30% of the sky gets thrown away."
        ),
    ),
    Knob(
        id="lmax",
        label="Maximum multipole",
        kind="number",
        default=800,
        minimum=100,
        maximum=1500,
        step=50,
        physics=(
            "How far into small angular scales to compute. WMAP's V-band beam and noise "
            "set a practical ceiling around ℓ ≈ 650."
        ),
        watch_for=(
            "Push beyond 800 and the signal-to-noise cut kicks in, removing bandpowers "
            "rather than showing you noise dressed up as data."
        ),
    ),
    Knob(
        id="binning",
        label="Bandpower binning",
        kind="select",
        default="linear:30",
        options=["linear:15", "linear:30", "linear:50", "log:20", "planck"],
        physics=(
            "Averaging neighbouring multipoles trades angular resolution for "
            "signal-to-noise. Each bandpower averages 2ℓ+1 weighted modes."
        ),
        watch_for=(
            "Narrow bins show more structure but noisier points; wide bins are smooth but "
            "can smear the peaks. Notice the error bars shrink as √(number of modes)."
        ),
    ),
    Knob(
        id="subtract_point_sources",
        label="Subtract point sources",
        kind="boolean",
        default=True,
        physics=(
            "Unresolved radio galaxies form a Poisson field with flat Cℓ, which grows as "
            "ℓ² in 𝒟ℓ. Cross-spectra cancel detector noise but not real sky signal."
        ),
        watch_for=(
            "Turn this OFF and watch the spectrum lift away from ΛCDM above ℓ ≈ 350, with "
            "χ²/dof jumping from about 1 to about 32. This single term is the difference "
            "between agreement and disagreement."
        ),
    ),
    Knob(
        id="apply_pixwin",
        label="Pixel window correction",
        kind="boolean",
        default=True,
        physics=(
            "HEALPix pixels have finite size, which smooths the sky slightly — a second, "
            "smaller beam on top of the instrument's."
        ),
        watch_for=(
            "A subtle few-percent tilt at high ℓ. Small, but it is the kind of systematic "
            "that shifts a fitted parameter by a fraction of a sigma."
        ),
    ),
]

THEORY_KNOBS = [
    Knob(
        id="H0",
        label="H₀  (km/s/Mpc)",
        kind="number",
        default=67.36,
        minimum=55,
        maximum=85,
        step=0.5,
        physics=(
            "The present expansion rate. With the physical densities Ω_b h² and Ω_c h² held "
            "fixed, raising H₀ shrinks the comoving distance to last scattering."
        ),
        watch_for=(
            "The sound horizon is a fixed length. Put it at a shorter distance and it "
            "subtends a LARGER angle, so the peaks move to LOWER ℓ — ℓ = 225 at H₀ = 60, "
            "ℓ = 213 at H₀ = 80. Try 73, the value local distance-ladder measurements "
            "prefer, and see how badly it fits. That mismatch is the Hubble tension."
        ),
    ),
    Knob(
        id="ombh2",
        label="Ω_b h²  (baryons)",
        kind="number",
        default=0.02237,
        minimum=0.017,
        maximum=0.027,
        step=0.0005,
        physics=(
            "Baryon density. Baryons add inertia to the photon-baryon fluid, deepening "
            "compressions relative to rarefactions."
        ),
        watch_for=(
            "Raise it and odd peaks (1st, 3rd) grow while even peaks (2nd) shrink. The "
            "first-to-second peak ratio is a direct weighing of ordinary matter — and it "
            "agrees with Big Bang nucleosynthesis, which knows nothing about the CMB."
        ),
    ),
    Knob(
        id="omch2",
        label="Ω_c h²  (cold dark matter)",
        kind="number",
        default=0.1200,
        minimum=0.09,
        maximum=0.15,
        step=0.002,
        physics=(
            "Dark matter density. It sets when the universe stopped being radiation "
            "dominated, which controls how much the gravitational potentials decayed."
        ),
        watch_for=(
            "Lower it and the first peak grows dramatically through the early integrated "
            "Sachs-Wolfe effect. The observed peak heights need substantial non-baryonic "
            "matter — you cannot fit this spectrum with baryons alone."
        ),
    ),
    Knob(
        id="ns",
        label="n_s  (spectral index)",
        kind="number",
        default=0.9649,
        minimum=0.88,
        maximum=1.05,
        step=0.005,
        physics=(
            "The tilt of the primordial power spectrum. n_s = 1 is exactly scale "
            "invariant; inflation predicts slightly less."
        ),
        watch_for=(
            "Tilts the whole curve about its pivot. The measured value is 0.965, about 8σ "
            "away from exactly 1 — one of the strongest quantitative confirmations of "
            "inflation we have."
        ),
    ),
    Knob(
        id="tau",
        label="τ  (reionization optical depth)",
        kind="number",
        default=0.0544,
        minimum=0.01,
        maximum=0.15,
        step=0.005,
        physics=(
            "How much the CMB was re-scattered when the first stars reionized the "
            "universe. It suppresses power by e^(−2τ) above ℓ ≈ 40."
        ),
        watch_for=(
            "Changes the overall amplitude but barely the shape — which is exactly why it "
            "is degenerate with A_s and why TT data alone cannot measure it."
        ),
    ),
]

EXPERIMENTS: list[dict[str, Any]] = [
    {
        "id": "noise-bias",
        "title": "Why cross-spectra exist",
        "question": "What happens if you use one detector instead of two?",
        "difficulty": "essential",
        "baseline": {"product_a": "da-v1", "product_b": "da-v2"},
        "variant": {"product_a": "da-v1", "product_b": "da-v1"},
        "expect": (
            "The auto-spectrum (A = B) turns sharply upward past ℓ ≈ 400. That rise is not "
            "cosmology — it is the detector's own noise, amplified by beam deconvolution. "
            "Using two detectors makes the noise term vanish by construction."
        ),
        "lesson": "estimator#beam-noise",
    },
    {
        "id": "point-sources",
        "title": "The last 3%",
        "question": "How much do unresolved radio galaxies matter?",
        "difficulty": "essential",
        "baseline": {"subtract_point_sources": True},
        "variant": {"subtract_point_sources": False},
        "expect": (
            "Without the correction the spectrum drifts above ΛCDM in a way that grows as "
            "ℓ². χ²/dof goes from about 1 to about 32. Cross-spectra remove noise, but "
            "point sources are real sky and survive."
        ),
        "lesson": "estimator#beam-noise",
    },
    {
        "id": "mask-matters",
        "title": "The Galaxy is in the way",
        "question": "What if you keep the Milky Way?",
        "difficulty": "essential",
        "baseline": {"mask_product": "mask-kq75"},
        "variant": {"mask_product": "none"},
        "expect": (
            "Galactic synchrotron and dust are orders of magnitude brighter than the CMB. "
            "Without a mask the low-ℓ end explodes and the acoustic structure is buried."
        ),
        "lesson": "estimator#pseudo-cl",
    },
    {
        "id": "frequency-check",
        "title": "Is it really cosmological?",
        "question": "Do two different frequency bands agree?",
        "difficulty": "intermediate",
        "baseline": {"product_a": "da-v1", "product_b": "da-v2"},
        "variant": {"product_a": "da-w1", "product_b": "da-w2"},
        "expect": (
            "V band is 61 GHz, W band is 94 GHz — different optics, different detectors, "
            "different foreground contamination. They give ℓ = 220 and ℓ = 218. Foregrounds "
            "are strongly frequency dependent; the CMB is not. This is the check."
        ),
        "lesson": "estimator#beam-noise",
    },
    {
        "id": "hubble-tension",
        "title": "Can the CMB accommodate H₀ = 73?",
        "question": "Set H₀ to the local distance-ladder value and look at the fit.",
        "difficulty": "intermediate",
        "kind": "theory",
        "baseline": {"H0": 67.36},
        "variant": {"H0": 73.04},
        "expect": (
            "Every acoustic peak shifts to LOWER ℓ, because a shorter distance to last "
            "scattering makes the fixed sound horizon subtend a larger angle. The fit "
            "degrades badly. You can partly compensate by raising Ω_c h² — that is the "
            "geometric degeneracy — but not fully. This is the Hubble tension from the "
            "CMB side."
        ),
        "lesson": "inference#degeneracies",
    },
    {
        "id": "baryon-ratio",
        "title": "Weighing ordinary matter",
        "question": "How do baryons change the peak pattern?",
        "difficulty": "intermediate",
        "kind": "theory",
        "baseline": {"ombh2": 0.02237},
        "variant": {"ombh2": 0.026},
        "expect": (
            "More baryons deepen compressions: the first and third peaks rise while the "
            "second is suppressed. The odd-to-even peak ratio is a direct measurement of "
            "the baryon density, and it agrees with Big Bang nucleosynthesis."
        ),
        "lesson": "peaks#peak-heights",
    },
    {
        "id": "no-dark-matter",
        "title": "What if there were no dark matter?",
        "question": "Drop Ω_c h² towards zero and watch the spectrum fall apart.",
        "difficulty": "advanced",
        "kind": "theory",
        "baseline": {"omch2": 0.1200},
        "variant": {"omch2": 0.09},
        "expect": (
            "With less dark matter the potentials decay more, driving the oscillations "
            "harder and boosting the first peak while damping the third. The observed peak "
            "heights simply cannot be reproduced without a substantial non-baryonic "
            "component."
        ),
        "lesson": "peaks#peak-heights",
    },
    {
        "id": "scale-invariance",
        "title": "Testing inflation's tilt",
        "question": "Is the primordial spectrum exactly scale invariant?",
        "difficulty": "advanced",
        "kind": "theory",
        "baseline": {"ns": 0.9649},
        "variant": {"ns": 1.0},
        "expect": (
            "n_s = 1 is the Harrison–Zel'dovich spectrum: perfectly scale invariant. The "
            "data prefer 0.965, about 8σ away. That small tilt is a genuine quantitative "
            "prediction of inflation, and it is confirmed."
        ),
        "lesson": "harmonics#dl-convention",
    },
]


def get_experiment(experiment_id: str) -> dict[str, Any]:
    for experiment in EXPERIMENTS:
        if experiment["id"] == experiment_id:
            return experiment
    raise KeyError(f"Unknown experiment {experiment_id!r}. Known: {[e['id'] for e in EXPERIMENTS]}")
