"""Mollweide sky projections for the web UI.

Matplotlib runs headless inside the worker, so the Agg backend is selected before pyplot is
imported. Without this the worker crashes on macOS trying to reach a window server.
"""

from __future__ import annotations

import io as _io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import healpy as hp  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .io import UNSEEN  # noqa: E402

#: Percentile clip used when no explicit range is given. CMB maps have rare bright
#: foreground residuals that would otherwise flatten the whole colour scale.
_DEFAULT_CLIP_PERCENTILE = 99.0


def render_mollweide(
    sky: np.ndarray,
    *,
    title: str = "",
    unit: str = r"$\mu$K",
    vmin: float | None = None,
    vmax: float | None = None,
    cmap: str = "RdBu_r",
    graticule: bool = True,
    dpi: int = 110,
    output: str | Path | None = None,
) -> bytes:
    """Render a HEALPix map as a Mollweide PNG and return the encoded bytes.

    Symmetric colour limits are chosen by default so that zero sits at the centre of the
    diverging colormap — the standard way CMB temperature maps are presented.
    """
    sky = np.asarray(sky, dtype=np.float64)
    valid = sky[sky != UNSEEN]
    if vmin is None or vmax is None:
        limit = float(np.percentile(np.abs(valid), _DEFAULT_CLIP_PERCENTILE)) if valid.size else 1.0
        vmin = -limit if vmin is None else vmin
        vmax = limit if vmax is None else vmax

    # hp.mollview always builds its own figure; let it, then capture the current figure.
    plt.close("all")
    try:
        hp.mollview(
            sky,
            title=title,
            unit=unit,
            min=vmin,
            max=vmax,
            cmap=cmap,
            badcolor="0.85",
            bgcolor="white",
            cbar=True,
        )
        if graticule:
            hp.graticule(dpar=30, dmer=30, color="0.6", linewidth=0.4)

        fig = plt.gcf()
        buffer = _io.BytesIO()
        fig.savefig(buffer, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
        data = buffer.getvalue()
    finally:
        plt.close("all")

    if output is not None:
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)

    return data
