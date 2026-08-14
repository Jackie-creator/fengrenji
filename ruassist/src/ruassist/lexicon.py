"""Loading and whole-lexicon validation.

Per-entry rules live in :mod:`ruassist.schema`. This module adds the checks that
only make sense across the entire lexicon -- reciprocal links, duplicate keys,
dangling references.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .schema import POS, LexEntry
from .stress import search_key


@dataclass
class Issue:
    level: str  # "error" | "warning"
    entry: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level:7}] {self.entry}: {self.message}"


@dataclass
class Lexicon:
    entries: list[LexEntry] = field(default_factory=list)

    def by_lemma(self, lemma: str) -> list[LexEntry]:
        target = search_key(lemma)
        return [e for e in self.entries if search_key(e.lemma) == target]

    def __len__(self) -> int:
        return len(self.entries)


def load_dir(path: Path) -> tuple[Lexicon, list[Issue]]:
    """Load every ``*.yaml`` under ``path``, returning entries and parse errors."""
    lexicon = Lexicon()
    issues: list[Issue] = []

    for file in sorted(path.glob("*.yaml")):
        raw = yaml.safe_load(file.read_text(encoding="utf-8")) or []
        if not isinstance(raw, list):
            issues.append(Issue("error", file.name, "top level must be a list"))
            continue
        for i, item in enumerate(raw):
            label = f"{file.name}[{i}]"
            try:
                lexicon.entries.append(LexEntry.model_validate(item))
            except Exception as exc:  # pydantic ValidationError or ValueError
                lemma = item.get("lemma", "?") if isinstance(item, dict) else "?"
                issues.append(Issue("error", f"{label} {lemma}", str(exc)))

    return lexicon, issues


def check(lexicon: Lexicon) -> list[Issue]:
    """Run cross-entry consistency checks."""
    issues: list[Issue] = []
    seen: dict[str, LexEntry] = {}
    known = {search_key(e.lemma) for e in lexicon.entries}

    for entry in lexicon.entries:
        if entry.key in seen:
            issues.append(
                Issue(
                    "error",
                    entry.lemma,
                    f"duplicate key {entry.key!r}; set homonym_id to distinguish",
                )
            )
        seen[entry.key] = entry

    for entry in lexicon.entries:
        issues.extend(_check_aspect(entry, lexicon, known))
        issues.extend(_check_motion(entry, lexicon, known))
        issues.extend(_check_verify(entry))

    return issues


def _check_aspect(entry: LexEntry, lexicon: Lexicon, known: set[str]) -> list[Issue]:
    if entry.pos is not POS.VERB or entry.aspect_pair is None:
        return []

    key = search_key(entry.aspect_pair)
    if key not in known:
        # The sample lexicon is deliberately partial, so this is not fatal.
        return [
            Issue("warning", entry.lemma, f"aspect_pair {entry.aspect_pair!r} not in lexicon")
        ]

    issues: list[Issue] = []
    for partner in lexicon.by_lemma(entry.aspect_pair):
        if partner.pos is not POS.VERB:
            continue
        if partner.aspect_pair is None or search_key(partner.aspect_pair) != search_key(
            entry.lemma
        ):
            issues.append(
                Issue(
                    "error",
                    entry.lemma,
                    f"aspect_pair not reciprocal: {partner.lemma} points to "
                    f"{partner.aspect_pair!r}",
                )
            )
        if partner.aspect == entry.aspect:
            issues.append(
                Issue(
                    "error",
                    entry.lemma,
                    f"aspect_pair {partner.lemma} has the same aspect ({entry.aspect})",
                )
            )
    return issues


def _check_motion(entry: LexEntry, lexicon: Lexicon, known: set[str]) -> list[Issue]:
    if entry.motion_partner is None:
        return []
    if search_key(entry.motion_partner) not in known:
        return [
            Issue(
                "warning",
                entry.lemma,
                f"motion_partner {entry.motion_partner!r} not in lexicon",
            )
        ]
    issues: list[Issue] = []
    for partner in lexicon.by_lemma(entry.motion_partner):
        if partner.motion_partner is None or search_key(
            partner.motion_partner
        ) != search_key(entry.lemma):
            issues.append(
                Issue("error", entry.lemma, f"motion_partner not reciprocal with {partner.lemma}")
            )
    return issues


def _check_verify(entry: LexEntry) -> list[Issue]:
    valid = set(LexEntry.model_fields)
    unknown = set(entry.verify) - valid
    if unknown:
        return [
            Issue("error", entry.lemma, f"verify names non-existent fields: {sorted(unknown)}")
        ]
    return []
