# ingest

**Path:** `services/ingest/` · **No HTTP port — command-line only**

Downloads raw data from NASA LAMBDA and the ESA Planck Legacy Archive, verifies it, cleans
it, and writes it where every other service can find it. This is gate **G1**.

## Why it is a CLI and not a service

Ingestion runs rarely, takes minutes, and writes to disk. Exposing it over HTTP would mean
either a blocking request or a job queue for something a person runs once during setup. A
CLI is the honest shape.

## Usage

```bash
cmblab-ingest list                     # every known product
cmblab-ingest fetch wmap9 ilc-map      # one product
cmblab-ingest bootstrap                # the 8 products needed for a full run (~170 MB)

make data-bootstrap                    # same thing via make
```

## Modules

### `registry.py` — what can be downloaded

A hand-verified table of archive URLs. Every entry carries its dataset, slug, URL, expected
format, and whether it is a mask (masks skip unit conversion and dipole removal).

| Group | Products |
| --- | --- |
| WMAP9 maps | `ilc-map`, `band-{k,ka,q,v,w}` |
| WMAP9 detector maps | `da-{q1,q2,v1,v2,w1,w2,w3,w4}` — foreground-reduced, each with a `beam_product` |
| WMAP9 masks | `mask-kq75`, `mask-kq85` |
| WMAP9 beams | `beam-{K1..W4}` |
| WMAP9 spectra | `tt-spectrum`, `tt-spectrum-binned` |
| Planck PR3 | maps and spectra via `pla.esac.esa.int/pla/aio/product-action` |

`BOOTSTRAP_PRODUCTS` is the eight-item subset that a first-time user needs.

> The detector maps (`da-v1`, `da-v2`, …) are the important ones. Cross-correlating two
> detectors is what makes the spectrum work; the ILC map alone cannot produce a usable
> result. See [why-cross-spectra](../why-cross-spectra.md).

### `downloader.py` — fetching

Resumable byte-range downloads, SHA-256 verification, and retries with backoff on
`{401, 408, 429, 5xx}`. Uses the OS trust store via `cmblab_core.net`, without which the
ESA archive rejects the connection.

### `pipeline.py` — cleaning

`ingest_product()` runs the chain: read FITS → convert to µK → remove monopole and dipole
(with a Galactic cut) → validate → save as `.npz`.

**Gate G2** asserts that the fitted dipole matches the known CMB dipole (3362.08 µK toward
l = 264.021°, b = 48.253°) and that the residual after removal is below
`RESIDUAL_DIPOLE_TOL_UK = 50`. Our ILC residual is 7.9 µK.

Masks bypass unit conversion and dipole removal — they are 0/1 arrays, not temperatures.

## Output layout

```
data/
  raw/<dataset>/<product>.fits      # exactly as downloaded, never modified
  clean/<dataset>/<product>.npz     # µK, monopole and dipole removed
  logs/
```

Raw files are treated as immutable. Every derived product can be regenerated from them, so
if a cleaning step is wrong the fix is to re-run, never to patch a file in place.

## Adding a product

1. Add an entry to `registry.py` with the verified URL.
2. `cmblab-ingest fetch <dataset> <slug>`.
3. If it is a map, confirm gate G2 passes in the output.
