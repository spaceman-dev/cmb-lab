"""CLI for the spectrum service.

cmblab-spectrum estimate wmap9 ilc-map --mask wmap9:mask-kq75 --beam-fwhm 60
"""

from __future__ import annotations

import argparse

from .pipeline import run_cross_spectrum, run_spectrum, save_bandpowers
from .references import available_references, load_reference


def _report(run, show: int, output: str | None) -> int:
    spectrum = run.spectrum
    print(f"\n  estimator       {'cross-spectrum' if spectrum.is_cross else 'auto-spectrum'}")
    if spectrum.meta.get("beams"):
        for label in spectrum.meta["beams"]:
            print(f"  beam            {label}")
    print(f"  f_sky           {spectrum.f_sky:.4f}")
    print(f"  lmax requested  {spectrum.lmax}")
    print(f"  lmax reliable   {spectrum.reliable_lmax}")
    print(f"  bandpowers      {len(run.bandpowers)}")
    if run.point_source_fit:
        print(f"  point sources   {run.point_source_fit.summary()}")

    print(f"\n  GATE G3  {'PASS' if run.gate_g3_passed else 'FAIL'}")
    print(f"    {run.gate_g3_detail}")

    if run.comparisons:
        print("\n  GATE G4")
        for comparison in run.comparisons.values():
            print(f"    {comparison.summary()}")

    print("\n  bandpowers (l_eff, D_l +/- err, uK^2)")
    for band in run.bandpowers[:show]:
        err = f" +/- {band.dl_err_uk2:7.1f}" if band.dl_err_uk2 else ""
        print(f"    {band.ell_eff:7.1f}  {band.dl_uk2:9.1f}{err}")

    if output:
        print(f"\n  saved {save_bandpowers(run, output)}")

    return 0 if run.gate_g3_passed else 1


def cmd_estimate(args: argparse.Namespace) -> int:
    mask_dataset = mask_product = None
    if args.mask:
        mask_dataset, _, mask_product = args.mask.partition(":")

    print(f"estimating auto-spectrum for {args.dataset}/{args.product}")
    if mask_product:
        print(f"  mask        {mask_dataset}/{mask_product}")

    run = run_spectrum(
        args.dataset,
        args.product,
        mask_dataset=mask_dataset,
        mask_product=mask_product,
        lmax=args.lmax,
        beam_fwhm_arcmin=args.beam_fwhm,
        binning=args.binning,
    )
    return _report(run, args.show, args.output)


def cmd_cross(args: argparse.Namespace) -> int:
    mask_dataset = mask_product = None
    if args.mask:
        mask_dataset, _, mask_product = args.mask.partition(":")

    print(f"cross-spectrum {args.dataset}: {args.product_a} x {args.product_b}")
    if mask_product:
        print(f"  mask        {mask_dataset}/{mask_product}")

    run = run_cross_spectrum(
        args.dataset,
        args.product_a,
        args.product_b,
        mask_dataset=mask_dataset,
        mask_product=mask_product,
        lmax=args.lmax,
        binning=args.binning,
        subtract_point_sources=not args.no_point_source_correction,
    )
    return _report(run, args.show, args.output)


def cmd_references(args: argparse.Namespace) -> int:
    for slug in available_references():
        try:
            reference = load_reference(slug)
        except FileNotFoundError as exc:
            print(f"{slug:24s} NOT DOWNLOADED — {exc}")
            continue
        peak_ell, peak_dl = reference.first_peak()
        print(
            f"{slug:24s} {reference.mission:8s} {reference.ell.size:4d} bins  "
            f"l={reference.ell.min():.0f}-{reference.ell.max():.0f}  "
            f"peak1 l={peak_ell:.0f} D_l={peak_dl:.0f} uK^2"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cmblab-spectrum", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_est = sub.add_parser("estimate", help="Estimate a power spectrum from a cleaned map")
    p_est.add_argument("dataset")
    p_est.add_argument("product")
    p_est.add_argument("--mask", help="Mask as dataset:product")
    p_est.add_argument("--lmax", type=int, default=600)
    p_est.add_argument(
        "--beam-fwhm",
        type=float,
        help="Gaussian beam FWHM in arcmin to deconvolve (WMAP ILC is 60)",
    )
    p_est.add_argument("--binning", default="linear:30")
    p_est.add_argument("--show", type=int, default=15, help="Bandpowers to print")
    p_est.add_argument("--output", help="Write bandpowers to this .npz path")
    p_est.set_defaults(func=cmd_estimate)

    p_cross = sub.add_parser(
        "cross", help="Cross-spectrum of two maps (noise-unbiased, the correct estimator)"
    )
    p_cross.add_argument("dataset")
    p_cross.add_argument("product_a")
    p_cross.add_argument("product_b")
    p_cross.add_argument("--mask", help="Mask as dataset:product")
    p_cross.add_argument("--lmax", type=int, default=800)
    p_cross.add_argument("--binning", default="linear:30")
    p_cross.add_argument("--show", type=int, default=15)
    p_cross.add_argument(
        "--no-point-source-correction",
        action="store_true",
        help="Skip the unresolved point source subtraction",
    )
    p_cross.add_argument("--output", help="Write bandpowers to this .npz path")
    p_cross.set_defaults(func=cmd_cross)

    p_ref = sub.add_parser("references", help="List published reference spectra")
    p_ref.set_defaults(func=cmd_references)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
