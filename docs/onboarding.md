# Onboarding

*For someone meeting both this codebase and this physics for the first time. Assumes a
science or engineering degree: you know calculus, you have seen a wave equation, you can
read Python. It assumes **no** cosmology and **no** knowledge of this project.*

Read Part 1 before touching the code. The architecture only makes sense once you know what
the pipeline is trying to do.

- [Part 1 — The physics, from zero](#part-1--the-physics-from-zero)
- [Part 2 — The codebase](#part-2--the-codebase)
- [Part 3 — Your first week](#part-3--your-first-week)
- [Glossary of symbols](#glossary-of-symbols)

---

# Part 1 — The physics, from zero

## 1.1 What the CMB is

The early universe was hot and dense. Above about 3000 K, hydrogen cannot stay neutral —
every atom that forms is immediately smashed apart by a photon. So the universe was a plasma
of free electrons and protons, and free electrons scatter light ferociously. Light could not
travel in a straight line. The universe was a glowing fog, like the inside of a star.

About 380,000 years in, expansion had cooled things to ~3000 K. Electrons and protons
combined into neutral hydrogen, which does not scatter light at these energies. **The fog
lifted, essentially all at once.**

The light released at that moment has been travelling ever since. Expansion has stretched it
from visible/infrared into microwaves, cooling it to **2.7255 K**. That is the cosmic
microwave background.

> **The single most important mental image:** you are looking at a *surface*, not a volume.
> Light from farther away takes longer to arrive, so what you see is the shell of points
> whose fog-clearing light is landing on us right now. It is a sphere centred on you, and
> it is the oldest thing anyone can see.

<details>
<summary>Why 3000 K, when hydrogen's binding energy is 13.6 eV ≈ 160,000 K?</summary>

Because photons outnumber atoms about a billion to one. Even when the *average* photon is
far too weak to ionise hydrogen, the rare energetic ones in the tail of the distribution are
still numerous enough to keep tearing atoms apart. You have to cool until even that
billion-to-one tail runs dry, which costs a factor of ~40 in temperature.
</details>

## 1.2 Why it is bumpy

The CMB is almost uniform — but not quite. After removing the Doppler shift from our own
motion, patches differ by about **one part in 100,000**.

Those patches are **sound waves, frozen mid-ring.**

Before the fog lifted, dark matter had already clumped into gravitational wells. Ordinary
matter and photons, tightly coupled, behaved as a single fluid that fell into those wells.
Gravity pulled it in; photon pressure pushed it back out. In, out, in — an oscillation.
Exactly like a mass on a spring, or a plucked guitar string.

A well of a given size has a characteristic oscillation period, just as a pipe of a given
length has a characteristic note.

Then the fog lifted and the photons flew free. **Whatever phase each oscillation happened to
be in at that instant was frozen into the temperature pattern forever.** Regions caught
mid-squeeze are hot; regions caught mid-stretch are cold.

So the CMB is a photograph of a standing wave field, taken at the moment the music stopped.

## 1.3 The power spectrum

We do not care where any individual hot spot is. We care **which wavelengths are loudest** —
exactly what a sound engineer's spectrum analyser shows.

Two reasons this is the right question:

1. **Theory cannot predict individual spots.** Inflation produced random quantum
   fluctuations. It predicts *statistics*, not specific locations. Asking "why is there a
   hot spot at those coordinates" is like asking why a particular die roll came up 4.
2. **It compresses everything.** Millions of pixels reduce to one curve.

On a flat surface you would use a Fourier transform. On a sphere the right basis is
**spherical harmonics** $Y_{\ell m}$ — the sphere's version of sine waves.

$$\frac{\Delta T(\hat{n})}{T_0} = \sum_{\ell}\sum_{m} a_{\ell m} Y_{\ell m}(\hat{n})$$

- **$\ell$ (multipole)** — how fine the pattern is. Roughly, **angle ≈ 180°/ℓ**.
  $\ell = 2$ is two huge lobes across the sky; $\ell = 220$ is patches about 1° wide.
- **$m$** — orientation of that pattern. There are $2\ell+1$ of them for each $\ell$.
- **$a_{\ell m}$** — how much of that specific ripple the real sky contains.

If the universe has no preferred direction, the typical strength can only depend on $\ell$,
not on $m$. That gives the **angular power spectrum**:

$$\hat{C}_\ell = \frac{1}{2\ell+1}\sum_m |a_{\ell m}|^2$$

Average the power over all orientations at each scale. That is the curve on the front page.

> Plots show $\mathcal{D}_\ell = \ell(\ell+1)C_\ell/2\pi$, not $C_\ell$. There are many more
> fine ripples than coarse ones, so raw $C_\ell$ makes small scales look feeble even when
> they carry lots of total power. The reweighting means **equal areas under the curve are
> equal contributions to how blotchy the sky actually looks.**

## 1.4 Why ℓ = 220 is the whole point

Sound waves had a deadline: when the fog lifted, they stopped. So there is a maximum
distance any wave could have travelled — the **sound horizon**, $r_s \approx 144$ Mpc.

Crucially, **that length is computed from atomic physics and thermodynamics, not fitted to
data.** It is a ruler of known size sitting at the edge of the observable universe.

Now do the oldest trick in geometry — angle = size / distance:

$$\theta_* = \frac{r_s}{D_A} = \frac{144}{13900} \approx 0.0104\ \text{rad} = 0.6°$$

Convert an angle to a multipole with $\ell \approx \pi/\theta$ and you get $\ell_A \approx 302$.
The observed first peak is at 220, and the gap is real physics: gravity kept *driving* the
oscillations rather than letting them ring freely, shifting the pattern by a phase
$\varphi \approx 0.27$. So $302 \times 0.73 \approx 220$. ✓

**Why this matters:** that angle depends on the geometry of space. Curved space bends light
paths and changes how big distant things look. Measuring where the first peak sits therefore
measures **whether the universe is flat**. It is, to high precision.

Peak *positions* give geometry. Peak *heights* give composition:

| Feature | Measures |
| :-- | :-- |
| Peak 1 height | Depth of the gravitational wells |
| Peak 2 / peak 1 | **Ordinary matter.** Heavy fluid squeezes deeper than it stretches, so baryons raise odd peaks and suppress even ones |
| Peak 3 height | **Dark matter.** Without it, decaying potentials would damp peak 3 |
| Fade-out beyond ℓ ≈ 1000 | Silk damping — the fog took time to clear, blurring fine detail |

## 1.5 What makes the measurement hard

This is where most of the engineering effort went. Four problems, each of which produced a
wrong answer before it was fixed:

**1. The Galaxy is in the way.** The Milky Way glows in microwaves across the middle of the
sky. We mask ~30% of it out. But the clean harmonic mathematics assumed a *whole* sphere;
with a hole, scales leak into each other. We correct with the standard `f_sky`
approximation.

**2. The telescope blurs the sky.** Fine detail is suppressed by a beam function $B_\ell$
that falls off exponentially. To undo it you divide by $B_\ell$ — dividing by a tiny number,
which amplifies everything, including noise.

**3. Noise looks exactly like signal.** A power spectrum squares things, and squared noise
is positive, so it just adds power. Combined with problem 2, our first attempt overestimated
the spectrum by **26×** at ℓ = 350 — no peaks at all, just a wall.

> **The key insight of this project.** Take two *different detectors* that observed the same
> sky. The real sky is identical in both; their noise is unrelated. Correlate them instead
> of squaring one:
>
> $$\langle a^A_{\ell m} a^{B*}_{\ell m}\rangle = C_\ell B^A_\ell B^B_\ell + \underbrace{\langle n^A n^{B*}\rangle}_{=\,0}$$
>
> The noise term vanishes because uncorrelated things have zero expected product. **No noise
> model, no instrument simulation.** χ²/dof went from 1669 to 1.02.

**4. Unresolved radio sources.** Distant galaxies too faint to catch individually add a flat
component in $C_\ell$, which grows as ℓ² in $\mathcal{D}_\ell$. Left in, it produced a
rising residual and χ²/dof ≈ 5.

### Cosmic variance — the floor you cannot beat

At multipole $\ell$ there are only $2\ell+1$ independent samples. At $\ell = 2$, that is
**five numbers**. Estimating a spread from five samples is inherently imprecise — the same
reason a poll of five people tells you little.

No better telescope helps. **There is only one universe and we have already measured all of
it.** This is why the large-angle anomalies are so hard to settle: with five numbers,
"genuinely strange" and "unlucky" look nearly identical.

## 1.6 From a curve to the universe

`CAMB` predicts $C_\ell$ for any given universe. Fitting means searching parameter space for
the universe whose predicted curve best matches ours, scored by

$$\chi^2 = \sum_b \frac{[\mathcal{D}_b^{\text{measured}} - \mathcal{D}_b(\theta)]^2}{\sigma_b^2}$$

Ordinary least squares, except each gap is divided by that point's error bar first — missing
a precise point by a little is worse than missing a vague one by a lot.

We use MCMC (`emcee`) rather than a grid, because the posterior has a long narrow diagonal
valley: raise H₀ and the peaks shift one way, lower the dark matter density and they shift
back. Many universes fit equally well. A grid would waste nearly every point; an ensemble
sampler learns the valley's shape automatically.

## 1.7 The anomalies, and intellectual honesty

Four features of the large-angle CMB look odd: the two largest patterns point in suspiciously
similar directions, one hemisphere is bumpier than the other, there is a large cold region in
the south, and the largest-scale ripple is weak.

Measuring these is easy. **Deciding whether they are surprising is the hard part**, and this
is the most important methodological lesson in the project:

1. **Look elsewhere.** Run four tests and something will look odd by luck. Corrected with
   Šidák: $p_{\text{corr}} = 1-(1-p)^n$. Our Cold Spot goes from p = 0.010 to p = 0.039 —
   from "interesting" to "unremarkable".
2. **Angles on a sphere.** Two random directions are uniform in $\cos\gamma$, not $\gamma$,
   so the typical separation is 60°, not 45°. Getting this backwards makes small angles look
   far rarer than they are.

We avoid analytic arguments entirely: generate 500 isotropic universes, measure each exactly
as we measured the real one, and count. **Result: nothing exceeds 2.1σ.** That is a boring
answer, and publishing it is the point.

---

# Part 2 — The codebase

## 2.1 Ten-thousand-foot view

```
cmb-lab/
├── libs/cmblab-core/     shared: app factory, config, HEALPix I/O, jobs
├── services/
│   ├── gateway/          Go. The only public entry point
│   ├── ingest/           CLI. Download + verify + clean
│   ├── catalog/  8001    what data exists
│   ├── spectrum/ 8003    the measurement          ← the heart
│   ├── cosmology/8004    CAMB + MCMC
│   ├── anomaly/  8005    statistics + Monte Carlo
│   ├── skymap/   8007    rendering
│   ├── tutor/    8008    curriculum
│   ├── chat/     8009    assistant
│   └── playground/8010   interactive experiments
├── web/                  React + TypeScript
├── docs/                 you are here
├── scripts/dev.sh        start/stop/status/logs
└── data/                 gitignored. raw/ clean/ logs/
```

**One rule explains most of the structure:** each service owns exactly one pipeline stage.
They do not call each other over HTTP. Shared state lives on disk under `data/`.

The single exception: `chat` imports `tutor` as a Python library, so the assistant answers
from the same curriculum the Learn tab shows. Deliberate — no network hop, no duplicated
content.

## 2.2 Following one request end to end

You press **Recompute** in the Spectrum tab.

```
web/src/views/SpectrumView.tsx
  └─ api.crossSpectrum({...})                    web/src/api/client.ts
       └─ POST http://localhost:8080/api/v1/spectrum/spectra/cross
            └─ Go gateway                        services/gateway/cmd/gateway/main.go
                 ├─ middleware: request ID, logging, rate limit
                 └─ proxy → http://localhost:8003/spectra/cross
                      └─ FastAPI                 services/spectrum/.../main.py
                           └─ run_spectrum()     .../pipeline.py
                                ├─ read_healpix_map()      cmblab_core.healpix.io
                                ├─ apply_mask()            cmblab_core.healpix.clean
                                ├─ estimate_cross_spectrum()  .../estimator.py
                                ├─ load_beam()             .../beams.py
                                ├─ subtract point sources  .../pointsources.py
                                ├─ bin_spectrum()          .../binning.py
                                └─ compare_to_reference()  .../compare.py   ← gates G3, G4
```

Trace that path once with a debugger and the architecture will click.

## 2.3 Conventions you must follow

**Raise ordinary exceptions.** `create_app()` maps `FileNotFoundError` → 404,
`KeyError` → 404, `ValueError` → 400. Do not construct `HTTPException` for these.

```python
# yes
if not path.exists():
    raise FileNotFoundError(f"Map {slug!r} has not been downloaded. Run `make data-bootstrap`.")

# no
raise HTTPException(404, "not found")
```

**Long work goes through `JobManager`.** MCMC and Monte Carlo take minutes. Return a job id
immediately; never block a request.

**Never hard-code a physical constant in a service.** It belongs in
`cmblab_core.constants`, with its source.

**Every published number carries a citation.** `Measurement(value, err_lo, err_hi, source)`.
If it has no source it does not go in the UI.

**Raw data is immutable.** `data/raw/` is written once by ingest and never touched again.
Wrong cleaning? Fix the code and re-run. Never patch a file in place.

## 2.4 Gotchas that have already bitten us

Each of these cost real time. They are in the code comments too, but read them now.

| Gotcha | Symptom | Fix |
| :-- | :-- | :-- |
| **certifi lacks ESA's CA** | `curl` works, Python gets an SSL error | `truststore.inject_into_ssl()`, called at `cmblab_core` import |
| **healpy `remove_dipole` returns a MaskedArray** | `sky != UNSEEN` silently wrong | `.filled(UNSEEN)` before returning |
| **CAMB truncates lensed spectra** | Broadcast error, array too short | Request `lmax + 400`, slice back |
| **OpenMP oversubscription** | Monte Carlo ~20× slower than expected | Set 5 thread-count env vars to `"1"` in the pool initialiser |
| **`dataclass(slots=True)` has no `__dict__`** | 500 errors in chat/tutor | Use `dataclasses.asdict()` |
| **`hp.mollview` owns its figure** | Figure-reuse warning, blank PNG | Let healpy create it, grab `plt.gcf()` |
| **Glossary matched stopwords** | "of" → "Axis of Evil" | `_STOPWORDS` filter |
| **`get_settings()` is cached** | `.env` edit has no effect | `./scripts/dev.sh restart` |
| **zsh does not word-split** | Service-start loop broke | Use `scripts/dev.sh` |

## 2.5 The gates

Six assertions. They are how the project avoids fooling itself, and they run in CI.

| Gate | Where | Asserts |
| :-- | :-- | :-- |
| G1 | `ingest/downloader.py` | SHA-256 matches the archive |
| G2 | `ingest/pipeline.py` | Dipole is 3362 µK toward (264°, 48°); residual < 50 µK |
| G3 | `spectrum/pipeline.py` | First peak at ℓ = 220 ± 8 |
| G4 | `spectrum/compare.py` | 0.3 ≤ χ²/dof ≤ 3.0 vs published |
| G5 | `cosmology/pipeline.py` | Every parameter within 3σ of Planck 2018 |
| G6 | `anomaly/pipeline.py` | p-values on simulated data are uniform |

> G4 is bounded on **both** sides on purpose. A suspiciously *low* χ² means overestimated
> error bars, which is just as wrong as a high one.

## 2.6 Development commands

```bash
make setup                  # one-time
make data-bootstrap         # ~170 MB

./scripts/dev.sh up         # all services
./scripts/dev.sh status     # health table
./scripts/dev.sh logs spectrum
./scripts/dev.sh restart    # after .env changes

make dev-spectrum           # one service, foreground, autoreload
make web                    # frontend :5174

make test                   # pytest
make lint                   # ruff + go vet + tsc
```

---

# Part 3 — Your first week

## Day 1 — Make it run, and look at it

```bash
make setup && make data-bootstrap
make spectrum          # watch G1-G4 pass
./scripts/dev.sh up && make web
```

Open http://localhost:5174. Then:

1. **Spectrum** → Recompute. Find ℓ = 220.
2. **Sky Map** → view the quadrupole and octupole presets side by side. That is the
   alignment anomaly, visible by eye.
3. **Learn** → lesson 1 at *Plain English*, then switch to *With equations* and expand
   "What each symbol means".
4. Ask the assistant: *"What did our pipeline measure?"*

## Day 2 — Break it on purpose

The **Playground** tab is the fastest way to understand why the code is shaped as it is.
Each of these reproduces a real bug from this project's history:

| Turn off | Watch |
| :-- | :-- |
| Beam deconvolution | Spectrum collapses at high ℓ |
| Point-source subtraction | Residual grows as ℓ² |
| Noise term in the variance | χ²/dof explodes to ~198 |

Then run an auto-spectrum instead of a cross-spectrum and see the 26× wall of noise.

## Day 3 — Read code in this order

1. [`cmblab_core/service.py`](../libs/cmblab-core/src/cmblab_core/service.py) — the shape of every service
2. [`spectrum/pipeline.py`](../services/spectrum/src/cmblab_spectrum/pipeline.py) — the main flow
3. [`spectrum/estimator.py`](../services/spectrum/src/cmblab_spectrum/estimator.py) — the actual physics
4. [`gateway/cmd/gateway/main.go`](../services/gateway/cmd/gateway/main.go) — the public surface
5. [`web/src/api/client.ts`](../web/src/api/client.ts) — every call the frontend makes

## Day 4 — First change

Good starter tasks, roughly in order of difficulty:

- **Add a glossary term.** `services/tutor/src/cmblab_tutor/glossary.py`. One dict entry, and
  the assistant can answer about it immediately.
- **Add a colormap.** `services/skymap/src/cmblab_skymap/render.py`.
- **Add a Playground knob.** `services/playground/src/cmblab_playground/experiments.py`.
- **Add a curated question.** `services/chat/src/cmblab_chat/topics.py` — a test enforces
  that every listed question is answerable without an API key, so you will find out
  immediately if it is not.
- **Add a detector pair.** `services/ingest/src/cmblab_ingest/registry.py`, then check the
  spectrum still passes G3/G4. This is the best way to convince yourself the pipeline is
  real: a different pair of detectors must give the same answer.

### Adding an endpoint — the checklist

1. Route in the service's `main.py`
2. Pydantic model in `cmblab_core/models/` if it is shared
3. **Route in `services/gateway/cmd/gateway/main.go`** ← easy to forget
4. `make gateway-build`
5. Types in `web/src/api/types.ts`
6. Function in `web/src/api/client.ts`
7. Test

## Day 5 — Verify everything

```bash
make test && make lint
npm --prefix web run build
./scripts/dev.sh status
```

Green across the board means you have a working environment and you are ready to take on
real work.

---

# Glossary of symbols

| Symbol | Read as | Means |
| :-- | :-- | :-- |
| $\ell$ | "ell" | Multipole — how fine a pattern is. Angle ≈ 180°/ℓ |
| $m$ | "em" | Orientation of that pattern; $2\ell+1$ per $\ell$ |
| $a_{\ell m}$ | "a-ell-em" | Amplitude of one specific ripple |
| $C_\ell$ | "C-ell" | Angular power spectrum — typical power at scale ℓ |
| $\mathcal{D}_\ell$ | "D-ell" | $\ell(\ell+1)C_\ell/2\pi$ — what is actually plotted |
| $\hat{\ }$ | "hat" | Measured, as opposed to true |
| $\tilde{\ }$ | "tilde" | Contaminated by masking |
| $T_0$ | | CMB temperature today, 2.7255 K |
| $z$ | "redshift" | How much the universe has stretched. $z=1100$ ≈ last scattering |
| $r_s$ | | Sound horizon, ~144 Mpc — the standard ruler |
| $D_A$ | | Distance to last scattering, ~13.9 Gpc |
| $\theta_*$ | "theta star" | Angle the ruler subtends, ~0.6°. Best-measured quantity in cosmology |
| $B_\ell$ | | Beam transfer function — how much survives telescope blurring |
| $N_\ell$ | | Noise power |
| $f_{\rm sky}$ | | Fraction of sky left after masking. Ours: 0.69 |
| $H_0$ | "H-naught" | Hubble constant — today's expansion rate |
| $\Omega_b h^2$ | "omega-b-h-squared" | Physical density of ordinary matter |
| $\Omega_c h^2$ | | Physical density of cold dark matter |
| $\tau$ | "tau" | Optical depth — re-scattering by the first stars |
| $A_s$, $n_s$ | | Amplitude and tilt of the primordial fluctuations |
| $\sigma_8$ | "sigma-eight" | How clumpy matter is on 8 Mpc/h scales |
| $\ast$ subscript | "star" | Evaluated at last scattering |

---

## Where to go next

- **[Service reference](services/README.md)** — every service in detail
- **[Why cross-spectra](why-cross-spectra.md)** — the central methodological choice
- **[Architecture](architecture.md)** — design decisions and trade-offs
- **The Learn tab** — the same physics as Part 1, but deeper, with audio and live numbers
- **The assistant** — ask it anything; it will not invent numbers
