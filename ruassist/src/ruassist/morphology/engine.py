"""The `inflect()` entry point promised by docs/SCHEMA.md.

Contract, restated:

1. Every generated form carries a stress mark.
2. ``form_overrides`` replace generated cells rather than adding to them.
3. Failure names the entry; a partial paradigm is never returned silently.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..schema import POS, LexEntry
from ..stress import STRESS, count_vowels, normalize
from .adjectives import inflect_adjective
from .forms import Form, canonical_tag, parse_tag
from .nouns import inflect_noun
from .verbs import inflect_verb
from .zaliznyak import UnsupportedIndex

#: Parts of speech with a productive paradigm the engine can expand.
INFLECTED = {POS.NOUN, POS.VERB, POS.ADJ}


@dataclass
class Paradigm:
    lemma: str
    pos: POS
    cells: dict[str, Form] = field(default_factory=dict)
    generated: bool = True
    reason: str | None = None

    @property
    def forms(self) -> list[Form]:
        return list(self.cells.values())

    def __len__(self) -> int:
        return len(self.cells)


def inflect(entry: LexEntry) -> Paradigm:
    """Expand an entry into its paradigm, overrides applied last."""
    generated: dict[str, Form] = {}
    generated_ok = True
    reason: str | None = None

    if entry.pos in INFLECTED:
        try:
            if entry.pos is POS.NOUN:
                generated = inflect_noun(entry)
            elif entry.pos is POS.ADJ:
                generated = inflect_adjective(entry)
            else:
                generated = inflect_verb(entry)
        except UnsupportedIndex as exc:
            generated_ok = False
            reason = str(exc)
    else:
        generated_ok = False
        reason = f"{entry.pos.value} has no productive paradigm"

    cells = dict(generated)
    for tag, text in entry.form_overrides.items():
        tags = parse_tag(tag)
        cells[canonical_tag(tags)] = Form.make(text, tags)

    if not cells:
        cells[canonical_tag({"lemma"})] = Form.make(entry.stress, {"lemma"})

    _assert_stressed(entry, cells)
    return Paradigm(
        lemma=entry.lemma,
        pos=entry.pos,
        cells=cells,
        generated=generated_ok,
        reason=reason,
    )


def _assert_stressed(entry: LexEntry, cells: dict[str, Form]) -> None:
    """Rule 1 of the contract, enforced rather than trusted."""
    for tag, form in cells.items():
        text = normalize(form.text)
        if count_vowels(text) > 1 and STRESS not in text and "ё" not in text:
            raise ValueError(
                f"{entry.lemma}: generated form {form.text!r} ({tag}) has no stress"
            )


__all__ = ["Paradigm", "inflect", "INFLECTED"]
