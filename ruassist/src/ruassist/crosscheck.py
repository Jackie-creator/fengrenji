"""CLI: verify generated forms against OpenCorpora via pymorphy3.

    python -m ruassist.crosscheck
    python -m ruassist.crosscheck --lemma рука

This is the mechanism promised when entries were first written: paradigm indices
I was unsure of were flagged in ``verify`` rather than asserted, and this tool is
what settles them. OpenCorpora has authoritative *forms* but no stress at all,
so the division is exact -- it adjudicates spelling, we own stress.

pymorphy3 is a development dependency only. The shipped product contains the
expanded tables, not the analyser.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .lexicon import load_dir
from .morphology import INFLECTED, inflect, parse_tag
from .schema import POS, LexEntry
from .stress import fold_yo, strip_stress

#: Grammemes both sides express identically. Everything else (our `adjf`, our
#: anim/inan accusative split) is skipped rather than guessed at.
COMPARABLE = frozenset(
    {
        "sing", "plur",
        "nomn", "gent", "datv", "accs", "ablt", "loct",
        "masc", "femn", "neut",
        "1per", "2per", "3per",
        "pres", "past", "futr", "impr",
    }
)

SKIP_IF_PRESENT = frozenset({"anim", "inan", "lemma", "infn", "gen2", "loc2", "voct"})

#: Cells where we knowingly differ from OpenCorpora, with the reason. Kept
#: deliberately short: each line is a claim that our data is right and theirs is
#: not applicable, so it has to be argued, not just silenced.
ACCEPTED_DIVERGENCES = {
    ("голова", "accs,plur"): (
        "OpenCorpora 收了 голова 的动物性义项（牲畜头数、人头），因此宾格复数给 голов。"
        "我们的词条只收身体部位义，是非动物名词，宾格复数与主格同形 го́ловы。"
    ),
    ("мечта", "gent,plur"): (
        "мечта 的复数第二格在规范语里是 мечта́ний（借自 мечта́ние）；"
        "OpenCorpora 给的 мечт 形式上成立，但辞书与教学一致推荐 мечта́ний，"
        "面向学习者应当给推荐形式。"
    ),
}

_POS_TAGS = {POS.NOUN: "NOUN", POS.VERB: {"VERB", "INFN"}, POS.ADJ: "ADJF"}

GENDERS = frozenset({"masc", "femn", "neut"})


def comparable_for(pos: POS) -> frozenset[str]:
    """Gender is inherent on a noun but agreeing on an adjective.

    OpenCorpora tags a noun with its own gender (го́род is masc in every cell),
    while our noun paradigm carries only number and case. Comparing the two
    directly makes every key miss, so gender is dropped from the noun key on
    both sides. Adjectives and past-tense verbs really do vary by gender, so
    there it is kept.
    """
    return COMPARABLE - GENDERS if pos is POS.NOUN else COMPARABLE


@dataclass
class Mismatch:
    lemma: str
    tag: str
    ours: str
    theirs: set[str]


@dataclass
class Report:
    checked: int = 0
    cells: int = 0
    agreed: int = 0
    accepted: int = 0
    unknown: list[str] = None
    mismatches: list[Mismatch] = None
    ungenerated: list[tuple[str, str]] = None

    def __post_init__(self):
        self.unknown = self.unknown or []
        self.mismatches = self.mismatches or []
        self.ungenerated = self.ungenerated or []


def _key(word: str) -> str:
    return fold_yo(strip_stress(word)).lower()


def _lexeme(morph, entry: LexEntry) -> dict[frozenset[str], set[str]]:
    """All OpenCorpora forms for this lemma, keyed by comparable grammemes."""
    wanted = _POS_TAGS.get(entry.pos)
    comparable = comparable_for(entry.pos)
    table: dict[frozenset[str], set[str]] = {}
    for parse_result in morph.parse(_key(entry.lemma)):
        if _key(parse_result.normal_form) != _key(entry.lemma):
            continue
        pos = parse_result.tag.POS
        if isinstance(wanted, set):
            if pos not in wanted:
                continue
        elif pos != wanted:
            continue
        for form in parse_result.lexeme:
            grammemes = frozenset(str(g) for g in form.tag.grammemes) & comparable
            if grammemes:
                table.setdefault(grammemes, set()).add(_key(form.word))
    return table


def check_entry(morph, entry: LexEntry, report: Report) -> None:
    paradigm = inflect(entry)
    if not paradigm.generated:
        report.ungenerated.append((entry.lemma, paradigm.reason or ""))
        return

    table = _lexeme(morph, entry)
    if not table:
        report.unknown.append(entry.lemma)
        return

    report.checked += 1
    comparable_set = comparable_for(entry.pos)
    for tag, form in paradigm.cells.items():
        tags = parse_tag(tag)
        if tags & SKIP_IF_PRESENT:
            continue
        comparable = tags & comparable_set
        if not comparable:
            continue
        theirs = table.get(comparable)
        if theirs is None:
            continue
        report.cells += 1
        if form.plain in theirs:
            report.agreed += 1
        elif (entry.lemma, tag) in ACCEPTED_DIVERGENCES:
            report.accepted += 1
        else:
            report.mismatches.append(
                Mismatch(entry.lemma, tag, form.plain, theirs)
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cross-check forms against OpenCorpora")
    parser.add_argument("--lexicon", type=Path, default=Path("data/lexicon"))
    parser.add_argument("--lemma", help="check a single lemma")
    parser.add_argument(
        "--verify-only", action="store_true", help="only entries flagged in `verify`"
    )
    args = parser.parse_args(argv)

    try:
        import pymorphy3
    except ImportError:
        print("pymorphy3 not installed: pip install -e '.[dev]'", file=sys.stderr)
        return 2

    lexicon, issues = load_dir(args.lexicon)
    if issues:
        print("lexicon has errors; run validate first", file=sys.stderr)
        return 2

    entries = [e for e in lexicon.entries if e.pos in INFLECTED]
    if args.lemma:
        entries = [e for e in entries if _key(e.lemma) == _key(args.lemma)]
    if args.verify_only:
        entries = [e for e in entries if e.verify]

    morph = pymorphy3.MorphAnalyzer()
    report = Report()
    for entry in entries:
        check_entry(morph, entry, report)

    _print(report, entries)
    return 1 if report.mismatches else 0


def _print(report: Report, entries: list[LexEntry]) -> None:
    if report.mismatches:
        print("-- 与 OpenCorpora 不一致 --")
        for m in sorted(report.mismatches, key=lambda m: m.lemma):
            print(f"  {m.lemma:14} {m.tag:20} 我们: {m.ours:16} OpenCorpora: {sorted(m.theirs)}")
        print()

    if report.ungenerated:
        print("-- 未生成（走 form_overrides）--")
        by_reason = Counter(r.split(":", 1)[-1].strip() for _, r in report.ungenerated)
        for reason, count in by_reason.most_common():
            print(f"  {count:3}  {reason}")
        print()

    if report.unknown:
        print(f"-- OpenCorpora 无此词元 --\n  {', '.join(sorted(report.unknown))}\n")

    rate = report.agreed / report.cells if report.cells else 0
    print(f"词条 {len(entries)}，其中生成 {report.checked}，未生成 {len(report.ungenerated)}")
    print(
        f"比对词形 {report.cells}，一致 {report.agreed}（{rate:.1%}），"
        f"已知差异 {report.accepted}，不一致 {len(report.mismatches)}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
