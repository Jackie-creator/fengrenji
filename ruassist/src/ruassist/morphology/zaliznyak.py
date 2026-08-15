"""Parsing of Zaliznyak paradigm indices.

An index such as ``ж 3*d`` packs everything the generator needs into a few
characters:

    ж      grammatical class (gender for nouns, aspect for verbs)
    3      declension/conjugation type, determined by the stem's final sound
    *      the stem has a fleeting vowel
    d      stress scheme
    ′      accusative singular takes stem stress (рука́ -> ру́ку)
    (1)    nominative plural in -а (го́род -> города́)

The stress scheme is the part that matters most and the part no other free
resource provides: OpenCorpora gives correct forms but no stress at all.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

INDEX_RE = re.compile(
    r"""^
    (?P<cls>[а-яё]{1,3})\           # grammatical class
    (?P<type>\d{1,2})               # declension / conjugation type
    (?P<fleeting>\*)?               # fleeting vowel
    (?P<irregular>°)?               # non-standard stem
    (?P<scheme>[a-f])               # stress scheme
    (?P<primed>[′'*])?              # acc.sg stem-stress variant
    (?:/(?P<alt>[a-f])(?:[′'*])?)?  # secondary scheme (short forms)
    (?:\((?P<plural>\d)\))?         # nominative plural marker
    $""",
    re.VERBOSE,
)

NOUN_CLASSES = {"м", "ж", "с", "мо", "жо", "со", "мн"}
ADJ_CLASSES = {"п"}
VERB_CLASSES = {"нсв", "св", "дв"}


class UnsupportedIndex(ValueError):
    """The index is well-formed but the generator cannot expand it yet."""


@dataclass(frozen=True)
class Index:
    grammatical_class: str
    type: int
    scheme: str
    fleeting: bool = False
    irregular: bool = False
    acc_sg_stem: bool = False
    alt_scheme: str | None = None
    plural_marker: int | None = None

    @property
    def is_noun(self) -> bool:
        return self.grammatical_class in NOUN_CLASSES

    @property
    def is_adjective(self) -> bool:
        return self.grammatical_class in ADJ_CLASSES

    @property
    def is_verb(self) -> bool:
        return self.grammatical_class in VERB_CLASSES

    @property
    def nominative_plural_in_a(self) -> bool:
        """го́род -> города́, дом -> дома́, but стол -> столы́."""
        return self.plural_marker == 1


def parse(index: str) -> Index:
    match = INDEX_RE.match(index.strip())
    if not match:
        raise ValueError(f"malformed Zaliznyak index: {index!r}")
    return Index(
        grammatical_class=match["cls"],
        type=int(match["type"]),
        scheme=match["scheme"],
        fleeting=bool(match["fleeting"]),
        irregular=bool(match["irregular"]),
        acc_sg_stem=bool(match["primed"]),
        alt_scheme=match["alt"],
        plural_marker=int(match["plural"]) if match["plural"] else None,
    )


# --- Stress schemes ---------------------------------------------------------

STEM = "stem"
ENDING = "ending"


def noun_stress(index: Index, number: str, case: str) -> str:
    """Where the stress falls for a given noun cell.

    Schemes (Zaliznyak):

        a  stem everywhere
        b  ending everywhere
        c  singular stem, plural ending
        d  singular ending, plural stem
        e  singular stem; plural nominative stem, obliques ending
        f  singular ending; plural nominative stem, obliques ending

    The primed variants (b′, d′, f′) pull the accusative singular back onto the
    stem, which is why рука́ becomes ру́ку. Accusative is otherwise never asked
    about here -- the generator copies it from nominative or genitive according
    to animacy.
    """
    scheme = index.scheme
    singular = number == "sing"

    if scheme == "a":
        return STEM
    if scheme == "b":
        if singular and case == "accs" and index.acc_sg_stem:
            return STEM
        return ENDING
    if scheme == "c":
        return STEM if singular else ENDING
    if scheme == "d":
        if singular:
            if case == "accs" and index.acc_sg_stem:
                return STEM
            return ENDING
        return STEM
    if scheme == "e":
        if singular:
            return STEM
        return STEM if case == "nomn" else ENDING
    if scheme == "f":
        if singular:
            if case == "accs" and index.acc_sg_stem:
                return STEM
            return ENDING
        return STEM if case == "nomn" else ENDING
    raise UnsupportedIndex(f"unknown stress scheme {scheme!r}")


def verb_present_stress(index: Index, person: str, number: str) -> str:
    """Stress in the present/simple-future paradigm.

        a  stem everywhere        (де́лаю, де́лаешь)
        b  ending everywhere      (говорю́, говори́шь)
        c  ending in 1sg, stem elsewhere  (пишу́, пи́шешь)
    """
    scheme = index.scheme
    if scheme == "a":
        return STEM
    if scheme == "b":
        return ENDING
    if scheme == "c":
        return ENDING if (person == "1per" and number == "sing") else STEM
    raise UnsupportedIndex(f"unsupported verb stress scheme {scheme!r}")
