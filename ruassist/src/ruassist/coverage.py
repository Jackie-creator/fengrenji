"""CLI: report lexicon coverage against a target wordlist.

    python -m ruassist.coverage
    python -m ruassist.coverage --missing        # only what still needs writing

Bulk authoring needs a backbone: without a target list there is no way to say
how far along the lexicon is, or which words to write next.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from .lexicon import load_dir
from .stress import search_key


@dataclass
class Wordlist:
    name: str
    official: bool
    themes: dict[str, list[str]]

    @property
    def lemmas(self) -> list[str]:
        """All target lemmas, de-duplicated but keeping theme order."""
        seen: dict[str, None] = {}
        for words in self.themes.values():
            for word in words:
                seen.setdefault(word, None)
        return list(seen)


def load_wordlist(path: Path) -> Wordlist:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Wordlist(
        name=raw.get("name", path.stem),
        official=bool(raw.get("official", False)),
        themes=raw.get("themes", {}),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lexicon coverage report")
    parser.add_argument("--lexicon", type=Path, default=Path("data/lexicon"))
    parser.add_argument(
        "--wordlist",
        type=Path,
        default=Path("data/wordlists"),
        help="a wordlist file, or a directory of them (the default)",
    )
    parser.add_argument(
        "--missing", action="store_true", help="list only the missing lemmas"
    )
    args = parser.parse_args(argv)

    if args.wordlist.is_dir():
        paths = sorted(args.wordlist.glob("*.yaml"))
    elif args.wordlist.is_file():
        paths = [args.wordlist]
    else:
        print(f"wordlist not found: {args.wordlist}", file=sys.stderr)
        return 2
    if not paths:
        print(f"no wordlists in {args.wordlist}", file=sys.stderr)
        return 2

    lexicon, issues = load_dir(args.lexicon)
    if issues:
        print("lexicon has parse errors; run validate first", file=sys.stderr)
        return 2

    have = {search_key(e.lemma) for e in lexicon.entries}

    if args.missing:
        for path in paths:
            for lemma in load_wordlist(path).lemmas:
                if search_key(lemma) not in have:
                    print(lemma)
        return 0

    for n, path in enumerate(paths):
        if n:
            print()
        _report(load_wordlist(path), have, len(lexicon))
    return 0


def _report(wordlist, have: set[str], lexicon_size: int) -> None:

    print(f"目标词表：{wordlist.name}")
    if not wordlist.official:
        print("  ⚠ 自建词表，非官方考纲。拿到官方词表后需比对补齐。")
    print()

    for theme, words in wordlist.themes.items():
        done = sum(1 for w in words if search_key(w) in have)
        bar = _bar(done, len(words))
        print(f"  {theme:<12} {bar} {done:>3}/{len(words)}")

    targets = wordlist.lemmas
    covered = sum(1 for w in targets if search_key(w) in have)

    print()
    print(f"  词表覆盖   {covered}/{len(targets)}  ({covered / len(targets):.0%})")
    print(f"  词库总数   {lexicon_size}")


def _bar(done: int, total: int, width: int = 20) -> str:
    filled = round(width * done / total) if total else 0
    return "█" * filled + "·" * (width - filled)


if __name__ == "__main__":
    raise SystemExit(main())
