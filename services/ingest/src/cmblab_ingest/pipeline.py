"""End-to-end ingest: fetch a product from an archive, clean it, persist it.

This is Steps 4 and 5 of the build plan in one function. The worker calls
:func:`ingest_product`; the CLI calls it too, so there is exactly one code path.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from cmblab_core.config import get_settings
from cmblab_core.healpix import (
    clean_map,
    inspect_fits,
    read_healpix_map,
    render_mollweide,
    save_npz_map,
)

from .downloader import DownloadResult, download
from .registry import ProductSpec, get_product

StatusCallback = Callable[[str, float], None]

#: Residual dipole tolerance for archive maps that are already dipole-subtracted.
RESIDUAL_DIPOLE_TOL_UK = 50.0


@dataclass(slots=True)
class IngestResult:
    dataset_slug: str
    product_slug: str
    raw_path: Path
    download: DownloadResult
    clean_path: Path | None = None
    preview_path: Path | None = None
    nside: int | None = None
    report: dict[str, Any] = field(default_factory=dict)
    gate_g2_passed: bool | None = None
    gate_g2_detail: str = ""

    def summary(self) -> str:
        lines = [
            f"{self.dataset_slug}/{self.product_slug}",
            f"  raw       {self.raw_path.name}  ({self.download.mb:.1f} MB)",
            f"  sha256    {self.download.sha256[:16]}...",
        ]
        if self.clean_path:
            lines.append(f"  cleaned   {self.clean_path.name}  (Nside={self.nside})")
        if self.gate_g2_passed is not None:
            mark = "PASS" if self.gate_g2_passed else "FAIL"
            lines.append(f"  gate G2   {mark} — {self.gate_g2_detail}")
        return "\n".join(lines)


def _paths(dataset_slug: str, product: ProductSpec) -> tuple[Path, Path, Path]:
    data_dir = Path(get_settings().data_dir)
    raw = data_dir / "raw" / dataset_slug / product.filename
    stem = product.slug
    clean = data_dir / "clean" / dataset_slug / f"{stem}.npz"
    preview = data_dir / "previews" / dataset_slug / f"{stem}.png"
    return raw, clean, preview


def _check_gate_g2(report_dict: dict[str, Any], product: ProductSpec) -> tuple[bool, str]:
    """Gate G2 means different things depending on whether the archive removed the dipole.

    For a pre-subtracted map the correct assertion is that the *residual* dipole is small,
    not that we recover 3362 uK. See docs/data-sources.md section 4.
    """
    fit = report_dict.get("dipole_fit")
    if not fit:
        return False, "no dipole fit recorded"

    amplitude = fit["amplitude_uk"]

    if product.dipole_removed:
        passed = amplitude < RESIDUAL_DIPOLE_TOL_UK
        return passed, (
            f"residual dipole {amplitude:.1f} uK "
            f"({'<' if passed else '>='} {RESIDUAL_DIPOLE_TOL_UK:.0f} uK tolerance)"
        )

    separation = fit["separation_from_published_deg"]
    passed = abs(amplitude - 3362.08) < 150.0 and separation < 5.0
    return passed, (
        f"dipole {amplitude:.1f} uK at {separation:.2f} deg from the published direction"
    )


def ingest_product(
    dataset_slug: str,
    product_slug: str,
    *,
    field_index: int = 0,
    mask_path: str | Path | None = None,
    nside_out: int | None = None,
    gal_cut_deg: float = 30.0,
    make_preview: bool = True,
    force: bool = False,
    on_status: StatusCallback | None = None,
) -> IngestResult:
    """Download, clean, and store one archive product."""
    product = get_product(dataset_slug, product_slug)
    raw_path, clean_path, preview_path = _paths(dataset_slug, product)

    def status(message: str, progress: float) -> None:
        if on_status:
            on_status(message, progress)

    # ---- download ----------------------------------------------------------------
    status(f"downloading {product.filename}", 0.0)

    def report_progress(done: int, total: int | None) -> None:
        if total:
            status(f"downloading {product.filename}", 0.5 * done / total)

    if force:
        raw_path.unlink(missing_ok=True)

    result = download(product.url, raw_path, progress=report_progress)
    status(f"downloaded {result.mb:.1f} MB", 0.5)

    ingest = IngestResult(
        dataset_slug=dataset_slug,
        product_slug=product_slug,
        raw_path=raw_path,
        download=result,
    )

    # Text products (spectra, beams) need no HEALPix processing.
    if product.kind in {"spectrum", "beam"}:
        status("stored (tabular product, no cleaning required)", 1.0)
        return ingest

    # ---- clean -------------------------------------------------------------------
    status("reading FITS", 0.55)
    info = inspect_fits(raw_path)
    sky = read_healpix_map(raw_path, field=field_index)

    # A mask is a 0/1 indicator field, not a temperature field. Unit conversion and dipole
    # subtraction are meaningless for it and would corrupt it.
    if product.kind == "mask":
        status("binarising mask", 0.8)
        binary = (np.asarray(sky) > 0.5).astype(np.float64)
        save_npz_map(
            clean_path,
            binary,
            unit="dimensionless",
            coord_system=info.coord_system or "G",
            metadata={"kind": "mask", "f_sky": float(binary.mean())},
        )
        ingest.clean_path = clean_path
        ingest.nside = info.nside
        ingest.report = {"kind": "mask", "f_sky": float(binary.mean())}
        status(f"mask stored, f_sky = {binary.mean():.4f}", 1.0)
        return ingest

    unit = product.unit or (info.column_units[field_index] if info.column_units else "K_CMB")

    mask = None
    if mask_path is not None:
        mask = read_healpix_map(mask_path, field=0)

    status("cleaning: units, dipole, mask", 0.7)
    cleaned, report = clean_map(
        sky,
        unit=unit,
        mask=mask,
        remove_dipole=True,
        gal_cut_deg=gal_cut_deg,
        nside_out=nside_out,
    )
    report_dict = report.to_dict()

    # Masks are 0/1 indicator maps; dipole talk is meaningless for them.
    if product.kind == "map":
        passed, detail = _check_gate_g2(report_dict, product)
        ingest.gate_g2_passed = passed
        ingest.gate_g2_detail = detail

    status("saving cleaned map", 0.85)
    save_npz_map(
        clean_path,
        cleaned,
        nside=report.nside_out,
        unit="uK",
        coord_system=info.coord_system or "G",
        metadata=report_dict,
    )

    ingest.clean_path = clean_path
    ingest.nside = report.nside_out
    ingest.report = report_dict

    # ---- preview -----------------------------------------------------------------
    if make_preview:
        status("rendering Mollweide preview", 0.95)
        render_mollweide(
            cleaned,
            title=f"{dataset_slug} · {product_slug}",
            output=preview_path,
        )
        ingest.preview_path = preview_path

    status("done", 1.0)
    return ingest


def load_mask(dataset_slug: str, product_slug: str) -> np.ndarray:
    """Fetch a mask product if needed and return it as a 0/1 array."""
    product = get_product(dataset_slug, product_slug)
    raw_path, _, _ = _paths(dataset_slug, product)
    download(product.url, raw_path)
    mask = read_healpix_map(raw_path, field=0)
    return (mask > 0.5).astype(np.float64)
