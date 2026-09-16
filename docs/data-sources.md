# Data Sources — where everything comes from

Every URL in this document was verified with a live HEAD request. If one 404s later, the
archive reorganised; regenerate from the LAMBDA bulk-download scripts described at the end.

**No API key is needed for any CMB data.** The only token in this project is for NASA ADS,
and that is only used by the `literature` service.

---

## Quick start — the files you need for a first result

Total download: about 170 MB. This is enough to produce a real, validated power spectrum.

```bash
make data-bootstrap
```

That command fetches:

| File | Size | What it is |
|---|---|---|
| `wmap_ilc_9yr_v5.fits` | 24 MB | Foreground-cleaned full-sky CMB map, N_side=512 |
| `wmap_forered_imap_r9_9yr_V1_v5.fits` | 24 MB | V1 detector map — half of the cross-spectrum |
| `wmap_forered_imap_r9_9yr_V2_v5.fits` | 24 MB | V2 detector map — independent noise |
| `wmap_ampl_bl_V1_9yr_v5p1.txt` | 40 KB | V1 measured beam transfer function |
| `wmap_ampl_bl_V2_9yr_v5p1.txt` | 40 KB | V2 measured beam transfer function |
| `wmap_temperature_kq75_analysis_mask_r9_9yr_v5.fits` | 24 MB | Galactic + point-source mask |
| `wmap_binned_tt_spectrum_9yr_v5.txt` | 4 KB | WMAP's published TT spectrum |
| `COM_PowerSpect_CMB-TT-binned_R3.01.txt` | 6 KB | Planck 2018 binned TT spectrum |

**The ILC map is not the right input for a power spectrum.** It is excellent for
visualisation and low-ℓ work, but its auto-spectrum carries a noise bias and its effective
beam is not a clean Gaussian. Use the V1/V2 detector pair with a cross-spectrum instead —
see section 7.

**Start with WMAP, not Planck.** WMAP maps are N_side=512 (3.1M pixels, 24 MB). Planck maps
are N_side=2048 (50M pixels, ~600 MB). The dev loop on WMAP is seconds instead of minutes,
and the physics you are validating is identical.

---

## 1. NASA LAMBDA — WMAP 9-year (DR5)

Base: `https://lambda.gsfc.nasa.gov/data/map/dr5/`
Landing page: <https://lambda.gsfc.nasa.gov/product/wmap/dr5/m_products.html>

### CMB maps

The **ILC (Internal Linear Combination)** map is the one you want. It is a weighted
combination of the five frequency bands built to cancel foregrounds, leaving CMB.

```
https://lambda.gsfc.nasa.gov/data/map/dr5/dfp/ilc/wmap_ilc_9yr_v5.fits
```

Units are **mK_CMB**, N_side=512, Galactic coordinates, NESTED ordering.
The monopole and dipole have already been removed by the WMAP team — expect a residual
dipole of a few μK, not 3362 μK. See the note on gate G2 below.

### Raw frequency band maps

Use these if you want to do your own component separation.

```
https://lambda.gsfc.nasa.gov/data/map/dr5/skymaps/9yr/raw/wmap_band_imap_r9_9yr_K_v5.fits    22.8 GHz
https://lambda.gsfc.nasa.gov/data/map/dr5/skymaps/9yr/raw/wmap_band_imap_r9_9yr_Ka_v5.fits   33.0 GHz
https://lambda.gsfc.nasa.gov/data/map/dr5/skymaps/9yr/raw/wmap_band_imap_r9_9yr_Q_v5.fits    40.7 GHz
https://lambda.gsfc.nasa.gov/data/map/dr5/skymaps/9yr/raw/wmap_band_imap_r9_9yr_V_v5.fits    60.8 GHz
https://lambda.gsfc.nasa.gov/data/map/dr5/skymaps/9yr/raw/wmap_band_imap_r9_9yr_W_v5.fits    93.5 GHz
```

K band is synchrotron-dominated, W band is dust-dominated, V band is the cleanest CMB
channel. That frequency dependence is exactly what component separation exploits.

### Masks

```
https://lambda.gsfc.nasa.gov/data/map/dr5/ancillary/masks/wmap_temperature_kq75_analysis_mask_r9_9yr_v5.fits
https://lambda.gsfc.nasa.gov/data/map/dr5/ancillary/masks/wmap_temperature_kq85_analysis_mask_r9_9yr_v5.fits
https://lambda.gsfc.nasa.gov/data/map/dr5/ancillary/masks/wmap_temperature_source_mask_r9_9yr_v5.fits
```

KQ75 is the conservative choice, keeping about 69% of the sky (measured f_sky = 0.688).
KQ85 keeps roughly 82% but leaves more Galactic residual. **Use KQ75 for power spectrum
work.** Convention: 1 = keep, 0 = reject.

### Beam transfer functions

Needed to deconvolve the instrument's finite resolution. Without this your spectrum falls
off at high ℓ for an entirely instrumental reason.

```
https://lambda.gsfc.nasa.gov/data/map/dr5/ancillary/beams/wmap_ampl_bl_{DA}_9yr_v5p1.txt
```

where `{DA}` is one of `K1 Ka1 Q1 Q2 V1 V2 W1 W2 W3 W4`.

### Published power spectra — your comparison target

```
https://lambda.gsfc.nasa.gov/data/map/dr5/dcp/spectra/wmap_tt_spectrum_9yr_v5.txt
https://lambda.gsfc.nasa.gov/data/map/dr5/dcp/spectra/wmap_binned_tt_spectrum_9yr_v5.txt
```

---

## 2. ESA Planck Legacy Archive — PR3 (2018)

LAMBDA does **not** mirror the Planck maps. They come from ESA's PLA, which serves files
through a query endpoint rather than static paths.

Pattern for maps:
```
https://pla.esac.esa.int/pla/aio/product-action?MAP.MAP_ID=<FILENAME>
```

### Component-separated CMB maps

Four independent pipelines applied to the same data. Running your analysis across all four
is a free systematics check: if a result only appears in one, it is a method artifact.

```
COM_CMB_IQU-commander_2048_R3.00_full.fits     parametric Bayesian fitting
COM_CMB_IQU-nilc_2048_R3.00_full.fits          needlet internal linear combination
COM_CMB_IQU-sevem_2048_R3.00_full.fits         template fitting
COM_CMB_IQU-smica_2048_R3.00_full.fits         spectral matching ILC  <- default choice
```

Each is roughly 600 MB, N_side=2048, units **K_CMB**, Galactic, NESTED.
Field 0 is I (temperature), field 1 is Q, field 2 is U.

### Common mask

```
COM_Mask_CMB-common-Mask-Int_2048_R3.00.fits
```

### Published power spectra

Note the **different query parameter** — `COSMOLOGY.FILE_ID`, not `MAP.MAP_ID`:

```
https://pla.esac.esa.int/pla/aio/product-action?COSMOLOGY.FILE_ID=COM_PowerSpect_CMB-TT-full_R3.01.txt
https://pla.esac.esa.int/pla/aio/product-action?COSMOLOGY.FILE_ID=COM_PowerSpect_CMB-TT-binned_R3.01.txt
```

The binned file is the one plotted in every Planck paper. Columns are
`ell, D_ell, -dD_ell, +dD_ell` with `D_ell` in μK².

**PLA occasionally returns HTTP 401 under rapid sequential requests.** This is rate
limiting, not an auth requirement. The ingest service retries with backoff.

---

## 3. NASA ADS — literature

Free token: <https://ui.adsabs.harvard.edu/user/settings/token> (requires a free account).
Put it in `.env` as `ADS_API_TOKEN`. Limit is 5000 requests/day.

```
https://api.adsabs.harvard.edu/v1/search/query?q=...&fl=bibcode,title,author,year,citation_count
Authorization: Bearer <token>
```

arXiv needs no key at all: `http://export.arxiv.org/api/query`.

---

## 4. A critical note on validation gate G2

The architecture plan says cleaning must recover the CMB dipole at 3362 μK toward
(l, b) = (264°, 48°). **That gate only applies to maps that still contain the dipole.**

| Map | Dipole present? | What G2 asserts |
|---|---|---|
| Synthetic test sky | Yes, injected | Recover 3362 μK within 2% |
| WMAP raw band maps | Partially | Fit is dominated by foregrounds without a Galactic cut |
| WMAP ILC | No, pre-removed | **Residual** dipole must be < 50 μK |
| Planck component-separated | No, pre-removed | **Residual** dipole must be < 50 μK |

So on real component-separated data, G2 is an *upper bound* test, not a recovery test. The
recovery test runs against the synthetic sky in
[libs/cmblab-core/tests/test_healpix_clean.py](../libs/cmblab-core/tests/test_healpix_clean.py).
Getting this backwards is the single most common way to convince yourself the pipeline is
broken when it is fine.

---

## 5. Other archives worth knowing

| Archive | Contents |
|---|---|
| **ACT DR6** on LAMBDA | Higher-resolution ground-based CMB, extends to ℓ ≈ 4000 |
| **SPT-3G** on LAMBDA | Deep small-patch survey, excellent damping-tail measurement |
| **IRSA** (`irsa.ipac.caltech.edu`) | Mirrors Planck, offers VO/TAP queries |
| **COBE/DMR** on LAMBDA | The 1992 discovery data. Tiny, and historically wonderful |

---

## 6. Regenerating these URLs if the archive moves

LAMBDA publishes a `wget` script per product group. The scripts are the authoritative
source of file paths:

```bash
curl -s https://lambda.gsfc.nasa.gov/product/wmap/dr5/m_products.html \
  | grep -oiE '/product/wmap/dr5/[a-z0-9_.-]*_wget\.sh' | sort -u

# then extract real URLs from any of them
curl -s https://lambda.gsfc.nasa.gov/product/wmap/dr5/ilc_map_wget.sh \
  | grep -oE 'https://lambda[^ "]+'
```

Useful script names: `ilc_map_wget.sh`, `masks_wget.sh`, `beam_xfer_wget.sh`,
`maps_band_r9_i_9yr_wget.sh`, `pow_tt_spec_wget.sh`.
