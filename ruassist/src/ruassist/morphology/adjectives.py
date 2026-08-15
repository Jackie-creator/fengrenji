"""Adjective declension.

Two paradigms carry almost the whole class: hard stems (но́вый) and soft stems
(си́ний). Velar and hushing stems differ from the hard one only by the
orthographic rules already used for nouns.

Long-form stress does *not* come from the Zaliznyak scheme letter. That letter
describes the short forms -- весёлый is «п 1*b» because of ве́сел / весела́ --
while the long forms are stem-stressed for every adjective except the -о́й type
(большо́й, молодо́й, дорого́й). Both softness and end-stress are legible from the
lemma's spelling, so they are read there rather than inferred from the index.

Short forms and comparatives are not generated: they are irregular often enough
(лу́чше, ме́ньше, ле́гче) that the entry records them directly.
"""

from __future__ import annotations

from ..schema import LexEntry
from ..stress import count_vowels, strip_stress, stress_index
from .forms import Form, canonical_tag, stress_on_ending, stress_on_stem
from .zaliznyak import UnsupportedIndex, parse

VELAR = frozenset("кгх")
HUSHING = frozenset("жшчщ")

# case -> (masc, femn, neut, plur)
_HARD = {
    "nomn": ("ый", "ая", "ое", "ые"),
    "gent": ("ого", "ой", "ого", "ых"),
    "datv": ("ому", "ой", "ому", "ым"),
    "ablt": ("ым", "ой", "ым", "ыми"),
    "loct": ("ом", "ой", "ом", "ых"),
}

_SOFT = {
    "nomn": ("ий", "яя", "ее", "ие"),
    "gent": ("его", "ей", "его", "их"),
    "datv": ("ему", "ей", "ему", "им"),
    "ablt": ("им", "ей", "им", "ими"),
    "loct": ("ем", "ей", "ем", "их"),
}

_GENDER_SLOT = {"masc": 0, "femn": 1, "neut": 2}


def inflect_adjective(entry: LexEntry) -> dict[str, Form]:
    if entry.zaliznyak is None:
        raise UnsupportedIndex(f"{entry.lemma}: no paradigm index")

    parse(entry.zaliznyak)  # validate shape; the letter drives short forms only
    lemma = strip_stress(entry.lemma)
    stem = lemma[:-2]
    soft = is_soft(lemma)
    end_stressed = is_end_stressed(lemma)
    table = _SOFT if soft else _HARD
    ordinal = _stem_ordinal(entry, stem)

    cells: dict[str, Form] = {}
    for case, slots in table.items():
        for gender, slot in _GENDER_SLOT.items():
            ending = slots[slot]
            if case == "nomn" and gender == "masc" and end_stressed and not soft:
                ending = "ой"
            cells |= _cell(
                stem, ending, soft, end_stressed, ordinal, {"adjf", "sing", gender, case}
            )
        cells |= _cell(
            stem, slots[3], soft, end_stressed, ordinal, {"adjf", "plur", case}
        )

    _derive_accusative(cells, stem, soft, end_stressed, ordinal)
    return cells


def _cell(
    stem: str,
    ending: str,
    soft: bool,
    end_stressed: bool,
    ordinal: int,
    tags: set[str],
) -> dict[str, Form]:
    ending = _spell(stem, ending, soft, end_stressed)
    text = (
        stress_on_ending(stem, ending)
        if end_stressed
        else stress_on_stem(stem, ending, ordinal)
    )
    return {canonical_tag(tags): Form.make(text, tags)}


def is_end_stressed(lemma: str) -> bool:
    """Only the -о́й type carries its stress on the ending."""
    return lemma.endswith("ой")


def is_soft(lemma: str) -> bool:
    """A soft adjective ends in -ий after a genuinely soft consonant.

    The same -ий after a velar or hushing stem is just the ы->и spelling rule
    applied to a hard adjective: ру́сский and хоро́ший decline hard, си́ний and
    после́дний decline soft.
    """
    if not lemma.endswith("ий") or len(lemma) < 3:
        return False
    return lemma[-3] not in VELAR | HUSHING


def _spell(stem: str, ending: str, soft: bool, stressed: bool) -> str:
    """о/е after a hushing stem is stress-driven: большо́го but хоро́шего."""
    if soft or not stem:
        return ending
    last = stem[-1]
    if ending[0] == "ы" and last in VELAR | HUSHING:
        return "и" + ending[1:]
    if ending[0] == "о" and last in HUSHING and not stressed:
        return "е" + ending[1:]
    return ending


def _derive_accusative(
    cells: dict[str, Form], stem: str, soft: bool, end_stressed: bool, ordinal: int
) -> None:
    """Masculine and plural accusative depend on the head noun's animacy.

    Both variants are emitted so the consumer can pick; feminine has its own
    ending and neuter always mirrors the nominative.
    """
    cells |= _cell(
        stem,
        "юю" if soft else "ую",
        soft,
        end_stressed,
        ordinal,
        {"adjf", "sing", "femn", "accs"},
    )

    for number, gender in (("sing", "masc"), ("sing", "neut"), ("plur", None)):
        base = {"adjf", number} | ({gender} if gender else set())
        nominative = cells.get(canonical_tag(base | {"nomn"}))
        genitive = cells.get(canonical_tag(base | {"gent"}))
        if gender == "neut":
            genitive = nominative
        for source, animacy in ((nominative, "inan"), (genitive, "anim")):
            if source is None:
                continue
            tags = base | {"accs", animacy}
            cells[canonical_tag(tags)] = Form.make(source.text, tags)


def _stem_ordinal(entry: LexEntry, stem: str) -> int:
    at = stress_index(entry.stress)
    if at is None:
        return 0
    ordinal = count_vowels(strip_stress(entry.stress)[:at])
    return min(ordinal, max(count_vowels(stem) - 1, 0))
