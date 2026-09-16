# skymap

**Path:** `services/skymap/` · **Port:** 8007

Renders HEALPix maps as images, and filters them by angular scale so you can see the physics
rather than just a pretty picture.

## Responsibility

Turn a sphere of ~3 million pixels into something a browser can display, in several
projections, with a filter stage that isolates individual multipole ranges.

## Modules

### `render.py`

Four projections, each answering a different question:

| Projection | Good for |
| --- | --- |
| Mollweide | The whole sky at once, equal-area. The default |
| Orthographic | A globe — intuitive for judging direction |
| Gnomonic | Zooming into one feature, e.g. the Cold Spot |
| Cartesian | Flat lon/lat, easiest to read coordinates off |

`sphere_grid` returns raw values for the WebGL 3D sphere in the frontend rather than a PNG.

Seven colormaps including `PLANCK_CMAP` (the official Planck colour scheme) and a dark
`NIGHT_CMAP` matching the site theme.

> **Gotcha:** `hp.mollview` creates and owns its own matplotlib figure. Creating one
> beforehand and passing it in produces a figure-reuse warning and a blank image. Let
> healpy make the figure and capture it with `plt.gcf()`.

### `filters.py`

`multipole_band(lo, hi)` keeps only a range of angular scales; `smooth(fwhm)` applies a
Gaussian beam.

Eight presets, each with an `explain` string shown in the UI:

| Preset | Shows |
| --- | --- |
| `quadrupole` | ℓ = 2 alone |
| `octupole` | ℓ = 3 alone |
| `low-multipoles` | ℓ = 2–10, where the anomalies live |
| `acoustic` | ℓ = 100–400, the first peak scales |
| `damping` | ℓ > 800, Silk-damped detail |
| … | |

The quadrupole and octupole presets side by side make the alignment anomaly visible
directly, without any statistics.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/projections` | Available projections and colormaps |
| GET | `/render/{dataset}/{product}.png` | Rendered map. Query params control projection, colormap, range, filtering |
| GET | `/preset/{dataset}/{product}/{preset}.png` | A named preset |
| GET | `/sphere/{dataset}/{product}` | Vertex data for the 3D view |
| GET | `/profile/{dataset}/{product}` | Temperature along a great circle |
| GET | `/stats/{dataset}/{product}` | Min, max, mean, RMS for scaling the colour bar |

## Caching

Renders are deterministic in their inputs, so the gateway caches the PNGs. Changing a
colormap in the UI is instant the second time.

## Running

```bash
make dev-skymap
```
