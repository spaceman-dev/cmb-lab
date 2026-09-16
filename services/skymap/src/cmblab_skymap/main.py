"""HTTP API for the skymap service: render the CMB in every projection and filter."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import healpy as hp
import numpy as np
from cmblab_core.config import get_settings
from cmblab_core.healpix import UNSEEN, load_npz_map
from cmblab_core.service import create_app
from fastapi import Query
from fastapi.responses import Response

from .filters import PRESETS, multipole_band, smooth
from .render import COLORMAPS, PROJECTIONS, RenderOptions, render, sphere_grid

app = create_app(
    service_name="skymap",
    description="Multi-projection rendering and harmonic filtering of CMB sky maps.",
)

#: Rendering resolution. Nside 256 is plenty for a screen and keeps every request fast;
#: the underlying science always runs at native resolution.
RENDER_NSIDE = 256

PNG_CACHE_HEADERS = {"Cache-Control": "public, max-age=3600"}


@lru_cache(maxsize=32)
def _load(dataset: str, product: str, nside: int) -> np.ndarray:
    path = Path(get_settings().data_dir) / "clean" / dataset / f"{product}.npz"
    if not path.exists():
        raise FileNotFoundError(
            f"No cleaned map at {path}. Run `cmblab-ingest fetch {dataset} {product}`."
        )
    sky, _ = load_npz_map(path)
    if hp.npix2nside(sky.size) != nside:
        sky = hp.ud_grade(sky, nside_out=nside, order_in="RING")
    return sky


@lru_cache(maxsize=64)
def _filtered(dataset: str, product: str, ell_min: int, ell_max: int) -> np.ndarray:
    sky = _load(dataset, product, RENDER_NSIDE)
    if ell_min <= 2 and ell_max >= 3 * RENDER_NSIDE - 1:
        return sky
    return multipole_band(sky, ell_min, ell_max).sky


@app.get("/projections", tags=["meta"])
async def list_projections() -> dict[str, Any]:
    return {
        "projections": [
            {
                "id": "mollweide",
                "label": "Mollweide",
                "description": "Equal-area whole sky. The CMB standard.",
                "supports_direction": False,
            },
            {
                "id": "orthographic",
                "label": "Orthographic globe",
                "description": "The sky as seen from outside, centred on a direction.",
                "supports_direction": True,
            },
            {
                "id": "gnomonic",
                "label": "Gnomonic zoom",
                "description": "Tangent-plane close-up of a patch.",
                "supports_direction": True,
            },
            {
                "id": "cartesian",
                "label": "Cartesian",
                "description": "Longitude-latitude rectangle.",
                "supports_direction": True,
            },
            {
                "id": "sphere3d",
                "label": "3D sphere",
                "description": "Interactive globe, no projection distortion.",
                "supports_direction": True,
            },
        ],
        "colormaps": sorted(COLORMAPS),
        "presets": [
            {"id": key, **{k: v for k, v in preset.items()}} for key, preset in PRESETS.items()
        ],
    }


@app.get("/render/{dataset}/{product}.png", tags=["render"])
async def render_map(
    dataset: str,
    product: str,
    projection: str = Query(default="mollweide"),
    cmap: str = Query(default="planck"),
    lon: float = Query(default=0.0, ge=-360, le=360),
    lat: float = Query(default=0.0, ge=-90, le=90),
    fov_deg: float = Query(default=20.0, gt=0.1, le=180),
    ell_min: int = Query(default=2, ge=0, le=2048),
    ell_max: int = Query(default=767, ge=1, le=2048),
    smooth_deg: float = Query(default=0.0, ge=0.0, le=20.0),
    clip_percentile: float = Query(default=99.0, gt=50, le=100),
    graticule: bool = Query(default=True),
    transparent: bool = Query(default=True),
    title: str = Query(default=""),
) -> Response:
    """Render a sky map as PNG. Every knob the UI exposes lands here."""
    if projection not in PROJECTIONS:
        raise ValueError(f"Unknown projection {projection!r}. Use one of {PROJECTIONS}")

    sky = _filtered(dataset, product, ell_min, ell_max)
    if smooth_deg > 0:
        sky = smooth(sky, smooth_deg).sky

    png = render(
        sky,
        RenderOptions(
            projection=projection,
            cmap=cmap,
            lon=lon,
            lat=lat,
            fov_deg=fov_deg,
            clip_percentile=clip_percentile,
            graticule=graticule,
            transparent=transparent,
            title=title or f"{dataset}/{product}",
        ),
    )
    return Response(content=png, media_type="image/png", headers=PNG_CACHE_HEADERS)


@app.get("/preset/{dataset}/{product}/{preset}.png", tags=["render"])
async def render_preset(
    dataset: str,
    product: str,
    preset: str,
    projection: str = Query(default="mollweide"),
    cmap: str = Query(default="planck"),
    lon: float = 0.0,
    lat: float = 0.0,
) -> Response:
    """Render one of the named story views (quadrupole, acoustic scales, ...)."""
    if preset not in PRESETS:
        raise KeyError(f"Unknown preset {preset!r}. Known: {sorted(PRESETS)}")

    config = PRESETS[preset]
    sky = _filtered(dataset, product, config["ell_min"], config["ell_max"])

    png = render(
        sky,
        RenderOptions(
            projection=projection,
            cmap=cmap,
            lon=lon,
            lat=lat,
            title=config["label"],
        ),
    )
    return Response(content=png, media_type="image/png", headers=PNG_CACHE_HEADERS)


@app.get("/sphere/{dataset}/{product}", tags=["render"])
async def sphere(
    dataset: str,
    product: str,
    ell_min: int = Query(default=2, ge=0),
    ell_max: int = Query(default=767, ge=1),
    n_lon: int = Query(default=360, ge=60, le=720),
    n_lat: int = Query(default=180, ge=30, le=360),
) -> dict[str, Any]:
    """Sphere-sampled data for the interactive 3D globe."""
    sky = _filtered(dataset, product, ell_min, ell_max)
    payload = sphere_grid(sky, n_lon=n_lon, n_lat=n_lat)
    payload["dataset"] = dataset
    payload["product"] = product
    payload["ell_min"] = ell_min
    payload["ell_max"] = ell_max
    return payload


@app.get("/profile/{dataset}/{product}", tags=["analysis"])
async def profile(
    dataset: str,
    product: str,
    lon: float = Query(default=0.0),
    lat: float = Query(default=0.0),
    radius_deg: float = Query(default=10.0, gt=0.1, le=90),
    n_points: int = Query(default=60, ge=10, le=400),
) -> dict[str, Any]:
    """Radial temperature profile around a direction.

    Averaging in rings around a point is how the Cold Spot's extent was characterised: a
    statistical fluctuation and a genuinely extended structure look different here.
    """
    sky = _load(dataset, product, RENDER_NSIDE)
    centre = hp.ang2vec(lon, lat, lonlat=True)

    radii = np.linspace(0.0, radius_deg, n_points)
    means: list[float | None] = []
    errors: list[float | None] = []
    counts: list[int] = []

    previous = 0.0
    for radius in radii[1:]:
        outer = hp.query_disc(RENDER_NSIDE, centre, np.radians(radius))
        inner = hp.query_disc(RENDER_NSIDE, centre, np.radians(previous))
        ring = np.setdiff1d(outer, inner, assume_unique=False)

        values = sky[ring]
        values = values[(values != UNSEEN) & np.isfinite(values)]

        if values.size:
            means.append(round(float(values.mean()), 3))
            errors.append(round(float(values.std() / np.sqrt(values.size)), 3))
        else:
            means.append(None)
            errors.append(None)
        counts.append(int(values.size))
        previous = radius

    return {
        "dataset": dataset,
        "product": product,
        "centre": {"lon": lon, "lat": lat},
        "radius_deg": radii[1:].tolist(),
        "mean_uk": means,
        "err_uk": errors,
        "n_pixels": counts,
    }


@app.get("/stats/{dataset}/{product}", tags=["analysis"])
async def stats(
    dataset: str,
    product: str,
    ell_min: int = Query(default=2, ge=0),
    ell_max: int = Query(default=767, ge=1),
    bins: int = Query(default=60, ge=10, le=200),
) -> dict[str, Any]:
    """Pixel temperature histogram, compared against a Gaussian of the same variance.

    Inflation predicts the primordial fluctuations are very nearly Gaussian, so this
    histogram should follow a bell curve. Deviations would be a major discovery.
    """
    sky = _filtered(dataset, product, ell_min, ell_max)
    values = sky[(sky != UNSEEN) & np.isfinite(sky)]

    counts, edges = np.histogram(values, bins=bins, density=True)
    centres = 0.5 * (edges[:-1] + edges[1:])

    mean = float(values.mean())
    sigma = float(values.std())
    gaussian = np.exp(-0.5 * ((centres - mean) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))

    from scipy import stats as scipy_stats

    return {
        "dataset": dataset,
        "product": product,
        "ell_min": ell_min,
        "ell_max": ell_max,
        "mean_uk": round(mean, 4),
        "rms_uk": round(sigma, 4),
        "skewness": round(float(scipy_stats.skew(values)), 5),
        "kurtosis": round(float(scipy_stats.kurtosis(values)), 5),
        "n_pixels": int(values.size),
        "histogram": {
            "centres": np.round(centres, 3).tolist(),
            "density": np.round(counts, 8).tolist(),
            "gaussian": np.round(gaussian, 8).tolist(),
        },
    }
