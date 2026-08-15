"""Form representation and stress placement.

Everything the generator emits carries a stress mark. A form without one is a
build failure, not a warning: an unstressed Russian form is actively harmful to
a learner, who has no way to notice it is missing.
"""

from __future__ import annotations

from typing import NamedTuple

from ..stress import STRESS, VOWELS, count_vowels, search_key


class Form(NamedTuple):
    """One cell of a paradigm."""

    text: str  # display form, stress-marked
    plain: str  # search key: stressless, ё-folded, lowercase
    tags: frozenset[str]

    @classmethod
    def make(cls, text: str, tags: frozenset[str] | set[str]) -> Form:
        return cls(text=text, plain=search_key(text), tags=frozenset(tags))


def canonical_tag(tags: frozenset[str] | set[str] | list[str]) -> str:
    """Stable dict key for a grammeme set, independent of authoring order."""
    return ",".join(sorted(tags))


def parse_tag(tag: str) -> frozenset[str]:
    return frozenset(part.strip() for part in tag.split(",") if part.strip())


def vowel_positions(word: str) -> list[int]:
    return [i for i, ch in enumerate(word) if ch in VOWELS]


def place_stress(word: str, vowel_ordinal: int) -> str:
    """Mark the nth vowel (0-based) of a stressless word.

    Returns the word unchanged when the target vowel is ё (inherently stressed)
    or when the word is monosyllabic, matching the convention used throughout
    the lexicon.
    """
    positions = vowel_positions(word)
    if not positions:
        return word
    if vowel_ordinal < 0:
        vowel_ordinal += len(positions)
    vowel_ordinal = max(0, min(vowel_ordinal, len(positions) - 1))

    if count_vowels(word) == 1:
        return word
    at = positions[vowel_ordinal]
    if word[at] in "ёЁ":
        return word
    return word[: at + 1] + STRESS + word[at + 1 :]


def stress_on_stem(stem: str, ending: str, stem_vowel_ordinal: int) -> str:
    """Assemble a form with the stress on a given stem vowel."""
    return place_stress(stem + ending, stem_vowel_ordinal)


def stress_on_ending(stem: str, ending: str) -> str:
    """Assemble a form with the stress on the ending's first vowel.

    A zero ending (or one with no vowel, like -ь) cannot carry stress, so it
    falls back to the final stem vowel -- which is what actually happens in
    ending-stressed paradigms: стол -> стола́ but nominative стол.
    """
    stem_vowels = count_vowels(stem)
    if count_vowels(ending) == 0:
        return place_stress(stem + ending, stem_vowels - 1)
    return place_stress(stem + ending, stem_vowels)
