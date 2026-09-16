"""Sky map rendering in every standard projection.

No single projection of a sphere onto a plane is faithful; each sacrifices something.
Which one to use depends on the question being asked:

* **Mollweide** — equal area. Regions of equal solid angle occupy equal paper area, so it
  does not exaggerate any part of the sky. This is why every CMB paper uses it.
* **Orthographic** — the view from outside, as if looking at a globe. Honest about shape
  near the centre, severely compressed at the limb. Best for showing a specific direction.
* **Gnomonic** — a tangent-plane zoom. Great circles map to straight lines. Use it to
  inspect a small patch such as the Cold Spot.
* **Cartesian** — plate carrée. Distorts area badly near the poles but is the easiest to
  read off coordinates from.
* **Sphere** — the actual 3D object, with no projection at all.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")

import healpy as hp  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from cmblab_core.healpix import UNSEEN  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

PROJECTIONS = ("mollweide", "orthographic", "gnomonic", "cartesian")

#: The Planck collaboration's colour scheme: deep blue through white to red, with the
#: extremes rolling into warmer tones. Chosen so that zero sits at the neutral midpoint.
_PLANCK_COLORS = [
    (0.00, "#0000ff"),
    (0.20, "#00aaff"),
    (0.40, "#00ffff"),
    (0.50, "#ffffff"),
    (0.60, "#ffff00"),
    (0.80, "#ff7700"),
    (1.00, "#aa0000"),
]

PLANCK_CMAP = LinearSegmentedColormap.from_list("planck", _PLANCK_COLORS)

#: A palette tuned for the dark night-sky UI: cool cyan through black to warm amber.
_NIGHT_COLORS = [
    (0.00, "#1d4ed8"),
    (0.25, "#06b6d4"),
    (0.50, "#0b1120"),
    (0.75, "#f59e0b"),
    (1.00, "#ef4444"),
]

NIGHT_CMAP = LinearSegmentedColormap.from_list("night", _NIGHT_COLORS)

COLORMAPS = {
    "planck": PLANCK_CMAP,
    "night": NIGHT_CMAP,
    "RdBu_r": plt.get_cmap("RdBu_r"),
    "coolwarm": plt.get_cmap("coolwarm"),
    "inferno": plt.get_cmap("inferno"),
    "viridis": plt.get_cmap("viridis"),
    "gray": plt.get_cmap("gray"),
}


@dataclass(slots=True)
class RenderOptions:
    projection: str = "mollweide"
    cmap: str = "planck"
    lon: float = 0.0
    lat: float = 0.0
    fov_deg: float = 20.0
    clip_percentile: float = 99.0
    vmin: float | None = None
    vmax: float | None = None
    graticule: bool = True
    title: str = ""
    unit: str = "µK"
    dpi: int = 120
    transparent: bool = True
    cbar: bool = True


def symmetric_limits(sky: np.ndarray, percentile: float = 99.0) -> tuple[float, float]:
    """Colour limits symmetric about zero.

    CMB anisotropies are symmetric fluctuations about the mean, so a diverging colormap
    centred on zero is the honest choice. A percentile clip stops a handful of bright
    foreground residuals from flattening everything else to mid-grey.
    """
    valid = sky[(sky != UNSEEN) & np.isfinite(sky)]
    if valid.size == 0:
        return -1.0, 1.0
    limit = float(np.percentile(np.abs(valid), percentile))
    return -limit, limit


def render(sky: np.ndarray, options: RenderOptions) -> bytes:
    """Render a HEALPix map to PNG bytes in the requested projection."""
    sky = np.asarray(sky, dtype=np.float64)

    vmin, vmax = options.vmin, options.vmax
    if vmin is None or vmax is None:
        auto_min, auto_max = symmetric_limits(sky, options.clip_percentile)
        vmin = auto_min if vmin is None else vmin
        vmax = auto_max if vmax is None else vmax

    cmap = COLORMAPS.get(options.cmap, PLANCK_CMAP)
    background = "none" if options.transparent else "white"
    text_colour = "#cbd5e1" if options.transparent else "black"

    shared = {
        "title": options.title,
        "unit": options.unit,
        "min": vmin,
        "max": vmax,
        "cmap": cmap,
        "badcolor": "#1e293b" if options.transparent else "0.85",
        "bgcolor": "#00000000" if options.transparent else "white",
        "cbar": options.cbar,
    }

    plt.close("all")
    projection = options.projection.lower()

    if projection == "mollweide":
        hp.mollview(sky, **shared)
    elif projection == "orthographic":
        hp.orthview(sky, rot=(options.lon, options.lat, 0), half_sky=True, **shared)
    elif projection == "gnomonic":
        # reso is arcmin per pixel; pick it so the requested field of view fills the frame.
        pixels = 600
        hp.gnomview(
            sky,
            rot=(options.lon, options.lat, 0),
            reso=options.fov_deg * 60.0 / pixels,
            xsize=pixels,
            **shared,
        )
    elif projection == "cartesian":
        hp.cartview(sky, rot=(options.lon, options.lat, 0), **shared)
    else:
        raise ValueError(f"Unknown projection {options.projection!r}. Use one of {PROJECTIONS}")

    if options.graticule:
        hp.graticule(dpar=30, dmer=30, color="#64748b", linewidth=0.4, alpha=0.6)

    figure = plt.gcf()
    for axis in figure.get_axes():
        for text in axis.texts:
            text.set_color(text_colour)

    buffer = io.BytesIO()
    figure.savefig(
        buffer,
        format="png",
        dpi=options.dpi,
        bbox_inches="tight",
        transparent=options.transparent,
        facecolor=background,
    )
    plt.close("all")
    return buffer.getvalue()


def sphere_grid(
    sky: np.ndarray,
    *,
    n_lon: int = 360,
    n_lat: int = 180,
) -> dict[str, list]:
    """Resample a HEALPix map onto a lon/lat grid for 3D rendering in the browser.

    Plotly draws surfaces from Cartesian arrays, so we return the unit-sphere coordinates
    alongside the temperature values. Sending the raw HEALPix array instead would push
    three million pixels down the wire and still need this interpolation client-side.
    """
    nside = hp.npix2nside(sky.size)

    lons = np.linspace(-180.0, 180.0, n_lon)
    lats = np.linspace(-90.0, 90.0, n_lat)
    lon_grid, lat_grid = np.meshgrid(lons, lats)

    pixels = hp.ang2pix(nside, lon_grid.ravel(), lat_grid.ravel(), lonlat=True)
    values = sky[pixels].reshape(lat_grid.shape)
    values = np.where(values == UNSEEN, np.nan, values)

    theta = np.radians(90.0 - lat_grid)
    phi = np.radians(lon_grid)
    x = np.sin(theta) * np.cos(phi)
    y = np.sin(theta) * np.sin(phi)
    z = np.cos(theta)

    finite = values[np.isfinite(values)]
    limit = float(np.percentile(np.abs(finite), 99.0)) if finite.size else 1.0

    return {
        "x": x.tolist(),
        "y": y.tolist(),
        "z": z.tolist(),
        "values": [
            [None if not np.isfinite(v) else round(float(v), 3) for v in row] for row in values
        ],
        "lon": lons.tolist(),
        "lat": lats.tolist(),
        "vmin": -limit,
        "vmax": limit,
        "n_lon": n_lon,
        "n_lat": n_lat,
    }
