"""Command-line entry point for generating patterns without the API.

Example:
    python -m app.cli card_holder --slots 3 --leather 1.2 -o card_holder.svg
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .export.svg_export import pattern_to_svg
from .geometry.core import EdgeFinish
from .geometry.templates.card_holder import CardHolder, CardHolderParams


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="leatherpattern", description="Generate leather cutting patterns")
    sub = parser.add_subparsers(dest="template", required=True)

    ch = sub.add_parser("card_holder", help="simple card holder")
    ch.add_argument("--slots", type=int, default=3, help="number of card slots (1-3)")
    ch.add_argument("--leather", type=float, default=1.2, help="leather thickness in mm")
    ch.add_argument("--seam", type=float, default=3.5, help="seam allowance in mm (3-5)")
    ch.add_argument("--stagger", type=float, default=12.0, help="visible slot lip in mm (10-14)")
    ch.add_argument("--pitch", type=float, default=4.0, help="stitch pitch in mm")
    ch.add_argument(
        "--edge",
        choices=[e.value for e in EdgeFinish],
        default=EdgeFinish.BURNISHED.value,
        help="edge finish",
    )
    ch.add_argument("-o", "--output", type=Path, default=Path("card_holder.svg"))

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
        args.output.write_text(pattern_to_svg(pattern), encoding="utf-8")
        print(f"已生成 {pattern.name} -> {args.output}（{len(pattern.pieces)} 种裁片）")


if __name__ == "__main__":
    main()
