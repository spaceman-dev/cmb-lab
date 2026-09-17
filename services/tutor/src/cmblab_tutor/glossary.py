"""Glossary of CMB terms.

Doubles as the knowledge base for the stage-1 chat assistant: a retrieval bot with good
source material beats a generative one with none.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Term:
    key: str
    term: str
    short: str
    long: str
    latex: str = ""
    lesson: str = ""
    section: str = ""
    aliases: list[str] = field(default_factory=list)

    def public(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "term": self.term,
            "short": self.short,
            "long": self.long,
            "latex": self.latex,
            "lesson": self.lesson,
            "section": self.section,
            "aliases": self.aliases,
        }


_ENTRIES = [
    Term(
        key="cmb",
        term="Cosmic microwave background (CMB)",
        short="The light released when the universe first became transparent, 380,000 "
        "years after the Big Bang.",
        long=(
            "Before recombination the universe was an opaque plasma: free electrons "
            "scattered photons constantly, so light could not travel far. Around 380,000 "
            "years in, expansion cooled it to roughly 3000 K, electrons and protons "
            "combined into neutral hydrogen, and the fog lifted. The light set free at "
            "that moment has been travelling ever since, stretched by expansion into "
            "microwaves at 2.7255 K. Because more distant light takes longer to arrive, "
            "what we observe is a spherical surface centred on us — the surface of last "
            "scattering. Its temperature varies by about one part in 100,000, and those "
            "variations are frozen sound waves that encode what the universe is made of."
        ),
        latex=r"T_0 = 2.7255 \pm 0.0006\ \mathrm{K}",
        lesson="origin",
        section="hot-soup",
        aliases=[
            "cmb",
            "cosmic microwave background",
            "cosmic microwave background radiation",
            "microwave background",
            "relic radiation",
            "surface of last scattering",
        ],
    ),
    Term(
        key="recombination",
        term="Recombination",
        short="When electrons and protons combined into neutral hydrogen and the universe "
        "became transparent.",
        long=(
            "At redshift z ≈ 1090, about 380,000 years after the Big Bang, the universe "
            "cooled to roughly 3000 K and free electrons combined with protons to form "
            "neutral hydrogen. Neutral hydrogen does not scatter photons at these "
            "energies, so the universe turned transparent and released the CMB. It "
            "happens far below hydrogen's 13.6 eV binding energy because photons "
            "outnumber baryons a billion to one, so even the rare energetic tail keeps "
            "hydrogen ionised until things are much cooler."
        ),
        latex=r"z_* \simeq 1090,\qquad T_* \simeq 3000\ \mathrm{K}",
        lesson="origin",
        section="hot-soup",
        aliases=[
            "recombination",
            "last scattering",
            "decoupling",
            "when the universe became transparent",
        ],
    ),
    Term(
        key="multipole",
        term="Multipole (ℓ)",
        short="An angular scale index. Roughly, θ ≈ 180°/ℓ.",
        long=(
            "The index of the spherical harmonic expansion. ℓ = 0 is the monopole (mean "
            "temperature), ℓ = 1 the dipole (our motion), ℓ = 2 the quadrupole. Large ℓ "
            "means small angular scales. The first acoustic peak at ℓ = 220 corresponds to "
            "patches about one degree across."
        ),
        latex=r"\theta \approx \frac{180°}{\ell}",
        lesson="harmonics",
        section="expansion",
        aliases=["ell", "l", "multipole moment"],
    ),
    Term(
        key="power_spectrum",
        term="Angular power spectrum (Cℓ)",
        short="The variance of the temperature field at each angular scale.",
        long=(
            "Under statistical isotropy, the variance of the harmonic coefficients cannot "
            "depend on orientation, so a single number per multipole describes everything "
            "cosmology predicts. Comparing theory to CMB data means comparing Cℓ curves."
        ),
        latex=r"\langle a_{\ell m}a^*_{\ell'm'}\rangle = C_\ell\delta_{\ell\ell'}\delta_{mm'}",
        lesson="harmonics",
        section="cl",
        aliases=["cl", "c_l", "angular power spectrum"],
    ),
    Term(
        key="dl",
        term="𝒟ℓ convention",
        short="ℓ(ℓ+1)Cℓ/2π — the power per logarithmic interval in ℓ.",
        long=(
            "Plotted instead of Cℓ because equal areas under the curve on a log axis mean "
            "equal contributions to the observed temperature variance. It also makes a "
            "scale-invariant primordial spectrum appear flat at low ℓ."
        ),
        latex=r"\mathcal{D}_\ell = \frac{\ell(\ell+1)C_\ell}{2\pi}",
        lesson="harmonics",
        section="dl-convention",
        aliases=["d_l", "dl", "d ell"],
    ),
    Term(
        key="acoustic_peak",
        term="Acoustic peak",
        short="A resonance of sound waves in the primordial photon-baryon plasma.",
        long=(
            "Before recombination, photons and baryons formed one fluid oscillating in "
            "dark matter potential wells. Modes caught at extremes of compression or "
            "rarefaction at recombination left the strongest imprint. The first peak sits "
            "at ℓ ≈ 220; its position measures the spatial flatness of the universe."
        ),
        latex=r"\ell_m \approx \ell_A(m - \varphi), \quad \ell_A = \pi D_A / r_s",
        lesson="peaks",
        section="angular-scale",
        aliases=["first peak", "acoustic oscillation", "peaks"],
    ),
    Term(
        key="sound_horizon",
        term="Sound horizon (r_s)",
        short="How far a sound wave travelled before recombination: about 144 Mpc.",
        long=(
            "Computed from atomic physics and thermodynamics rather than fitted, which "
            "makes it a standard ruler. Measuring the angle it subtends gives the geometry "
            "of the universe."
        ),
        latex=r"r_s = \int_{z_*}^{\infty}\frac{c_s(z)}{H(z)}dz",
        lesson="peaks",
        section="sound-horizon",
        aliases=["r_s", "sound horizon"],
    ),
    Term(
        key="cosmic_variance",
        term="Cosmic variance",
        short="The irreducible error from having only one universe to measure.",
        long=(
            "Multipole ℓ contains only 2ℓ+1 independent numbers, so its variance can only "
            "ever be estimated to √(2/(2ℓ+1)). At ℓ = 2 that is 63%, and no instrument "
            "will ever improve it. It is why the low-ℓ anomalies are so hard to settle."
        ),
        latex=r"\frac{\Delta C_\ell}{C_\ell} = \sqrt{\frac{2}{(2\ell+1)f_{sky}}}",
        lesson="estimator",
        section="cosmic-variance",
        aliases=["sample variance"],
    ),
    Term(
        key="cross_spectrum",
        term="Cross-spectrum",
        short="Correlating two detectors so their independent noise cancels.",
        long=(
            "An auto-spectrum contains the map's own noise, which beam deconvolution "
            "amplifies without bound. Correlating two detectors that saw the same sky but "
            "have uncorrelated noise removes the bias exactly, with no noise model. This "
            "is how every published CMB spectrum is made, and what this project does."
        ),
        latex=r"\langle a^A_{\ell m}a^{B*}_{\ell m}\rangle = C_\ell B^A_\ell B^B_\ell",
        lesson="estimator",
        section="beam-noise",
        aliases=["cross spectrum", "cross power spectrum"],
    ),
    Term(
        key="beam",
        term="Beam transfer function (bℓ)",
        short="How much the telescope smoothed the sky at each multipole.",
        long=(
            "Finite angular resolution multiplies the harmonic coefficients by bℓ, which "
            "falls roughly like a Gaussian. Recovering the true spectrum requires dividing "
            "by bℓ², which amplifies noise exponentially at high ℓ. WMAP measured its "
            "beams from observations of Jupiter."
        ),
        latex=r"B_\ell = \exp[-\ell(\ell+1)\sigma^2/2]",
        lesson="estimator",
        section="beam-noise",
        aliases=["b_l", "beam window", "beam function"],
    ),
    Term(
        key="mask",
        term="Mask",
        short="The sky cut that removes Galactic foregrounds. 1 = keep, 0 = reject.",
        long=(
            "The Milky Way is far brighter than the CMB, so about 30% of the sky must be "
            "discarded. Masking destroys harmonic orthogonality and couples multipoles, "
            "which is what the MASTER algorithm corrects. We use WMAP's KQ75 mask, keeping "
            "f_sky ≈ 0.69."
        ),
        lesson="estimator",
        section="pseudo-cl",
        aliases=["kq75", "sky cut", "f_sky"],
    ),
    Term(
        key="healpix",
        term="HEALPix",
        short="Equal-area pixelisation of the sphere used by all CMB experiments.",
        long=(
            "Hierarchical Equal Area isoLatitude Pixelisation. Every pixel has identical "
            "solid angle, which makes harmonic transforms fast and unbiased. Resolution is "
            "set by N_side; the number of pixels is 12 N_side²."
        ),
        latex=r"N_{pix} = 12 N_{side}^2",
        aliases=["nside", "n_side", "pixelisation"],
    ),
    Term(
        key="lcdm",
        term="ΛCDM",
        short="The six-parameter standard model of cosmology.",
        long=(
            "A spatially flat universe with cold dark matter and a cosmological constant. "
            "The six parameters are Ω_b h², Ω_c h², θ*, τ, n_s and A_s; H₀, Ω_m and σ₈ are "
            "derived from them. It fits the CMB remarkably well."
        ),
        lesson="inference",
        section="likelihood",
        aliases=["lambda cdm", "standard model of cosmology"],
    ),
    Term(
        key="hubble_tension",
        term="Hubble tension",
        short="CMB gives H₀ = 67.4; Cepheid distance ladders give 73.0. They disagree.",
        long=(
            "Early-universe measurements (CMB, BAO) consistently give a lower expansion "
            "rate than late-universe distance-ladder measurements, at roughly 5σ. Either "
            "one measurement has an unknown systematic, or ΛCDM is incomplete. It is the "
            "biggest open problem in observational cosmology."
        ),
        lesson="inference",
        section="degeneracies",
        aliases=["h0 tension", "hubble constant tension"],
    ),
    Term(
        key="look_elsewhere",
        term="Look-elsewhere effect",
        short="Searching many places makes rare events common. Correct for it.",
        long=(
            "If you scan thousands of axes for the most extreme alignment, extreme values "
            "appear even under the null hypothesis. Simulations must repeat the identical "
            "search, and quoting the best of several tests needs a correction such as "
            "Šidák: p_corr = 1 − (1−p)ⁿ."
        ),
        latex=r"p_{corr} = 1 - (1-p)^n",
        lesson="anomalies",
        section="look-elsewhere",
        aliases=["multiple comparisons", "trials factor", "a posteriori"],
    ),
    Term(
        key="axis_of_evil",
        term="Axis of Evil",
        short="The unexplained alignment of the CMB quadrupole and octupole.",
        long=(
            "The ℓ=2 and ℓ=3 multipoles each define a preferred axis. Under statistical "
            "isotropy they should be unrelated, giving a typical angle of 60°. Published "
            "analyses find about 10°. Whether this is new physics, a foreground residual, "
            "or a look-elsewhere artefact remains unsettled."
        ),
        lesson="anomalies",
        section="the-four",
        aliases=["quadrupole octupole alignment", "alignment"],
    ),
    Term(
        key="cold_spot",
        term="CMB Cold Spot",
        short="An unusually cold, unusually large region in the southern sky.",
        long=(
            "Found with spherical Mexican-hat wavelets at about 5° scale. A supervoid along "
            "the line of sight has been proposed, but the observed void appears too small "
            "to explain the full effect via the integrated Sachs-Wolfe mechanism."
        ),
        lesson="anomalies",
        section="the-four",
        aliases=["cold spot", "eridanus supervoid"],
    ),
    Term(
        key="silk_damping",
        term="Silk damping",
        short="Photon diffusion washing out small-scale structure.",
        long=(
            "Recombination was not instantaneous. During it, photons random-walked out of "
            "the smallest overdensities, exponentially suppressing power beyond ℓ ≈ 1000. "
            "This produces the damping tail of the spectrum."
        ),
        lesson="peaks",
        section="peak-heights",
        aliases=["diffusion damping", "damping tail"],
    ),
    Term(
        key="sachs_wolfe",
        term="Sachs–Wolfe plateau",
        short="The flat part of the spectrum below ℓ ≈ 30.",
        long=(
            "Fluctuations larger than the horizon at recombination never had time to "
            "oscillate, so they show the primordial gravitational potential almost "
            "unprocessed. A scale-invariant primordial spectrum makes 𝒟ℓ flat here, which "
            "is a direct visual test of inflation's prediction."
        ),
        lesson="harmonics",
        section="dl-convention",
        aliases=["sachs wolfe", "plateau"],
    ),
    Term(
        key="point_sources",
        term="Unresolved point sources",
        short="Faint galaxies adding a flat Cℓ that grows as ℓ² in 𝒟ℓ.",
        long=(
            "Below the detection threshold, extragalactic radio sources form a Poisson "
            "field with a flat angular power spectrum. Cross-spectra cancel detector noise "
            "but not real sky signal, so this survives and dominates the residual above "
            "ℓ ≈ 350. Subtracting it took our χ²/dof from 32 to 1."
        ),
        latex=r"C_\ell^{ps} = A_{ps}, \quad \mathcal{D}_\ell^{ps} \propto \ell^2",
        lesson="estimator",
        section="beam-noise",
        aliases=["point source", "poisson sources"],
    ),
]

GLOSSARY: dict[str, Term] = {entry.key: entry for entry in _ENTRIES}


#: Words too common to carry meaning. Without this filter, "what is the airspeed of a
#: swallow" matches "Axis of Evil" on the word "of".
_STOPWORDS = frozenset(
    {
        "the",
        "is",
        "of",
        "and",
        "in",
        "to",
        "a",
        "an",
        "for",
        "on",
        "at",
        "by",
        "it",
        "as",
        "be",
        "are",
        "was",
        "we",
        "do",
        "does",
        "did",
        "how",
        "why",
        "what",
        "which",
        "that",
        "this",
        "with",
        "from",
        "can",
        "you",
        "me",
        "my",
        "our",
        "its",
        "has",
        "have",
        "about",
        "tell",
        "explain",
        "mean",
        "means",
    }
)


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def _significant(text: str) -> list[str]:
    """Words that carry meaning, with stopwords dropped.

    Applied to term names as well as the query: comparing a stopword-stripped query
    against a raw name means "Axis of Evil" never matches the term of that name.
    """
    return [w for w in _words(text) if len(w) > 1 and w not in _STOPWORDS]


def search_glossary(query: str, limit: int = 6) -> list[dict[str, Any]]:
    """Rank glossary terms against a question.

    Scoring is word-based rather than substring-based. Substring matching made "cosmic
    microwave background" rank "Cosmic variance" first (it contains "cosmic") and "what is
    cmb" rank "CMB Cold Spot" (it contains "cmb"), which is exactly backwards.

    The ranking is driven by two ideas:
      * an exact match against a term name or alias should dominate everything else, and
      * a candidate is penalised for the words in *its own name* that the query never
        mentioned, so a short precise term beats a longer one it happens to be a prefix of.
    """
    tokens = _significant(query)
    if not tokens:
        return []

    token_set = set(tokens)
    phrase = " ".join(tokens)

    scored: list[tuple[float, Term]] = []
    for entry in GLOSSARY.values():
        names = [entry.term, entry.key, *entry.aliases]
        score = 0.0

        # Whole query is exactly a name: unambiguous, outrank everything.
        if any(phrase == " ".join(_significant(n)) for n in names):
            score += 100

        # Whole query appears inside a name, or a name inside the query.
        for name in names:
            name_phrase = " ".join(_significant(name))
            if not name_phrase:
                continue
            if name_phrase in phrase or phrase in name_phrase:
                score += 25

        # Word overlap against names, normalised by the name's own length so a one-word
        # hit on a two-word term does not beat a full match on a one-word term.
        best_name = 0.0
        for name in names:
            nw = set(_significant(name))
            if not nw:
                continue
            hit = token_set & nw
            if hit:
                coverage = len(hit) / len(nw)
                best_name = max(best_name, 10 * len(hit) * coverage)
        score += best_name

        # Definition text is weak evidence; it should only break ties.
        body = set(_words(f"{entry.short} {entry.long}"))
        score += 0.5 * len(token_set & body)

        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda pair: (-pair[0], pair[1].term))
    return [{**entry.public(), "score": round(score, 2)} for score, entry in scored[:limit]]
