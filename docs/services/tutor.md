# tutor

**Path:** `services/tutor/` · **Port:** 8008

The teaching layer: a six-lesson curriculum deriving every piece of physics the project
uses, with audio narration, a glossary, and live numbers spliced in from the actual
pipeline.

## What makes it different from a textbook

Every lesson section can quote **your** results. When the text says "our measurement puts
the first peak at ℓ = 220", that 220 is resolved at request time from the spectrum service,
not written into the prose. If you re-run the pipeline with different settings, the lessons
update.

## Three reading depths

The material is correct but dense, and a first-time reader was getting overwhelmed. Every
section is therefore layered, and the reader chooses the depth:

| Depth | Shows |
| --- | --- |
| **Plain English** | `Section.plain` — the whole idea in a few sentences, no symbols at all |
| **With equations** | Adds the narrative, plus for every equation a gloss of **every symbol** and an `intuition` paragraph arguing its shape from high-school physics |
| **Full derivations** | Adds the numbered `Step` chain |

The default is Plain English. Tests in `test_tutor.py` enforce that every section has a
plain summary, every equation glosses every symbol, and no plain text contains LaTeX.

Current coverage: **15 sections, 34 equations, 121 individual symbol glosses.**

## Modules

### `content.py` — the curriculum

Six lessons:

| Lesson | Sections | Covers |
| --- | --- | --- |
| `origin` | 2 | Recombination, last scattering, why the bumps are sound |
| `harmonics` | 3 | Spherical harmonics, C_ℓ, the 𝒟ℓ plotting convention |
| `peaks` | 3 | Sound horizon, angular scale, what each peak measures |
| `estimator` | 3 | Masking, beams, noise, cosmic variance |
| `inference` | 2 | Likelihood, Bayes, degeneracies |
| `anomalies` | 2 | The four anomalies, the look-elsewhere effect |

Data model:

```python
Var(symbol, meaning, units)              # one symbol, in plain words
Equation(latex, label, explain, variables, intuition)
Step(n, latex, reason)
Section(id, title, narrative, narration, plain, equations, derivation, live)
Lesson(id, title, subtitle, duration_min, prerequisites, sections)
```

`narrative` is prose with inline LaTeX for the browser; `narration` is the same idea as
speakable plain text for audio; `live` lists keys resolved against real results.

### `live.py`

`RESOLVERS` maps a key such as `first_peak_ell` to a function that reads the current
pipeline output. This is the bridge that keeps the teaching honest — if the pipeline has not
been run, the value is `None` and the UI says so rather than inventing a number.

### `audio.py`

Generates narration with macOS `say`, converts with `afconvert`, caches as `.m4a`.
`speakable()` rewrites symbols into words using a `_SPOKEN` table so "ℓ = 220" is read as
"ell equals two hundred twenty". The frontend falls back to the browser's `SpeechSynthesis`
API when server audio is unavailable, so the feature degrades rather than disappearing.

### `glossary.py`

18 terms, each with a short and long definition and often an equation. `search_glossary`
scores matches against term names and aliases.

> **Gotcha:** an early version matched stopwords — "of" hit "Axis of Evil". `_STOPWORDS`
> fixes that. Any new search feature needs the same guard.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/curriculum` | All lessons, durations, prerequisites |
| GET | `/lessons/{lesson_id}` | Full lesson with live values resolved |
| GET | `/lessons/{lesson_id}/sections/{section_id}` | One section |
| GET | `/audio/{lesson_id}/{section_id}.m4a` | Narration audio |
| POST | `/audio/speak` | Speak arbitrary text |
| GET | `/audio/clip/{clip_id}.m4a` | A generated clip |
| GET | `/audio/voices` | Available system voices |
| GET | `/glossary` | All terms |
| GET | `/glossary/{term}` | One term |

## Consumed by chat

The [chat](chat.md) service imports `search_glossary` and `resolve` directly as a Python
library. That is the one intentional cross-service dependency: it lets the assistant answer
from the same curriculum the Learn tab shows, with no network hop and no duplicated content.

## Running

```bash
make dev-tutor
.venv/bin/python -m pytest services/tutor/tests -q     # 28 tests
```
