"""CLI: validate the hand-authored lexicon.

    python -m ruassist.validate data/lexicon

Exits non-zero if any error-level issue is found, so it can gate a build.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from .lexicon import check, load_dir
from .schema import POS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the ruassist lexicon")
    parser.add_argument("path", type=Path, nargs="?", default=Path("data/lexicon"))
    parser.add_argument(
        "--strict", action="store_true", help="treat warnings as errors"
    )
    args = parser.parse_args(argv)

    if not args.path.is_dir():
        print(f"not a directory: {args.path}", file=sys.stderr)
        return 2

    lexicon, issues = load_dir(args.path)
    issues += check(lexicon)

    for issue in issues:
        print(issue, file=sys.stderr if issue.level == "error" else sys.stdout)

    _summary(lexicon)

    errors = sum(1 for i in issues if i.level == "error")
    warnings = sum(1 for i in issues if i.level == "warning")
    print(f"\n{len(lexicon)} entries, {errors} errors, {warnings} warnings")

    if errors or (args.strict and warnings):
        return 1
    return 0


def _summary(lexicon) -> None:
    by_pos = Counter(e.pos.value for e in lexicon.entries)
    needs_verify = [e for e in lexicon.entries if e.verify]
    overridden = [e for e in lexicon.entries if e.form_overrides]

    print("\n-- lexicon summary --")
    for pos in POS:
        if by_pos.get(pos.value):
            print(f"  {pos.value:8} {by_pos[pos.value]:4}")
    print(f"  {'senses':8} {sum(len(e.senses) for e in lexicon.entries):4}")
    print(
        f"  {'examples':8} "
        f"{sum(len(s.examples) for e in lexicon.entries for s in e.senses):4}"
    )
    print(f"\n  entries with hand-written forms : {len(overridden)}")
    print(f"  entries pending cross-check     : {len(needs_verify)}")
    if needs_verify:
        for entry in needs_verify:
            print(f"    - {entry.lemma:12} {', '.join(entry.verify)}")


if __name__ == "__main__":
    raise SystemExit(main())
