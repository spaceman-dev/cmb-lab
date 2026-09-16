# cmblab-core

**Path:** `libs/cmblab-core/` · **Importable as:** `cmblab_core` · **Not a service**

The shared library every Python service depends on. If a piece of logic is needed by more
than one service, it lives here; if only one service needs it, it stays in that service.

## Why it exists

Eight services that each rolled their own FastAPI setup, error handling, and HEALPix I/O
would drift apart within a week. `cmblab_core` makes the boring parts identical everywhere,
so a bug fixed once is fixed everywhere.

## Modules

### `service.py` — the app factory

```python
from cmblab_core.service import create_app

app = create_app(title="cmb-lab spectrum", version="0.1.0")
```

Gives every service:

- `GET /health` returning `{"status": "ok", "service": ..., "version": ...}`
- CORS for `localhost:5173`, `localhost:5174`, and `localhost:8080`
- A request-ID middleware that echoes `X-Request-ID` (the gateway generates one if absent),
  so a single browser action can be traced across services in the logs
- Exception handlers mapping `FileNotFoundError` → 404, `KeyError` → 404, `ValueError` → 400

That last point matters stylistically: service code raises plain Python exceptions and never
constructs `HTTPException` for these cases.

### `config.py` — settings

`Settings` is a `pydantic-settings` model loaded from `.env`. Fields include `data_dir`,
per-service ports, `gemini_api_key`, and `gemini_model`.

```python
from cmblab_core.config import get_settings
settings = get_settings()      # lru_cached
```

> **Gotcha:** `get_settings()` is cached for the process lifetime. Editing `.env` has no
> effect until you restart: `./scripts/dev.sh restart`.

### `net.py` — TLS trust store

```python
enable_os_trust_store()   # called at cmblab_core import time
```

ESA's Planck Legacy Archive presents a certificate chain that `certifi` does not carry, so
`httpx`/`requests` fail while `curl` succeeds. `truststore.inject_into_ssl()` makes Python
use the operating system's trust store instead. Without this, Planck downloads fail with an
opaque SSL error.

### `healpix/` — sphere operations

| Module | Contents |
| --- | --- |
| `io.py` | `read_healpix_map` (forces RING ordering, normalises `UNSEEN`), `inspect_fits`, `save_npz_map`, `load_npz_map` |
| `clean.py` | `to_microkelvin`, `fit_dipole`, `remove_monopole_dipole`, `apply_mask`, `degrade`, `clean_map`, `CleaningReport` |
| `preview.py` | `render_mollweide` |

> **Gotcha:** healpy's `remove_dipole` returns a masked array. `remove_monopole_dipole`
> calls `.filled(UNSEEN)` before returning, because downstream code compares
> `sky != UNSEEN` and a masked array silently breaks that test.

### `jobs.py` — background work

`JobManager` wraps a `ThreadPoolExecutor` and hands out `JobRecord`s carrying `state`,
`progress`, `message`, `result`, and `error`. Used by `cosmology` (MCMC) and `anomaly`
(Monte Carlo), both of which take minutes and must not block a request.

### `constants.py` — physical reference values

Measured constants and published results used for validation gates:
`T_CMB_NOMINAL_K`, `DIPOLE_AMPLITUDE_UK`, `ACOUSTIC_PEAKS`, `PLANCK_2018` (a dict of
`Measurement(value, err_lo, err_hi, source)`), `H0_MEASUREMENTS`.

Every published number carries its source string, so nothing appears in the UI without a
citation.

### `models/` — shared pydantic schemas

`catalog.py`, `jobs.py`, `spectrum.py` (`Bandpower`), `cosmology.py` (`CosmoParams`),
`anomaly.py`. These are the wire contracts between services and the frontend.

## Tests

```bash
.venv/bin/python -m pytest libs/cmblab-core/tests -q
```

Covers dipole fitting and removal, unit conversion, masking, and degrading — the
transformations where a silent error would corrupt every downstream result.
