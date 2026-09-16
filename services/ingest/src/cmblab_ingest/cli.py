"""Command-line interface for the ingest service.

cmblab-ingest list
cmblab-ingest bootstrap
cmblab-ingest fetch wmap9 ilc-map --mask wmap9:mask-kq75
"""

from __future__ import annotations

import argparse
import sys

from .pipeline import ingest_product, load_mask
from .registry import BOOTSTRAP_PRODUCTS, DATASETS, get_dataset


def _print_progress(message: str, progress: float) -> None:
    bar = "#" * int(30 * progress)
    sys.stdout.write(f"\r  [{bar:<30}] {progress:5.1%}  {message[:45]:<45}")
    sys.stdout.flush()
    if progress >= 1.0:
        sys.stdout.write("\n")


def cmd_list(args: argparse.Namespace) -> int:
    datasets = [get_dataset(args.dataset)] if args.dataset else list(DATASETS)
    for dataset in datasets:
        print(f"\n{dataset.slug}  —  {dataset.name}")
        print(f"  {dataset.mission} · {dataset.release} · {dataset.archive} · {dataset.reference}")
        for product in dataset.products:
            size = f"{product.approx_mb:>7.1f} MB" if product.approx_mb else "        ?"
            print(f"    {product.slug:<22} {product.kind:<9} {size}   {product.notes}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    mask = None
    if args.mask:
        mask_dataset, _, mask_product = args.mask.partition(":")
        print(f"resolving mask {mask_dataset}/{mask_product}")
        mask = load_mask(mask_dataset, mask_product)

    result = ingest_product(
        args.dataset,
        args.product,
        field_index=args.field,
        nside_out=args.nside,
        gal_cut_deg=args.gal_cut,
        force=args.force,
        on_status=_print_progress,
    )
    if mask is not None:
        print("  note: mask supplied but applied during spectrum estimation, not ingest")

    print(result.summary())
    return 0 if result.gate_g2_passed is not False else 1


def cmd_bootstrap(args: argparse.Namespace) -> int:
    failures = 0
    for dataset_slug, product_slug in BOOTSTRAP_PRODUCTS:
        print(f"\n=== {dataset_slug}/{product_slug} ===")
        try:
            result = ingest_product(dataset_slug, product_slug, on_status=_print_progress)
            print(result.summary())
            if result.gate_g2_passed is False:
                failures += 1
        except Exception as exc:  # noqa: BLE001 - CLI reports, does not crash
            print(f"  FAILED: {exc}")
            failures += 1

    print(f"\nbootstrap complete, {failures} failure(s)")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cmblab-ingest", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="Show known datasets and products")
    p_list.add_argument("--dataset", help="Limit to one dataset slug")
    p_list.set_defaults(func=cmd_list)

    p_fetch = sub.add_parser("fetch", help="Download and clean one product")
    p_fetch.add_argument("dataset")
    p_fetch.add_argument("product")
    p_fetch.add_argument("--field", type=int, default=0, help="FITS column index (0 = I)")
    p_fetch.add_argument("--mask", help="Mask to load, as dataset:product")
    p_fetch.add_argument("--nside", type=int, help="Degrade to this Nside")
    p_fetch.add_argument("--gal-cut", type=float, default=30.0, help="|b| cut for dipole fit")
    p_fetch.add_argument("--force", action="store_true", help="Re-download even if cached")
    p_fetch.set_defaults(func=cmd_fetch)

    p_boot = sub.add_parser("bootstrap", help="Fetch the minimal working set (~75 MB)")
    p_boot.set_defaults(func=cmd_bootstrap)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
