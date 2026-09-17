# The Cosmic Microwave Background

### A self-contained course, from high-school algebra to a measured cosmology

---

**What this book is.** `cmb-lab` measures the age, shape and composition of the universe from
raw NASA satellite data. This book explains *every* piece of physics, mathematics and statistics
behind that measurement, starting from scratch.

**Who it is for.** A new graduate student — or a curious engineer — who has opened the website,
seen a plot with a peak at $\ell = 220$, a table of six Greek letters, and a claim that the
universe is 13.8 billion years old, and wants to know **why any of that follows**.

**The promise.** You should not need to open another book. Everything is derived here. Where I
use a result without deriving it, I say so explicitly and tell you what it would take.

---

## How to use this book

Read it in order. Each part depends on the one before.

If you are impatient, here is the entire argument in six sentences, which you will not fully
believe until you have read the book:

1. The early universe was a hot plasma; sound waves rang in it.
2. It suddenly became transparent, freezing those waves into a temperature pattern on the sky.
3. The loudest wave had a known physical wavelength — a **standard ruler**.
4. We measure the *angle* that ruler subtends today.
5. Ruler + angle $\Rightarrow$ distance $\Rightarrow$ geometry and contents of the universe.
6. Everything else is the engineering required to measure that angle without lying to yourself.

Step 6 is most of the work, and most of this book.

### Conventions

- **Exercises** appear throughout. Solutions are in Appendix C. Do them; the derivations are short
  and the numbers are real.
- **Worked numbers** use the actual values this project measures, not textbook round figures.
- ⚙ marks a link between the physics and the code in this repository.
- ⚠ marks a place where the naive thing is wrong and will silently ruin your result.

### Prerequisites

Honestly, very little:

| You need | Level | Where it is used |
|---|---|---|
| Algebra, rearranging equations | High school | Everywhere |
| Trigonometry, small-angle approximation | High school | Angular scales |
| Newton's laws, gravity, energy conservation | High school | The Friedmann equation |
| Waves: wavelength, frequency, speed | High school | Acoustic oscillations |
| Derivatives and integrals | First-year calculus | Everywhere |
| Complex exponentials $e^{i\theta}$ | First-year | Fourier analysis |
| Mean, variance, Gaussian distribution | First-year | Error bars, inference |

You do **not** need general relativity, quantum field theory, or a course in statistics. Where
those would normally be invoked, I either derive the needed result by elementary means or flag
the shortcut honestly.

---

## Table of contents

**Part 0 — The toolkit**
0.1 Units, scales, and how to not be intimidated ·
0.2 The calculus you actually need ·
0.3 Waves, Fourier, and why we decompose ·
0.4 Probability, variance, and $\chi^2$

**Part I — The expanding universe**
1 Hubble's law and the scale factor ·
2 The Friedmann equation from Newtonian energy conservation ·
3 What the universe is made of, and how each ingredient dilutes ·
4 Redshift, temperature, and the thermal history ·
5 Recombination: why the fog cleared at 3000 K and not 158,000 K

**Part II — Sound in the early universe**
6 Perturbations: the universe is lumpy at the $10^{-5}$ level ·
7 The photon–baryon fluid is a harmonic oscillator ·
8 The sound horizon: a ruler built from first principles ·
9 Why the first peak sits at $\ell = 220$ ·
10 Reading the other peaks: baryons, dark matter, damping

**Part III — The statistics of a sky**
11 Spherical harmonics, built from Fourier series ·
12 The angular power spectrum $C_\ell$ ·
13 Why every plot shows $\mathcal{D}_\ell$ ·
14 Cosmic variance: the error bar you can never beat

**Part IV — The measurement**
15 What a CMB map actually is ·
16 Cleaning: monopole and dipole ·
17 Foregrounds and masks ·
18 The mask breaks orthogonality: pseudo-$C_\ell$ ·
19 Beams and pixel windows ·
20 Noise, and the central trick: cross-spectra ·
21 Unresolved point sources ·
22 Binning and error bars

**Part V — From a curve to a cosmology**
23 Boltzmann codes: what CAMB actually computes ·
24 The six parameters ·
25 Likelihood and $\chi^2$ ·
26 MCMC from first principles ·
27 Degeneracies ·
28 The Hubble tension

**Part VI — Anomalies and honest statistics**
29 The four anomalies ·
30 The look-elsewhere effect ·
31 Calibrating $p$-values with simulations

**Part VII — The pipeline**
32 The six gates, mapped to the physics ·
33 Service by service

**Appendices**
A Symbols · B Constants · C Solutions · D Further reading

---
---

# PART 0 — THE TOOLKIT

Skip any section here that is already familiar. Nothing in Part 0 is cosmology; it is the
vocabulary.

---

## 0.1 Units, scales, and how to not be intimidated

Cosmology uses a small number of unfamiliar units. They are all just scaled metres, seconds and
kelvin.

### Distance

| Unit | Symbol | In metres | Intuition |
|---|---|---|---|
| Astronomical unit | AU | $1.496 \times 10^{11}$ | Earth–Sun distance |
| Light year | ly | $9.461 \times 10^{15}$ | Distance light travels in a year |
| Parsec | pc | $3.086 \times 10^{16}$ | 3.26 ly |
| Megaparsec | Mpc | $3.086 \times 10^{22}$ | Typical galaxy separation |
| Gigaparsec | Gpc | $3.086 \times 10^{25}$ | A good fraction of the observable universe |

The **observable universe** has a comoving radius of about 14 Gpc. The **sound horizon**, the
ruler at the heart of this entire book, is about 144 Mpc — roughly 1% of that.

### Temperature and energy

The CMB today is at

$$T_0 = 2.7255 \pm 0.0006 \ \text{K}$$

That is 2.7 degrees above absolute zero. Its temperature *fluctuations* are about

$$\frac{\Delta T}{T} \sim 10^{-5} \quad \Rightarrow \quad \Delta T \sim 30\ \mu\text{K}$$

where $\mu\text{K} = 10^{-6}$ K. **This is the entire signal.** Everything in Part IV exists
because measuring a 30-microkelvin ripple on a 2.7-kelvin background, through a galaxy that
glows, with a detector that has noise, is hard.

Energy and temperature are related by Boltzmann's constant $k_B$:

$$E = k_B T, \qquad k_B = 8.617 \times 10^{-5}\ \text{eV/K}$$

An electronvolt (eV) is the energy an electron gains falling through one volt. The binding energy
of hydrogen is 13.6 eV — remember that number, it returns in Chapter 5.

### Orders of magnitude

Physicists survive by estimating before calculating. The single most useful habit in this book:
**check the exponent before you trust the digits.**

> **Exercise 0.1** The CMB photon number density today is about $411$ photons per cm³. The
> baryon (ordinary matter) number density is about $2.5 \times 10^{-7}$ per cm³. What is the
> ratio of photons to baryons? *(This number governs Chapter 5.)*

---

## 0.2 The calculus you actually need

### Derivatives

A derivative is a rate of change. If $x(t)$ is position, $\dot{x} \equiv dx/dt$ is velocity.
Cosmologists write time derivatives with a dot:

$$\dot{a} \equiv \frac{da}{dt}, \qquad \ddot{a} \equiv \frac{d^2a}{dt^2}$$

You need three rules:

$$\frac{d}{dx}x^n = nx^{n-1}, \qquad \frac{d}{dx}e^{kx} = ke^{kx}, \qquad \frac{d}{dx}\ln x = \frac{1}{x}$$

and the chain rule, $\frac{d}{dx}f(g(x)) = f'(g)\,g'(x)$.

### Integrals

An integral is a sum of infinitely many infinitesimal pieces. When we write

$$r_s = \int_{0}^{t_*} c_s(t)\,dt$$

it means: chop the time from the Big Bang to recombination into tiny slices $dt$, in each slice
the sound travels $c_s\,dt$, add them all up. That is *literally* all an integral is here — a
total distance accumulated at a varying speed.

### Taylor expansion

For small $x$:

$$(1+x)^n \approx 1 + nx, \qquad e^x \approx 1 + x, \qquad \cos x \approx 1 - \tfrac{1}{2}x^2$$

The **small-angle approximation** is the workhorse of Part II:

$$\sin\theta \approx \theta \qquad (\theta \ \text{in radians}, \ \theta \ll 1)$$

A degree is $\pi/180 = 0.01745$ rad, so for anything smaller than a few degrees this is excellent.
The first acoustic peak subtends $\approx 0.6°$, so we are firmly in this regime.

> **Exercise 0.2** The sound horizon is $r_s = 144$ Mpc and it lies at a distance
> $D_A = 13{,}870$ Mpc. Using the small-angle approximation, what angle does it subtend, in
> radians and in degrees?

---

## 0.3 Waves, Fourier, and why we decompose

### A wave

A wave travelling in one dimension:

$$f(x,t) = A\cos(kx - \omega t)$$

- $A$ — amplitude
- $k = 2\pi/\lambda$ — **wavenumber**; large $k$ means short wavelength
- $\omega = 2\pi/T$ — angular frequency
- $\omega/k = c_s$ — the wave speed

A **standing wave** is what you get when the medium is bounded or the wave is driven from rest:

$$f(x,t) = A\cos(kx)\cos(\omega t)$$

The spatial pattern $\cos(kx)$ stays put; only the amplitude oscillates. Chapter 7 shows the
early universe rings in exactly this way, and that is the origin of the peaks.

### Fourier series

**Claim.** Any reasonable periodic function can be written as a sum of sines and cosines.

On a circle (period $2\pi$):

$$f(\theta) = \sum_{m=-\infty}^{\infty} c_m e^{im\theta}, \qquad
c_m = \frac{1}{2\pi}\int_0^{2\pi} f(\theta)e^{-im\theta}\,d\theta$$

Why does the coefficient formula work? Because the basis functions are **orthogonal**:

$$\frac{1}{2\pi}\int_0^{2\pi} e^{im\theta}e^{-im'\theta}\,d\theta = \delta_{mm'}$$

where $\delta_{mm'}$ (the Kronecker delta) is 1 if $m=m'$ and 0 otherwise. Multiply $f$ by
$e^{-im'\theta}$, integrate, and every term dies except the one you want. **Remember this
mechanism** — in Chapter 11 we do the identical thing on a sphere, and in Chapter 18 we discover
that cutting out the Galaxy destroys the orthogonality and creates real problems.

### Why decompose at all?

Three reasons, all of which matter later:

1. **Physics is simpler per-mode.** The equation of motion for the plasma couples neighbouring
   points in space in a complicated way. In Fourier space each wavenumber $k$ evolves
   *independently*, as a simple oscillator. This is the whole reason Chapter 7 works.
2. **Theory predicts a spectrum, not a map.** Inflation predicts the statistical *amplitude* of
   each mode, not where the hot spots are. So the comparison between theory and data must be
   made mode by mode.
3. **Scales are physically distinct.** Large angles probe primordial conditions; small angles
   probe plasma physics at recombination. Separating them separates the physics.

> **Exercise 0.3** Show that $\cos(kx) = \frac{1}{2}(e^{ikx} + e^{-ikx})$, and hence that a real
> function requires $c_{-m} = c_m^*$.

---

## 0.4 Probability, variance, and $\chi^2$

This section is short but is the backbone of Parts IV–VI. Nearly every serious mistake in CMB
analysis is a statistics mistake, not a physics mistake.

### Mean and variance

For a random variable $X$ with $N$ samples:

$$\langle X \rangle = \frac{1}{N}\sum_i X_i, \qquad
\mathrm{Var}(X) = \langle (X - \langle X\rangle)^2 \rangle = \langle X^2\rangle - \langle X\rangle^2$$

The standard deviation is $\sigma = \sqrt{\mathrm{Var}(X)}$.

### The Gaussian

$$P(x) = \frac{1}{\sqrt{2\pi\sigma^2}}\exp\left[-\frac{(x-\mu)^2}{2\sigma^2}\right]$$

68% of the probability lies within $1\sigma$ of the mean, 95% within $2\sigma$, 99.7% within
$3\sigma$. When we say a parameter is "within $3\sigma$ of the published value", we mean the
discrepancy is unremarkable.

**The CMB temperature field is Gaussian** to excellent accuracy. This is a prediction of simple
inflation, it is strongly supported by the data, and it is enormously convenient: a Gaussian
field is *completely described* by its variance as a function of scale — which is exactly the
power spectrum. Chapter 12 makes this precise.

### The $\chi^2$ distribution

If $Z_1,\dots,Z_n$ are independent standard Gaussians (mean 0, variance 1), then

$$\chi^2_n \equiv \sum_{i=1}^{n} Z_i^2$$

follows the chi-squared distribution with $n$ degrees of freedom. Two facts we will use
repeatedly:

$$\langle \chi^2_n \rangle = n, \qquad \mathrm{Var}(\chi^2_n) = 2n$$

The first fact is why **"$\chi^2$ per degree of freedom $\approx 1$" means "the model fits"**:
each data point should contribute about $1$ if the model is right and the error bars are honest.

- $\chi^2/\text{dof} \gg 1$ — model is wrong, or error bars are underestimated.
- $\chi^2/\text{dof} \ll 1$ — error bars are *over*estimated, or you fitted noise.

⚙ This project's Gate G4 demands $0.3 \le \chi^2/\text{dof} \le 3.0$ and achieves $0.57$ against
WMAP and $0.87$ against Planck.

> **Exercise 0.4** Derive $\mathrm{Var}(\chi^2_n) = 2n$ from $\mathrm{Var}(Z^2) = 2$ for a single
> standard Gaussian. *(Hint: $\langle Z^4\rangle = 3$.)* This innocuous result becomes cosmic
> variance in Chapter 14.

---
---

# PART I — THE EXPANDING UNIVERSE

We now build the background on which everything else happens. The goal of Part I is one
equation — the Friedmann equation — and one consequence: the universe was hot, dense and opaque,
and then it wasn't.

---

## 1 Hubble's law and the scale factor

### The observation

In 1929 Hubble found that galaxies recede from us with velocity proportional to distance:

$$v = H_0 d$$

$H_0$ is the **Hubble constant**, measured in km s⁻¹ Mpc⁻¹. A galaxy 10 Mpc away recedes at
about 674 km/s.

### The interpretation

Naively this puts us at the centre of an explosion. It does not. Consider a rubber sheet with
dots painted on it, stretched uniformly. Every dot sees every other dot receding, with speed
proportional to separation, and no dot is special.

Formalise this. Let the physical distance between two objects be

$$\boxed{\ r(t) = a(t)\,x\ }$$

where $x$ is a fixed **comoving** coordinate (a label painted on the sheet, never changing) and
$a(t)$ is the **scale factor** (how stretched the sheet is). Normalise $a(t_0) = 1$ today.

Differentiate:

$$v = \dot{r} = \dot{a}x = \frac{\dot{a}}{a}(ax) = \frac{\dot{a}}{a}r$$

So Hubble's law is automatic, with

$$\boxed{\ H(t) \equiv \frac{\dot{a}}{a}\ }$$

$H$ is the **Hubble parameter**; $H_0$ is its value today. Note $H$ is not constant in time —
calling it the "Hubble constant" is a historical accident.

### The dimensionless $h$

Because $H_0$ was uncertain for decades, cosmologists factor it out:

$$H_0 = 100\,h \ \ \text{km s}^{-1}\text{Mpc}^{-1}$$

Planck 2018 gives $h = 0.6736$. Watch for this: the parameters we fit in Chapter 24 are
$\Omega_b h^2$ and $\Omega_c h^2$, *not* $\Omega_b$ and $\Omega_c$. Chapter 27 explains why the
CMB insists on that particular combination.

> **Exercise 1.1** $1/H_0$ has units of time. Compute it in years for $h=0.6736$. Compare to the
> measured age of the universe, 13.797 Gyr. Why are they close but not equal?

---

## 2 The Friedmann equation from Newtonian energy conservation

This is the most important derivation in Part I, and it needs **no general relativity**. The full
GR derivation gives the identical answer for the cases we care about.

### Setup

Imagine a large uniform sphere of matter with density $\rho(t)$, expanding with the universe.
Put a test galaxy of mass $m$ on its surface at radius $r$.

Newton's shell theorem: the gravitational force on the galaxy comes only from mass *inside*
radius $r$, and acts as if concentrated at the centre. That mass is

$$M = \frac{4}{3}\pi r^3 \rho$$

### Energy conservation

The galaxy's total energy is kinetic plus potential:

$$E = \frac{1}{2}m\dot{r}^2 - \frac{GMm}{r}$$

Substitute $M$:

$$E = \frac{1}{2}m\dot{r}^2 - \frac{4\pi G}{3}\rho r^2 m$$

Now put in $r = a x$, so $\dot r = \dot a x$:

$$E = \frac{1}{2}m\dot{a}^2x^2 - \frac{4\pi G}{3}\rho a^2x^2 m$$

Divide through by $\frac{1}{2}ma^2x^2$:

$$\frac{2E}{ma^2x^2} = \frac{\dot{a}^2}{a^2} - \frac{8\pi G}{3}\rho$$

Rearrange, and define the constant $kc^2 \equiv -2E/(mx^2)$:

$$\boxed{\ \left(\frac{\dot{a}}{a}\right)^2 = H^2 = \frac{8\pi G}{3}\rho - \frac{kc^2}{a^2}\ }$$

**That is the Friedmann equation.** We derived the central equation of cosmology from high-school
energy conservation.

### What $k$ means

$k$ is the **curvature**. Its sign is the sign of $-E$:

| $k$ | Total energy | Geometry | Fate |
|---|---|---|---|
| $k > 0$ | $E<0$, bound | Closed (sphere-like) | Recollapses |
| $k = 0$ | $E=0$, critical | **Flat** (Euclidean) | Expands forever, just barely |
| $k < 0$ | $E>0$, unbound | Open (saddle-like) | Expands forever |

This is exactly the escape-velocity problem from high-school physics, applied to the universe.

⚠ The Newtonian derivation gives the right equation but the wrong *interpretation* of $k$: in GR
it is genuine spatial curvature, not just an energy constant. And pressure gravitates in GR,
which Newtonian gravity misses — that matters in the next section.

### Critical density

Set $k=0$ and solve for the density:

$$\boxed{\ \rho_c = \frac{3H^2}{8\pi G}\ }$$

Today $\rho_c \approx 8.5\times10^{-27}$ kg/m³ — about five hydrogen atoms per cubic metre. Define
the **density parameter** for each component $i$:

$$\Omega_i \equiv \frac{\rho_i}{\rho_c}$$

The Friedmann equation becomes an accounting identity:

$$\Omega_m + \Omega_r + \Omega_\Lambda + \Omega_k = 1$$

**A flat universe is one where the $\Omega$s of real stuff sum to exactly 1.** The first
acoustic peak measures this, and finds it to be 1 to within a fraction of a percent. Chapter 9
shows how.

> **Exercise 2.1** Verify $\rho_c \approx 8.5\times 10^{-27}$ kg/m³ using $H_0 = 67.36$
> km/s/Mpc and $G = 6.674\times10^{-11}$ SI. Convert to hydrogen atoms per cubic metre.

---

## 3 What the universe is made of, and how each ingredient dilutes

Different substances dilute differently as space stretches. This is the key to the thermal
history.

### The fluid equation from thermodynamics

Take the first law, $dU = -p\,dV$ (no heat flows in or out of a comoving volume — there is
nowhere for it to go). With energy density $\rho c^2$ in a volume $V \propto a^3$:

$$d(\rho c^2 a^3) = -p\,d(a^3)$$

Expand both sides:

$$c^2(\dot\rho a^3 + 3\rho a^2 \dot a) = -3pa^2\dot a$$

Divide by $c^2a^3$:

$$\boxed{\ \dot\rho = -3\frac{\dot a}{a}\left(\rho + \frac{p}{c^2}\right) = -3H\left(\rho + \frac{p}{c^2}\right)}$$

### Three kinds of stuff

Each component has an **equation of state** $p = w\rho c^2$:

**Matter** (galaxies, dark matter) — pressureless dust, $w=0$:

$$\dot\rho = -3H\rho \implies \rho_m \propto a^{-3}$$

Obvious: fixed number of particles, volume grows as $a^3$.

**Radiation** (photons, neutrinos) — $w = 1/3$:

$$\dot\rho = -4H\rho \implies \rho_r \propto a^{-4}$$

One power of $a$ *more* than matter. Why? Number density dilutes as $a^{-3}$, **and** each photon
redshifts, losing energy as $a^{-1}$. That extra factor is the whole reason the early universe
was radiation dominated.

**Dark energy / cosmological constant** — $w = -1$:

$$\dot\rho = 0 \implies \rho_\Lambda = \text{constant}$$

Energy density that does not dilute. Negative pressure. Nobody knows what it is.

### The expansion history

Substituting into Friedmann:

$$\boxed{\ H^2(z) = H_0^2\left[\Omega_r(1+z)^4 + \Omega_m(1+z)^3 + \Omega_k(1+z)^2 + \Omega_\Lambda\right]}$$

using $1+z = 1/a$ (proved in the next chapter). Define

$$E(z) \equiv \frac{H(z)}{H_0}$$

This function appears in every distance integral from here on.

### Eras

Because the powers differ, whichever component wins changes with time:

| Era | Redshift | Dominant | $a(t)$ |
|---|---|---|---|
| Radiation | $z \gtrsim 3400$ | $\rho_r$ | $a \propto t^{1/2}$ |
| Matter | $3400 \gtrsim z \gtrsim 0.3$ | $\rho_m$ | $a \propto t^{2/3}$ |
| Dark energy | $z \lesssim 0.3$ | $\rho_\Lambda$ | $a \propto e^{Ht}$ |

**Recombination ($z_* \approx 1090$) happens in the matter era, shortly after
matter–radiation equality.** That timing is not a coincidence we can ignore — it affects peak
heights, as Chapter 10 explains.

> **Exercise 3.1** Matter–radiation equality is where $\rho_m = \rho_r$. Given
> $\Omega_m = 0.3153$ and $\Omega_r = 9.2\times10^{-5}$, find $z_{eq}$.

> **Exercise 3.2** Show that for a flat, matter-only universe, $a \propto t^{2/3}$.
> *(Substitute $\rho \propto a^{-3}$ into Friedmann with $k=0$ and solve.)*

---

## 4 Redshift, temperature, and the thermal history

### Redshift

Light emitted with wavelength $\lambda_{emit}$ arrives stretched by exactly the factor the
universe grew:

$$\frac{\lambda_{obs}}{\lambda_{emit}} = \frac{a(t_{obs})}{a(t_{emit})}$$

Define redshift $z$ by $\lambda_{obs} = (1+z)\lambda_{emit}$. With $a(t_0)=1$:

$$\boxed{\ 1+z = \frac{1}{a}\ }$$

Redshift is therefore a **stand-in for time**: $z=0$ is now, $z=1090$ is recombination,
$z\to\infty$ is the Big Bang. Cosmologists quote epochs in $z$ because it is what we observe.

### Temperature

A blackbody stays a blackbody as the universe expands; only its temperature drops. Since photon
energy $E = hc/\lambda \propto 1/a$:

$$\boxed{\ T(z) = T_0(1+z)\ }$$

⚙ This equation appears in the site's first lesson.

**Worked example.** At recombination, $z_* = 1090$:

$$T_* = 2.7255 \times 1091 \approx 2973 \ \text{K}$$

About half the surface temperature of the Sun. Going further back, the universe was arbitrarily
hot — that is the Big Bang.

### The blackbody

The CMB is the most perfect blackbody ever measured — COBE/FIRAS found deviations below
$10^{-4}$. Why does that matter? **Because it proves thermal equilibrium.** Only many scatterings
produce a perfect Planck spectrum. The CMB is therefore not starlight or any late-time emission;
it is the thermalised radiation of a dense early universe. This single observation killed the
steady-state model.

> **Exercise 4.1** The Planck spectrum peaks at $\lambda_{peak} T = 2.898\times10^{-3}$ m·K
> (Wien). Find the peak wavelength of the CMB today, and confirm it is microwave.

---

## 5 Recombination: why the fog cleared at 3000 K

Here is a puzzle whose resolution is genuinely beautiful, and which explains why the CMB exists
at all.

### The puzzle

Hydrogen's binding energy is 13.6 eV. Setting $k_BT = 13.6$ eV gives

$$T = \frac{13.6}{8.617\times10^{-5}} \approx 158{,}000 \ \text{K}$$

So you would expect hydrogen to form — and the universe to become transparent — at 158,000 K.
But it actually happens at **3000 K**, a factor of 50 lower. Why?

### The resolution: photons hugely outnumber baryons

From Exercise 0.1, the photon-to-baryon ratio is

$$\eta^{-1} = \frac{n_\gamma}{n_b} \approx 1.6\times10^{9}$$

There are **1.6 billion photons per proton**. Even when the *average* photon is far too feeble to
ionise hydrogen, the exponential tail of the Planck distribution still contains enough
high-energy photons to keep everything ionised. The number in the tail above energy $E$ falls as
$e^{-E/k_BT}$, so ionisation persists until

$$e^{-13.6\,\text{eV}/k_BT} \sim \eta \sim 10^{-9}$$

Taking logarithms: $13.6/k_BT \sim \ln(10^9) \approx 21$, giving $k_BT \sim 0.65$ eV, i.e.
$T \sim 7500$ K. A more careful treatment (below) gives $\approx 3000$ K.

**The delay is caused entirely by the enormous photon-to-baryon ratio.** A beautiful example of
an exponentially small number being beaten by an exponentially large one.

### The Saha equation

Quantitatively, in equilibrium the ionisation fraction $x_e = n_e/n_b$ obeys

$$\frac{x_e^2}{1-x_e} = \frac{1}{n_b}\left(\frac{m_ek_BT}{2\pi\hbar^2}\right)^{3/2}e^{-13.6\,\text{eV}/k_BT}$$

The exponential does the work; the prefactor supplies the large ratio. Solving numerically:
$x_e$ plunges from 1 to $\sim10^{-4}$ over a narrow range around $z \approx 1100$.

### Last scattering

Photons scatter off *free* electrons (Thomson scattering). Once electrons are bound into neutral
hydrogen, there is nothing left to scatter from, and photons stream freely. The moment this
happens:

$$z_* = 1089.92 \pm 0.25, \qquad t_* \approx 380{,}000 \ \text{yr}, \qquad T_* \approx 2970 \ \text{K}$$

⚙ These are the numbers in the site's first lesson.

### The surface of last scattering

Because recombination is fast but not instantaneous, the CMB comes from a **shell** of finite
thickness ($\Delta z \approx 80$), not a surface. This matters: the shell's thickness smears out
features smaller than its depth, contributing to the damping of Chapter 10.

Think of it exactly like the surface of the Sun. You cannot see into the Sun; you see the layer
where it becomes transparent. The CMB is the same thing for the whole universe — **we are looking
at a wall of fog, 13.8 billion years away, in every direction.**

> **Exercise 5.1** Photons decouple when the scattering rate $\Gamma = n_e\sigma_T c$ drops below
> the expansion rate $H$. Explain physically why this particular comparison is the right
> criterion.

> **Exercise 5.2** If the photon-to-baryon ratio were $10^{-3}$ instead of $10^{9}$, roughly what
> temperature would recombination occur at? What would that do to the CMB we see?

---
---

# PART II — SOUND IN THE EARLY UNIVERSE

Part I gave us a hot, smooth, expanding plasma that suddenly turns transparent. But a perfectly
smooth universe has no galaxies and a featureless CMB. Part II is about the **deviations from
smoothness** — where they come from, how they oscillate, and why they leave a ruler on the sky.

---

## 6 Perturbations: the universe is lumpy at the $10^{-5}$ level

### The contrast

Define the fractional overdensity:

$$\delta(\vec{x}) \equiv \frac{\rho(\vec{x}) - \bar{\rho}}{\bar{\rho}}$$

$\delta = 0$ is perfectly smooth; $\delta = 1$ means twice the average density. In the CMB,

$$\frac{\Delta T}{T} \sim 10^{-5}$$

so the perturbations at recombination are **tiny**. This is superb news mathematically: we can
drop all terms of order $\delta^2$ and work with *linear* equations. Cosmological perturbation
theory is accurate to parts in $10^5$ at recombination, which is why CMB predictions are so
precise, and why the CMB is a far cleaner probe than galaxy surveys (where $\delta \gg 1$ today).

### Where the perturbations came from

Inflation: a burst of exponential expansion in the first $10^{-34}$ s stretched quantum vacuum
fluctuations to cosmological size. It predicts a **nearly scale-invariant** spectrum of
perturbations:

$$P(k) \propto k^{n_s}, \qquad n_s \approx 1$$

"Scale-invariant" ($n_s = 1$ exactly) means every scale enters with equal amplitude. Inflation
predicts $n_s$ slightly *less* than 1, because the expansion rate drifts slowly.

⚙ This project measures $n_s = 0.9649 \pm 0.0042$. That number is $8\sigma$ from 1. **Inflation
predicted a small deviation from scale invariance, and we measure it.** It is one of the genuine
triumphs of modern cosmology, and it falls out of the fit in Chapter 24.

### Fourier modes again

Expand $\delta$ in plane waves:

$$\delta(\vec{x}) = \int \frac{d^3k}{(2\pi)^3}\,\delta_{\vec{k}}\,e^{i\vec{k}\cdot\vec{x}}$$

Because the equations are linear and the background is homogeneous, **each $\vec{k}$ evolves
independently**. This turns a partial differential equation in space and time into an ordinary
differential equation in time, one per mode. That is the payoff promised in §0.3.

---

## 7 The photon–baryon fluid is a harmonic oscillator

This chapter is the heart of the physics. Everything observable follows from it.

### The two competing forces

Before recombination, photons and baryons are locked together by Thomson scattering into a single
fluid. Dark matter does *not* participate — it has no electromagnetic interaction — so it just
sits there providing gravitational wells.

Two forces act on a lump of this photon–baryon fluid:

1. **Gravity** pulls it inward, into dark-matter potential wells.
2. **Radiation pressure** from the photons pushes it outward.

Gravity compresses, pressure resists, the fluid overshoots, pressure pushes back, it overshoots
the other way. **The early universe rings like a bell.** These are literally sound waves — the
universe was filled with sound at enormous amplitude.

### The sound speed

For a fluid, the sound speed is $c_s^2 = \delta p/\delta\rho$. The pressure comes almost entirely
from photons:

$$p = p_\gamma = \frac{1}{3}\rho_\gamma c^2$$

but the *inertia* comes from photons **and** baryons: $\delta\rho = \delta\rho_\gamma + \delta\rho_b$.

For adiabatic perturbations, $\delta\rho_b/\rho_b = \frac{3}{4}\,\delta\rho_\gamma/\rho_\gamma$
(because $\rho_b \propto a^{-3}$ while $\rho_\gamma \propto a^{-4}$, so
$\delta_b = \frac{3}{4}\delta_\gamma$). Therefore

$$\frac{\delta\rho_b}{\delta\rho_\gamma} = \frac{3\rho_b}{4\rho_\gamma} \equiv R$$

and

$$c_s^2 = \frac{\delta p}{\delta\rho} = \frac{\frac{1}{3}c^2\,\delta\rho_\gamma}{\delta\rho_\gamma(1+R)}$$

$$\boxed{\ c_s = \frac{c}{\sqrt{3(1+R)}}, \qquad R \equiv \frac{3\rho_b}{4\rho_\gamma} \propto \Omega_b h^2 \,a\ }$$

⚙ This is the equation on the site's second lesson card.

**Read this physically.** With no baryons ($R=0$), $c_s = c/\sqrt{3} \approx 0.577c$ — the sound
speed of a pure photon gas, and an *enormous* fraction of the speed of light. Adding baryons
loads the fluid with inertia without adding pressure, so the sound slows. **More baryons, slower
sound, smaller sound horizon.** Keep that chain; Chapter 10 uses it.

### The oscillator equation

Combining continuity and Euler equations for the fluid in a gravitational potential $\Psi$, and
working mode by mode, gives (for constant $R$, and neglecting the slow evolution of the
potential):

$$\boxed{\ \ddot{\delta}_\gamma + c_s^2k^2\delta_\gamma = F\ }$$

This is **exactly** the equation of a mass on a spring, $\ddot{x} + \omega^2 x = F$, with
$\omega = c_sk$ and a constant gravitational driving term $F$.

You already know the solution from high-school physics. Starting from rest (which is what
inflation's adiabatic initial conditions give), the solution is a cosine:

$$\delta_\gamma(\eta) \propto \cos(c_sk\eta) + \text{const}$$

where $\eta$ is conformal time (see below). Writing $r_s(\eta) = \int_0^{\eta}c_s\,d\eta'$ for the
distance sound has travelled:

$$\boxed{\ \delta_\gamma \propto \cos(k\,r_s)\ }$$

### Conformal time

$$\eta \equiv \int_0^t \frac{dt'}{a(t')}$$

Conformal time is the comoving distance light has travelled. It is convenient because in these
coordinates light moves on 45° lines, exactly as in flat spacetime.

### The resonance condition

At recombination, the oscillation **stops dead** — photons stop interacting with baryons and the
pattern is frozen. Whatever phase each mode was at, it is preserved forever.

Modes caught at **maximum compression or maximum rarefaction** have the largest $|\delta_\gamma|$,
hence the largest temperature contrast. Since we observe *power* $\propto |\delta|^2$, both
extremes show up as peaks. That happens when

$$\boxed{\ k_n r_s(\eta_*) = n\pi, \qquad n = 1, 2, 3,\dots}$$

- $n=1$ — first compression — **first peak**, the most prominent
- $n=2$ — first rarefaction — second peak
- $n=3$ — second compression — third peak

Modes with $k r_s = (n+\tfrac{1}{2})\pi$ were caught at zero displacement and show troughs.

**This is the origin of every peak in the plot on the website.** It is a standing-wave resonance
condition, no different in principle from an organ pipe.

> **Exercise 7.1** Using $\rho_b \propto a^{-3}$ and $\rho_\gamma \propto a^{-4}$, show
> $R \propto a$. What does that imply about how $c_s$ changed with time?

> **Exercise 7.2** Show that $c_s$ falls from $0.577c$ to about $0.45c$ at recombination, given
> $R(z_*) \approx 0.61$.

---

## 8 The sound horizon: a ruler built from first principles

### Definition

The **sound horizon** is the comoving distance a sound wave could travel from the Big Bang to
recombination:

$$\boxed{\ r_s = \int_0^{\eta_*} c_s\,d\eta = \int_{z_*}^{\infty}\frac{c_s(z)}{H(z)}\,dz \approx 144\ \text{Mpc}}$$

That integral is doing something remarkable. Every ingredient in it is known from *other*
physics:

- $c_s(z) = c/\sqrt{3(1+R)}$ — from $\Omega_bh^2$
- $H(z)$ — from the Friedmann equation with $\Omega_mh^2$ and $\Omega_rh^2$
- $z_*$ — from atomic physics (the Saha equation)

**So $r_s$ is not fitted to the CMB. It is predicted.** That is what makes it a *standard ruler*:
a length whose physical size we know from first principles, placed at a known redshift.

Standard rulers are precious. Given a ruler of known length $L$ subtending a measured angle
$\theta$, the distance follows immediately:

$$D = \frac{L}{\theta}$$

The rest of Part II is about measuring $\theta$ and what $D$ then tells us.

### Why 144 Mpc?

Rough estimate: the sound speed is $\sim 0.55c$ and the age at recombination is 380,000 yr, so
the sound travelled $\sim 0.55 \times 380{,}000 = 2.1\times10^5$ light-years $\approx 64$ kpc in
*physical* units at that time. Converting to comoving units multiplies by $(1+z_*) \approx 1091$:

$$64\ \text{kpc} \times 1091 \approx 70\ \text{Mpc}$$

The same order as the true 144 Mpc; the factor of two comes from the proper relativistic integral
through the radiation era. Good enough to show where the number comes from.

> **Exercise 8.1** Explain why $r_s$ *decreases* when $\Omega_bh^2$ increases. Then explain why
> $r_s$ decreases when $\Omega_mh^2$ increases. *(Different reasons — one through $c_s$, one
> through $H$ and the timing of matter–radiation equality.)*

---

## 9 Why the first peak sits at $\ell = 220$

Now we put the ruler on the sky.

### The angle

The sound horizon $r_s$ sits on the last-scattering surface at comoving distance $D_A$. It
subtends

$$\boxed{\ \theta_* = \frac{r_s}{D_A}\ }$$

The comoving distance to last scattering is

$$D_A = \frac{c}{H_0}\int_0^{z_*}\frac{dz}{E(z)}, \qquad
E(z) = \sqrt{\Omega_m(1+z)^3 + \Omega_\Lambda + \Omega_k(1+z)^2}$$

**Worked numbers.** With $r_s = 144.4$ Mpc and $D_A = 13{,}870$ Mpc:

$$\theta_* = \frac{144.4}{13870} = 0.01041 \ \text{rad} = 0.596°$$

Conventionally quoted as $100\,\theta_* = 1.0411 \pm 0.0003$. **This is the single
best-measured quantity in all of cosmology** — 0.03% precision.

### From angle to multipole

A feature of angular size $\theta$ appears in the power spectrum at multipole

$$\ell \approx \frac{\pi}{\theta}$$

(Chapter 11 justifies this properly; for now, $\ell$ counts how many wavelengths fit around the
sky, so small angle ↔ large $\ell$.) Define the **acoustic scale**:

$$\ell_A \equiv \frac{\pi D_A}{r_s} = \frac{\pi}{\theta_*} = \frac{\pi}{0.01041} \approx 302$$

### The phase shift

Naively the first peak would be at $\ell_A \approx 302$. It is observed at 220. The difference is
a genuine physical effect, not an error:

$$\ell_m \approx \ell_A\left(m - \varphi\right), \qquad \varphi \approx 0.27$$

$$\ell_1 \approx 302 \times (1 - 0.27) = 302 \times 0.73 \approx \boxed{220}$$

The phase shift $\varphi$ arises because the gravitational potentials are *decaying* while the
modes oscillate (the early Integrated Sachs–Wolfe effect) and because the driving force is not
perfectly constant. It shifts all peaks to slightly lower $\ell$.

⚙ **This project measures $\ell = 220$ and $\mathcal{D}_\ell = 5949\ \mu\text{K}^2$ from WMAP
V1×V2 detector maps, and independently $\ell = 218$ from W1×W2.** Gate G3 requires
$220 \pm 8$.

### Why this measures flatness

Here is the payoff. $\theta_* = r_s/D_A$ is a measured angle. $r_s$ is predicted. So $D_A$ is
determined — and $D_A$ depends on the *geometry* of space between us and the last-scattering
surface.

- **Flat** ($\Omega_k=0$): light travels in straight lines, $\theta_* = 0.6°$, first peak at 220.
- **Closed** ($\Omega_k>0$): space acts as a converging lens, objects look *bigger*, peak moves
  to *lower* $\ell$.
- **Open** ($\Omega_k<0$): diverging lens, objects look smaller, peak moves to *higher* $\ell$.

Observing the peak at exactly 220 tells us

$$\Omega_k = 0.001 \pm 0.002$$

**The universe is spatially flat to within 0.2%.** That measurement — one of the most important
results in the history of cosmology — is nothing more than measuring where the first bump sits,
because we independently know the size of the thing making the bump.

> **Exercise 9.1** If the universe were closed with $\Omega_k = +0.05$, would the first peak move
> to higher or lower $\ell$? Explain using the lensing analogy.

> **Exercise 9.2** Using $\ell_m \approx \ell_A(m-0.27)$ with $\ell_A=302$, predict the second
> and third peaks. Compare with this project's measured $\ell \approx 537$ and $\ell \approx 810$.

---

## 10 Reading the other peaks: baryons, dark matter, damping

The first peak gives geometry. The others give contents.

### Odd vs even peaks: weighing the baryons

Baryons add inertia. In a gravitational well, extra inertia means compression goes *deeper* but
rarefaction does not rebound as far — gravity assists compression and opposes rarefaction.

Since **odd peaks are compressions** and **even peaks are rarefactions**:

$$\boxed{\ \text{More baryons} \implies \text{odd peaks enhanced relative to even peaks}}$$

So the ratio $\mathcal{D}_2/\mathcal{D}_1$ is a **baryometer**. It gives

$$\Omega_bh^2 = 0.02237 \pm 0.00015$$

Independently, Big Bang nucleosynthesis — a completely different physical process at $t\sim3$
minutes, measured through primordial deuterium in distant gas clouds — gives the *same* answer.
Two utterly independent probes of the baryon density agreeing to a few percent is one of the
strongest pillars of the hot Big Bang model.

### The third peak: dark matter

The third peak's height relative to the first is sensitive to $\Omega_ch^2$, because dark matter
determines when matter–radiation equality occurred, which sets how much the potentials decayed
while the modes were oscillating. A universe with only baryons would show a very different third
peak. We measure

$$\Omega_ch^2 = 0.1200 \pm 0.0012$$

which is about **five times** the baryon density. **The CMB power spectrum alone demonstrates that
most matter is not made of atoms.**

### Silk damping

Photons do not scatter instantaneously — they random-walk with a finite mean free path. Over time
they diffuse a comoving distance $\lambda_D$, dragging baryons with them and **washing out any
perturbation smaller than that**. This is **Silk damping**, and it suppresses the spectrum
exponentially at high $\ell$:

$$C_\ell \to C_\ell\, e^{-(\ell/\ell_D)^2}, \qquad \ell_D \sim 1400$$

Two further effects add to it: the finite thickness of the last-scattering shell (§5), and the
pixel/beam smoothing of the instrument (Chapter 19) — though only the first two are physical.

⚙ This is why this project caps analysis around $\ell_{max} \approx 800$ with WMAP: beyond that
the true signal is falling exponentially while noise is not, so the measurement stops being
informative.

### The Sachs–Wolfe plateau

At $\ell \lesssim 30$, the angular scales are larger than the sound horizon — those modes never
had time to oscillate. They preserve the primordial spectrum directly:

$$\frac{\Delta T}{T} = \frac{1}{3}\Psi$$

This is the **Sachs–Wolfe effect**: photons climbing out of a potential well lose energy, so
overdense regions appear *cold*. The resulting flat plateau is a direct image of the initial
conditions from inflation, essentially unprocessed.

### Summary: the anatomy of the spectrum

| Feature | Location | What it measures |
|---|---|---|
| Sachs–Wolfe plateau | $\ell \lesssim 30$ | Primordial spectrum, $n_s$, $A_s$ |
| First peak | $\ell = 220$ | **Spatial curvature** (flatness) |
| Ratio 2nd/1st | $\ell \approx 537$ | **Baryon density** $\Omega_bh^2$ |
| Third peak | $\ell \approx 810$ | **Dark matter density** $\Omega_ch^2$ |
| Damping tail | $\ell \gtrsim 1000$ | Recombination physics, $n_s$ |
| Overall amplitude | all | $A_se^{-2\tau}$ |

Every one of those is visible in the plot on the front page of the site. You now know what each
wiggle means.

> **Exercise 10.1** Sketch what the spectrum would look like with $\Omega_bh^2$ doubled. Which
> peaks move, which change height, and does $r_s$ grow or shrink?

---
---

# PART III — THE STATISTICS OF A SKY

Part II told us what pattern to expect. Part III builds the language to describe a pattern
painted on a sphere, and — crucially — explains what we can and cannot learn from having only
**one** sky to look at.

---

## 11 Spherical harmonics, built from Fourier series

### The problem

Our data is a temperature at every direction $\hat{n}$ on the sky:

$$\frac{\Delta T(\hat{n})}{T_0}$$

We want to decompose it into scales, exactly as Fourier series did on a line. But a sphere is not
a line, and plane waves $e^{i\vec k\cdot\vec x}$ do not fit on it.

### What makes a good basis

Recall *why* Fourier worked (§0.3): $e^{ikx}$ are **eigenfunctions of the second derivative**,

$$\frac{d^2}{dx^2}e^{ikx} = -k^2e^{ikx}$$

and eigenfunctions of a symmetric operator are orthogonal. So on a sphere we need eigenfunctions
of the **Laplacian on the sphere**:

$$\nabla^2_{S^2}\,Y_{\ell m} = -\ell(\ell+1)\,Y_{\ell m}$$

These are the **spherical harmonics**. Compare the two eigenvalues:

$$k^2 \quad \longleftrightarrow \quad \ell(\ell+1)$$

⚠ **This correspondence is the single most useful thing to remember in Part III.** Every
appearance of the odd-looking combination $\ell(\ell+1)$ — in the $\mathcal{D}_\ell$ convention, in
beam functions, in damping — is just "$k^2$ on a sphere". It is not a convention someone invented;
it is an eigenvalue.

### Their form

$$Y_{\ell m}(\theta,\phi) = N_{\ell m}\,P_\ell^m(\cos\theta)\,e^{im\phi}$$

- $\ell = 0,1,2,\dots$ — **multipole moment**; how many oscillations across the sky
- $m = -\ell,\dots,+\ell$ — orientation; $2\ell+1$ values for each $\ell$
- $P_\ell^m$ — associated Legendre polynomials
- $N_{\ell m}$ — normalisation

Note the $e^{im\phi}$: around the equator, it is *literally a Fourier series*. Spherical harmonics
are Fourier in longitude and Legendre in latitude.

The first few:

| $\ell$ | Name | Pattern |
|---|---|---|
| 0 | monopole | uniform — the mean temperature, 2.7255 K |
| 1 | dipole | one hot side, one cold side — dominated by our motion |
| 2 | quadrupole | four alternating lobes |
| $\ell$ | — | structure on angular scale $\theta \approx 180°/\ell$ |

### The expansion

$$\boxed{\ \frac{\Delta T(\hat{n})}{T_0} = \sum_{\ell=0}^{\infty}\sum_{m=-\ell}^{\ell}a_{\ell m}Y_{\ell m}(\hat{n})\ }$$

and, using orthogonality exactly as in §0.3,

$$\boxed{\ a_{\ell m} = \int d\Omega\ \frac{\Delta T(\hat{n})}{T_0}\ Y^*_{\ell m}(\hat{n})\ }$$

⚙ These are the two equations in the site's "Fourier analysis on a sphere" lesson. The
orthogonality relation making it work is

$$\int d\Omega\ Y_{\ell m}Y^*_{\ell'm'} = \delta_{\ell\ell'}\delta_{mm'}$$

⚠ **Remember that this integral runs over the *whole* sphere.** In Chapter 18 we will cut out the
Galaxy, the integral will no longer cover the full sphere, orthogonality will fail, and we will
have to repair the damage. Almost every subtlety in CMB analysis traces back to that one broken
assumption.

### Angular scale

A rough but reliable rule:

$$\theta \approx \frac{180°}{\ell}$$

| $\ell$ | Angular scale | Physical meaning |
|---|---|---|
| 2 | 90° | quadrupole; largest scales |
| 30 | 6° | end of Sachs–Wolfe plateau |
| **220** | **0.8°** | **first acoustic peak** |
| 800 | 0.2° | third peak |
| 1400 | 0.13° | damping scale |

> **Exercise 11.1** How many independent $a_{\ell m}$ coefficients exist for $\ell \le 1000$?
> *(Sum $2\ell+1$.)* This is roughly how many numbers a CMB map contains.

---

## 12 The angular power spectrum $C_\ell$

### Statistical isotropy

Inflation does not predict *where* hot spots are. It predicts their statistics. The crucial
assumption — well tested, and itself questioned in Part VI — is **statistical isotropy**: the
universe has no preferred direction.

Its consequence is powerful. Since $m$ labels orientation, and no orientation is special:

$$\boxed{\ \langle a_{\ell m}a^*_{\ell'm'}\rangle = C_\ell\,\delta_{\ell\ell'}\delta_{mm'}\ }$$

Read carefully:

- Different $\ell$ are uncorrelated.
- Different $m$ are uncorrelated.
- The variance depends **only on $\ell$**, not on $m$.

So the entire statistical content of the CMB collapses from millions of $a_{\ell m}$ into **one
number per multipole**: $C_\ell$, the **angular power spectrum**. That is what theory predicts and
what we measure.

⚠ $\langle\cdot\rangle$ means an average over *hypothetical realisations of the universe*. We have
one universe. Chapter 14 is about the price of that.

### Estimating it

With one sky, the natural estimator averages over the $2\ell+1$ available $m$ values:

$$\boxed{\ \hat{C}_\ell = \frac{1}{2\ell+1}\sum_{m=-\ell}^{\ell}|a_{\ell m}|^2\ }$$

The hat denotes "estimated from data". This is an unbiased estimator: $\langle\hat{C}_\ell\rangle = C_\ell$.

### The correlation function

Equivalently, in real space, the two-point correlation between points separated by angle $\theta$:

$$C(\theta) = \left\langle \frac{\Delta T}{T}(\hat n_1)\frac{\Delta T}{T}(\hat n_2)\right\rangle_{\hat n_1\cdot\hat n_2 = \cos\theta}
= \frac{1}{4\pi}\sum_\ell (2\ell+1)C_\ell P_\ell(\cos\theta)$$

The power spectrum and the correlation function are a Legendre transform pair — the same
information in two forms. We use $C_\ell$ because the modes are independent, which makes the
likelihood in Chapter 25 simple.

> **Exercise 12.1** Show that the total temperature variance is
> $\langle(\Delta T/T)^2\rangle = \frac{1}{4\pi}\sum_\ell(2\ell+1)C_\ell$, i.e. $C(0)$.

---

## 13 Why every plot shows $\mathcal{D}_\ell$

Look at the site's spectrum plot. The $y$-axis is not $C_\ell$ but

$$\boxed{\ \mathcal{D}_\ell \equiv \frac{\ell(\ell+1)C_\ell}{2\pi}\ }$$

with units of $\mu\text{K}^2$. Why the strange combination?

### The reason

From Exercise 12.1, total variance is $\sum_\ell (2\ell+1)C_\ell/4\pi$. For large $\ell$,
$2\ell+1 \approx 2\ell$ and $\ell(\ell+1)\approx\ell^2$, so

$$\sum_\ell \frac{(2\ell+1)C_\ell}{4\pi} \approx \int \frac{\ell^2C_\ell}{2\pi}\,\frac{d\ell}{\ell}
= \int \mathcal{D}_\ell\, d\ln\ell$$

$$\boxed{\ \langle(\Delta T/T)^2\rangle \approx \int\mathcal{D}_\ell\ d\ln\ell\ }$$

**$\mathcal{D}_\ell$ is the power per logarithmic interval in $\ell$.** On a log-$x$ plot, **equal
areas under the curve represent equal contributions to the temperature variance you actually see
on the sky.** The plot is honest about where the signal lives.

Practically, $C_\ell$ falls steeply (roughly as $\ell^{-2}$), so plotting it would squash all the
acoustic peaks into an invisible corner. Multiplying by $\ell(\ell+1)$ flattens the Sachs–Wolfe
plateau to a horizontal line and makes the peaks plainly visible. And per §11, $\ell(\ell+1)$ is
just $k^2$ on a sphere — it is the physically natural weighting, not cosmetic.

⚙ The site's Learn tab derives exactly this; the first peak has $\mathcal{D}_{220} = 5949\ \mu\text{K}^2$,
so $\Delta T \sim \sqrt{5949} \approx 77\ \mu$K of temperature contrast at that scale.

---

## 14 Cosmic variance: the error bar you can never beat

This chapter explains the single most important limitation in cosmology, and it follows in three
lines from Exercise 0.4.

### The argument

For a Gaussian field, each $a_{\ell m}$ is an independent Gaussian with variance $C_\ell$. So
$a_{\ell m}/\sqrt{C_\ell}$ is a standard Gaussian, and

$$\frac{(2\ell+1)\hat{C}_\ell}{C_\ell} = \sum_{m}\frac{|a_{\ell m}|^2}{C_\ell} \sim \chi^2_{2\ell+1}$$

Using $\mathrm{Var}(\chi^2_n) = 2n$:

$$\mathrm{Var}\!\left(\frac{(2\ell+1)\hat C_\ell}{C_\ell}\right) = 2(2\ell+1)
\implies \mathrm{Var}(\hat{C}_\ell) = \frac{2C_\ell^2}{2\ell+1}$$

$$\boxed{\ \frac{\Delta C_\ell}{C_\ell} = \sqrt{\frac{2}{2\ell+1}}\ }$$

### What it means

There are only $2\ell+1$ independent $m$-modes at each $\ell$. At $\ell=2$ there are **five
numbers in the entire observable universe**. You cannot average away a small sample.

| $\ell$ | modes | irreducible error |
|---|---|---|
| 2 | 5 | 63% |
| 10 | 21 | 31% |
| 220 | 441 | 6.7% |
| 1000 | 2001 | 3.2% |

This is not instrumental. **A perfect, noiseless, infinite-resolution telescope would still have
these error bars.** We have one universe and can only see one Hubble volume of it.

Two consequences that echo through the rest of the book:

1. **Low $\ell$ can never be measured precisely.** Which is why the "anomalies" of Part VI —
   nearly all at low $\ell$ — are so hard to adjudicate.
2. WMAP is **already cosmic-variance-limited** at $\ell \lesssim 500$. Building a better
   satellite would not improve those measurements at all.

### Partial sky

Cut out the Galaxy and you have fewer independent modes, degrading the error by roughly
$1/\sqrt{f_{sky}}$ where $f_{sky}$ is the surviving sky fraction:

$$\boxed{\ \frac{\Delta C_\ell}{C_\ell} = \sqrt{\frac{2}{(2\ell+1)f_{sky}}}\ }$$

⚙ This project uses the WMAP KQ75 mask, $f_{sky} = 0.688$, costing about 21% in error bars.

### With noise: the Knox formula

Adding instrumental noise power $N_\ell$:

$$\boxed{\ \frac{\Delta C_\ell}{C_\ell} = \sqrt{\frac{2}{(2\ell+1)f_{sky}}}\left(1 + \frac{N_\ell}{C_\ell}\right)}$$

⚙ This is the "error bar you can never beat" equation in the site's estimator lesson. Note its
structure: when $N_\ell \ll C_\ell$ you are cosmic-variance limited and more integration time buys
nothing; when $N_\ell \gg C_\ell$ you are noise limited. The transition sets the useful $\ell$
range of any experiment.

> **Exercise 14.1** At what $\ell$ does cosmic variance alone fall below 5%? Below 1%?

> **Exercise 14.2** The observed quadrupole is about 70% of the ΛCDM prediction. Given a 63%
> error bar, how many sigma is that? *(This is the entire "low quadrupole anomaly".)*

---
---

# PART IV — THE MEASUREMENT

Parts I–III were physics. Part IV is **engineering**, and it is where nearly all the real work
lies. A naive analysis of CMB data does not give a slightly wrong answer — it gives an answer
wrong by a factor of 26, with no peaks at all. This project made exactly that mistake first.

The chain we must invert:

$$\text{true sky} \xrightarrow{\text{beam}} \text{smoothed}
\xrightarrow{\text{pixelise}} \text{map}
\xrightarrow{+\ \text{foregrounds}} \xrightarrow{+\ \text{noise}} \text{data}$$

---

## 15 What a CMB map actually is

### HEALPix

A CMB map is a list of temperatures, one per pixel. The standard pixelisation is **HEALPix**
(Hierarchical Equal Area isoLatitude Pixelisation):

$$N_{pix} = 12\,N_{side}^2$$

| $N_{side}$ | pixels | resolution |
|---|---|---|
| 64 | 49,152 | 55′ |
| 512 | 3,145,728 | 6.9′ |
| 2048 | 50,331,648 | 1.7′ |

Two properties matter:

1. **Equal area** — every pixel subtends the same solid angle, so no weighting is needed when
   averaging, and noise is uniform per pixel.
2. **Iso-latitude** — pixels lie on rings of constant latitude, which allows the spherical
   harmonic transform to use an FFT in longitude. Without this, computing $a_{\ell m}$ for 50
   million pixels would be computationally hopeless.

⚙ WMAP maps here are $N_{side}=512$; Planck are 2048; anomaly Monte Carlos degrade to 64 to make
500 simulations affordable.

### What's in the file

FITS files containing a temperature array plus metadata. Units vary and **this is a classic
source of silent factor errors**:

- WMAP ILC: mK
- WMAP raw DAs: K
- Planck: K

⚙ The cleaning stage converts everything to µK immediately. A factor of $10^3$ error here would
show up as a factor of $10^6$ in the power spectrum.

> **Exercise 15.1** A map has $N_{side}=512$. What solid angle does one pixel subtend, in
> steradians and in square arcminutes? *(Total sphere = $4\pi$ sr.)*

---

## 16 Cleaning: monopole and dipole

### The monopole ($\ell=0$)

The mean temperature, $T_0 = 2.7255$ K. It carries no anisotropy information, and it is $10^5$
times larger than the signal. Subtract it.

### The dipole ($\ell=1$)

The largest anisotropy on the sky, about 3.36 mK — **a hundred times larger than the primordial
signal**. It is not cosmological: it is the Doppler shift from our own motion through the CMB
rest frame at about 370 km/s.

$$\frac{\Delta T}{T} = \frac{v}{c}\cos\theta$$

Measured values:

$$A_{dip} = 3362.08 \pm 0.99\ \mu\text{K}, \qquad (l,b) = (264.021°,\ 48.253°)$$

This is a genuinely useful *calibration* signal: we know its amplitude and direction
independently, so recovering it verifies the pipeline end to end.

⚙ **Gate G2** does exactly this:
- On raw or synthetic maps: recover 3362 µK within 2%.
- On pre-cleaned maps (ILC, Planck component-separated, where the dipole is already removed):
  demand a *residual* below 50 µK. The project measures **7.9 µK** residual on WMAP ILC — and
  10.0 µK on the deployed server.

⚠ Fit the dipole with a Galactic cut ($|b| > 30°$). Otherwise the bright Galactic plane drags the
fit and you subtract the wrong dipole, leaving a residual that contaminates low $\ell$ — precisely
where the Part VI anomalies live.

> **Exercise 16.1** From $A_{dip} = 3362\ \mu$K and $T_0 = 2.7255$ K, compute our velocity
> relative to the CMB rest frame.

---

## 17 Foregrounds and masks

### The Galaxy is in the way

We sit inside a galaxy that emits microwaves:

| Foreground | Dominant | Origin |
|---|---|---|
| Synchrotron | low freq | relativistic electrons spiralling in magnetic fields |
| Free–free | low freq | electron–ion scattering in ionised gas |
| Thermal dust | high freq | warm dust grains re-radiating starlight |
| Point sources | all | radio galaxies, dusty star-forming galaxies |

Near the Galactic plane these **exceed the CMB by orders of magnitude**.

### Two strategies

**1. Component separation.** Foregrounds have different frequency dependence from the CMB (which
is a blackbody, identical in thermodynamic temperature at all frequencies). Observe at many
frequencies and solve for the CMB component. WMAP's ILC and Planck's SMICA/NILC/SEVEM/COMMANDER
do this.

⚙ WMAP observes at 22.8, 33.0, 40.7, 60.8, 93.5 GHz; Planck at 30–857 GHz. The multiple Planck
methods exist precisely so you can check the answer is not an artefact of one algorithm.

**2. Masking.** Simply refuse to use the worst regions. The WMAP **KQ75** mask removes the
Galactic plane and known point sources, leaving

$$f_{sky} = 0.688$$

Masking is more conservative — it throws away information rather than modelling something
imperfectly understood — and it is what this project uses for spectrum estimation. But it comes
at a price, which is the entire subject of the next chapter.

---

## 18 The mask breaks orthogonality: pseudo-$C_\ell$

### The problem

In §11 we warned that $a_{\ell m} = \int d\Omega\,\frac{\Delta T}{T}Y^*_{\ell m}$ requires the
**full** sphere. With a mask $W(\hat n)$ (1 = keep, 0 = cut) we can only compute

$$\tilde{a}_{\ell m} = \int d\Omega\ W(\hat n)\frac{\Delta T(\hat n)}{T_0}\,Y^*_{\ell m}(\hat n)$$

Multiplication in real space is **convolution in harmonic space**. The mask therefore mixes
multipoles: the clean statement $\langle a_{\ell m}a^*_{\ell'm'}\rangle = C_\ell\delta_{\ell\ell'}\delta_{mm'}$
is destroyed. The measured **pseudo-spectrum** $\tilde{C}_\ell$ is a smeared version of the truth:

$$\boxed{\ \langle\tilde{C}_\ell\rangle = \sum_{\ell'}M_{\ell\ell'}\,C_{\ell'}B^2_{\ell'}p^2_{\ell'}\ }$$

with the **mode-coupling matrix** (the MASTER formalism, Hivon et al. 2002)

$$M_{\ell\ell'} = \frac{2\ell'+1}{4\pi}\sum_{\ell''}(2\ell''+1)\,\mathcal{W}_{\ell''}
\begin{pmatrix}\ell&\ell'&\ell''\\0&0&0\end{pmatrix}^2$$

The bracketed object is a **Wigner 3-j symbol**, which encodes how three angular momenta couple —
the same mathematics as in quantum mechanics. $\mathcal{W}_\ell$ is the power spectrum of the
mask itself.

### The approximation we use

Inverting $M_{\ell\ell'}$ exactly is expensive. But if the mask is large and smooth and we bin
over $\Delta\ell$ wider than the coupling width, the matrix is nearly diagonal and reduces to a
simple normalisation:

$$\boxed{\ C_\ell \approx \frac{\tilde{C}_\ell}{w_2}, \qquad
w_2 = \frac{1}{4\pi}\int W^2(\hat n)\,d\Omega = \langle W^2\rangle}$$

For KQ75, $w_2 = 0.688$.

**Intuition**: masking removes a fraction of the sky, so it removes a proportional fraction of the
power. Divide it back.

⚙ This project uses this leading-order MASTER approximation. It is legitimate here because:
- KQ75 is large ($f_{sky}=0.69$) and smooth,
- we bin with $\Delta\ell = 30$, far wider than the coupling scale,
- we work at $\ell \gtrsim 30$, not at the lowest multipoles where it fails.

⚠ Honest limitation: at very low $\ell$, and for small or ragged masks, this is **not** adequate
and you need the full matrix inversion (e.g. `NaMaster`). The approximation also leaves
off-diagonal correlations between bins, which we ignore in the covariance — making our error bars
slightly optimistic. Chapter 25 revisits this.

---

## 19 Beams and pixel windows

### The beam

No telescope has infinite resolution. The instrument smooths the sky with a **beam**, and
smoothing in real space is multiplication in harmonic space:

$$\tilde{a}_{\ell m} = B_\ell\,a_{\ell m}$$

For a Gaussian beam of width $\sigma$:

$$B_\ell = \exp\left[-\frac{\ell(\ell+1)\sigma^2}{2}\right]$$

There is $\ell(\ell+1)$ again — $k^2$ on a sphere (§11).

⚠ Real beams are **not** Gaussian. They have sidelobes. WMAP measured its beams directly by
observing Jupiter, and this project uses those tabulated $b_\ell$ files
(`wmap_ampl_bl_{DA}_9yr_v5p1.txt`), not a Gaussian approximation. Using a Gaussian would
mis-deconvolve at high $\ell$ and tilt the damping tail — which would then be absorbed into a
wrong $n_s$.

### The pixel window

Averaging the sky within finite pixels smooths it further, described by $p_\ell$. HEALPix
provides these.

### Deconvolution and its danger

To recover the truth, divide:

$$C_\ell = \frac{\tilde{C}_\ell}{B_\ell^2 p_\ell^2}$$

⚠ **$B_\ell$ falls exponentially.** Dividing by a number heading to zero amplifies everything —
*including noise* — without limit. At high $\ell$ this makes the reconstruction explode.

⚙ This project refuses to report multipoles where $B_\ell p_\ell < 0.02$, flagging them as
`reliable_lmax`. That is the right instinct: **do not report numbers your method cannot support.**

The deeper fix for the noise explosion is the subject of the next chapter, which is the most
important in Part IV.

---

## 20 Noise, and the central trick: cross-spectra

### The failure

Detectors have noise. Model a map as signal plus noise:

$$a^A_{\ell m} = s_{\ell m}B^A_\ell + n^A_{\ell m}$$

Take the naive **auto-spectrum** of one map:

$$\langle|a^A_{\ell m}|^2\rangle = C_\ell (B^A_\ell)^2 + N^A_\ell$$

The noise term $N^A_\ell$ **does not average away**. It is a positive bias, present no matter how
long you observe. Worse, deconvolving the beam divides the *whole thing* by $(B_\ell^A)^2$:

$$\hat{C}_\ell = C_\ell + \frac{N^A_\ell}{(B^A_\ell)^2}$$

and since $B_\ell \to 0$ exponentially, the noise term **blows up exponentially**.

⚙ This project hit exactly this. The first attempt used an auto-spectrum and the result was
**26× too high at $\ell = 350$, with no acoustic peaks visible at all** — total failure, not a
subtle bias. That is worth dwelling on: the physics of Parts I–III was completely correct, and
the answer was still garbage.

### The trick

Take **two detectors that observe the same sky with independent noise**, and correlate them:

$$\langle a^A_{\ell m}a^{B*}_{\ell m}\rangle
= \underbrace{C_\ell B^A_\ell B^B_\ell}_{\text{signal}}
+ \underbrace{\langle n^A_{\ell m}n^{B*}_{\ell m}\rangle}_{= \ 0}$$

**The noise term vanishes identically.** Not "is reduced" — vanishes, because the two noise
realisations are uncorrelated and their expected product is zero.

$$\boxed{\ \langle a^A_{\ell m}a^{B*}_{\ell m}\rangle = C_\ell B^A_\ell B^B_\ell\ }$$

This is the single most important practical idea in CMB analysis. The same sky, seen twice
independently; the signal correlates, the noise does not.

⚙ This project crosses WMAP **V1 × V2** — two independent differencing assemblies in the same
V band (60.8 GHz), which see the same sky with entirely separate detector chains. It
cross-checks with **W1 × W2** at 93.5 GHz, obtaining $\ell = 218$ versus $\ell = 220$ — an
independent confirmation at a different frequency, which also argues against a foreground
origin.

### The full estimator

Putting Chapters 18–20 together, the quantity this project actually computes is:

$$\boxed{\ \hat{C}^{AB}_\ell = \frac{\tilde{C}^{AB}_\ell}{w_2\,B^A_\ell\,B^B_\ell\,p^2_\ell}\ }$$

⚠ Note **one power of each beam**, not the square. A common and silent error is writing $B_\ell^2$
out of habit from the auto-spectrum case.

### Measuring the noise anyway

We still want $N_\ell$ for the error bars. Subtract cross from auto:

$$\boxed{\ N^A_\ell = \hat{C}^{AA}_\ell - \hat{C}^{AB}_\ell\ }$$

The auto has signal+noise, the cross has signal only, so the difference is noise — **measured from
the data itself**, with no noise model required. Elegant and assumption-free.

> **Exercise 20.1** Show that if the two detectors had *correlated* noise (say from a shared
> thermal environment), the cross-spectrum would be biased. Suggest a test on real data that
> would reveal this.

---

## 21 Unresolved point sources

### The contaminant

Below the detection threshold lies a sea of faint radio galaxies. Being effectively a random
Poisson sprinkling of point-like objects, they contribute a **flat** power spectrum:

$$C^{ps}_\ell = A_{ps} = \text{constant}$$

Flat in $C_\ell$ means, in the plotted convention,

$$\mathcal{D}^{ps}_\ell = \frac{\ell(\ell+1)}{2\pi}A_{ps} \propto \ell^2$$

**a rising parabola** that eventually swamps the exponentially-falling CMB damping tail.

### Fitting it

⚙ This project fits a single constant $A_{ps}$ over $\ell \in [400,800]$, obtaining

$$A_{ps} = 1.45\times10^{-2}\ \mu\text{K}^2\,\text{sr}$$

Its impact is dramatic: **$\chi^2/\text{dof}$ falls from 32 to about 1.**

⚠ **Be honest about the circularity.** The amplitude is fitted by assuming the ΛCDM theory curve is
correct at high $\ell$, then attributing the excess to sources. So the high-$\ell$ agreement is
partly *constructed*, not independently verified. This is standard practice — WMAP and Planck both
marginalise over a point-source amplitude — but it means the $\chi^2$ at high $\ell$ is not a fully
independent test. The first peak at $\ell=220$, well below the fitting range, **is** independent,
which is why Gate G3 is the more meaningful check.

Being clear about which of your results are independent tests and which are partly assumed is not
pedantry; it is the difference between a measurement and a self-fulfilling prophecy.

---

## 22 Binning and error bars

### Why bin

Individual $\hat{C}_\ell$ are extremely noisy ($\chi^2$ with few degrees of freedom, §14).
Averaging neighbouring multipoles into **bandpowers** trades resolution for precision.

Weight by the number of modes, $w_\ell = 2\ell+1$:

$$\bar{\mathcal{D}}_b = \frac{\sum_{\ell\in b}w_\ell\,\mathcal{D}_\ell}{\sum_{\ell\in b}w_\ell},
\qquad
\ell^{\rm eff}_b = \frac{\sum_{\ell\in b}w_\ell\,\ell}{\sum_{\ell\in b}w_\ell}$$

⚙ Schemes available: linear $\Delta\ell = 30$ (default), and a Planck-like variable scheme
($\Delta\ell=1$ below 30, 5 to $\ell=100$, 15 to 500, 30 to 1200, 60 above) — fine where cosmic
variance is large, coarse where it is small.

### The covariance

Combining cosmic variance (§14) with the cross-spectrum structure (§20):

$$\boxed{\ \mathrm{Var}(\hat{C}^{AB}_\ell) = \frac{1}{(2\ell+1)f_{sky}}
\left[(C^{AB}_\ell)^2 + (C_\ell+N^A_\ell)(C_\ell+N^B_\ell)\right]}$$

⚙ This is the site's estimator-lesson variance formula. The first term is cosmic variance; the
second is the noise contribution, using the **measured** $N_\ell$ from §20.

⚠ This is a **diagonal** covariance: we ignore correlations between bins induced by the mask
(§18). Real bins are correlated, so our error bars are mildly optimistic, and the $\chi^2$ values
in Gate G4 should be read as indicative rather than rigorous. A full treatment would propagate
the mode-coupling matrix into a band-power covariance matrix. This is a deliberate, documented
simplification — not an oversight.

> **Exercise 22.1** With $\Delta\ell=30$ at $\ell\approx220$ and $f_{sky}=0.688$, estimate the
> fractional cosmic-variance error on that bandpower. Compare to the single-$\ell$ value of 6.7%
> from §14.

---
---

# PART V — FROM A CURVE TO A COSMOLOGY

We now have a measured curve with error bars. Part V turns it into numbers: the age, shape and
composition of the universe.

---

## 23 Boltzmann codes: what CAMB actually computes

### The problem

Part II gave a cartoon: a harmonic oscillator with a sound speed. Reality is a coupled system of
differential equations for every species, all gravitating:

- photons — must be tracked as a *distribution* in direction, not just a density, because
  anisotropic stress matters
- baryons — coupled to photons by Thomson scattering
- cold dark matter — gravity only
- neutrinos — free-streaming, decoupled at $t\sim1$ s
- metric perturbations — general relativity

The governing equation for each species is the **Boltzmann equation**, describing how a phase-space
distribution $f(\vec{x},\vec{p},t)$ evolves under free-streaming, gravity and collisions:

$$\frac{df}{dt} = C[f]$$

The photon distribution is expanded in multipoles $\Theta_\ell$, producing an infinite hierarchy
of coupled ODEs, truncated at high $\ell$.

### What comes out

For a given set of cosmological parameters, a Boltzmann code (**CAMB** here; `CLASS` is the other
standard) integrates this system and outputs the theoretical $C_\ell$.

⚙ CAMB takes about **60 ms** per evaluation at $\ell_{max}=700$ on one core in this project.
That number sets the entire computational budget of Chapter 26: 24 walkers × 1500 steps = 36,000
evaluations ≈ 36 minutes of pure CPU, parallelised across cores.

**You should treat CAMB as a trusted black box.** Writing your own Boltzmann code is a serious
undertaking and not the point of this project. What *is* the point is that everything *around* it
— the measurement, the errors, the inference — is ours.

---

## 24 The six parameters

ΛCDM fits the entire CMB with **six numbers**. That is the astonishing fact at the centre of
modern cosmology: a few million data points, described by six parameters, with $\chi^2/\text{dof} \approx 1$.

| # | Parameter | Symbol | Value (Planck 2018) | What it controls |
|---|---|---|---|---|
| 1 | Baryon density | $\Omega_bh^2$ | $0.02237 \pm 0.00015$ | odd/even peak ratio |
| 2 | Cold dark matter density | $\Omega_ch^2$ | $0.1200 \pm 0.0012$ | third peak, equality epoch |
| 3 | Acoustic scale | $100\,\theta_*$ | $1.04092 \pm 0.00031$ | peak positions |
| 4 | Optical depth | $\tau$ | $0.0544 \pm 0.0073$ | large-scale suppression |
| 5 | Spectral index | $n_s$ | $0.9649 \pm 0.0042$ | tilt of primordial spectrum |
| 6 | Primordial amplitude | $\ln(10^{10}A_s)$ | $3.044 \pm 0.014$ | overall normalisation |

⚙ These are exactly the six sampled in `services/cosmology`, with uniform priors on all but
$\tau$.

### Why these six

**Why $\Omega_bh^2$ and not $\Omega_b$?** Because the physics at recombination depends on the
*physical* density (particles per cubic metre), not the density relative to today's critical
density. $\rho_b = \Omega_b\rho_c \propto \Omega_bh^2$. The CMB measures what was actually there.

**Why $\theta_*$ and not $H_0$?** Because $\theta_*$ is what we *directly observe* — the peak
position. $H_0$ is inferred from it, given the other parameters. Sampling in the
directly-measured quantity gives a much better-conditioned posterior. This is a general and
valuable principle: **parametrise in what you measure.**

### Optical depth

After recombination the universe was neutral. The first stars re-ionised it around $z \approx 8$,
providing free electrons that scattered a fraction of CMB photons again. The fraction scattered is
$1 - e^{-\tau}$, which *suppresses* anisotropy on scales inside the horizon at reionisation:

$$C_\ell \to C_\ell e^{-2\tau} \quad (\text{high } \ell)$$

⚠ This creates a serious problem for temperature-only analysis: $C_\ell \propto A_se^{-2\tau}$,
so raising $A_s$ and raising $\tau$ have **nearly identical effects**. From TT data alone they are
degenerate and neither can be determined.

⚙ This project therefore applies a **Gaussian prior** $\tau = 0.0544 \pm 0.0073$, taken from
Planck's large-scale *polarisation* measurement, which breaks the degeneracy by a completely
different observable. This is an honest external input and must be declared: our $A_s$ is not
independently measured, it is conditional on Planck's $\tau$.

### Derived parameters

These are not sampled; they are computed from the six:

| Quantity | Symbol | Value |
|---|---|---|
| Hubble constant | $H_0$ | $67.36 \pm 0.54$ km/s/Mpc |
| Matter density | $\Omega_m$ | $0.3153 \pm 0.0073$ |
| Dark energy density | $\Omega_\Lambda$ | $0.6847 \pm 0.0073$ |
| Clustering amplitude | $\sigma_8$ | $0.8111 \pm 0.0060$ |
| **Age of the universe** | $t_0$ | $13.797 \pm 0.023$ Gyr |
| Recombination redshift | $z_*$ | $1089.92 \pm 0.25$ |

**The age of the universe is a derived parameter.** Nobody measures it directly. It falls out of
integrating the Friedmann equation (Chapter 2) with the fitted contents:

$$t_0 = \int_0^\infty \frac{dz}{(1+z)H(z)}$$

⚙ When the site reports "13.8 billion years", *this* is the chain: peak positions → six
parameters → Friedmann integral → age. Every link is in this book.

---

## 25 Likelihood and $\chi^2$

### The likelihood

Given parameters $\theta$, CAMB predicts bandpowers $\mathcal{D}_b(\theta)$. We measured
$\mathcal{D}_b$ with errors $\sigma_b$. Assuming Gaussian, independent bandpowers:

$$\mathcal{L}(\mathcal{D}|\theta) \propto \exp\left[-\frac{1}{2}\chi^2(\theta)\right],
\qquad
\boxed{\ \chi^2(\theta) = \sum_b\frac{[\mathcal{D}_b - \mathcal{D}_b(\theta)]^2}{\sigma_b^2}\ }$$

⚙ This project uses 27 bandpowers from $\ell_{min}=30$ upward.

### Bayes' theorem

We want the probability of the *parameters* given the *data*, not the reverse. Bayes:

$$\boxed{\ P(\theta|\mathcal{D}) = \frac{\mathcal{L}(\mathcal{D}|\theta)P(\theta)}{P(\mathcal{D})} \propto \mathcal{L}(\mathcal{D}|\theta)\,P(\theta)}$$

- $P(\theta|\mathcal{D})$ — **posterior**, what we want
- $\mathcal{L}(\mathcal{D}|\theta)$ — **likelihood**, computable
- $P(\theta)$ — **prior**, what we believed beforehand
- $P(\mathcal{D})$ — evidence, a normalisation we can ignore for parameter fitting

⚙ Priors here: uniform over generous ranges for five parameters; Gaussian for $\tau$ (§24).

### Why $\ell_{min}=30$

Below $\ell \approx 30$, cosmic variance is enormous (§14) and the Gaussian-likelihood
approximation is poor — $\hat{C}_\ell$ follows a skewed $\chi^2$ distribution with few degrees of
freedom, not a Gaussian. Using a Gaussian there would bias the fit. Cutting to $\ell \ge 30$ is
the honest choice; proper low-$\ell$ analysis requires an exact pixel-space likelihood.

---

## 26 MCMC from first principles

Six parameters, and we want the full posterior, not just a best fit. Grid evaluation at 20 points
per dimension would need $20^6 = 6.4\times10^7$ CAMB calls at 60 ms each — **44 days**. We need
something better.

### The idea

**Markov Chain Monte Carlo**: construct a random walk through parameter space that visits regions
in proportion to their posterior probability. Then the *histogram of visited points is the
posterior*. Instead of mapping the whole function, sample it.

### Metropolis–Hastings

1. Start at $\theta$.
2. Propose $\theta'$ from some symmetric distribution $q(\theta'|\theta)$.
3. Compute the ratio $r = P(\theta'|\mathcal{D})/P(\theta|\mathcal{D})$.
4. If $r \ge 1$, accept. If $r<1$, accept **with probability $r$**.
5. If accepted move to $\theta'$; otherwise stay at $\theta$ (and record it again).
6. Repeat.

### Why it works

The chain satisfies **detailed balance**:

$$P(\theta)\,T(\theta\to\theta') = P(\theta')\,T(\theta'\to\theta)$$

where $T$ is the transition probability. Verify for $P(\theta') < P(\theta)$: the left side is
$P(\theta)\,q\cdot\frac{P(\theta')}{P(\theta)} = q\,P(\theta')$; the right side is
$P(\theta')\,q\cdot 1 = q\,P(\theta')$. Equal. ∎

Detailed balance guarantees $P$ is the stationary distribution: run long enough and the chain's
occupancy converges to the posterior, regardless of where you started.

Notice the normalisation $P(\mathcal{D})$ cancels in the ratio — which is exactly why we could
ignore it in §25.

### emcee: affine-invariant sampling

⚙ This project uses **emcee**, which runs an *ensemble* of walkers that propose moves by
"stretching" toward each other:

$$\theta'_i = \theta_j + Z(\theta_i - \theta_j)$$

The virtue is **affine invariance**: performance is unchanged by linear rescaling of parameters.
Since cosmological parameters have wildly different scales ($\Omega_bh^2 \sim 0.022$ versus
$\ln(10^{10}A_s) \sim 3$) and strong linear correlations, this matters enormously — a naive
Metropolis sampler would crawl.

⚙ Configuration: **24 walkers**, **1500 steps**, **300 discarded as burn-in**, 12 parallel
workers.

### Diagnostics

- **Burn-in** — the chain starts wherever you put it; early samples are not from the posterior.
  Discard them.
- **Acceptance fraction** — should be ~0.2–0.5. Too high means steps are tiny; too low means
  they are wild.
- **Autocorrelation time $\tau_{ac}$** — successive samples are correlated. The number of
  *independent* samples is $N_{steps}/\tau_{ac}$. A common rule: run for at least $50\tau_{ac}$.

⚠ **A converged-looking chain is not necessarily converged.** A chain can be stuck in a local
mode and look perfectly healthy. Run multiple chains from dispersed starts and compare (the
Gelman–Rubin $\hat{R}$ statistic).

### Reading the results

Report the 16th, 50th and 84th percentiles of the marginalised posterior — the median and the
central 68% interval, which reduces to $\pm1\sigma$ for a Gaussian.

**Corner plots** show every 1-D marginal and every 2-D joint distribution. The 2-D panels are
where you *see* degeneracies as tilted ellipses — which is the subject of the next chapter.

> **Exercise 26.1** Why does the Metropolis rule accept *downhill* moves at all? What would go
> wrong if you only ever accepted uphill moves?

---

## 27 Degeneracies

A degeneracy is a direction in parameter space along which the data barely changes. It shows up
as a long, thin, tilted ellipse in the corner plot.

### $A_s$–$\tau$

$$C_\ell \propto A_s e^{-2\tau}$$

Only the product is constrained by TT data. Broken by polarisation (§24) — here, by an external
prior.

### The geometric degeneracy

$$\theta_* = \frac{r_s(\Omega_bh^2,\Omega_ch^2)}{D_A(H_0,\Omega_m,\Omega_k)}$$

We measure $\theta_*$ superbly. But many combinations of $H_0$, $\Omega_m$, $\Omega_k$ give the
same $D_A$. **The CMB alone cannot separate them.** ΛCDM breaks the degeneracy by *assuming*
$\Omega_k=0$ — after which $H_0$ is tightly determined.

⚠ This is worth saying plainly: the famous CMB value $H_0 = 67.36$ is not a direct measurement of
an expansion rate. It is an *inference* that assumes a flat ΛCDM universe. If you allow curvature
to float, the CMB-only constraint on $H_0$ weakens dramatically. Keep this in mind for the next
chapter.

### Why $h^2$ appears everywhere

Recombination physics depends on physical densities. $D_A$ depends on $H_0$. So the CMB naturally
constrains $\Omega_bh^2$, $\Omega_ch^2$ and $\theta_*$ — and $H_0$, $\Omega_m$ only through
their combinations. This is not notational fussiness; it is what the data actually determines.

---

## 28 The Hubble tension

### The discrepancy

Two ways to measure how fast the universe expands today:

| Method | $H_0$ (km/s/Mpc) | Type |
|---|---|---|
| CMB (Planck 2018) | $67.36 \pm 0.54$ | Early universe + ΛCDM |
| Cepheids + SNe Ia (SH0ES 2022) | $73.04 \pm 1.04$ | Direct, local distance ladder |

The difference is $5.68$ with combined error $\sqrt{0.54^2+1.04^2} = 1.17$, i.e. about
**4.8σ**. By particle-physics convention, 5σ is discovery. This is the largest unresolved
discrepancy in cosmology.

### Why it matters

These are **not** the same kind of measurement:

- The distance ladder measures $H_0$ *directly and locally*, with essentially no cosmological
  model assumed.
- The CMB **infers** $H_0$ from the acoustic scale at $z=1090$, extrapolated to today
  **assuming flat ΛCDM** (§27).

So the tension is not "two thermometers disagree". It is: *the early universe, evolved forward
with our standard model, does not arrive at the universe we see locally.* Either one measurement
has an unknown systematic, or **ΛCDM is incomplete** — early dark energy, extra relativistic
species, or something not yet imagined.

⚙ The site's cosmology service exposes an $H_0$ tension endpoint precisely so you can see both
numbers with their error bars side by side, rather than being told an answer.

This is where cosmology is genuinely unfinished, and it is a good place for a new graduate student
to be paying attention.

---
---

# PART VI — ANOMALIES AND HONEST STATISTICS

ΛCDM fits the CMB beautifully. But a handful of large-scale features look odd. Part VI is as much
about **statistical integrity** as about physics — it is the part of the subject where careful
people most often fool themselves.

---

## 29 The four anomalies

⚙ The anomaly service computes exactly these four.

### 1. The low quadrupole

The observed $C_2$ is roughly 70% of the ΛCDM prediction. But cosmic variance at $\ell=2$ is 63%
(§14). **A 30% shortfall against a 63% error bar is about 0.5σ — which is nothing.**

This is the cleanest lesson in Part VI: an "anomaly" that dissolves the moment you compute the
correct error bar.

### 2. The Axis of Evil

The quadrupole ($\ell=2$) and octupole ($\ell=3$) each define a preferred axis. Define it as the
direction maximising the power in the equatorial modes:

$$\boxed{\ \hat{n}_\ell = \arg\max_{\hat{n}}\sum_m m^2\,|a_{\ell m}(\hat{n})|^2\ }$$

Rotate the coefficients so $\hat n$ is the $z$-axis; the $m^2$ weighting rewards power
concentrated in high-$|m|$ modes, which wrap around the equator.

Under statistical isotropy the two axes should be independent, so $\cos\gamma$ is uniform on
$[-1,1]$ and the typical separation is about 60°. Observed: roughly **10°**.

⚙ Implementation: grid search on an $N_{side}=8$ grid (768 directions, halved to 384 by the
$\hat n \leftrightarrow -\hat n$ symmetry), then local refinement. Because an axis is
"headless", the separation must be folded:

$$\gamma = \arccos|\hat{n}_2\cdot\hat{n}_3| \in [0°,90°]$$

⚠ Forgetting the absolute value is a real bug that makes aligned axes look anti-aligned.

### 3. Hemispherical power asymmetry

One half of the sky appears to have more large-scale power than the other:

$$A = \frac{\langle \mathcal{D}^2\rangle_N - \langle \mathcal{D}^2\rangle_S}{\langle \mathcal{D}^2\rangle_N + \langle \mathcal{D}^2\rangle_S}$$

⚙ Computed after low-pass filtering to $\ell \le 64$, scanning 768 candidate axes for the
maximum.

⚠ Note what "maximum over 768 axes" does to the statistics — that is precisely Chapter 30.

### 4. The Cold Spot

An unusually cold region about 5° across in the southern sky. Found by filtering with a spherical
**Mexican-hat wavelet**:

$$W_\ell(R) \propto x\,e^{-x/2}, \qquad x = \ell(\ell+1)R^2$$

This filter is *compensated* — it has zero response to a constant offset — so it responds to
localised features at scale $R$ and ignores the mean. The statistic is the most extreme negative
excursion in units of the map RMS.

---

## 30 The look-elsewhere effect

This chapter is the most important one in Part VI, and its lesson generalises far beyond
cosmology.

### The problem

Toss 20 coins. The chance of any *particular* one landing heads is 1/2. The chance that *at least
one* of them does is $1 - (1/2)^{20} \approx 0.999999$.

Now: search 768 hemisphere axes for the one with the largest asymmetry. Even in a perfectly
isotropic universe, *some* axis will look unusual. Reporting its $p$-value as if you had chosen
that axis in advance is simply wrong.

This is the **look-elsewhere effect**. It has other names — multiple comparisons, $p$-hacking,
the garden of forking paths — and it is the single most common way that scientists produce
convincing results that are not true.

### The correction

For $n$ independent tests, the probability that at least one gives $p$ or better:

$$\boxed{\ p_{corr} = 1 - (1-p)^n\ }$$

This is the **Šidák correction**. ⚙ This project applies it with $n=4$ for the four anomalies.

**Worked example.** A single test gives $p = 0.01$ — apparently 2.6σ. With four tests:

$$p_{corr} = 1-(1-0.01)^4 = 1 - 0.99^4 = 0.0394$$

Four times less impressive, and now unremarkable.

⚠ **An honest admission**: $n=4$ counts the four anomalies, but it does *not* count the 768 axes
searched *within* the asymmetry statistic, nor the many wavelet scales one could choose for the
Cold Spot, nor the anomalies proposed by the community and discarded over twenty years. The true
effective $n$ is much larger and genuinely hard to define. **The corrected $p$-values here should
be read as upper bounds on significance, not as final answers.**

That admission is not a weakness of the analysis. Being unable to state your true trials factor,
and saying so, is more scientifically useful than quoting a precise number you cannot justify.

### The deeper issue: a posteriori statistics

All of these anomalies were **found by looking at the data**. That is fundamentally different from
predicting a signal and then testing for it. There is no rigorous way to assign significance to a
feature that was discovered by inspection, because you cannot reconstruct how many alternative
features you would have found equally interesting.

The only clean resolution is **independent data**: a new statistic, a new frequency, or a new
survey — which is why large-scale structure surveys testing the same axes are so valuable.

---

## 31 Calibrating $p$-values with simulations

### The method

Rather than trusting analytic distributions for complicated statistics, **simulate**:

1. Generate a random sky from the theoretical $C_\ell$ — isotropic and Gaussian **by
   construction**.
2. Apply the *identical* analysis pipeline: same mask, same filtering, same axis search.
3. Record the statistic.
4. Repeat many times to build the null distribution.
5. The $p$-value is the fraction of simulations more extreme than the real data.

⚙ This project uses **500 simulations** at $N_{side}=64$.

The virtue of this approach is that it needs no analytic result. Whatever biases your pipeline
has — mask effects, filtering, the axis search itself — are **present identically in the
simulations**, so they cancel out of the comparison.

### Gate G6: testing the test

Here is the elegant part. How do you know the $p$-values are right?

Feed the pipeline skies that are isotropic **by construction**, and check that the resulting
$p$-values are **uniform on $[0,1]$**. That is the definition of a correctly calibrated $p$-value:
under the null hypothesis, $p$ is uniform.

- If $p$-values cluster near 0, the pipeline manufactures false anomalies.
- If they cluster near 1, it is over-conservative and will miss real ones.

⚙ **Gate G6 passes with mean $p = 0.462$** — consistent with the expected 0.5.

This is a genuinely valuable idea and worth carrying into any other field: **before you use a
statistical test on real data, run it on data where you know the answer, and check it gives the
right distribution of answers.**

> **Exercise 31.1** With 500 simulations, what is the smallest non-zero $p$-value you can
> measure? What does that imply about claiming a 4σ detection with this setup?

---
---

# PART VII — THE PIPELINE

Everything above, assembled. This part maps the physics onto the code you can actually run.

---

## 32 The six gates, mapped to the physics

The project refuses to report a result unless each stage passes an independent check.

```
NASA/ESA archive → clean → cross-spectrum → compare → fit ΛCDM → test anomalies
      (G1)         (G2)        (G3)          (G4)      (G5)         (G6)
```

| Gate | Asserts | Physics | Chapter | Status |
|---|---|---|---|---|
| **G1** | SHA-256 matches published checksum | none — data integrity | §15 | PASS |
| **G2** | Monopole 2.7255 K; dipole 3362 µK at $(264°,48°)$ | blackbody + our motion | §4, §16 | PASS (10.0 µK residual) |
| **G3** | First peak at $\ell = 220\pm8$ | acoustic ruler + flat geometry | §7–§9 | **PASS — $\ell=220$, $\mathcal{D}_\ell = 5949\ \mu$K²** |
| **G4** | $\chi^2/\text{dof} \approx 1$ vs published | consistency | §0.4, §25 | **PASS — 0.57 WMAP, 0.87 Planck** |
| **G5** | ΛCDM parameters within 3σ | Boltzmann + inference | §23–§27 | **PASS — 6/6 within 3σ** |
| **G6** | $p$-values uniform on isotropic skies | calibration | §31 | **PASS — mean $p$ = 0.462** |

### Why gates matter

An unchecked pipeline that produces a plausible-looking spectrum is worthless — as §20 showed,
the auto-spectrum version produced a curve that *looked* like data and was wrong by 26×. Each
gate compares against something known independently:

- G1 against a published checksum
- G2 against COBE/FIRAS and Planck's dipole
- G3 against the predicted acoustic scale
- G4 against WMAP and Planck spectra
- G5 against Planck's parameters
- G6 against skies we generated ourselves

**Nothing is taken on trust, and the checks are computed after the measurement, never fitted to.**

---

## 33 Service by service

| Service | Port | Does | Chapters |
|---|---|---|---|
| **catalog** | 8001 | Download, verify checksums, expose map metadata | §15 |
| **spectrum** | 8003 | Clean, mask, cross-spectrum, deconvolve, bin | §16–§22 |
| **cosmology** | 8004 | CAMB theory, MCMC inference, derived parameters | §23–§28 |
| **anomaly** | 8005 | Four statistics, 500-simulation calibration | §29–§31 |
| **skymap** | 8007 | Projections and renders of the maps | §15 |
| **tutor** | 8008 | The physics lessons and glossary | all |
| **chat** | 8009 | Question answering over the live results | — |
| **playground** | 8010 | Vary parameters, see the spectrum respond | §24 |
| **gateway** | 8080 | Go reverse proxy, caching, rate limiting | — |

### The path of a single measurement

1. **catalog** fetches `wmap_forered_imap_r9_9yr_V1_v5.fits` and `..._V2_v5.fits`, verifies
   SHA-256 → **G1**
2. **spectrum** converts K → µK, removes monopole and dipole → **G2**
3. applies KQ75 mask, $f_{sky}=0.688$
4. computes $\tilde{C}^{V1\times V2}_\ell$ via spherical harmonic transform → §20
5. divides by $w_2\,B^{V1}_\ell B^{V2}_\ell p_\ell^2$ → §18, §19
6. subtracts the point-source amplitude → §21
7. bins with $\Delta\ell=30$, error bars from the Knox formula → §22
8. finds the first peak → **G3**; compares to WMAP/Planck → **G4**
9. **cosmology** runs emcee × CAMB over six parameters → **G5**
10. **anomaly** runs four statistics against 500 isotropic skies → **G6**

Every arrow in that list is a chapter of this book.

---
---

# APPENDIX A — Symbols

| Symbol | Name | Meaning | First used |
|---|---|---|---|
| $a(t)$ | scale factor | relative size of the universe; $a_0=1$ today | §1 |
| $H$ | Hubble parameter | $\dot a/a$, expansion rate | §1 |
| $h$ | reduced Hubble | $H_0 / 100$ km/s/Mpc | §1 |
| $z$ | redshift | $1+z = 1/a$; a proxy for time | §4 |
| $\rho_c$ | critical density | density for a flat universe | §2 |
| $\Omega_i$ | density parameter | $\rho_i/\rho_c$ | §2 |
| $\Omega_k$ | curvature | $0$ for flat space | §2 |
| $w$ | equation of state | $p = w\rho c^2$ | §3 |
| $E(z)$ | — | $H(z)/H_0$ | §3 |
| $T_0$ | CMB temperature | 2.7255 K | §4 |
| $z_*$ | recombination | $\approx 1090$ | §5 |
| $\delta$ | overdensity | $(\rho-\bar\rho)/\bar\rho$ | §6 |
| $n_s$ | spectral index | tilt of primordial spectrum | §6 |
| $R$ | baryon loading | $3\rho_b/4\rho_\gamma$ | §7 |
| $c_s$ | sound speed | $c/\sqrt{3(1+R)}$ | §7 |
| $\eta$ | conformal time | $\int dt/a$ | §7 |
| $r_s$ | sound horizon | $\approx 144$ Mpc — **the ruler** | §8 |
| $D_A$ | distance to last scattering | $\approx 13{,}870$ Mpc | §9 |
| $\theta_*$ | acoustic scale | $r_s/D_A \approx 0.6°$ | §9 |
| $\ell_A$ | acoustic multipole | $\pi/\theta_* \approx 302$ | §9 |
| $\ell_D$ | damping scale | $\approx 1400$ | §10 |
| $\ell$ | multipole | angular scale $\approx 180°/\ell$ | §11 |
| $m$ | azimuthal index | $-\ell \le m \le \ell$ | §11 |
| $Y_{\ell m}$ | spherical harmonic | basis on the sphere | §11 |
| $a_{\ell m}$ | harmonic coefficient | the map, in harmonic space | §11 |
| $C_\ell$ | power spectrum | variance per multipole | §12 |
| $\mathcal{D}_\ell$ | plotted spectrum | $\ell(\ell+1)C_\ell/2\pi$ | §13 |
| $f_{sky}$ | sky fraction | 0.688 for KQ75 | §14 |
| $N_{side}$ | HEALPix resolution | $N_{pix}=12N_{side}^2$ | §15 |
| $W(\hat n)$ | mask | 1 keep, 0 cut | §18 |
| $w_2$ | mask normalisation | $\langle W^2\rangle$ | §18 |
| $M_{\ell\ell'}$ | mode-coupling matrix | mask-induced mixing | §18 |
| $B_\ell$ | beam transfer | instrument smoothing | §19 |
| $p_\ell$ | pixel window | pixelisation smoothing | §19 |
| $N_\ell$ | noise power | $\hat C^{AA}_\ell - \hat C^{AB}_\ell$ | §20 |
| $A_{ps}$ | point-source amplitude | flat $C_\ell$ | §21 |
| $\tau$ | optical depth | reionisation scattering | §24 |
| $A_s$ | primordial amplitude | — | §24 |
| $\sigma_8$ | clustering amplitude | RMS in 8 Mpc/h spheres | §24 |
| $\chi^2$ | goodness of fit | $\approx$ dof when the model fits | §0.4, §25 |
| $\mathcal{L}$ | likelihood | $P(\text{data}|\theta)$ | §25 |

---

# APPENDIX B — Constants and conversions

| Constant | Symbol | Value |
|---|---|---|
| Speed of light | $c$ | $2.998\times10^8$ m/s |
| Gravitational constant | $G$ | $6.674\times10^{-11}$ m³ kg⁻¹ s⁻² |
| Planck constant | $h_P$ | $6.626\times10^{-34}$ J s |
| Boltzmann constant | $k_B$ | $1.381\times10^{-23}$ J/K $= 8.617\times10^{-5}$ eV/K |
| Thomson cross-section | $\sigma_T$ | $6.652\times10^{-29}$ m² |
| Electron mass | $m_e$ | $511$ keV/c² |
| Hydrogen binding energy | — | 13.6 eV |

| Conversion | Value |
|---|---|
| 1 pc | $3.086\times10^{16}$ m = 3.262 ly |
| 1 Mpc | $3.086\times10^{22}$ m |
| 1 eV | $1.602\times10^{-19}$ J |
| 1 rad | $57.296°$ = 3438′ |
| 1° | 0.01745 rad |

| Cosmological value | Symbol | Number |
|---|---|---|
| CMB temperature | $T_0$ | 2.7255 K |
| CMB dipole | — | 3362.08 µK at $(264.021°, 48.253°)$ |
| Photon/baryon ratio | $n_\gamma/n_b$ | $1.6\times10^9$ |
| Hubble constant | $H_0$ | 67.36 km/s/Mpc |
| Hubble distance | $c/H_0$ | 4451 Mpc |
| Hubble time | $1/H_0$ | 14.51 Gyr |
| Critical density | $\rho_c$ | $8.5\times10^{-27}$ kg/m³ |
| Matter–radiation equality | $z_{eq}$ | 3400 |
| Recombination | $z_*$ | 1089.92 |
| Sound horizon | $r_s$ | 144.4 Mpc |
| Distance to last scattering | $D_A$ | 13,870 Mpc |
| Age | $t_0$ | 13.797 Gyr |

---

# APPENDIX C — Solutions

**0.1** $411 / (2.5\times10^{-7}) \approx 1.6\times10^{9}$ photons per baryon. This factor is why
recombination is delayed to 3000 K (§5).

**0.2** $\theta = 144/13870 = 0.01038$ rad $= 0.595°$.

**0.3** $e^{ikx}=\cos kx + i\sin kx$ and $e^{-ikx}=\cos kx - i\sin kx$; adding gives
$2\cos kx$. Reality of $f$ requires $f = f^*$, i.e. $\sum c_me^{im\theta} = \sum c_m^*e^{-im\theta}$;
matching coefficients gives $c_{-m}=c_m^*$.

**0.4** $\mathrm{Var}(Z^2) = \langle Z^4\rangle - \langle Z^2\rangle^2 = 3-1 = 2$. For $n$
independent terms variances add: $\mathrm{Var}(\chi^2_n)=2n$.

**1.1** $1/H_0 = 14.51$ Gyr versus the true age 13.797 Gyr. They differ because the expansion rate
was *not* constant — gravity decelerated it early, dark energy accelerates it now, and those
partially cancel. $1/H_0$ would be exact only for an empty, freely-coasting universe.

**2.1** $\rho_c = 3H_0^2/8\pi G$ with $H_0 = 67.36$ km/s/Mpc $= 2.183\times10^{-18}$ s⁻¹ gives
$\rho_c = 3(2.183\times10^{-18})^2/(8\pi\times6.674\times10^{-11}) \approx 8.5\times10^{-27}$
kg/m³ — about 5 hydrogen atoms per cubic metre.

**3.1** $\Omega_m(1+z)^3 = \Omega_r(1+z)^4 \Rightarrow 1+z_{eq} = \Omega_m/\Omega_r$, so
$1+z_{eq} = 0.3153/9.2\times10^{-5} \approx 3427$.

**3.2** With $k=0$, $\dot a^2/a^2 \propto a^{-3}$, so $\dot a \propto a^{-1/2}$, giving
$a^{1/2}da \propto dt$, hence $a^{3/2}\propto t$ and $a\propto t^{2/3}$.

**4.1** $\lambda_{peak} = 2.898\times10^{-3}/2.7255 = 1.06$ mm — microwave, hence the name.

**5.1** $\Gamma > H$ means a photon scatters many times per expansion time, keeping it coupled.
$\Gamma < H$ means the universe expands faster than scattering occurs, so photons free-stream.
Comparing a rate to the expansion rate is the universal decoupling criterion.

**5.2** Recombination would occur much closer to $k_BT \sim 13.6$ eV, i.e. $T \sim 10^5$ K, hence
much earlier and at far higher redshift. The CMB would be hotter at emission, the sound horizon
much smaller, and the acoustic peaks would sit at very different $\ell$.

**7.1** $R = 3\rho_b/4\rho_\gamma \propto a^{-3}/a^{-4} = a$. So $R$ grew with time, meaning $c_s$
*decreased* as recombination approached — sound slowed as the universe aged.

**7.2** $c_s = c/\sqrt{3(1.61)} = c/\sqrt{4.83} = 0.455c$.

**8.1** More baryons → larger $R$ → smaller $c_s$ → sound travels less far → smaller $r_s$. More
matter → larger $H$ at fixed $z$ and earlier equality → less conformal time before recombination
→ smaller $r_s$.

**9.1** Closed space converges light rays, so a given physical size subtends a *larger* angle,
pushing the peak to *lower* $\ell$.

**9.2** $\ell_2 = 302(2-0.27)=522$; $\ell_3 = 302(2.73)=825$. Measured: 537 and 810. The simple
constant-phase formula is good to a few percent; the real phase shift drifts slowly with $\ell$.

**10.1** $r_s$ shrinks (Ex 8.1), so all peaks shift to **higher $\ell$**. Odd peaks (1st, 3rd) are
enhanced relative to even (2nd), so $\mathcal{D}_2/\mathcal{D}_1$ falls. Damping also increases
slightly.

**11.1** $\sum_{\ell=0}^{1000}(2\ell+1) = (1001)^2 = 1{,}002{,}001$ — about a million numbers.

**12.1** Set $\hat n_1 = \hat n_2$ so $\theta=0$ and $P_\ell(1)=1$; the sum gives
$C(0)=\frac{1}{4\pi}\sum(2\ell+1)C_\ell$, which is the variance by definition.

**14.1** $\sqrt{2/(2\ell+1)} = 0.05 \Rightarrow 2\ell+1 = 800 \Rightarrow \ell \approx 400$.
For 1%: $2\ell+1 = 20{,}000 \Rightarrow \ell\approx10^4$ — beyond where the primary CMB survives
damping, which is why 1% per-multipole precision is unobtainable.

**14.2** 30% deficit against a 63% error is $0.30/0.63 \approx 0.5\sigma$. Entirely unremarkable.

**15.1** $4\pi/(12\times512^2) = 3.99\times10^{-6}$ sr. In arcmin²: $\times(3438)^2 \approx 47.2$
arcmin², i.e. about $6.9' \times 6.9'$.

**16.1** $v = c\,\Delta T/T_0 = 2.998\times10^5 \times (3362\times10^{-6}/2.7255) \approx 370$
km/s.

**20.1** If $\langle n^An^{B*}\rangle = N^{AB}_\ell \neq 0$, that term survives and biases the
cross-spectrum. Test: compare spectra from *different* detector pairings (V1×V2 versus V1×W1
versus W1×W2). Shared systematics would show up as pair-dependent discrepancies. ⚙ This project
does exactly this cross-check.

**22.1** 30 multipoles near $\ell=220$ contain $\sum(2\ell+1)\approx 30\times441 = 13{,}230$
modes; times $f_{sky}=0.688$ gives $\approx 9100$. Error $\approx\sqrt{2/9100}=1.5\%$, versus
6.7% for a single $\ell$ — roughly the expected $\sqrt{30}$ improvement.

**26.1** Accepting only uphill moves is hill-climbing: it finds a maximum but never explores, so
it yields no posterior width and gets stuck in local maxima. Accepting downhill moves with
probability $r$ is exactly what makes the stationary distribution equal the posterior (detailed
balance, §26).

**31.1** The smallest measurable non-zero $p$ is $1/500 = 0.002$ ($\approx 3.1\sigma$). You
**cannot** establish 4σ ($p\sim3\times10^{-5}$) with 500 simulations — you would need $\gtrsim10^5$.
Any claim beyond ~3σ from this setup would be extrapolation beyond the simulations.

---

# APPENDIX D — Further reading

Ordered by increasing difficulty.

**Introductory**
- Ryden, *Introduction to Cosmology* — the gentlest rigorous treatment; Chapters 2–5 cover Part I
  of this book.
- Wayne Hu's CMB tutorials (background.uchicago.edu) — outstanding animations of acoustic
  oscillations; the best intuition available for Part II.

**Intermediate**
- Dodelson & Schmidt, *Modern Cosmology* — the standard graduate text. Chapter 8 is the Boltzmann
  hierarchy of §23.
- Baumann, *Cosmology* — modern, clear, excellent on inflation.

**The measurement**
- Hivon et al. (2002), "MASTER of the CMB Anisotropy Power Spectrum" — the mode-coupling
  formalism of §18.
- Knox (1995) — the error-bar formula of §14.
- Hinshaw et al. (2013), WMAP nine-year results — the data used here.
- Planck 2018 results VI, "Cosmological parameters" — the reference values throughout.

**Anomalies**
- Planck 2018 results VII, "Isotropy and statistics" — sober, thorough, and appropriately
  sceptical.
- Bennett et al. (2011), "Are there CMB anomalies?" — the best discussion of look-elsewhere in
  this context.

**Software**
- `healpy` / HEALPix — Górski et al. (2005)
- `CAMB` — Lewis, Challinor & Lasenby (2000)
- `emcee` — Foreman-Mackey et al. (2013)
- `NaMaster` — the full mode-coupling treatment this project approximates (§18)

---

## Closing note

If you have read this far, you can answer the question the website poses on its front page:

> *How do we know the universe is 13.8 billion years old, flat, and 5% ordinary matter?*

The chain is: sound waves rang in the primordial plasma (§7); they travelled a calculable distance
before the universe turned transparent (§8); that distance is a ruler whose angular size we
measure from satellite maps (§9); measuring it honestly requires cross-spectra, beam
deconvolution and mask corrections (§18–§22); fitting the resulting curve with a Boltzmann code
and an MCMC gives six numbers (§23–§26); and integrating the Friedmann equation with those six
numbers gives the age (§24).

Not one step requires you to take anything on faith. Every number in this book was either derived
here or measured by the code in this repository — and every claim it makes is checked against
something it did not fit to.

That is the whole point.

