"""CLI for the cosmology service.

cmblab-cosmology theory --H0 70
cmblab-cosmology fit --steps 1200
"""

from __future__ import annotations

import argparse
import sys

from .pipeline import run_inference
from .theory import PARAM_LABELS, theory_spectrum


def _progress(fraction: float, message: str) -> None:
    bar = "#" * int(30 * fraction)
    sys.stdout.write(f"\r  [{bar:<30}] {fraction:5.1%}  {message[:40]:<40}")
    sys.stdout.flush()
    if fraction >= 1.0:
        sys.stdout.write("\n")


def cmd_theory(args: argparse.Namespace) -> int:
    theory = theory_spectrum(
        {
            "H0": args.H0,
            "ombh2": args.ombh2,
            "omch2": args.omch2,
            "tau": args.tau,
            "ns": args.ns,
        },
        lmax=args.lmax,
    )
    peak_ell, peak_dl = theory.first_peak()

    print(f"first peak   l = {peak_ell},  D_l = {peak_dl:.0f} uK^2")
    print("\nderived parameters")
    for name, value in theory.derived.items():
        print(f"  {PARAM_LABELS.get(name, name):<18} {value:.5f}")
    return 0


def cmd_fit(args: argparse.Namespace) -> int:
    print(f"fitting {args.free} to {args.product_a} x {args.product_b}")
    run = run_inference(
        product_a=args.product_a,
        product_b=args.product_b,
        free_params=tuple(args.free),
        n_walkers=args.walkers,
        n_steps=args.steps,
        ell_min=args.ell_min,
        progress=_progress,
    )
    result = run.result

    print(f"\n  acceptance      {result.acceptance_fraction:.3f}")
    print(f"  autocorr time   {result.autocorr_time}")
    print(f"  best chi2/dof   {result.chi2_per_dof:.3f}  ({result.best_chi2:.1f}/{result.dof})")

    print("\n  posterior")
    for summary in {**result.summaries, **result.derived_summaries}.values():
        print(f"    {summary.label:<20} {summary.mean:9.5f} +/- {summary.std:.5f}")

    print(f"\n  GATE G5  {'PASS' if run.gate_g5_passed else 'FAIL'}")
    print(f"    {run.gate_g5_detail}")
    print("\n    parameter            ours                 Planck 2018          tension")
    for c in run.comparisons.values():
        mark = "ok" if c.consistent else "!!"
        print(
            f"    {c.label:<18} {c.ours:9.4f}+/-{c.ours_err:<8.4f} "
            f"{c.published:9.4f}+/-{c.published_err:<8.4f} {c.tension_sigma:5.2f}σ {mark}"
        )

    return 0 if run.gate_g5_passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cmblab-cosmology", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_theory = sub.add_parser("theory", help="Compute a LCDM theory spectrum")
    p_theory.add_argument("--H0", type=float, default=67.36)
    p_theory.add_argument("--ombh2", type=float, default=0.02237)
    p_theory.add_argument("--omch2", type=float, default=0.1200)
    p_theory.add_argument("--tau", type=float, default=0.0544)
    p_theory.add_argument("--ns", type=float, default=0.9649)
    p_theory.add_argument("--lmax", type=int, default=2500)
    p_theory.set_defaults(func=cmd_theory)

    p_fit = sub.add_parser("fit", help="Run MCMC against our measured bandpowers")
    p_fit.add_argument("--product-a", default="da-v1")
    p_fit.add_argument("--product-b", default="da-v2")
    p_fit.add_argument("--free", nargs="+", default=["H0", "ombh2", "omch2"])
    p_fit.add_argument("--walkers", type=int, default=24)
    p_fit.add_argument("--steps", type=int, default=1200)
    p_fit.add_argument("--ell-min", type=int, default=30)
    p_fit.set_defaults(func=cmd_fit)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
