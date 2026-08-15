"""CLI: look a word up the way the finished app will.

    python -m ruassist.cli стали
    python -m ruassist.cli рука --table

Accepts any inflected form, with or without stress marks, and Latin
transliteration for keyboards without Cyrillic (``ruka`` -> рука́).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .index import Candidate, FormIndex
from .lexicon import load_dir
from .morphology import canonical_tag
from .schema import POS
from .translit import to_cyrillic

CASES = [
    ("nomn", "主格"),
    ("gent", "属格"),
    ("datv", "与格"),
    ("accs", "宾格"),
    ("ablt", "工具格"),
    ("loct", "前置格"),
]

PERSONS = [("1per", "sing"), ("2per", "sing"), ("3per", "sing"),
           ("1per", "plur"), ("2per", "plur"), ("3per", "plur")]
PERSON_LABELS = ["я", "ты", "он/она́", "мы", "вы", "они́"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Look up a Russian word")
    parser.add_argument("query")
    parser.add_argument("--lexicon", type=Path, default=Path("data/lexicon"))
    parser.add_argument("--table", action="store_true", help="show the full paradigm")
    args = parser.parse_args(argv)

    lexicon, issues = load_dir(args.lexicon)
    if issues:
        print("lexicon has errors; run validate first")
        return 2

    index = FormIndex.build(lexicon)
    candidates = index.lookup(args.query)

    if not candidates:
        converted = to_cyrillic(args.query)
        if converted != args.query:
            candidates = index.lookup(converted)
            if candidates:
                print(f"（转写：{args.query} → {converted}）\n")

    if not candidates:
        print(f"未找到：{args.query}")
        return 1

    for i, candidate in enumerate(candidates):
        if i:
            print()
        _show(candidate, index, full=args.table)

    if len(candidates) > 1:
        print(f"\n※ 该词形有 {len(candidates)} 种解读，以上全部列出。")
    return 0


def _show(candidate: Candidate, index: FormIndex, *, full: bool) -> None:
    entry = candidate.entry
    header = f"{entry.stress}  [{entry.pos.value}]"
    if entry.aspect:
        header += f" {entry.aspect.value}"
        if entry.aspect_pair:
            header += f" ↔ {entry.aspect_pair}"
    if entry.gender:
        header += f" {entry.gender.value}/{entry.animacy.value}"
    if entry.zaliznyak:
        header += f"  «{entry.zaliznyak}»"
    print(header)

    if not candidate.is_lemma:
        print(f"  ← 查询词形：{candidate.form.text}  ({', '.join(sorted(candidate.form.tags))})")

    for n, sense in enumerate(entry.senses, 1):
        labels = f" [{', '.join(sense.labels)}]" if sense.labels else ""
        print(f"  {n}. {sense.zh}{labels}")
        for example in sense.examples[:2]:
            print(f"       {example.ru}")
            print(f"       {example.zh}")

    for label, text in (
        ("体", entry.aspect_note),
        ("常见错误", entry.common_errors),
        ("说明", entry.notes),
    ):
        if text:
            first = text.strip().splitlines()[0]
            print(f"  【{label}】{first}")

    if full:
        _table(candidate, index)


def _table(candidate: Candidate, index: FormIndex) -> None:
    paradigm = index.paradigm(candidate.entry)
    cells = paradigm.cells
    pos = candidate.entry.pos
    print()

    if pos is POS.NOUN:
        print(f"  {'':8} {'单数':<14} {'复数':<14}")
        for case, label in CASES:
            sg = cells.get(canonical_tag({"sing", case}))
            pl = cells.get(canonical_tag({"plur", case}))
            print(f"  {label:<8} {sg.text if sg else '—':<14} {pl.text if pl else '—':<14}")
    elif pos is POS.VERB:
        tense = "pres" if candidate.entry.aspect and candidate.entry.aspect.value == "impf" else "futr"
        for (person, number), label in zip(PERSONS, PERSON_LABELS):
            form = cells.get(canonical_tag({tense, person, number}))
            if form:
                print(f"  {label:<8} {form.text}")
        past = [cells.get(canonical_tag({"past", g})) for g in ("masc", "femn", "neut", "plur")]
        if any(past):
            print(f"  {'过去时':<8} " + " ".join(f.text for f in past if f))
        impr = [cells.get(canonical_tag({"impr", n})) for n in ("sing", "plur")]
        if any(impr):
            print(f"  {'命令式':<8} " + " ".join(f.text for f in impr if f))
    elif pos is POS.ADJ:
        for case, label in CASES[:5]:
            row = [
                cells.get(canonical_tag({"adjf", "sing", g, case}))
                for g in ("masc", "femn", "neut")
            ]
            plural = cells.get(canonical_tag({"adjf", "plur", case}))
            forms = " ".join(f.text for f in [*row, plural] if f)
            print(f"  {label:<8} {forms}")

    if not paradigm.generated:
        print(f"  （词形来自手写补充：{paradigm.reason}）")


if __name__ == "__main__":
    raise SystemExit(main())
