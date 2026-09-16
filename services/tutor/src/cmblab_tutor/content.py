"""The curriculum: derivations of every piece of physics this project uses.

Written for a physics-literate reader who has never done a CMB analysis. The style is
deliberately Feynman-ish: build the idea physically first, only then write the equation,
and never skip the step where you say *why* the equation looks the way it does.

The material is layered so nobody has to drink from the firehose. Every section can be read
at three depths, and the reader chooses:

  * **Plain English** — ``Section.plain``: the whole idea in a few sentences, no symbols.
  * **Equations**      — each one carries a gloss for *every* variable in it, plus an
    ``intuition`` paragraph that motivates its shape using only high-school physics
    (waves, springs, gravity, geometry). No step requires more than basic calculus.
  * **Full derivation** — the numbered ``Step`` chain, for readers who want the algebra.

So each section carries:
  * ``plain``      — jargon-free summary, the default view
  * ``narrative``  — prose with inline LaTeX, rendered in the browser
  * ``narration``  — the same idea as speakable plain text, for the audio explainer
  * ``equations``  — display equations, each with variable glosses and an intuition
  * ``derivation`` — numbered steps, each with the reason it follows from the last
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Var:
    """One symbol from an equation, in plain words.

    ``symbol`` is LaTeX (rendered inline). ``meaning`` must be readable by someone who has
    not met the symbol before — say what it *is*, not just what it is called.
    """

    symbol: str
    meaning: str
    units: str = ""


@dataclass(slots=True)
class Equation:
    latex: str
    label: str = ""
    explain: str = ""
    #: Every symbol that appears above, glossed. Nothing should be left unexplained.
    variables: list[Var] = field(default_factory=list)
    #: Why the equation has this shape, argued from high-school physics only.
    intuition: str = ""


@dataclass(slots=True)
class Step:
    n: int
    latex: str
    reason: str


@dataclass(slots=True)
class Section:
    id: str
    title: str
    narrative: str
    narration: str
    #: Jargon-free summary shown first. A reader should be able to stop here and still
    #: have learned something true.
    plain: str = ""
    equations: list[Equation] = field(default_factory=list)
    derivation: list[Step] = field(default_factory=list)
    #: Keys resolved at request time against live pipeline results.
    live: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Lesson:
    id: str
    title: str
    subtitle: str
    duration_min: int
    prerequisites: list[str] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)

    def public(self) -> dict[str, Any]:
        return asdict(self)

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "subtitle": self.subtitle,
            "duration_min": self.duration_min,
            "prerequisites": self.prerequisites,
            "n_sections": len(self.sections),
            "sections": [{"id": s.id, "title": s.title} for s in self.sections],
        }


# ══════════════════════════════════════════════════════════════════════════════
# 1. What the CMB actually is
# ══════════════════════════════════════════════════════════════════════════════

LESSON_ORIGIN = Lesson(
    id="origin",
    title="Where the light comes from",
    subtitle="Recombination, last scattering, and why there is a wall of light around us",
    duration_min=12,
    sections=[
        Section(
            id="hot-soup",
            title="The universe used to be a fog",
            plain=(
                "The early universe was so hot that atoms could not hold together. Light "
                "could not travel in a straight line — it bounced off loose electrons "
                "constantly, like light inside thick fog. About 380,000 years in, things "
                "cooled enough for electrons and protons to stick together as hydrogen, "
                "and the fog cleared all at once. The light set free at that moment has "
                "been flying ever since, and it is still arriving today. That is the CMB. "
                "Because light from farther away takes longer to reach us, what we see is "
                "a *shell* around us — the set of places whose fog-clearing light is only "
                "now landing in our telescopes."
            ),
            narrative=r"""
Here is the whole story in one sentence: **the early universe was opaque, then it became
transparent, and the light released at that instant is still arriving.**

Run the expansion backwards. Every length scale shrinks, so the same photons are squeezed
into a smaller volume and each one is blueshifted. Temperature scales as $T \propto 1/a$
where $a$ is the scale factor. Today $T_0 = 2.7255\,\mathrm{K}$. At redshift $z$, it was
$T = T_0(1+z)$.

Push back to $z \approx 1100$ and the temperature is about $3000\,\mathrm{K}$. That number
matters enormously, because it is roughly the temperature at which hydrogen stops being
ionised.

Above it, every atom that forms is immediately blasted apart by a photon. The universe is a
plasma of free electrons and protons, and free electrons scatter photons ferociously
(Thomson scattering). A photon travels a tiny distance, scatters, travels, scatters. It is
a fog — like being inside the Sun. You cannot see through it.

Below it, electrons and protons combine into neutral hydrogen. Neutral hydrogen does not
scatter photons at these energies. The fog lifts, in cosmic terms, almost instantly.

The photons that were scattering off that last electron before the fog lifted have been
travelling freely ever since. That is the CMB. When you look at it you are looking at a
**surface**, not a volume: the set of points from which light is only now reaching us,
which is a sphere centred on you. Cosmologists call it the surface of last scattering.
""",
            narration="""
Here is the whole story in one sentence. The early universe was opaque, then it became
transparent, and the light released at that instant is still arriving today.
Run the expansion backwards. Everything gets squeezed, and photons get blue shifted, so the
temperature rises as the universe shrinks. Today the temperature is 2.7255 kelvin. Go back
to a redshift of about eleven hundred, and it was about three thousand kelvin.
That number matters, because three thousand kelvin is roughly where hydrogen stops being
ionised. Above it, any atom that forms is immediately smashed apart, so the universe is a
plasma of free electrons and protons. Free electrons scatter photons ferociously. The
universe is a fog. You cannot see through it, just like you cannot see into the Sun.
Below three thousand kelvin, electrons and protons combine into neutral hydrogen, and
neutral hydrogen does not scatter these photons. The fog lifts, almost instantly in cosmic
terms. The photons that scattered off that very last electron have been flying freely ever
since. That light is the cosmic microwave background.
The key thing to understand is that you are looking at a surface, not a volume. It is the
set of points whose light is only now reaching you, which is a sphere centred on you. We
call it the surface of last scattering.
""",
            equations=[
                Equation(
                    latex=r"T(z) = T_0 (1 + z), \qquad T_0 = 2.7255 \pm 0.0006\ \mathrm{K}",
                    label="Temperature scaling",
                    explain=(
                        "Expansion stretches wavelengths, so a blackbody stays a blackbody "
                        "but cools as 1/a. The measured T₀ is from COBE/FIRAS, still the "
                        "most perfect blackbody ever measured."
                    ),
                    variables=[
                        Var("T(z)", "temperature of the radiation back when the universe "
                                     "was at redshift z", "K"),
                        Var("T_0", "temperature we measure today — 2.7255 K, just above "
                                    "absolute zero", "K"),
                        Var("z", "redshift: how much the universe has stretched since then. "
                                 "z = 0 is now; z = 1 means everything was half its "
                                 "present size"),
                    ],
                    intuition=(
                        "You already know that a wave's energy goes up as its wavelength "
                        "gets shorter (E = hc/λ). Expansion does the opposite: it stretches "
                        "every wavelength in step with the universe. Stretch a photon by a "
                        "factor (1+z) and you divide its energy by (1+z). Temperature is "
                        "just average energy per particle, so it falls by the same factor. "
                        "Read the formula backwards — go back in time and the universe was "
                        "hotter by exactly the factor it was smaller."
                    ),
                ),
                Equation(
                    latex=r"z_* \simeq 1090, \qquad T_* \simeq 2970\ \mathrm{K}, "
                    r"\qquad t_* \simeq 380{,}000\ \mathrm{yr}",
                    label="Last scattering",
                    explain=(
                        "Recombination happens well below hydrogen's 13.6 eV binding energy "
                        "because photons hugely outnumber baryons — roughly 10⁹ to 1 — so "
                        "even the rare high-energy tail keeps hydrogen ionised."
                    ),
                    variables=[
                        Var("z_*", "the redshift when the fog lifted. The star subscript "
                                   "always means 'at last scattering'"),
                        Var("T_*", "temperature at that moment — about 3000 K, roughly the "
                                   "surface of a cool star", "K"),
                        Var("t_*", "how long after the Big Bang it happened", "yr"),
                    ],
                    intuition=(
                        "Hydrogen needs 13.6 eV to ionise, which corresponds to about "
                        "160,000 K — so why did the fog only lift at 3000 K? Because there "
                        "are a billion photons for every atom. Even when the *average* "
                        "photon is far too weak to ionise hydrogen, the rare energetic ones "
                        "in the tail of the distribution are still numerous enough to keep "
                        "tearing atoms apart. You have to cool until even that billion-to-"
                        "one tail runs dry, which costs you a factor of about 40 in "
                        "temperature."
                    ),
                ),
            ],
            derivation=[
                Step(
                    1,
                    r"n_\gamma / n_b \sim 10^9",
                    "Photons outnumber baryons by a billion to one, measured from Ω_b h².",
                ),
                Step(
                    2,
                    r"N(>13.6\,\mathrm{eV}) \propto e^{-13.6\,\mathrm{eV}/k_BT}",
                    "The Wien tail holds the few photons energetic enough to ionise hydrogen.",
                ),
                Step(
                    3,
                    r"e^{-13.6/k_BT} \sim 10^{-9} \implies k_BT \sim 0.3\ \mathrm{eV}",
                    "Recombination waits until even that billion-to-one tail is exhausted.",
                ),
                Step(
                    4,
                    r"T \sim 0.3\,\mathrm{eV}/k_B \approx 3000\ \mathrm{K}",
                    "Which is far colder than 13.6 eV would naively suggest. The photon-to-"
                    "baryon ratio is what delays recombination by a factor of about 40.",
                ),
            ],
        ),
        Section(
            id="anisotropies",
            title="The bumps are sound",
            plain=(
                "The CMB is not perfectly smooth: some patches are a hair hotter than "
                "others, by about one part in 100,000. Those patches are sound waves, "
                "frozen mid-ring. Before the fog cleared, gravity was pulling gas into "
                "clumps while pressure pushed back out — the same push-and-pull that makes "
                "a plucked guitar string vibrate. When the fog cleared, the vibration "
                "stopped instantly and the pattern froze. Hot spots are where the gas was "
                "caught mid-squeeze, cold spots where it was caught mid-stretch. So the "
                "CMB is a photograph of sound."
            ),
            narrative=r"""
The CMB is almost perfectly uniform. Almost. After removing the dipole caused by our own
motion, what remains are fluctuations of about $70\ \mu\mathrm{K}$ against a
$2.7\ \mathrm{K}$ background — one part in $10^5$.

Those bumps are not random noise. They are **standing sound waves**.

Think about what the plasma actually was: photons and baryons tightly coupled by Thomson
scattering, behaving as a single fluid. Dark matter, which does not couple to photons, had
already begun clumping under gravity, creating potential wells.

Now the fluid falls into a well. Gravity pulls it in; as it compresses, photon pressure
pushes back. In it falls, out it bounces, in again — an oscillation. A well of a given size
has a characteristic oscillation period, exactly like an organ pipe of a given length has a
characteristic note.

Then, at recombination, the photons are released. Whatever phase each oscillation happened
to be in at that moment is frozen into the temperature pattern forever. Regions caught at
maximum compression are hot; regions caught at maximum rarefaction are cold.

So the CMB anisotropy pattern is a photograph of a standing wave field at the instant the
music stopped. Measuring which wavelengths are loudest — which is exactly what a power
spectrum does — tells you the composition and geometry of the universe that was ringing.
""",
            narration="""
The cosmic microwave background is almost perfectly uniform, but not quite. After removing
the dipole caused by our own motion through space, what is left are fluctuations of about
seventy microkelvin on a background of 2.7 kelvin. That is one part in a hundred thousand.
Those bumps are not random noise. They are standing sound waves.
Think about what the plasma actually was. Photons and baryons, tightly coupled by
scattering, behaving as a single fluid. Dark matter, which does not feel the photons, had
already started clumping under gravity, creating wells in the gravitational potential.
Now the fluid falls into a well. Gravity pulls it in, and as it compresses, photon pressure
pushes back out. In it falls, out it bounces, in again. An oscillation. And a well of a
given size has a characteristic period, exactly like an organ pipe of a given length has a
characteristic note.
Then recombination happens and the photons are released. Whatever phase each oscillation
was in at that moment gets frozen into the temperature pattern forever. Regions caught at
maximum compression are hot. Regions caught at maximum rarefaction are cold.
So the pattern you see is a photograph of a standing wave field at the instant the music
stopped. Measuring which wavelengths are loudest, which is exactly what a power spectrum
does, tells you the composition and the geometry of the universe that was ringing.
""",
            equations=[
                Equation(
                    latex=r"\frac{\Delta T}{T} \sim 10^{-5}",
                    label="Anisotropy amplitude",
                    explain=(
                        "Small enough that linear perturbation theory works beautifully, "
                        "which is why the CMB is such a clean cosmological probe."
                    ),
                    variables=[
                        Var("\\Delta T", "how much hotter or colder one patch of sky is than "
                                         "the average", "K"),
                        Var("T", "the average temperature, 2.7255 K", "K"),
                    ],
                    intuition=(
                        "One part in 100,000 is the thickness of a human hair compared to a "
                        "football pitch. This tininess is a gift: when ripples are this "
                        "small, effects simply add up instead of tangling together, so the "
                        "mathematics stays linear — double the cause, double the effect. "
                        "That is why the CMB can be predicted to a fraction of a percent "
                        "while galaxy formation, where lumps are huge, needs supercomputers."
                    ),
                ),
                Equation(
                    latex=r"c_s = \frac{c}{\sqrt{3(1+R)}}, \qquad "
                    r"R \equiv \frac{3\rho_b}{4\rho_\gamma}",
                    label="Sound speed in the photon-baryon fluid",
                    explain=(
                        "A pure photon gas has c_s = c/√3. Baryons add inertia without "
                        "pressure, so loading the fluid with baryons slows the sound and "
                        "deepens the compressions — which is how the spectrum measures Ω_b."
                    ),
                    variables=[
                        Var("c_s", "the speed of sound in the early-universe plasma", "m/s"),
                        Var("c", "the speed of light", "m/s"),
                        Var("R", "how heavily the fluid is 'loaded' with ordinary matter — "
                                 "the ratio of baryon inertia to photon inertia"),
                        Var("\\rho_b", "density of baryons: ordinary matter, protons and "
                                       "neutrons", "kg/m³"),
                        Var("\\rho_\\gamma", "density of the photons — the light itself",
                            "kg/m³"),
                    ],
                    intuition=(
                        "From high school: sound travels faster when a medium is stiffer, "
                        "and slower when it is heavier — v = √(stiffness / density). In "
                        "this plasma the *stiffness* comes entirely from photon pressure, "
                        "and photons alone give the famous c/√3. Now add baryons. They "
                        "bring mass but essentially no pressure, so they make the fluid "
                        "heavier without making it stiffer — exactly like taping coins to a "
                        "guitar string. The note drops. That is the (1+R) in the "
                        "denominator, and it is the handle the CMB gives us on how much "
                        "ordinary matter the universe contains."
                    ),
                ),
            ],
            live=["map_rms", "map_nside"],
        ),
    ],
)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Spherical harmonics and the power spectrum
# ══════════════════════════════════════════════════════════════════════════════

LESSON_HARMONICS = Lesson(
    id="harmonics",
    title="Fourier analysis on a sphere",
    subtitle="Why $a_{\\ell m}$, why $C_\\ell$, and why everyone plots $\\ell(\\ell+1)C_\\ell/2\\pi$",
    duration_min=15,
    prerequisites=["origin"],
    sections=[
        Section(
            id="expansion",
            title="The right basis for a sphere",
            plain=(
                "A sound engineer does not describe music by listing the position of the "
                "speaker cone every millisecond — they show which frequencies are loud. We "
                "do the same for the sky. Instead of listing a temperature for each of the "
                "millions of pixels, we ask: how much of the pattern is big blobs, and how "
                "much is fine speckle? Spherical harmonics are the tool for that. They are "
                "the natural 'notes' of a sphere, just as sine waves are the natural notes "
                "of a string. Each one has a number ℓ telling you how fine it is: low ℓ is "
                "broad patches, high ℓ is fine detail."
            ),
            narrative=r"""
On a flat surface you decompose a field into plane waves. On a sphere, plane waves are the
wrong tool — they do not fit. The functions that do fit are the **spherical harmonics**
$Y_{\ell m}$, which are eigenfunctions of the Laplacian on the sphere:

$$\nabla^2_{S^2} Y_{\ell m} = -\ell(\ell+1) Y_{\ell m}$$

That eigenvalue is the whole reason they are useful. Any rotationally-invariant physics —
and gravity on the sky is rotationally invariant — cannot mix different $\ell$. So the
expansion coefficients organise themselves by $\ell$ and stay organised.

The index $\ell$ tells you the angular scale, roughly $\theta \approx 180°/\ell$. The index
$m$ tells you the orientation within that scale, and runs over $2\ell+1$ values from
$-\ell$ to $+\ell$. A multipole $\ell$ therefore has $2\ell+1$ independent numbers.

Two special cases you already know: $\ell=0$ is the monopole, the average temperature
$2.7255\,\mathrm{K}$. $\ell=1$ is the dipole, $3362\,\mu\mathrm{K}$, which is not
primordial at all — it is the Doppler shift from our motion through the CMB rest frame at
about $370\ \mathrm{km/s}$. Both get removed before any analysis begins.
""",
            narration="""
On a flat surface you decompose a field into plane waves. On a sphere, plane waves are the
wrong tool. They simply do not fit. The functions that do fit are the spherical harmonics,
which are the eigenfunctions of the Laplacian on the sphere, with eigenvalue minus ell
times ell plus one.
That eigenvalue is the whole reason they are useful. Any rotationally invariant physics,
and gravity on the sky is rotationally invariant, cannot mix different values of ell. So
the expansion coefficients organise themselves by ell, and they stay organised.
The index ell tells you the angular scale, roughly one hundred eighty degrees divided by
ell. The index m tells you the orientation within that scale, and it runs over two ell plus
one values. So a multipole ell has two ell plus one independent numbers in it.
Two special cases you already know. Ell equals zero is the monopole, the average
temperature, 2.7255 kelvin. Ell equals one is the dipole, about three thousand three
hundred microkelvin, and it is not primordial at all. It is the Doppler shift from our own
motion through the cosmic rest frame at about three hundred seventy kilometres per second.
Both of those get removed before any analysis begins.
""",
            equations=[
                Equation(
                    latex=r"\frac{\Delta T(\hat{n})}{T_0} = "
                    r"\sum_{\ell=0}^{\infty}\sum_{m=-\ell}^{\ell} a_{\ell m} Y_{\ell m}(\hat{n})",
                    label="Harmonic expansion",
                    explain="The complete description of a scalar field on a sphere.",
                    variables=[
                        Var("\\hat{n}", "a direction on the sky — a unit vector, i.e. which "
                                        "way the telescope is pointing"),
                        Var("\\Delta T(\\hat{n})", "how much hotter or colder that direction "
                                                  "is than the sky average", "K"),
                        Var("T_0", "the average temperature, 2.7255 K", "K"),
                        Var("\\ell", "multipole — how fine the pattern is. ℓ = 2 is two big "
                                     "lobes across the sky; ℓ = 220 is patches about 1° "
                                     "wide. Roughly, angle ≈ 180° / ℓ"),
                        Var("m", "orientation of that pattern — how it is rotated about the "
                                 "poles. For each ℓ there are 2ℓ+1 choices"),
                        Var("Y_{\\ell m}", "a spherical harmonic: one fixed ripple pattern "
                                           "on the sphere — the sphere's version of a sine "
                                           "wave"),
                        Var("a_{\\ell m}", "how much of that particular ripple the real sky "
                                           "contains — its amplitude, like a volume slider"),
                    ],
                    intuition=(
                        "This is a Fourier series wrapped onto a ball. On a guitar string "
                        "you can write any shape as a sum of sine waves; on a sphere you "
                        "can write any pattern as a sum of Y_ℓm. The double sum says: take "
                        "every possible ripple pattern, dial each one up or down by its own "
                        "amount a_ℓm, add them all together, and you have rebuilt the sky "
                        "exactly. Nothing is lost — it is a change of description, not an "
                        "approximation."
                    ),
                ),
                Equation(
                    latex=r"a_{\ell m} = \int d\Omega\ "
                    r"\frac{\Delta T(\hat{n})}{T_0} Y^*_{\ell m}(\hat{n})",
                    label="Inverse transform",
                    explain=(
                        "Orthonormality of the Y_ℓm gives the coefficients directly. "
                        "In code this is healpy's map2alm."
                    ),
                    variables=[
                        Var("a_{\\ell m}", "the amplitude we are trying to extract"),
                        Var("\\int d\\Omega", "integrate over the whole sky — in practice, "
                                             "sum over every pixel in the map"),
                        Var("Y^*_{\\ell m}", "the complex conjugate of the ripple pattern. "
                                             "The star is just bookkeeping for complex "
                                             "numbers"),
                    ],
                    intuition=(
                        "How do you work out how much of one note is in a chord? Multiply "
                        "the signal by that note and average. Where the wiggles line up "
                        "they reinforce and survive the average; where they do not, they "
                        "cancel to zero. That is exactly what this integral does — it is a "
                        "filter asking the sky 'how much of *this* pattern do you contain?' "
                        "and getting one number back. It works because different harmonics "
                        "are orthogonal: multiply two different ones, average over the "
                        "sphere, and you get precisely zero."
                    ),
                ),
            ],
        ),
        Section(
            id="cl",
            title="Statistical isotropy collapses everything into one number per scale",
            plain=(
                "We only have one universe, so we cannot rerun it to see which patterns are "
                "typical. The saving idea: theory never predicts *this* hot spot here — it "
                "predicts how strong the ripples are on average at each size. And if the "
                "universe has no preferred direction, the strength can only depend on the "
                "*size* of a ripple, not its orientation. So the whole sky collapses to a "
                "single curve: how much power there is at each angular scale. That curve, "
                "Cℓ, is what everything else in this project is built on."
            ),
            narrative=r"""
Here is the conceptual heart of CMB analysis.

Inflation does not predict the value of any particular $a_{\ell m}$. It cannot — those
depend on which specific quantum fluctuation happened where, and that is random. What
inflation predicts is the **statistics** of the $a_{\ell m}$: they are drawn from a Gaussian
distribution with zero mean.

And if the universe has no preferred direction — statistical isotropy — then the variance
of that Gaussian cannot depend on $m$, because $m$ is just an orientation label that
changes if you rotate your coordinates. It can only depend on $\ell$.

That single sentence is what reduces an infinite number of unknowns to one function:

$$\langle a_{\ell m} a^*_{\ell' m'} \rangle = C_\ell\ \delta_{\ell\ell'}\delta_{mm'}$$

$C_\ell$ is the angular power spectrum. It contains **everything** cosmology can predict
about a Gaussian, isotropic CMB. Comparing theory to data means comparing $C_\ell$ curves,
and nothing else.

This is also why the anomaly hunt in this project is interesting. Every anomaly is a claim
that the equation above is not quite right — that there is $m$-dependence, or a preferred
direction, hiding in the largest angular scales.
""",
            narration="""
Here is the conceptual heart of all CMB analysis.
Inflation does not predict the value of any particular coefficient. It cannot. Those depend
on which specific quantum fluctuation happened where, and that is random. What inflation
predicts is the statistics of the coefficients. They are drawn from a Gaussian distribution
with zero mean.
Now, if the universe has no preferred direction, which we call statistical isotropy, then
the variance of that Gaussian cannot depend on m. Because m is just an orientation label
that changes when you rotate your coordinate system. So the variance can only depend on
ell.
That single sentence is what reduces an infinite number of unknowns down to one function.
We call it C sub ell, the angular power spectrum. It contains everything that cosmology can
predict about a Gaussian, isotropic microwave background. Comparing theory to data means
comparing C ell curves and nothing else.
This is also why the anomaly hunt is interesting. Every claimed anomaly is a claim that
this equation is not quite right. That there is some m dependence, or some preferred
direction, hiding in the very largest angular scales.
""",
            equations=[
                Equation(
                    latex=r"\langle a_{\ell m} a^*_{\ell'm'}\rangle = "
                    r"C_\ell \delta_{\ell\ell'}\delta_{mm'}",
                    label="Definition of the power spectrum",
                    explain="Statistical isotropy forbids any m dependence.",
                    variables=[
                        Var("\\langle \\cdots \\rangle", "average over all the universes "
                                                        "inflation could have produced — an "
                                                        "average over possibilities, not "
                                                        "over our sky"),
                        Var("a_{\\ell m}", "the amplitude of one ripple pattern"),
                        Var("C_\\ell", "the angular power spectrum: the typical squared "
                                       "amplitude of ripples at scale ℓ. The thing we "
                                       "measure", "K²"),
                        Var("\\delta_{\\ell\\ell'}", "Kronecker delta: 1 if the two indices "
                                                    "match, 0 otherwise. It is a compact "
                                                    "way of saying 'different scales are "
                                                    "uncorrelated'"),
                    ],
                    intuition=(
                        "Think of rolling dice. You cannot predict any single roll, but you "
                        "can predict the spread of many rolls. Inflation is the same: it "
                        "cannot say where a hot spot will land, only how big hot spots "
                        "typically are at each size. The two deltas say the dice are "
                        "independent — knowing the ripple at one scale or orientation tells "
                        "you nothing about any other. And because no direction is special, "
                        "the spread cannot depend on orientation m, only on scale ℓ. That is "
                        "the entire content of the equation, and it is what turns an "
                        "unpredictable sky into a predictable curve."
                    ),
                ),
                Equation(
                    latex=r"\hat{C}_\ell = \frac{1}{2\ell+1}\sum_{m=-\ell}^{\ell}|a_{\ell m}|^2",
                    label="The estimator we actually compute",
                    explain=(
                        "Average the power over the 2ℓ+1 orientations. This is healpy's "
                        "alm2cl, and it is unbiased for a full sky."
                    ),
                    variables=[
                        Var("\\hat{C}_\\ell", "our *estimate* of Cℓ from the one sky we have. "
                                             "The hat always means 'measured, not true'",
                            "K²"),
                        Var("|a_{\\ell m}|^2", "the squared amplitude — the power — in one "
                                              "ripple"),
                        Var("2\\ell+1", "how many independent orientations exist at scale ℓ. "
                                        "This is the sample size, and it is why large "
                                        "scales are noisy: ℓ = 2 offers only 5 samples"),
                    ],
                    intuition=(
                        "We cannot average over other universes, so we do the next best "
                        "thing: average over the 2ℓ+1 orientations available on our own sky. "
                        "It is the ordinary mean you already know — add up the values, "
                        "divide by how many there are. Squaring first is deliberate: power "
                        "does not care whether a spot is hot or cold, only how far from "
                        "average it is, exactly as the energy in a wave goes as amplitude "
                        "squared. The catch is that at small ℓ there are very few "
                        "orientations to average over, which is the origin of cosmic "
                        "variance."
                    ),
                ),
                Equation(
                    latex=r"C(\theta) = \frac{1}{4\pi}\sum_\ell (2\ell+1) C_\ell "
                    r"P_\ell(\cos\theta)",
                    label="Two-point correlation function",
                    explain=(
                        "The real-space view: C_ℓ and C(θ) are a Legendre transform pair, "
                        "so they carry identical information."
                    ),
                    variables=[
                        Var("C(\\theta)", "how similar the temperature is at two points "
                                          "separated by angle θ on the sky", "K²"),
                        Var("\\theta", "the angle between the two points you are comparing",
                            "deg"),
                        Var("P_\\ell(\\cos\\theta)", "Legendre polynomial — the mathematical "
                                                    "bridge that converts 'power at scale "
                                                    "ℓ' into 'similarity at angle θ'"),
                    ],
                    intuition=(
                        "Two ways to describe the same music: a list of which frequencies "
                        "are loud, or a measurement of how much the waveform resembles "
                        "itself a moment later. Neither holds more information than the "
                        "other, and a transform gets you between them. Cℓ is the frequency "
                        "view; C(θ) is the 'pick two points θ apart and see if they tend to "
                        "agree' view. We work in Cℓ because the physics separates cleanly by "
                        "scale there — but C(θ) is where one of the anomalies shows up most "
                        "clearly."
                    ),
                ),
            ],
        ),
        Section(
            id="dl-convention",
            title="Why the plots show $\\ell(\\ell+1)C_\\ell/2\\pi$",
            plain=(
                "Every CMB plot rescales the raw spectrum before drawing it, and there is a "
                "good reason. There are far more small ripples than large ones, so raw "
                "power per ripple makes fine detail look unimportant when it is not. The "
                "rescaling counts all the ripples of a given size together, so the height "
                "of the curve answers a physically honest question: how much does this "
                "range of scales contribute to how blotchy the sky actually looks? Equal "
                "areas under the curve mean equal contributions."
            ),
            narrative=r"""
Every CMB plot you have ever seen has $\mathcal{D}_\ell = \ell(\ell+1)C_\ell/2\pi$ on the
vertical axis, never $C_\ell$. This is not decoration; it makes a physical statement
visible.

Start from the total variance of the temperature field, which is the correlation function
at zero lag:

$$\left\langle \left(\frac{\Delta T}{T}\right)^2 \right\rangle
= C(0) = \frac{1}{4\pi}\sum_\ell (2\ell+1)C_\ell$$

For large $\ell$, $2\ell+1 \approx 2\ell$, and treating the sum as an integral:

$$\frac{1}{4\pi}\int 2\ell\, C_\ell\, d\ell
= \int \frac{\ell^2 C_\ell}{2\pi}\frac{d\ell}{\ell}
\approx \int \mathcal{D}_\ell\ d\ln\ell$$

So $\mathcal{D}_\ell$ is the **variance contributed per logarithmic interval in $\ell$** —
the power per octave, if you like. Equal areas under a $\mathcal{D}_\ell$ curve on a log
axis mean equal contributions to the temperature variance you actually see on the sky.

There is a bonus: a scale-invariant primordial spectrum ($n_s = 1$) produces a
$\mathcal{D}_\ell$ that is *flat* at low $\ell$. That flat Sachs–Wolfe plateau below
$\ell \approx 30$ in our measured spectrum is a direct visual confirmation that the
primordial fluctuations were nearly scale-invariant — which is exactly what inflation
predicts.
""",
            narration="""
Every CMB plot you have ever seen has ell times ell plus one, times C ell, divided by two
pi on the vertical axis. Never just C ell. This is not decoration. It makes a physical
statement visible.
Start from the total variance of the temperature field, which is the correlation function
at zero separation. That equals one over four pi, times the sum over ell of two ell plus
one, times C ell.
For large ell, two ell plus one is approximately two ell. And if you treat the sum as an
integral, you can rewrite it as the integral of ell squared C ell over two pi, with respect
to d log ell.
So the quantity we plot is the variance contributed per logarithmic interval in ell. The
power per octave, if you like. Equal areas under the curve on a log axis mean equal
contributions to the temperature variance you actually see on the sky.
And there is a bonus. A scale invariant primordial spectrum produces a curve that is flat
at low ell. That flat plateau below ell of about thirty in our measured spectrum is direct
visual confirmation that the primordial fluctuations were nearly scale invariant, which is
exactly what inflation predicts.
""",
            equations=[
                Equation(
                    latex=r"\mathcal{D}_\ell \equiv \frac{\ell(\ell+1)C_\ell}{2\pi}",
                    label="The plotting convention",
                    explain="Variance per logarithmic interval in multipole.",
                    variables=[
                        Var("\\mathcal{D}_\\ell", "the quantity actually plotted on every CMB "
                                                 "graph, including ours", "µK²"),
                        Var("C_\\ell", "the raw angular power spectrum", "K²"),
                        Var("\\ell(\\ell+1)/2\\pi", "the reweighting factor that converts "
                                                   "'power per mode' into 'power per "
                                                   "octave of scale'"),
                    ],
                    intuition=(
                        "There are many more fine ripples than coarse ones — 2ℓ+1 of them at "
                        "each scale ℓ — so plotting raw Cℓ makes small scales look feeble "
                        "even when they carry plenty of total power. It is like judging a "
                        "choir by how loud one singer is instead of the whole section. "
                        "Multiplying by roughly ℓ² counts the whole section, so the curve "
                        "shows how much each *band* of scales contributes. It is the same "
                        "reason audio engineers use octaves rather than raw hertz."
                    ),
                ),
                Equation(
                    latex=r"\left\langle\left(\frac{\Delta T}{T}\right)^2\right\rangle "
                    r"\approx \int \mathcal{D}_\ell\, d\ln\ell",
                    label="Why it is the natural variable",
                    explain="Area under the curve equals observable temperature variance.",
                    variables=[
                        Var("\\langle (\\Delta T/T)^2 \\rangle", "the total mean-square "
                                                                "temperature wobble of the "
                                                                "sky — what you would "
                                                                "actually measure"),
                        Var("d\\ln\\ell", "an interval in *log* ℓ: one step is a doubling of "
                                         "scale, not a step of one"),
                    ],
                    intuition=(
                        "This is the payoff of the previous equation, and it gives the plot "
                        "an honest meaning: equal areas under the curve are equal "
                        "contributions to the bumpiness of the real sky. So when you look "
                        "at our spectrum and see the first peak towering over everything "
                        "else, that is not an artefact of axis choice — those 1° patches "
                        "genuinely dominate what the CMB looks like."
                    ),
                ),
            ],
            derivation=[
                Step(
                    1,
                    r"C(0) = \frac{1}{4\pi}\sum_\ell (2\ell+1) C_\ell P_\ell(1)",
                    "Set θ = 0 in the correlation function.",
                ),
                Step(2, r"P_\ell(1) = 1", "Legendre polynomials are normalised to 1 at θ=0."),
                Step(
                    3,
                    r"\sum_\ell (2\ell+1)C_\ell \to \int 2\ell\, C_\ell\, d\ell",
                    "Large ℓ: the sum becomes an integral and 2ℓ+1 ≈ 2ℓ.",
                ),
                Step(
                    4,
                    r"\frac{2\ell C_\ell}{4\pi} d\ell = \frac{\ell^2 C_\ell}{2\pi}"
                    r"\frac{d\ell}{\ell}",
                    "Multiply and divide by ℓ to produce a logarithmic measure.",
                ),
                Step(
                    5,
                    r"\approx \mathcal{D}_\ell\, d\ln\ell",
                    "And ℓ² ≈ ℓ(ℓ+1) at large ℓ, giving the standard definition.",
                ),
            ],
            live=["first_peak_ell", "first_peak_dl"],
        ),
    ],
)


# ══════════════════════════════════════════════════════════════════════════════
# 3. The acoustic peaks
# ══════════════════════════════════════════════════════════════════════════════

LESSON_PEAKS = Lesson(
    id="peaks",
    title="Why the first peak sits at ℓ = 220",
    subtitle="The sound horizon, the angular diameter distance, and a ruler 13.8 billion years long",
    duration_min=18,
    prerequisites=["origin", "harmonics"],
    sections=[
        Section(
            id="sound-horizon",
            title="How far could sound travel?",
            plain=(
                "Sound waves in the early universe had a deadline: when the fog lifted, "
                "they stopped. So there is a maximum distance any wave could have "
                "travelled, set by its speed and the time available. That distance — about "
                "144 Mpc — is a real physical length we can calculate from known physics "
                "without measuring anything. It is a ruler of known size, sitting at the "
                "edge of the observable universe. Everything this project measures comes "
                "down to asking how big that ruler looks from here."
            ),
            narrative=r"""
A sound wave in the primordial plasma had a finite amount of time to propagate: from the
end of inflation until recombination. The comoving distance it covered is the **sound
horizon**, $r_s$.

$$r_s = \int_{z_*}^{\infty} \frac{c_s(z)}{H(z)}\,dz$$

This is nothing more exotic than speed multiplied by time, with the integral accounting for
the fact that both the sound speed and the expansion rate were changing.

The sound speed is the interesting part. For a pure photon gas, $c_s = c/\sqrt{3}$ — a
standard result for a relativistic fluid with $p = \rho c^2/3$. Adding baryons adds inertia
but almost no pressure, so the fluid gets heavier without getting stiffer, and the sound
slows:

$$c_s = \frac{c}{\sqrt{3(1+R)}}, \qquad R = \frac{3\rho_b}{4\rho_\gamma}$$

Plugging in the measured densities gives $r_s \approx 144\ \mathrm{Mpc}$ in comoving units.

Now here is why this matters: **that is a known physical length.** Not estimated from a
model of galaxy formation, not calibrated against anything — computed from atomic physics
and thermodynamics. It is a standard ruler, laid down at $z \approx 1090$, and we get to
measure how big it looks.
""",
            narration="""
A sound wave in the primordial plasma had a finite amount of time to travel. From the end
of inflation until recombination. The comoving distance it covered is called the sound
horizon.
It is nothing more exotic than speed multiplied by time, written as an integral because
both the sound speed and the expansion rate were changing as the universe evolved.
The sound speed is the interesting part. For a pure photon gas, the sound speed is the
speed of light divided by the square root of three. That is the standard result for a
relativistic fluid. Adding baryons adds inertia, but almost no pressure. So the fluid gets
heavier without getting stiffer, and the sound slows down.
Plugging in the measured densities gives a sound horizon of about one hundred forty four
megaparsecs in comoving units.
Now here is why this matters so much. That is a known physical length. It was not estimated
from a model of galaxy formation. It was not calibrated against anything. It was computed
from atomic physics and thermodynamics. It is a standard ruler, laid down when the universe
was three hundred eighty thousand years old. And we get to measure how big it looks.
""",
            equations=[
                Equation(
                    latex=r"r_s = \int_{z_*}^{\infty}\frac{c_s(z)}{H(z)}dz "
                    r"\approx 144\ \mathrm{Mpc}",
                    label="Comoving sound horizon at last scattering",
                    explain="A length computed from first principles, not fitted.",
                    variables=[
                        Var("r_s", "the sound horizon: how far a sound wave could travel "
                                   "before the fog lifted. Our standard ruler", "Mpc"),
                        Var("c_s(z)", "the speed of sound back then — it changes slowly as "
                                      "the universe cools", "m/s"),
                        Var("H(z)", "the expansion rate at redshift z. Its reciprocal 1/H is "
                                    "essentially the age of the universe at that moment",
                            "1/s"),
                        Var("z_*", "redshift of last scattering — the lower limit, i.e. stop "
                                   "integrating when the fog lifts"),
                        Var("\\mathrm{Mpc}", "megaparsec, about 3.26 million light years"),
                    ],
                    intuition=(
                        "Distance = speed × time. That is genuinely all this is; the "
                        "integral is only there because both the speed and the clock rate "
                        "change as the universe expands. The factor c_s/H is speed divided "
                        "by expansion rate, and since 1/H plays the role of the age, c_s/H "
                        "is 'how far sound gets in the time available'. Add up those "
                        "contributions from the beginning until the fog lifts and you get "
                        "144 Mpc. The crucial point: this length comes out of atomic physics "
                        "and thermodynamics, with no cosmology fitted to data — which is "
                        "exactly what makes it trustworthy as a ruler."
                    ),
                ),
                Equation(
                    latex=r"c_s = \frac{c}{\sqrt{3(1+R)}},\qquad "
                    r"R = \frac{3\rho_b}{4\rho_\gamma} \propto \Omega_b h^2",
                    label="Baryon loading",
                    explain=(
                        "More baryons → slower sound → smaller r_s, and also deeper "
                        "compressions, which raises odd peaks relative to even ones."
                    ),
                    variables=[
                        Var("R", "baryon loading — how heavy the fluid is compared to how "
                                 "springy it is"),
                        Var("\\Omega_b h^2", "the physical density of ordinary matter in the "
                                            "universe. One of the numbers we fit for in the "
                                            "Inference tab"),
                        Var("h", "the Hubble constant in units of 100 km/s/Mpc, so h ≈ 0.67"),
                    ],
                    intuition=(
                        "Tape coins to a guitar string and the pitch drops: you added mass "
                        "but no extra tension. Baryons do that to the photon-baryon fluid — "
                        "mass without pressure. Slower sound means sound travels less far "
                        "before the fog lifts, so the ruler r_s is shorter and the peaks "
                        "shift. The heavier fluid also falls deeper into each gravity well "
                        "before pressure stops it, which makes compression peaks stronger "
                        "than rarefaction peaks. That asymmetry between odd and even peaks "
                        "is literally how we weigh the ordinary matter in the universe."
                    ),
                ),
            ],
        ),
        Section(
            id="angular-scale",
            title="A triangle 13.8 billion years tall",
            plain=(
                "We know the ruler's true length and we can see how big it looks. That is "
                "enough to do the oldest trick in geometry: angle = size / distance. The "
                "sound horizon spans about 0.6° on the sky — slightly larger than the full "
                "Moon. Crucially, that angle also depends on whether space itself is flat "
                "or curved, because curved space bends light paths and changes how big "
                "distant things look. Measuring the angle therefore measures the geometry "
                "of the universe. We get ℓ = 220, which is what a flat universe predicts."
            ),
            narrative=r"""
We have a ruler of known length $r_s$ sitting at a known distance $D_A$ (the comoving
angular diameter distance to last scattering, about $13.9\ \mathrm{Gpc}$). Elementary
geometry gives the angle it subtends:

$$\theta_* = \frac{r_s}{D_A}$$

Numerically: $144 / 13900 = 0.0104$ radians, which is $0.6°$ — about the angular size of
the Moon, seen from a distance of 13.8 billion light years.

Converting an angle to a multipole, $\ell \approx \pi/\theta$, gives the **acoustic scale**:

$$\ell_A = \frac{\pi D_A}{r_s} \approx 302$$

But the observed first peak is at $\ell = 220$, not 302. That is not an error — it is
physics. The oscillations are not free; they are driven by decaying gravitational
potentials, which shifts their phase. Empirically the peaks sit at

$$\ell_m \approx \ell_A (m - \varphi), \qquad \varphi \approx 0.27$$

Check it: $302 \times (1 - 0.27) = 220$. $302 \times (2 - 0.27) = 523$, observed $\approx 537$.
$302 \times (3 - 0.27) = 825$, observed $\approx 810$.

**This is the flatness measurement.** $D_A$ depends on the spatial curvature: in a closed
universe light paths converge and the same ruler looks bigger, pushing the peak to lower
$\ell$; in an open universe it looks smaller and the peak moves higher. The peak lands where
flat geometry predicts. That is how we know $\Omega_k \approx 0$, to better than a percent.
""",
            narration="""
We have a ruler of known length sitting at a known distance. The angular diameter distance
to last scattering is about thirteen point nine gigaparsecs. Elementary geometry gives the
angle it subtends. Just the length divided by the distance.
Numerically that is one hundred forty four divided by thirteen thousand nine hundred, which
is about zero point zero one zero four radians. That is zero point six degrees. Roughly the
angular size of the Moon, seen from a distance of thirteen point eight billion light years.
Converting an angle to a multipole, ell is approximately pi divided by theta. That gives an
acoustic scale of about three hundred and two.
But the observed first peak is at two hundred and twenty, not three hundred and two. That
is not an error. It is physics. The oscillations are not free. They are driven by decaying
gravitational potentials, and that shifts their phase. Empirically the peaks sit at the
acoustic scale times the peak number minus about zero point two seven.
Check it. Three hundred two times zero point seven three is two hundred and twenty. For the
second peak, three hundred two times one point seven three is five hundred twenty three,
and we observe about five hundred thirty seven. Close.
And this is the flatness measurement. The angular diameter distance depends on the spatial
curvature. In a closed universe, light paths converge, the same ruler looks bigger, and the
peak moves to lower ell. In an open universe it looks smaller and the peak moves higher.
The peak lands exactly where flat geometry predicts. That is how we know the universe is
spatially flat to better than one percent.
""",
            equations=[
                Equation(
                    latex=r"\theta_* = \frac{r_s}{D_A}, \qquad 100\,\theta_* = 1.0411 \pm 0.0003",
                    label="The best-measured quantity in cosmology",
                    explain=(
                        "Known to 0.03%. Almost everything else in the ΛCDM fit is derived "
                        "by combining this with other constraints."
                    ),
                    variables=[
                        Var("\\theta_*", "the angle the sound horizon appears to span on our "
                                         "sky — about 0.6°, just larger than the Moon",
                            "rad"),
                        Var("r_s", "the ruler's true length, 144 Mpc", "Mpc"),
                        Var("D_A", "how far away the ruler is — the distance to the "
                                   "last-scattering surface, about 13.9 Gpc", "Mpc"),
                    ],
                    intuition=(
                        "Hold your thumb at arm's length and it covers the Moon. Angle = "
                        "size / distance — the same rule you used in school for small "
                        "angles, and it is the entire equation. We know the ruler's true "
                        "size from physics, and we measure the angle it appears to span. "
                        "Divide, and you have the distance to the edge of the observable "
                        "universe. This is the single most precisely known number in "
                        "cosmology, good to three parts in ten thousand."
                    ),
                ),
                Equation(
                    latex=r"\ell_A = \frac{\pi D_A}{r_s} \approx 302, \qquad "
                    r"\ell_m \approx \ell_A(m - \varphi)",
                    label="Peak positions",
                    explain="φ ≈ 0.27 is the phase shift from gravitational driving.",
                    variables=[
                        Var("\\ell_A", "the acoustic scale — the multipole corresponding to "
                                       "the sound horizon, ≈ 302"),
                        Var("\\ell_m", "where the m-th peak actually sits. m = 1 is the first "
                                       "peak, which we measure at ℓ = 220"),
                        Var("m", "which peak you are talking about: 1, 2, 3, …"),
                        Var("\\varphi", "a phase offset of about 0.27, caused by gravity "
                                        "driving the oscillations rather than letting them "
                                        "ring freely"),
                    ],
                    intuition=(
                        "Converting an angle into ℓ is just ℓ ≈ π/θ — a smaller feature needs "
                        "a higher harmonic, exactly as a shorter string gives a higher "
                        "note. That predicts the first peak at 302, but we measure 220. The "
                        "gap is real physics, not error. A freely swinging pendulum keeps "
                        "its own rhythm, but one you keep pushing gets nudged off phase. "
                        "Gravity kept pushing these oscillations while their wells decayed, "
                        "shifting the pattern by φ ≈ 0.27 of a cycle. Multiply: 302 × 0.73 ≈ "
                        "220 — which is exactly what came out of our WMAP analysis."
                    ),
                ),
                Equation(
                    latex=r"D_A = \frac{c}{H_0}\int_0^{z_*}\frac{dz}{E(z)}, \qquad "
                    r"E(z)=\sqrt{\Omega_m(1+z)^3 + \Omega_\Lambda}",
                    label="Angular diameter distance",
                    explain=(
                        "This is where H₀, Ω_m and curvature enter. The peak position "
                        "constrains a combination of them, which is the geometric "
                        "degeneracy the MCMC has to work around."
                    ),
                    variables=[
                        Var("D_A", "distance to the last-scattering surface", "Mpc"),
                        Var("H_0", "the Hubble constant — how fast the universe expands "
                                   "today", "km/s/Mpc"),
                        Var("E(z)", "how much faster the universe was expanding at redshift "
                                    "z, relative to today"),
                        Var("\\Omega_m", "fraction of the universe's energy that is matter "
                                        "(dark + ordinary), about 0.31"),
                        Var("\\Omega_\\Lambda", "fraction that is dark energy, about 0.69. "
                                               "The two sum to 1 in a flat universe"),
                    ],
                    intuition=(
                        "Distance = speed × time again, but light has been travelling for "
                        "13.8 billion years through a universe whose expansion rate kept "
                        "changing, so you must add up the journey in slices. c/H₀ sets the "
                        "overall scale — roughly the size of the observable universe — and "
                        "the integral corrects for expansion history. The (1+z)³ is simply "
                        "matter diluting as volume grows, while Ω_Λ stays constant because "
                        "dark energy does not dilute. This equation is why measuring the "
                        "peak position alone cannot pin down H₀: many combinations of H₀ and "
                        "Ω_m give the same D_A, which is the degeneracy our MCMC has to "
                        "break."
                    ),
                ),
            ],
            derivation=[
                Step(
                    1, r"r_s \approx 144\ \mathrm{Mpc}", "Computed from the sound-speed integral."
                ),
                Step(2, r"D_A \approx 13.9\ \mathrm{Gpc}", "From the ΛCDM expansion history."),
                Step(
                    3,
                    r"\theta_* = 144/13900 = 1.04\times10^{-2}\ \mathrm{rad} = 0.594°",
                    "Small-angle geometry. No approximation beyond θ ≪ 1.",
                ),
                Step(
                    4,
                    r"\ell_A \simeq \pi/\theta_* = 3.1416/0.0104 \approx 302",
                    "A half-wavelength fits into angle θ, so ℓ ≈ π/θ.",
                ),
                Step(
                    5,
                    r"\ell_1 \approx 302 \times (1-0.27) \approx 220",
                    "Apply the driving phase shift, and you land on the measured peak.",
                ),
            ],
            live=["first_peak_ell", "first_peak_dl", "theory_peak_ell"],
        ),
        Section(
            id="peak-heights",
            title="What each peak tells you",
            plain=(
                "Where the peaks sit tells you the shape of space. How *tall* they are "
                "tells you what the universe is made of. Peak 1 reflects how deep the "
                "gravity wells were. Peak 2 compared to peak 1 weighs ordinary matter, "
                "because heavy matter makes squeezes deeper than stretches. Peak 3 needs "
                "dark matter to stay as tall as it is. And beyond about ℓ = 1000 everything "
                "fades out, because the fog took time to clear and that blurred the finest "
                "detail. Our measurement clearly reaches peak 2."
            ),
            narrative=r"""
The *positions* of the peaks give geometry. The *heights* give composition, and each one
is sensitive to something different:

**First peak height** — the overall amplitude of fluctuations combined with the total
matter density. It sets how deep the potential wells were.

**Second peak, relative to the first** — baryons. Baryon inertia makes compressions
(odd peaks) deeper than rarefactions (even peaks). More baryons means a *suppressed* second
peak relative to the first. This is a direct weighing of the ordinary matter in the
universe, and it agrees with the completely independent Big Bang nucleosynthesis estimate
from deuterium abundance — one of the great consistency checks in physics.

**Third peak** — dark matter. If the universe were baryon-only, the potentials would decay
and the third peak would be strongly damped. Its observed height requires a substantial
non-baryonic component that had already stopped feeling radiation pressure.

**Damping tail beyond ℓ ≈ 1000** — Silk damping. Recombination was not instantaneous;
photons random-walked a finite distance during it, washing out structure smaller than that
diffusion length.

Our measurement reaches the second peak clearly. Going further needs either Planck's higher
resolution or combining more WMAP detector pairs.
""",
            narration="""
The positions of the peaks give you geometry. The heights give you composition. And each
peak is sensitive to something different.
The first peak height tells you the overall amplitude of the fluctuations combined with the
total matter density. It sets how deep the potential wells were.
The second peak, relative to the first, tells you about baryons. Baryon inertia makes the
compressions deeper than the rarefactions. Odd numbered peaks are compressions, even
numbered peaks are rarefactions. So more baryons means a suppressed second peak relative to
the first. This is a direct weighing of the ordinary matter in the universe. And remarkably,
it agrees with the completely independent estimate from big bang nucleosynthesis and the
deuterium abundance. That is one of the great consistency checks in all of physics.
The third peak tells you about dark matter. If the universe were baryon only, the
gravitational potentials would decay away and the third peak would be strongly damped. The
height we observe requires a substantial non baryonic component that had already stopped
feeling radiation pressure.
And beyond ell of about one thousand, you see the damping tail. Recombination was not
instantaneous. Photons random walked a finite distance during it, and that washed out any
structure smaller than that diffusion length.
""",
            equations=[
                Equation(
                    latex=r"\frac{\mathcal{D}_2}{\mathcal{D}_1} \ \text{decreases as}\ "
                    r"\Omega_b h^2 \ \text{increases}",
                    label="Baryon signature",
                    explain="Odd peaks are compressions; baryon loading deepens them.",
                    variables=[
                        Var("\\mathcal{D}_1", "height of the first peak — a compression",
                            "µK²"),
                        Var("\\mathcal{D}_2", "height of the second peak — a rarefaction",
                            "µK²"),
                        Var("\\Omega_b h^2", "the physical density of ordinary matter"),
                    ],
                    intuition=(
                        "Hang a weight on a spring and let it bounce. It sags further down "
                        "than it springs back up, because gravity helps on the way down and "
                        "fights on the way up. Baryons are that weight. Odd-numbered peaks "
                        "are caught at maximum squeeze, even-numbered ones at maximum "
                        "stretch — so more baryons means the odd peaks grow and the even "
                        "peaks shrink. Comparing peak 1 to peak 2 literally weighs the "
                        "ordinary matter in the universe, and the answer agrees with the "
                        "completely independent measurement from Big Bang nucleosynthesis."
                    ),
                ),
                Equation(
                    latex=r"\ell_D \sim \sqrt{\frac{1}{\lambda_D}}, \qquad "
                    r"C_\ell \to C_\ell e^{-(\ell/\ell_D)^2}",
                    label="Silk damping",
                    explain=(
                        "Photon diffusion during the finite duration of recombination "
                        "exponentially suppresses small scales."
                    ),
                    variables=[
                        Var("\\lambda_D", "the diffusion length — how far a photon wandered "
                                          "while the fog was clearing", "Mpc"),
                        Var("\\ell_D", "the damping scale: the multipole beyond which detail "
                                       "is washed out, around ℓ ≈ 1400"),
                        Var("e^{-(\\ell/\\ell_D)^2}", "a suppression factor — close to 1 for "
                                                     "ℓ ≪ ℓ_D, and falling off fast beyond"),
                    ],
                    intuition=(
                        "The fog did not lift everywhere at the same instant; it took time. "
                        "During that window photons were still bouncing around, drifting a "
                        "random distance like a drunkard's walk. Any hot and cold patches "
                        "smaller than that drift distance got stirred together and averaged "
                        "away — the same reason a photograph blurs if the subject moves "
                        "while the shutter is open. So the spectrum fades out at small "
                        "scales. Our measurement stops well before this, at ℓ ≈ 700, so we "
                        "see the onset of damping but not the full tail."
                    ),
                ),
            ],
        ),
    ],
)


# ══════════════════════════════════════════════════════════════════════════════
# 4. From a map to a spectrum — the estimator we actually implemented
# ══════════════════════════════════════════════════════════════════════════════

LESSON_ESTIMATOR = Lesson(
    id="estimator",
    title="From pixels to a power spectrum",
    subtitle="Masks, beams, pixel windows, noise bias, and why we used cross-spectra",
    duration_min=20,
    prerequisites=["harmonics"],
    sections=[
        Section(
            id="pseudo-cl",
            title="The mask ruins orthogonality",
            plain=(
                "Our own galaxy glows brightly in microwaves and sits right across the "
                "middle of the sky, so we have to cut it out — about 30% of the sky gets "
                "thrown away. But the clean mathematics of spherical harmonics assumed we "
                "had the *whole* sphere. With a hole in it, scales start leaking into each "
                "other, like trying to identify a song from a recording with gaps. The full "
                "fix is a big matrix inversion; we use the standard approximation instead — "
                "divide by the fraction of sky retained — which is accurate as long as the "
                "features you care about are smaller than the hole."
            ),
            narrative=r"""
The estimator $\hat{C}_\ell = \frac{1}{2\ell+1}\sum_m |a_{\ell m}|^2$ is unbiased — on a
complete sky. But we cannot use a complete sky. The Milky Way sits across the middle of it,
glowing in synchrotron and dust emission far brighter than any CMB anisotropy, so about 30%
of the sky has to be cut out.

The moment you multiply by a mask $W(\hat{n})$, the spherical harmonics are no longer
orthogonal over the region you kept. Power leaks between multipoles. What you compute is
the **pseudo power spectrum** $\tilde{C}_\ell$, and its expectation is a smeared version of
the truth:

$$\langle \tilde{C}_\ell \rangle = \sum_{\ell'} M_{\ell\ell'} C_{\ell'} B^2_{\ell'} p^2_{\ell'}$$

$M_{\ell\ell'}$ is the mode-coupling matrix, built from the mask's own power spectrum and a
sum over Wigner 3j symbols. Inverting it properly is the MASTER algorithm.

We use the leading-order approximation. For a large, smooth mask the coupling matrix is
close to diagonal, and the whole effect reduces to a single number — the mean of the squared
mask:

$$C_\ell \approx \frac{\tilde{C}_\ell}{w_2}, \qquad w_2 = \langle W^2 \rangle$$

The intuition is simply that you threw away a fraction of the sky and therefore a
proportional fraction of the power, so you divide it back in. It is accurate when the mask
is large compared with the angular scale you are measuring — which holds comfortably
throughout the acoustic peaks, and is the main reason our lowest bandpower at
$\ell \approx 21$ is the least trustworthy one.
""",
            narration="""
The naive estimator is unbiased on a complete sky. But we cannot use a complete sky. The
Milky Way sits right across the middle of it, glowing in synchrotron and dust emission far
brighter than any cosmic signal. So about thirty percent of the sky has to be cut out.
The moment you multiply by a mask, the spherical harmonics are no longer orthogonal over
the region you kept. Power leaks between multipoles. What you actually compute is called
the pseudo power spectrum, and its expectation value is a smeared version of the truth,
related by a mode coupling matrix.
That matrix is built from the mask's own power spectrum and a sum over Wigner three j
symbols. Inverting it properly is called the MASTER algorithm.
We use the leading order approximation. For a large, smooth mask, the coupling matrix is
close to diagonal, and the whole effect reduces to a single number. The mean of the squared
mask, which we call w two. You just divide the pseudo spectrum by it.
The intuition is simply that you threw away a fraction of the sky, and therefore a
proportional fraction of the power, so you divide it back in. It is accurate when the mask
is large compared to the angular scale you are measuring. That holds comfortably throughout
the acoustic peaks. It is also the main reason our lowest bandpower, at ell of about twenty
one, is the least trustworthy one.
""",
            equations=[
                Equation(
                    latex=r"\langle\tilde{C}_\ell\rangle = \sum_{\ell'}M_{\ell\ell'}"
                    r"C_{\ell'}B^2_{\ell'}p^2_{\ell'}",
                    label="The full MASTER relation",
                    explain="Mask coupling, beam, and pixel window all multiply together.",
                    variables=[
                        Var("\\tilde{C}_\\ell", "what we actually measure on the cut sky. The "
                                               "tilde means 'distorted by masking'", "K²"),
                        Var("C_{\\ell'}", "the true full-sky spectrum we are trying to "
                                          "recover", "K²"),
                        Var("M_{\\ell\\ell'}", "the mixing matrix: how much true power at "
                                              "scale ℓ' leaks into the measured scale ℓ"),
                        Var("B_{\\ell'}", "beam smoothing from the telescope's finite "
                                          "resolution"),
                        Var("p_{\\ell'}", "pixel smoothing from chopping the sky into finite "
                                          "pixels"),
                    ],
                    intuition=(
                        "Read right to left, this is the story of what happened to the real "
                        "sky on its way into our data file: the true spectrum was blurred by "
                        "the telescope, blurred again by pixelisation, then scrambled "
                        "between neighbouring scales by the mask. Measurement is that whole "
                        "chain of degradations, and analysis is undoing it. Undoing the "
                        "blurring is easy — divide it back out. Undoing the scrambling means "
                        "inverting a large matrix, which is expensive and numerically "
                        "fragile, so we use the much simpler approximation below and state "
                        "the limitation openly."
                    ),
                ),
                Equation(
                    latex=r"M_{\ell\ell'} = \frac{2\ell'+1}{4\pi}\sum_{\ell''}(2\ell''+1)"
                    r"\mathcal{W}_{\ell''}\begin{pmatrix}\ell&\ell'&\ell''\\0&0&0\end{pmatrix}^2",
                    label="Mode-coupling matrix",
                    explain="The Wigner 3j symbol encodes how the mask mixes multipoles.",
                    variables=[
                        Var("M_{\\ell\\ell'}", "how much power leaks from scale ℓ' into scale "
                                              "ℓ because of the mask"),
                        Var("\\mathcal{W}_{\\ell''}", "the power spectrum of the mask itself — "
                                                    "the shape of the hole, in harmonic "
                                                    "space"),
                        Var("\\begin{pmatrix}\\ell&\\ell'&\\ell''\\\\0&0&0\\end{pmatrix}",
                            "a Wigner 3j symbol — a standard lookup coefficient for how "
                            "three ripple patterns overlap on a sphere"),
                    ],
                    intuition=(
                        "When you multiply two waves together you get sums and differences "
                        "of their frequencies — the same effect that makes two slightly "
                        "out-of-tune guitar strings produce a slow beat. Masking *is* a "
                        "multiplication: sky × mask. So the mask's own frequencies mix with "
                        "the sky's, and power at one scale bleeds into neighbours. This "
                        "matrix is the complete bookkeeping for that leakage. It is exact "
                        "but expensive, which is why the next equation exists."
                    ),
                ),
                Equation(
                    latex=r"C_\ell \approx \frac{\tilde{C}_\ell}{w_2}, "
                    r"\qquad w_2 = \frac{1}{4\pi}\int W^2(\hat{n})\,d\Omega",
                    label="The f_sky approximation we implemented",
                    explain="Valid when the mask is smooth on the scale being measured.",
                    variables=[
                        Var("\\tilde{C}_\\ell", "the spectrum measured on the masked sky. The "
                                               "tilde means 'contaminated by the cut'",
                            "K²"),
                        Var("C_\\ell", "our estimate of the true full-sky spectrum", "K²"),
                        Var("W(\\hat{n})", "the mask: 1 where we keep the sky, 0 where we cut "
                                          "it out"),
                        Var("w_2", "the mean of the mask squared — effectively the fraction "
                                   "of sky surviving. We measure f_sky ≈ 0.69"),
                    ],
                    intuition=(
                        "If you survey 69% of a population, you scale your count up by "
                        "1/0.69 to estimate the whole. That is literally all this does. It "
                        "ignores the leakage between neighbouring scales described above, "
                        "which is fine here because the acoustic peaks are broad compared to "
                        "the leakage, and because we bin the spectrum anyway — binning "
                        "averages neighbouring scales together, which is exactly the "
                        "leakage we ignored."
                    ),
                ),
            ],
            live=["f_sky"],
        ),
        Section(
            id="beam-noise",
            title="The two things that will destroy your spectrum",
            plain=(
                "Two problems nearly sank this project. First, a telescope blurs the sky, "
                "so fine detail is suppressed and you must divide it back up — but the "
                "blurring gets exponentially worse at small scales, so that division "
                "amplifies anything left over, including noise. Second, detector noise "
                "looks exactly like signal to a power spectrum. Our first attempt came out "
                "26 times too high with no peaks at all. The fix is elegant: use two "
                "separate detectors looking at the same sky and correlate them. The real "
                "sky is identical in both, so it survives; their noise is unrelated, so it "
                "averages to zero. No noise model needed — the problem simply cancels."
            ),
            narrative=r"""
**Problem one: the beam.** A telescope with finite resolution smooths the sky. In harmonic
space that smoothing is a simple multiplication by $B_\ell$, which falls off roughly like a
Gaussian. Recovering the true spectrum means dividing by $B^2_\ell$.

That division is dangerous. $B_\ell$ falls *exponentially*. Dividing by something
exponentially small amplifies whatever is left — including noise — exponentially.

**Problem two: noise.** What you measure is signal plus noise:

$$\tilde{C}_\ell^{\mathrm{measured}} = C_\ell B^2_\ell p^2_\ell + N_\ell$$

Deconvolve the beam and you get $C_\ell + N_\ell/B^2_\ell$. The noise term blows up. In our
first attempt with the WMAP ILC map, the spectrum was 26 times too high at $\ell = 350$ and
rising — no acoustic peaks at all, just a wall going up.

**The solution is beautiful.** Take two detectors that observed the same sky but have
independent noise. Correlate them instead of squaring one:

$$\langle a^A_{\ell m} a^{B*}_{\ell m}\rangle
= C_\ell B^A_\ell B^B_\ell + \underbrace{\langle n^A n^{B*}\rangle}_{=\,0}$$

The noise term vanishes identically, because uncorrelated things have zero expected
product. No noise model. No instrument simulation. Just arithmetic.

And there is a free bonus: subtract the cross-spectrum from either auto-spectrum and what
remains is that detector's noise power, measured empirically from the data itself.
""",
            narration="""
There are two things that will destroy your power spectrum, and you have to handle both.
Problem one is the beam. A telescope with finite resolution smooths the sky. In harmonic
space, that smoothing is just a multiplication by a beam transfer function, which falls off
roughly like a Gaussian. So recovering the true spectrum means dividing by the beam
squared.
That division is dangerous, because the beam falls off exponentially. Dividing by something
exponentially small amplifies whatever is left, including noise, exponentially.
Problem two is the noise itself. What you measure is signal plus noise. Deconvolve the beam
and you get the signal plus the noise divided by the beam squared. That second term blows
up. In our first attempt with the WMAP internal linear combination map, the spectrum was
twenty six times too high at ell of three hundred fifty, and rising. No acoustic peaks at
all. Just a wall going up.
The solution is beautiful. Take two detectors that observed the same sky but have
independent noise. Correlate them, instead of squaring one of them. The cross correlation
contains the signal times both beams, plus the correlation of the two noise realisations.
And that noise term vanishes identically, because uncorrelated things have zero expected
product. No noise model. No instrument simulation. Just arithmetic.
And there is a free bonus. Subtract the cross spectrum from either auto spectrum, and what
remains is that detector's noise power, measured empirically from the data itself.
""",
            equations=[
                Equation(
                    latex=r"B_\ell = \exp\left[-\frac{\ell(\ell+1)\sigma^2}{2}\right], "
                    r"\qquad \sigma = \frac{\theta_{\mathrm{FWHM}}}{\sqrt{8\ln 2}}",
                    label="Gaussian beam transfer function",
                    explain=(
                        "Real beams have sidelobes a Gaussian misses, which is why we use "
                        "WMAP's tabulated b_ℓ measured from observations of Jupiter."
                    ),
                    variables=[
                        Var("B_\\ell", "how much of the true signal at scale ℓ survives the "
                                       "telescope's blurring. 1 means untouched, 0 means "
                                       "wiped out"),
                        Var("\\theta_{\\mathrm{FWHM}}", "the beam width — how blurry the "
                                                       "telescope is. About 13 arcminutes "
                                                       "for WMAP's V band", "arcmin"),
                        Var("\\sigma", "the same width expressed as a Gaussian standard "
                                       "deviation; the √(8 ln 2) just converts between the "
                                       "two conventions", "rad"),
                    ],
                    intuition=(
                        "Photograph a page of text slightly out of focus. Large headings "
                        "survive; fine print turns to mush. A telescope does the same to the "
                        "sky, and B_ℓ is the fraction of each detail size that survives. "
                        "Because it is an exponential, it crashes towards zero at high ℓ — "
                        "and to undo the blur you divide by it, which means dividing by a "
                        "tiny number. That magnifies everything, including noise, which is "
                        "precisely the trap described below. We do not actually use this "
                        "formula: we use WMAP's measured beam from observations of Jupiter, "
                        "because real telescopes are not perfect Gaussians."
                    ),
                ),
                Equation(
                    latex=r"\hat{C}^{AB}_\ell = \frac{\tilde{C}^{AB}_\ell}"
                    r"{w_2\, B^A_\ell B^B_\ell\, p^2_\ell}",
                    label="The cross-spectrum estimator we implemented",
                    explain="Note the single power of each beam, not the square.",
                    variables=[
                        Var("A, B", "two different detectors — for us, WMAP's V1 and V2, "
                                    "which see the same sky with unrelated noise"),
                        Var("\\hat{C}^{AB}_\\ell", "our final answer: the corrected power "
                                                  "spectrum of the real sky", "K²"),
                        Var("\\tilde{C}^{AB}_\\ell", "the raw cross-power measured between "
                                                    "the two detector maps", "K²"),
                        Var("B^A_\\ell, B^B_\\ell", "each detector's own beam blurring — note "
                                                   "one power of each, not the square"),
                        Var("p_\\ell", "the pixel window: extra smoothing from chopping the "
                                       "sky into finite pixels"),
                        Var("w_2", "the sky-fraction correction for the Galactic mask"),
                    ],
                    intuition=(
                        "Read it as a chain of undo operations. The raw number on top has "
                        "been reduced by three separate things — the mask threw away sky, "
                        "each telescope blurred the image, and pixelisation smoothed it "
                        "further — so we divide each one back out. The genuinely important "
                        "detail is what is *missing*: there is no noise term, because "
                        "correlating two independent detectors already cancelled it. That "
                        "single change took our χ²/dof from 1669 to about 1."
                    ),
                ),
                Equation(
                    latex=r"N^A_\ell = \hat{C}^{AA}_\ell - \hat{C}^{AB}_\ell",
                    label="Empirical noise measurement",
                    explain="Auto minus cross isolates the noise, with no model assumed.",
                    variables=[
                        Var("N^A_\\ell", "the noise power in detector A — measured, not "
                                        "modelled", "K²"),
                        Var("\\hat{C}^{AA}_\\ell", "detector A correlated with itself: signal "
                                                  "*plus* its own noise", "K²"),
                        Var("\\hat{C}^{AB}_\\ell", "A correlated with B: signal only", "K²"),
                    ],
                    intuition=(
                        "If one bucket holds water plus sand and another holds only water, "
                        "subtracting gives you the sand. The auto-spectrum contains signal "
                        "and noise; the cross-spectrum contains signal alone. Subtract and "
                        "the noise is left, measured directly from the data with no "
                        "instrument model at all. We need this number for the error bars — "
                        "leaving it out was what made our first uncertainties far too "
                        "small."
                    ),
                ),
            ],
            derivation=[
                Step(
                    1,
                    r"a^A_{\ell m} = s_{\ell m}B^A_\ell + n^A_{\ell m}",
                    "Each map is the same sky signal, beam-smoothed, plus its own noise.",
                ),
                Step(
                    2,
                    r"\langle a^A_{\ell m}a^{B*}_{\ell m}\rangle = "
                    r"B^A_\ell B^B_\ell\langle|s|^2\rangle + \langle n^A n^{B*}\rangle",
                    "Expand the product; cross terms between signal and noise vanish.",
                ),
                Step(
                    3,
                    r"\langle n^A n^{B*}\rangle = 0",
                    "Different detectors, independent noise. This is the entire trick.",
                ),
                Step(
                    4,
                    r"\Rightarrow \langle a^A a^{B*}\rangle = C_\ell B^A_\ell B^B_\ell",
                    "Unbiased at every multipole, with no noise model required.",
                ),
            ],
            live=["beam_labels", "chi2_per_dof"],
        ),
        Section(
            id="cosmic-variance",
            title="The error bar you can never beat",
            plain=(
                "There is a limit on how well the CMB can *ever* be measured, and it has "
                "nothing to do with telescopes. At each scale there are only so many "
                "independent patches on the sky — at the very largest scales, just five. "
                "Estimating an average from five samples is inherently imprecise, the same "
                "reason a poll of five people tells you little. We have already measured "
                "the entire sky, so no better instrument can help; there is only one "
                "universe to look at. This is called cosmic variance, and it is why the "
                "large-scale anomalies are so hard to settle: with five numbers, 'genuinely "
                "odd' and 'unlucky' look almost the same."
            ),
            narrative=r"""
There is a floor on how well anyone can ever measure $C_\ell$, and it has nothing to do
with your instrument.

At multipole $\ell$ there are exactly $2\ell+1$ independent coefficients $a_{\ell m}$. Each
is a Gaussian random number with variance $C_\ell$. Estimating a variance from $N$ samples
has a fractional uncertainty of $\sqrt{2/N}$. Therefore:

$$\frac{\Delta C_\ell}{C_\ell} = \sqrt{\frac{2}{2\ell+1}}$$

This is **cosmic variance**. At $\ell = 2$ there are five numbers, so the uncertainty is
63%. No telescope will ever improve that, because there is only one universe and we have
already measured all of it.

Cut the sky with a mask and it gets worse: fewer independent modes survive, and the error
grows as $1/\sqrt{f_{\mathrm{sky}}}$. Include instrument noise and you get the Knox formula
we implemented:

$$\frac{\Delta C_\ell}{C_\ell} = \sqrt{\frac{2}{(2\ell+1)f_{\mathrm{sky}}}}
\left(1 + \frac{N_\ell}{C_\ell}\right)$$

This is exactly why the low-$\ell$ anomalies are so hard to settle. The quadrupole really
does look low — but with only five independent numbers, "low" and "unlucky" are nearly
impossible to tell apart.
""",
            narration="""
There is a floor on how well anyone can ever measure the power spectrum, and it has nothing
to do with your instrument.
At multipole ell, there are exactly two ell plus one independent coefficients. Each one is
a Gaussian random number with variance C ell. And estimating a variance from N samples has
a fractional uncertainty of the square root of two over N. So the fractional error on C ell
is the square root of two over two ell plus one.
This is called cosmic variance. At ell equals two, there are only five numbers, so the
uncertainty is sixty three percent. No telescope will ever improve on that, because there
is only one universe and we have already measured all of it.
Cut the sky with a mask and it gets worse. Fewer independent modes survive, and the error
grows as one over the square root of the sky fraction. Include instrument noise and you get
the Knox formula, which is what we implemented for our error bars.
And this is exactly why the low multipole anomalies are so hard to settle. The quadrupole
really does look low. But with only five independent numbers in it, low and unlucky are
nearly impossible to tell apart.
""",
            equations=[
                Equation(
                    latex=r"\frac{\Delta C_\ell}{C_\ell} = \sqrt{\frac{2}{(2\ell+1)"
                    r"f_{\mathrm{sky}}}}\left(1 + \frac{N_\ell}{C_\ell}\right)",
                    label="Knox formula",
                    explain="Cosmic variance, sky cut, and noise, in one expression.",
                    variables=[
                        Var("\\Delta C_\\ell / C_\\ell", "the fractional uncertainty — the "
                                                        "error bar as a percentage"),
                        Var("2\\ell+1", "the number of independent samples available at scale "
                                        "ℓ. Only 5 at ℓ = 2; over 1000 at ℓ = 500"),
                        Var("f_{\\mathrm{sky}}", "fraction of sky left after masking — 0.69 "
                                                "for us. Less sky, fewer samples"),
                        Var("N_\\ell / C_\\ell", "noise relative to signal. Negligible at "
                                                "large scales, dominant at small ones"),
                    ],
                    intuition=(
                        "Poll five people and your result is rough; poll a thousand and it "
                        "tightens. Statistics says the error shrinks like 1/√N, and that is "
                        "the whole square root: N here is 2ℓ+1, the number of independent "
                        "patches at that scale. Masking the Galaxy removes samples, so "
                        "dividing by f_sky inflates the error. The last bracket adds "
                        "instrument noise on top. At large scales N is tiny and you are "
                        "stuck with irreducible cosmic variance; at small scales N is huge "
                        "but noise takes over. Our spectrum is cosmic-variance limited below "
                        "ℓ ≈ 300 and noise limited above it."
                    ),
                ),
                Equation(
                    latex=r"\mathrm{Var}(\hat{C}^{AB}_\ell) = \frac{1}{(2\ell+1)"
                    r"f_{\mathrm{sky}}}\left[(C^{AB}_\ell)^2 + "
                    r"(C_\ell+N^A_\ell)(C_\ell+N^B_\ell)\right]",
                    label="Cross-spectrum variance",
                    explain=(
                        "What our error bars actually use. Dropping the noise terms made "
                        "our first χ²/dof come out at 198 instead of 1."
                    ),
                    variables=[
                        Var("\\mathrm{Var}", "the squared error bar on each bandpower"),
                        Var("C^{AB}_\\ell", "the signal we measured from the cross-spectrum",
                            "K²"),
                        Var("N^A_\\ell, N^B_\\ell", "each detector's own noise, measured "
                                                   "empirically as auto minus cross", "K²"),
                    ],
                    intuition=(
                        "The cross-spectrum removes noise from the *answer*, but not from "
                        "the *uncertainty* — a noisy measurement of zero is still noisy. "
                        "The first term is the irreducible cosmic variance; the second is "
                        "how much the noise in each detector jiggles the result. We "
                        "originally left the noise terms out, and our error bars came out "
                        "so small that a perfectly good spectrum looked like a catastrophic "
                        "disagreement: χ²/dof of 198. Measuring the noise honestly and "
                        "putting it back brought that to about 1. A reminder that an error "
                        "bar is a physical claim, not decoration."
                    ),
                ),
            ],
            live=["f_sky", "n_bandpowers"],
        ),
    ],
)


# ══════════════════════════════════════════════════════════════════════════════
# 5. Inference
# ══════════════════════════════════════════════════════════════════════════════

LESSON_INFERENCE = Lesson(
    id="inference",
    title="Turning a curve into numbers",
    subtitle="Likelihoods, degeneracies, and why MCMC instead of a grid",
    duration_min=14,
    prerequisites=["estimator", "peaks"],
    sections=[
        Section(
            id="likelihood",
            title="What we are actually maximising",
            plain=(
                "We have a measured curve with error bars, and a physics code that can "
                "predict the curve for any given universe. Fitting means asking: which "
                "universe predicts a curve closest to ours? 'Closest' is measured by χ² — "
                "add up the squared gaps between prediction and data, weighted so that "
                "well-measured points count more. Rather than hunting for a single best "
                "answer, we explore the whole space of universes and record how well each "
                "fits, which gives both the answer and its honest uncertainty."
            ),
            narrative=r"""
We have bandpowers $\mathcal{D}_b$ with uncertainties $\sigma_b$, and a theory that predicts
$\mathcal{D}_b(\theta)$ for any parameter vector $\theta$. Assuming Gaussian errors, the
probability of the data given the parameters is

$$-2\ln\mathcal{L} = \sum_b \left[\frac{\mathcal{D}_b - \mathcal{D}_b(\theta)}{\sigma_b}\right]^2
\equiv \chi^2(\theta)$$

Bayes' theorem turns that into what we actually want, the probability of the parameters
given the data:

$$P(\theta | \mathcal{D}) \propto \mathcal{L}(\mathcal{D}|\theta)\,P(\theta)$$

Two honest caveats about our implementation:

First, we use a **diagonal** covariance. Masking couples neighbouring bandpowers, so the
true covariance has off-diagonal terms we are ignoring. Our error bars are therefore
slightly optimistic.

Second, you must bin the theory the same way you binned the data. Evaluating a curved theory
spectrum at the bin centre and comparing it to a bin average is a real bias — small, but it
is the kind of thing that quietly shifts a parameter by a fraction of a sigma.
""",
            narration="""
We have bandpowers with uncertainties, and a theory that predicts a bandpower value for any
set of cosmological parameters. Assuming Gaussian errors, the probability of the data given
the parameters is just the exponential of minus one half chi squared. And chi squared is the
usual sum of squared residuals divided by the errors.
Bayes theorem then turns that into what we actually want, which is the probability of the
parameters given the data. That is the likelihood times the prior.
Two honest caveats about our implementation. First, we use a diagonal covariance matrix.
Masking couples neighbouring bandpowers, so the true covariance has off diagonal terms that
we are ignoring. That makes our error bars slightly optimistic.
Second, you must bin the theory the same way you binned the data. Evaluating a curved theory
spectrum at the bin centre, and comparing that to a bin average, is a real bias. It is small,
but it is exactly the kind of thing that quietly shifts a parameter by a fraction of a sigma.
""",
            equations=[
                Equation(
                    latex=r"\chi^2(\theta) = \sum_b \frac{[\mathcal{D}_b - "
                    r"\mathcal{D}_b(\theta)]^2}{\sigma_b^2}",
                    label="Gaussian bandpower likelihood",
                    explain="What our sampler evaluates at every step.",
                    variables=[
                        Var("\\chi^2", "total mismatch between theory and data. Smaller is a "
                                       "better fit; χ² ≈ one per data point means ‘agrees "
                                       "within the errors’"),
                        Var("\\theta", "the parameters being tried — H₀, the matter density, "
                                       "and so on. One θ is one candidate universe"),
                        Var("\\mathcal{D}_b", "our measured power in bin b", "µK²"),
                        Var("\\mathcal{D}_b(\\theta)", "what CAMB predicts for bin b in that "
                                                      "candidate universe", "µK²"),
                        Var("\\sigma_b", "our error bar on bin b", "µK²"),
                        Var("b", "which bandpower bin — we use 27 of them"),
                    ],
                    intuition=(
                        "This is the least-squares fitting you already know from drawing a "
                        "line through data points, with one addition: each gap is divided "
                        "by that point's error bar before squaring. That division is the "
                        "whole trick — missing a precisely measured point by a little is "
                        "worse than missing a poorly measured one by a lot. Squaring means "
                        "over- and under-shooting count the same, and big misses hurt "
                        "disproportionately. Our best fit gives χ²/dof = 1.067, which is "
                        "almost exactly what an honest fit should produce."
                    ),
                ),
                Equation(
                    latex=r"P(\theta|\mathcal{D}) \propto "
                    r"\mathcal{L}(\mathcal{D}|\theta)P(\theta)",
                    label="Bayes' theorem",
                    explain="Posterior ∝ likelihood × prior.",
                    variables=[
                        Var("P(\\theta|\\mathcal{D})", "the posterior: how believable each "
                                                      "universe is, now that we have seen "
                                                      "the data. This is the answer"),
                        Var("\\mathcal{L}(\\mathcal{D}|\\theta)", "the likelihood: how well "
                                                                 "that universe reproduces "
                                                                 "our data, from χ² above"),
                        Var("P(\\theta)", "the prior: what we believed beforehand. We use "
                                          "wide flat ranges, plus one measured constraint "
                                          "on τ that the CMB temperature alone cannot "
                                          "provide"),
                    ],
                    intuition=(
                        "Everyday reasoning, written down. A cough is more likely to be a "
                        "cold than a rare disease — not because coughing fits a cold better, "
                        "but because colds are common to begin with. Bayes says: combine how "
                        "well an explanation fits the evidence with how plausible it was "
                        "beforehand. Here the evidence is our spectrum and the explanations "
                        "are candidate universes. The output is not one number but a full "
                        "probability landscape, which is where the error bars come from."
                    ),
                ),
            ],
        ),
        Section(
            id="degeneracies",
            title="Why H₀ is hard and θ* is easy",
            plain=(
                "The CMB pins down the *angle* of the sound horizon superbly. But that one "
                "angle depends on several ingredients at once, and they can trade off "
                "against each other: make the universe expand faster and the peaks shift "
                "one way, then add less dark matter and they shift back. The data cannot "
                "tell those two universes apart. It is like knowing a rectangle's area but "
                "not its sides. This is why H₀ from the CMB has a wider error bar than you "
                "might expect, and why the numbers are quoted as correlated rather than "
                "independent."
            ),
            narrative=r"""
The CMB measures $\theta_* = r_s/D_A$ superbly — to 0.03%. But $H_0$ is only one ingredient
in $D_A$, and different parameter combinations can produce the *same* $\theta_*$.

Raise $H_0$ and $D_A$ shrinks. A ruler of fixed length at a shorter distance subtends a
*larger* angle, so $\theta_*$ grows and the peaks move to **lower** $\ell$ — from
$\ell = 225$ at $H_0 = 60$ to $\ell = 213$ at $H_0 = 80$. (It is worth pausing on the
direction here: closer means bigger, so the multipole goes down, not up. This is an easy
sign to get backwards.)

But lower $\Omega_c h^2$ at the same time and $\theta_*$ comes back to where it started.
Along that ridge the combination $\Omega_m h^3$ stays very nearly constant, and the data
cannot distinguish the two universes. This is the **geometric degeneracy**: a long, narrow,
tilted valley in the posterior.

This has two consequences that matter for us.

First, it is why we sample with MCMC rather than scanning a grid. A grid wastes
almost all of its points in regions of zero probability; an ensemble sampler like emcee
proposes moves using the positions of other walkers, so it automatically learns the shape
of the ridge and moves along it.

Second, it is why TT data alone cannot pin down $\tau$. Reionization suppresses the spectrum
by $e^{-2\tau}$ at essentially all the multipoles we measure, which is exactly degenerate
with lowering the primordial amplitude $A_s$. Only large-scale polarization breaks it. We
therefore impose a prior on $\tau$ from the published measurement and say so explicitly —
pretending otherwise would be quietly dishonest.
""",
            narration="""
The CMB measures the acoustic angle superbly, to three parts in ten thousand. But the
Hubble constant is only one ingredient in the angular diameter distance, and different
combinations of parameters can produce exactly the same angle.
Raise the Hubble constant and the distance to last scattering shrinks. Now, a ruler of fixed
length placed at a shorter distance subtends a larger angle. So the acoustic angle grows and
the peaks move to lower ell, not higher. From ell of two hundred twenty five at a Hubble
constant of sixty, down to two hundred thirteen at eighty. Pause on that direction, because
it is an easy sign to get backwards. Closer means bigger, so the multipole goes down.
But lower the cold dark matter density at the same time, and the acoustic angle comes right
back to where it started. Along that ridge, the combination omega matter times h cubed stays
very nearly constant, and the data cannot distinguish the two universes. This is called the
geometric degeneracy, and it shows up as a long, narrow, tilted valley in the posterior
distribution.
This has two consequences that matter for us. First, it is why we sample with Markov chain
Monte Carlo rather than scanning a grid. A grid wastes almost all of its points in regions
of zero probability. An ensemble sampler proposes moves using the positions of the other
walkers, so it automatically learns the shape of the ridge and moves along it.
Second, it is why temperature data alone cannot pin down the optical depth to reionization.
Reionization suppresses the spectrum by e to the minus two tau at essentially every
multipole we measure, which is exactly degenerate with lowering the primordial amplitude.
Only large scale polarization breaks that degeneracy. So we impose a prior on tau from the
published measurement, and we say so explicitly. Pretending otherwise would be quietly
dishonest.
""",
            equations=[
                Equation(
                    latex=r"C_\ell \propto A_s e^{-2\tau} \quad (\ell \gtrsim 40)",
                    label="The τ–A_s degeneracy",
                    explain="Indistinguishable without large-scale polarization.",
                    variables=[
                        Var("A_s", "the amplitude of the original quantum ripples from "
                                   "inflation — how loud the universe started out"),
                        Var("\\tau", "optical depth: how much the CMB was re-scattered by "
                                     "the first stars ionising the gas again, billions of "
                                     "years later"),
                        Var("e^{-2\\tau}", "the resulting dimming factor — roughly 10% of the "
                                          "signal is scattered away"),
                    ],
                    intuition=(
                        "A photo looks identical whether the scene was dim or the lens was "
                        "slightly fogged — you cannot separate the two from brightness "
                        "alone. Here A_s is the brightness and e^{-2τ} is the fog, and only "
                        "their product appears in the data. Polarisation breaks the tie, "
                        "because scattering leaves a distinctive polarised fingerprint that "
                        "dimming does not. We measure temperature only, so we adopt the "
                        "published τ as a prior and say so plainly rather than pretending we "
                        "measured it."
                    ),
                ),
                Equation(
                    latex=r"\theta_* = \frac{r_s(\Omega_b h^2, \Omega_c h^2)}"
                    r"{D_A(H_0,\Omega_m,\Omega_k)}",
                    label="Geometric degeneracy",
                    explain="Many (H₀, Ω_m) pairs give the same θ*.",
                    variables=[
                        Var("\\theta_*", "the one exquisitely measured angle", "rad"),
                        Var("\\Omega_c h^2", "physical density of cold dark matter"),
                        Var("\\Omega_k", "curvature of space. Zero means flat, which is what "
                                         "we measure"),
                    ],
                    intuition=(
                        "One equation, several unknowns — so there are infinitely many "
                        "solutions, like knowing only that two numbers multiply to 12. "
                        "Raise H₀ and the last-scattering surface is closer, so the ruler "
                        "looks bigger and the peaks move to lower ℓ; lower the dark matter "
                        "density and they move back. Our own run confirms it: H₀ = 60 puts "
                        "the peak at ℓ = 225, H₀ = 80 puts it at ℓ = 213, and the "
                        "combination Ω_m h³ barely moves. That valley of equally good "
                        "answers is why we sample with MCMC instead of scanning a grid."
                    ),
                ),
            ],
            live=["posterior_H0", "posterior_ombh2", "tension_H0"],
        ),
    ],
)


# ══════════════════════════════════════════════════════════════════════════════
# 6. The anomalies
# ══════════════════════════════════════════════════════════════════════════════

LESSON_ANOMALIES = Lesson(
    id="anomalies",
    title="The four anomalies, and how to not fool yourself",
    subtitle="Alignment, asymmetry, the Cold Spot, the low quadrupole — and the look-elsewhere effect",
    duration_min=16,
    prerequisites=["harmonics"],
    sections=[
        Section(
            id="the-four",
            title="What is actually claimed",
            plain=(
                "Four things about the biggest patterns in the CMB look odd. The two "
                "largest-scale patterns point in suspiciously similar directions, when they "
                "should be unrelated. One half of the sky is bumpier than the other. There "
                "is a large, unusually cold region in the south. And the very largest-scale "
                "ripple is weaker than predicted. All four numbers are real — the argument "
                "is entirely about whether they are surprising, which is much harder to "
                "judge than it sounds."
            ),
            narrative=r"""
Four features of the large-angle CMB have resisted easy explanation for two decades.

**1. Quadrupole–octupole alignment.** Each multipole has a preferred axis, found by
maximising the angular momentum dispersion $\sum_m m^2 |a_{\ell m}(\hat{n})|^2$ over
directions $\hat{n}$. In an isotropic universe the $\ell=2$ and $\ell=3$ axes should be
unrelated, so $\cos\gamma$ is uniform and the typical angle is 60°. Observed: around 10°.

**2. Hemispherical power asymmetry.** One half of the sky has noticeably more large-angle
power than the other. Statistical isotropy forbids any such preferred direction.

**3. The Cold Spot.** An unusually cold, unusually *extended* region in the southern sky,
found with Mexican-hat wavelets at about 5° scale.

**4. The low quadrupole.** $C_2$ comes out below the ΛCDM prediction.

Every one of these is real in the sense that the number is what it is. The question is
entirely about significance — and that is much harder than it looks.
""",
            narration="""
Four features of the large angle microwave background have resisted easy explanation for
two decades now.
Number one, the quadrupole octupole alignment. Each multipole has a preferred axis, which
you find by maximising the angular momentum dispersion over all possible directions. In an
isotropic universe, the ell equals two and ell equals three axes should be completely
unrelated, so the cosine of the angle between them should be uniformly distributed, and the
typical angle should be sixty degrees. What we observe is around ten degrees.
Number two, the hemispherical power asymmetry. One half of the sky has noticeably more
large angle power than the other. Statistical isotropy forbids any such preferred direction.
Number three, the Cold Spot. An unusually cold and unusually extended region in the southern
sky, found using Mexican hat wavelets at about a five degree scale.
Number four, the low quadrupole. The ell equals two power comes out below what the standard
model predicts.
Every one of these is real, in the sense that the number is what it is. The question is
entirely about significance. And that is much harder than it looks.
""",
            equations=[
                Equation(
                    latex=r"\hat{n}_\ell = \arg\max_{\hat{n}} \sum_m m^2 "
                    r"|a_{\ell m}(\hat{n})|^2",
                    label="Preferred axis",
                    explain=(
                        "Power concentrated in high |m| means the multipole lives near the "
                        "equator of that frame, so the axis picks out its plane."
                    ),
                    variables=[
                        Var("\\hat{n}_\\ell", "the preferred axis of multipole ℓ — the "
                                             "direction this pattern is 'organised' around"),
                        Var("\\arg\\max", "'the direction that maximises what follows' — try "
                                          "every orientation and keep the winner"),
                        Var("m^2", "a weight favouring patterns wrapped around the equator "
                                   "rather than spread over the poles"),
                    ],
                    intuition=(
                        "Spin a globe and ask which axis makes the pattern look most like "
                        "stripes around the equator. That is the computation: rotate to "
                        "every possible orientation, score how concentrated the pattern is "
                        "around that equator, and keep the best. Every pattern has such an "
                        "axis — that is not suspicious by itself. What is odd is that the "
                        "axes for ℓ = 2 and ℓ = 3 come out close together when they should be "
                        "unrelated. We measure 23.6°; random skies typically give 55°."
                    ),
                ),
                Equation(
                    latex=r"P(\cos\gamma)\,d\cos\gamma = d\cos\gamma \ \ "
                    r"\text{(uniform under isotropy)}",
                    label="The null hypothesis",
                    explain="Uniform in cos γ, not in γ — a classic place to slip up.",
                    variables=[
                        Var("\\gamma", "the angle between the two preferred axes", "deg"),
                        Var("P(\\cos\\gamma)", "the probability distribution of that angle if "
                                              "nothing special is going on"),
                    ],
                    intuition=(
                        "Scatter points evenly over a globe and most of them land near the "
                        "equator — simply because there is more surface area there than near "
                        "the poles. So two random directions are usually far apart, not "
                        "close: the typical separation is 60°, not 45°. Getting this wrong "
                        "is the single most common error in anomaly claims, because assuming "
                        "γ is uniform makes small angles look far rarer than they are. We "
                        "sidestep the algebra entirely by generating 500 random skies and "
                        "measuring what actually happens."
                    ),
                ),
            ],
            live=["alignment_angle", "alignment_p"],
        ),
        Section(
            id="look-elsewhere",
            title="The hardest part is not the physics",
            plain=(
                "Measuring the anomalies is easy; deciding whether they are surprising is "
                "hard. Two traps catch people. First, if you run four tests, something will "
                "probably look odd by luck — like finding a face in clouds because you "
                "scanned the whole sky. Second, the intuitive maths for 'how close are two "
                "random directions' is easy to get backwards. We avoid both by simulating "
                "500 universes that obey standard cosmology, measuring them exactly as we "
                "measured the real one, and counting. After correcting honestly, none of "
                "the four anomalies exceeds 2.1σ."
            ),
            narrative=r"""
Suppose you compute the alignment angle, find 10°, and note that only 1% of random skies do
that well. Is that a $2.5\sigma$ detection of new physics?

**No.** And understanding why is the most valuable thing in this whole lesson.

*You searched.* The axis was found by maximising over thousands of candidate directions.
Maximising over many trials produces extreme values even under the null hypothesis. Unless
your simulations perform the same search, you are comparing two different quantities.

*You chose the statistic after seeing the data.* Nobody wrote down "measure the
quadrupole-octupole angle" before looking at the CMB. It was chosen because it looked odd.
If you examine enough statistics, one of them will be a 1-in-100 event — that is what 1 in
100 means.

*You are quoting the best of several tests.* We test four anomalies. The chance that at
least one reaches $p < 0.01$ under the null is roughly four times higher than for any one
alone. The Šidák correction, $p_{\mathrm{corr}} = 1-(1-p)^n$, accounts for it.

Our pipeline handles the first by running the identical maximisation on every simulated
sky, and the third by applying the Šidák correction. The second is not fixable after the
fact — it can only be honestly declared. That is why the API reports both the raw and the
corrected p-value, and labels which is which.

This is also why gate G6 tests *calibration* rather than significance: feed the pipeline
skies that are isotropic by construction, and check the p-values come out uniform. A
pipeline that returns $p = 0.01$ for an ordinary sky is broken, and that is by far the most
common way anomaly analyses go wrong.
""",
            narration="""
Suppose you compute the alignment angle, you find ten degrees, and you note that only one
percent of random skies do that well. Is that a two point five sigma detection of new
physics?
No. And understanding why is the most valuable thing in this entire lesson.
First, you searched. The axis was found by maximising over thousands of candidate
directions. Maximising over many trials produces extreme values even under the null
hypothesis. Unless your simulations perform exactly the same search, you are comparing two
completely different quantities.
Second, you chose the statistic after seeing the data. Nobody wrote down, measure the
quadrupole octupole angle, before looking at the microwave background. It was chosen
because it looked odd. And if you examine enough statistics, one of them will be a one in a
hundred event. That is what one in a hundred means.
Third, you are quoting the best of several tests. We test four anomalies. The chance that at
least one of them reaches p less than point zero one under the null is roughly four times
higher than for any single one. The Sidak correction accounts for that.
Our pipeline handles the first problem by running the identical maximisation on every
simulated sky. It handles the third with the Sidak correction. The second one is not fixable
after the fact. It can only be honestly declared. That is why the API reports both the raw
and the corrected p value, and labels which is which.
And this is why our validation gate tests calibration rather than significance. Feed the
pipeline skies that are isotropic by construction, and check that the p values come out
uniform. A pipeline that returns p equals point zero one for a perfectly ordinary sky is
broken. And that is by far the most common way these analyses go wrong.
""",
            equations=[
                Equation(
                    latex=r"p_{\mathrm{corrected}} = 1 - (1-p)^{n}",
                    label="Šidák look-elsewhere correction",
                    explain="n = 4 here, the number of anomaly statistics tested.",
                    variables=[
                        Var("p", "the raw p-value: how often a random sky beats what we saw, "
                                 "for one specific test"),
                        Var("n", "how many different tests we ran — 4 for us"),
                        Var("p_{\\mathrm{corrected}}", "the honest p-value once you account "
                                                      "for having looked in several places"),
                    ],
                    intuition=(
                        "Roll a die once and a six is a 1-in-6 surprise. Roll it four times "
                        "and at least one six is no surprise at all — that is what this "
                        "corrects for. (1−p) is the chance one test looks normal, so "
                        "(1−p)ⁿ is the chance *all* of them do, and one minus that is the "
                        "chance something looked odd somewhere. It matters enormously here: "
                        "our Cold Spot goes from p = 0.010 to p = 0.039, dropping from "
                        "'interesting' to 'unremarkable'. Reporting only the raw number "
                        "would be misleading."
                    ),
                ),
                Equation(
                    latex=r"\hat{p} = \frac{N_{\mathrm{more\ extreme}} + 1}{N_{\mathrm{sims}} + 1}",
                    label="Empirical p-value with add-one smoothing",
                    explain=(
                        "The +1 prevents reporting p = 0, which would claim infinite "
                        "significance from a finite number of simulations."
                    ),
                    variables=[
                        Var("N_{\\mathrm{more\\ extreme}}", "how many simulated skies looked "
                                                           "at least as odd as the real one"),
                        Var("N_{\\mathrm{sims}}", "how many skies we simulated — 500"),
                        Var("\\hat{p}", "the resulting p-value. Small means the real sky is "
                                       "hard to reproduce by chance"),
                    ],
                    intuition=(
                        "Rather than trusting a formula, we build 500 fake universes that "
                        "obey standard cosmology, measure each one the same way, and count "
                        "how many are as strange as ours. That fraction is the p-value. The "
                        "+1 on top and bottom is important honesty: if none of 500 sims beat "
                        "the real sky, the truthful statement is 'less than about 1 in 500', "
                        "not 'exactly zero'. Without it you would claim infinite "
                        "significance from a finite experiment."
                    ),
                ),
            ],
            live=["anomaly_summary"],
        ),
    ],
)


LESSONS: dict[str, Lesson] = {
    lesson.id: lesson
    for lesson in (
        LESSON_ORIGIN,
        LESSON_HARMONICS,
        LESSON_PEAKS,
        LESSON_ESTIMATOR,
        LESSON_INFERENCE,
        LESSON_ANOMALIES,
    )
}

CURRICULUM_ORDER = ["origin", "harmonics", "peaks", "estimator", "inference", "anomalies"]


def get_lesson(lesson_id: str) -> Lesson:
    if lesson_id not in LESSONS:
        raise KeyError(f"Unknown lesson {lesson_id!r}. Known: {CURRICULUM_ORDER}")
    return LESSONS[lesson_id]


def get_section(lesson_id: str, section_id: str) -> Section:
    lesson = get_lesson(lesson_id)
    for section in lesson.sections:
        if section.id == section_id:
            return section
    raise KeyError(
        f"Unknown section {section_id!r} in {lesson_id!r}. Known: {[s.id for s in lesson.sections]}"
    )
