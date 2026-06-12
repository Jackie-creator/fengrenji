"""Command-line entry point for generating patterns without the API.

Examples:
    python -m app.cli card_holder --slots 3 --leather 1.2 -o card_holder.svg
    python -m app.cli bifold_wallet --slots-left 3 --slots-right 2 --format dxf
    python -m app.cli zipper_pouch --zipper 100 --style window
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .export.dxf_export import pattern_to_dxf_str
from .export.svg_export import pattern_to_svg
from .geometry.core import EdgeFinish, Pattern
from .geometry.templates.bifold_wallet import BifoldWallet, BifoldWalletParams
from .geometry.templates.card_holder import CardHolder, CardHolderParams
from .geometry.templates.zipper_pouch import ZipperPouch, ZipperPouchParams, ZipperStyle


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--leather", type=float, default=1.2, help="leather thickness in mm")
    parser.add_argument("--seam", type=float, default=3.5, help="seam allowance in mm (3-5)")
    parser.add_argument("--pitch", type=float, default=4.0, help="stitch pitch in mm")
    parser.add_argument(
        "--edge",
        choices=[e.value for e in EdgeFinish],
        default=EdgeFinish.BURNISHED.value,
        help="edge finish",
    )
    parser.add_argument("--format", choices=["svg", "dxf"], default="svg")
    parser.add_argument("-o", "--output", type=Path, default=None)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="leatherpattern", description="Generate leather cutting patterns")
    sub = parser.add_subparsers(dest="template", required=True)

    ch = sub.add_parser("card_holder", help="simple card holder")
    ch.add_argument("--slots", type=int, default=3, help="number of card slots (1-3)")
    ch.add_argument("--stagger", type=float, default=12.0, help="visible slot lip in mm (10-14)")
    _add_common(ch)

    bw = sub.add_parser("bifold_wallet", help="bifold short wallet")
    bw.add_argument("--slots-left", type=int, default=3, help="card slots on the left (0-3)")
    bw.add_argument("--slots-right", type=int, default=3, help="card slots on the right (0-3)")
    bw.add_argument("--stagger", type=float, default=12.0, help="visible slot lip in mm (10-14)")
    bw.add_argument("--bill-height", type=float, default=77.0, help="banknote height in mm")
    bw.add_argument("--fold-factor", type=float, default=3.0, help="fold-zone compensation factor")
    _add_common(bw)

    zp = sub.add_parser("zipper_pouch", help="zipper coin pouch")
    zp.add_argument("--width", type=float, default=120.0, help="body net width in mm")
    zp.add_argument("--height", type=float, default=85.0, help="body net height in mm")
    zp.add_argument("--zipper", type=float, default=100.0, help="nominal zipper length in mm")
    zp.add_argument(
        "--style",
        choices=[s.value for s in ZipperStyle],
        default=ZipperStyle.WINDOW.value,
        help="zipper installation style",
    )
    _add_common(zp)

    args = parser.parse_args(argv)

    if args.template == "card_holder":
        pattern = CardHolder(
            CardHolderParams(
                slots=args.slots,
                leather_thickness_mm=args.leather,
                seam_allowance_mm=args.seam,
                stagger_mm=args.stagger,
                stitch_pitch_mm=args.pitch,
                edge_finish=EdgeFinish(args.edge),
            )
        ).build()
    elif args.template == "bifold_wallet":
        pattern = BifoldWallet(
            BifoldWalletParams(
                slots_left=args.slots_left,
                slots_right=args.slots_right,
                leather_thickness_mm=args.leather,
                seam_allowance_mm=args.seam,
                stagger_mm=args.stagger,
                bill_height_mm=args.bill_height,
                fold_factor=args.fold_factor,
                stitch_pitch_mm=args.pitch,
                edge_finish=EdgeFinish(args.edge),
            )
        ).build()
    else:
        pattern = ZipperPouch(
            ZipperPouchParams(
                body_width_mm=args.width,
                body_height_mm=args.height,
                zipper_length_mm=args.zipper,
                style=ZipperStyle(args.style),
                leather_thickness_mm=args.leather,
                seam_allowance_mm=args.seam,
                stitch_pitch_mm=args.pitch,
                edge_finish=EdgeFinish(args.edge),
            )
        ).build()

    output: Path = args.output or Path(f"{args.template}.{args.format}")
    _write(pattern, output, args.format)
    print(f"已生成 {pattern.name} -> {output}（{len(pattern.pieces)} 种裁片）")


def _write(pattern: Pattern, output: Path, fmt: str) -> None:
    if fmt == "svg":
        output.write_text(pattern_to_svg(pattern), encoding="utf-8")
    else:
        output.write_text(pattern_to_dxf_str(pattern), encoding="utf-8")


if __name__ == "__main__":
    main()
