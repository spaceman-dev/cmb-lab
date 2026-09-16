"""HTTP API for the catalog service: what data exists, and what we did to it."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import numpy as np
from cmblab_core.config import get_settings
from cmblab_core.service import create_app
from cmblab_ingest.registry import DATASETS, get_dataset, get_product
from fastapi.responses import FileResponse

app = create_app(
    service_name="catalog",
    description="Registry of CMB archive datasets, products, and cleaned map artifacts.",
)


def _data_dir() -> Path:
    return Path(get_settings().data_dir)


def _product_payload(dataset_slug: str, product) -> dict[str, Any]:
    raw = _data_dir() / "raw" / dataset_slug / product.filename
    clean = _data_dir() / "clean" / dataset_slug / f"{product.slug}.npz"

    return {
        "slug": product.slug,
        "kind": product.kind,
        "url": product.url,
        "filename": product.filename,
        "unit": product.unit,
        "nside": product.nside,
        "frequency_ghz": product.frequency_ghz,
        "component_method": product.component_method,
        "approx_mb": product.approx_mb,
        "dipole_removed": product.dipole_removed,
        "beam_product": product.beam_product,
        "notes": product.notes,
        "downloaded": raw.exists(),
        "size_bytes": raw.stat().st_size if raw.exists() else None,
        "cleaned": clean.exists(),
    }


@app.get("/datasets", tags=["catalog"])
async def list_datasets() -> dict[str, Any]:
    return {
        "datasets": [
            {
                "slug": d.slug,
                "name": d.name,
                "mission": d.mission,
                "release": d.release,
                "archive": d.archive,
                "reference": d.reference,
                "description": d.description,
                "n_products": len(d.products),
                "n_downloaded": sum(
                    1 for p in d.products if (_data_dir() / "raw" / d.slug / p.filename).exists()
                ),
            }
            for d in DATASETS
        ]
    }


@app.get("/datasets/{dataset_slug}/products", tags=["catalog"])
async def list_products(dataset_slug: str, kind: str | None = None) -> dict[str, Any]:
    dataset = get_dataset(dataset_slug)
    products = [p for p in dataset.products if kind is None or p.kind == kind]
    return {
        "dataset": dataset.slug,
        "products": [_product_payload(dataset.slug, p) for p in products],
    }


@app.get("/datasets/{dataset_slug}/products/{product_slug}", tags=["catalog"])
async def get_product_detail(dataset_slug: str, product_slug: str) -> dict[str, Any]:
    return _product_payload(dataset_slug, get_product(dataset_slug, product_slug))


@app.get("/maps", tags=["maps"])
async def list_maps() -> dict[str, Any]:
    entries = []
    for path in sorted((_data_dir() / "clean").glob("*/*.npz")):
        entries.append({"dataset": path.parent.name, "product": path.stem})
    return {"maps": entries}


@app.get("/maps/{dataset_slug}/{product_slug}/stats", tags=["maps"])
async def map_stats(dataset_slug: str, product_slug: str) -> dict[str, Any]:
    """Cleaning provenance and gate G2 statistics for a cleaned map."""
    path = _data_dir() / "clean" / dataset_slug / f"{product_slug}.npz"
    if not path.exists():
        raise FileNotFoundError(f"No cleaned map at {path}")

    with np.load(path, allow_pickle=False) as data:
        sky = data["sky"]
        nside = int(data["nside"])
        unit = str(data["unit"])
        coord = str(data["coord_system"])
        raw_meta = str(data["metadata"])

    try:
        metadata = ast.literal_eval(raw_meta)
    except (ValueError, SyntaxError):
        metadata = {}

    valid = sky[sky > -1e29]
    return {
        "dataset": dataset_slug,
        "product": product_slug,
        "nside": nside,
        "npix": int(sky.size),
        "unit": unit,
        "coord_system": coord,
        "statistics": {
            "mean": float(valid.mean()) if valid.size else None,
            "rms": float(valid.std()) if valid.size else None,
            "min": float(valid.min()) if valid.size else None,
            "max": float(valid.max()) if valid.size else None,
            "masked_fraction": float(1.0 - valid.size / sky.size),
        },
        "provenance": metadata,
    }


@app.get("/maps/{dataset_slug}/{product_slug}/preview.png", tags=["maps"])
async def map_preview(dataset_slug: str, product_slug: str) -> FileResponse:
    """Mollweide projection rendered during ingest."""
    path = _data_dir() / "previews" / dataset_slug / f"{product_slug}.png"
    if not path.exists():
        raise FileNotFoundError(f"No preview at {path}")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "max-age=3600"})
