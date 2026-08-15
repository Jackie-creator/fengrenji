"""CLI: compile the lexicon into the shipped offline package.

    python -m ruassist.build

Emits two artefacts from one source of truth:

* ``dist/dictionary.db``   -- SQLite, for desktop and any other consumer
* ``frontend/public/dictionary.json`` -- the bundle the web app caches

This is the step that makes the product offline. Paradigms are expanded here,
once, and the client only ever reads a lookup table -- no morphology engine, no
Python, no network. The size report exists because the bundle has to stay small
enough to cache on a phone; if it starts creeping, that shows up here before it
shows up on a user's data plan.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .index import FormIndex
from .lexicon import Lexicon, load_dir
from .morphology import inflect
from .schema import LexEntry


@dataclass
class Artefact:
    path: Path
    bytes_written: int

    @property
    def human(self) -> str:
        size = self.bytes_written
        for unit in ("B", "KB", "MB"):
            if size < 1024 or unit == "MB":
                return f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
            size /= 1024
        return f"{size:.1f} MB"


def entry_payload(entry: LexEntry, entry_id: int) -> dict:
    """Compact JSON shape. Keys are short because they repeat thousands of times."""
    paradigm = inflect(entry)
    payload = {
        "i": entry_id,
        "l": entry.lemma,
        "s": entry.stress,
        "p": entry.pos.value,
        "sen": [
            {
                "zh": sense.zh,
                **({"en": sense.en} if sense.en else {}),
                **({"lb": sense.labels} if sense.labels else {}),
                **({"col": sense.collocations} if sense.collocations else {}),
                **(
                    {"ex": [[e.ru, e.zh] for e in sense.examples]}
                    if sense.examples
                    else {}
                ),
            }
            for sense in entry.senses
        ],
        "f": {tag: form.text for tag, form in paradigm.cells.items()},
    }

    for key, value in (
        ("g", entry.gender), ("an", entry.animacy),
        ("asp", entry.aspect), ("tr", entry.transitivity),
        ("mg", entry.motion_group),
    ):
        if value is not None:
            payload[key] = value.value

    for key, value in (
        ("z", entry.zaliznyak), ("pair", entry.aspect_pair),
        ("gov", entry.government), ("mp", entry.motion_partner),
        ("cmp", entry.comparative), ("sup", entry.superlative),
        ("hom", entry.homonym_id), ("freq", entry.freq_rank),
        ("num", entry.number_only),
    ):
        if value is not None:
            payload[key] = value

    notes = {
        k: v
        for k, v in (
            ("aspect", entry.aspect_note),
            ("errors", entry.common_errors),
            ("notes", entry.notes),
        )
        if v
    }
    if notes:
        payload["n"] = notes
    if entry.level:
        payload["lv"] = entry.level
    if entry.synonyms or entry.antonyms:
        payload["rel"] = {"syn": entry.synonyms, "ant": entry.antonyms}
    if not paradigm.generated:
        payload["hand"] = True
    return payload


def build_bundle(lexicon: Lexicon, index: FormIndex) -> dict:
    ids = {id(entry): n for n, entry in enumerate(lexicon.entries)}
    entries = [entry_payload(e, ids[id(e)]) for e in lexicon.entries]

    forms: dict[str, list[int]] = {}
    for key in index.keys():
        forms[key] = sorted({ids[id(c.entry)] for c in index.lookup(key)})

    return {
        "version": __version__,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats": {
            "entries": len(entries),
            "forms": len(forms),
            "senses": sum(len(e["sen"]) for e in entries),
        },
        "entries": entries,
        "forms": forms,
    }


def write_json(bundle: dict, path: Path) -> Artefact:
    path.parent.mkdir(parents=True, exist_ok=True)
    # ensure_ascii=False keeps Cyrillic and Chinese as themselves, which is both
    # smaller and readable when debugging the bundle by eye.
    text = json.dumps(bundle, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")
    return Artefact(path, len(text.encode("utf-8")))


def write_sqlite(bundle: dict, path: Path) -> Artefact:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)

    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE entries (
            id INTEGER PRIMARY KEY,
            lemma TEXT NOT NULL,
            stress TEXT NOT NULL,
            pos TEXT NOT NULL,
            payload TEXT NOT NULL
        );
        CREATE TABLE forms (
            form TEXT NOT NULL,
            entry_id INTEGER NOT NULL REFERENCES entries(id)
        );
        CREATE INDEX idx_forms_form ON forms(form);
        CREATE INDEX idx_entries_lemma ON entries(lemma);
        """
    )
    connection.executemany(
        "INSERT INTO meta VALUES (?, ?)",
        [("version", bundle["version"]), ("generated", bundle["generated"])],
    )
    connection.executemany(
        "INSERT INTO entries VALUES (?, ?, ?, ?, ?)",
        [
            (e["i"], e["l"], e["s"], e["p"], json.dumps(e, ensure_ascii=False))
            for e in bundle["entries"]
        ],
    )
    connection.executemany(
        "INSERT INTO forms VALUES (?, ?)",
        [(form, i) for form, ids in bundle["forms"].items() for i in ids],
    )
    connection.commit()
    connection.execute("VACUUM")
    connection.close()
    return Artefact(path, path.stat().st_size)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the offline dictionary package")
    parser.add_argument("--lexicon", type=Path, default=Path("data/lexicon"))
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument(
        "--frontend",
        type=Path,
        default=Path("frontend/public/dictionary.json"),
        help="where the web app expects its bundle",
    )
    args = parser.parse_args(argv)

    lexicon, issues = load_dir(args.lexicon)
    errors = [i for i in issues if i.level == "error"]
    if errors:
        for issue in errors:
            print(issue)
        print("\nbuild aborted: fix the lexicon first")
        return 1

    index = FormIndex.build(lexicon)
    bundle = build_bundle(lexicon, index)

    artefacts = [
        write_json(bundle, args.frontend),
        write_sqlite(bundle, args.dist / "dictionary.db"),
    ]

    stats = bundle["stats"]
    print(f"词条 {stats['entries']}　义项 {stats['senses']}　词形 {stats['forms']}")
    for artefact in artefacts:
        print(f"  {str(artefact.path):40} {artefact.human:>10}")

    hand = sum(1 for e in bundle["entries"] if e.get("hand"))
    print(f"\n生成 {stats['entries'] - hand} 条，手写补充 {hand} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
