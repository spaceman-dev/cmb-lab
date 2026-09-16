# Contributing

Thanks for looking. A few things worth knowing before you start.

**New to the project?** Read [docs/onboarding.md](docs/onboarding.md) first. It covers the
physics from zero and then the codebase, and it will save you a lot of confusion.

## Setup

```bash
make setup            # venv, dependencies, Go toolchain, npm install
make data-bootstrap   # ~170 MB from NASA/ESA. No API key needed
make test && make lint
```

Python **3.12** specifically — healpy and camb do not yet ship arm64 wheels for 3.14.

## Before opening a PR

```bash
make test                       # pytest
make lint                       # ruff + go vet + tsc
npm --prefix web run build
```

If you touched the analysis pipeline, also confirm the gates still pass:

```bash
make spectrum                   # G1-G4
```

## Principles

**Nothing is taken on trust.** Every stage has a validation gate. If you add a stage, add a
gate. If a gate is inconvenient, that is usually the gate doing its job.

**Published results are a check, never an input.** We do not fit to WMAP or Planck. We
measure independently and compare afterwards. Any change that blurs that line will be asked
about.

**Every number in the UI carries a source.** Use
`Measurement(value, err_lo, err_hi, source)`. No source, no display.

**State limitations openly.** The README has a Limitations section and the code says
"this is mildly circular" where it is. Please keep that habit — it is more useful to a reader
than a clean-looking result.

**Raw data is immutable.** `data/raw/` is written once by ingest. If cleaning is wrong, fix
the code and re-run; never patch a file in place.

## Code style

- Services raise plain exceptions; `create_app()` maps them to status codes. Do not build
  `HTTPException` for `FileNotFoundError` / `KeyError` / `ValueError`.
- Physical constants live in `cmblab_core.constants`, never inline in a service.
- Work taking more than a second or two goes through `JobManager`.
- Comments explain *why*, not *what*. The gotcha table in the onboarding doc is the tone to
  aim for.
- Line length 100, enforced by ruff.

## Adding an endpoint

Easy to forget step 3:

1. Route in the service's `main.py`
2. Shared model in `cmblab_core/models/` if applicable
3. **Route in `services/gateway/cmd/gateway/main.go`**
4. `make gateway-build`
5. Type in `web/src/api/types.ts`
6. Function in `web/src/api/client.ts`
7. Test

## Tests

Markers: `physics` (validates a physical result), `slow`, `network`. CI runs
`-m "not slow and not network"`, so anything needing the 170 MB dataset must be marked.

Tests that encode a physical fact are the most valuable ones here. If you fix a subtle bug,
add a test that would have caught it.

## Reporting a problem

Useful bug reports include the output of `./scripts/dev.sh status`, the relevant tail of
`data/logs/<service>.log`, and your OS and Python version.

If you believe a *physics* result is wrong, that is the most interesting kind of issue —
please include which gate should have caught it.
