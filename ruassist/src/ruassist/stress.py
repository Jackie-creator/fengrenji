"""Stress-mark utilities for Russian text.

Stress is marked with COMBINING ACUTE ACCENT (U+0301) placed directly after
the stressed vowel: "чита́ть", "рука́". This is the single canonical
representation across the whole project -- lexicon YAML, generated forms and
the packaged database all use it.

Two derived forms matter downstream:

* ``strip_stress`` -- what the user actually types and what gets indexed.
* ``fold_yo``      -- ё is routinely written as е in real Russian text, so the
  search index must collapse the distinction while the display form keeps it.

Stress placement is the single most error-prone field in the lexicon, so the
rules below are enforced mechanically rather than trusted to the author.
"""

from __future__ import annotations

import unicodedata

#: COMBINING ACUTE ACCENT -- the only stress mark the project accepts.
STRESS = "́"

VOWELS = frozenset("аеёиоуыэюяАЕЁИОУЫЭЮЯ")

#: ё is inherently stressed in Russian, so a word carrying it needs no mark.
INHERENTLY_STRESSED = frozenset("ёЁ")

CYRILLIC = frozenset(
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
)

#: Prepositions that can pull the stress off the following noun, leaving it
#: unstressed: "взять за́ руку", "положи́ть на́ пол", "по́ два". When one of these
#: is itself marked, the word after it is legitimately stressless.
STRESS_ATTRACTING_PREPOSITIONS = frozenset(
    {"за", "на", "по", "под", "из", "без", "до", "об", "о", "от", "из-за"}
)


class StressError(ValueError):
    """Raised when a string violates the project's stress-marking rules."""


def normalize(text: str) -> str:
    """Return NFC-normalised text with any acute variants folded to U+0301.

    Editors and copy-paste sources produce several encodings of the same
    accented vowel (precomposed "у́" vs. base + combining mark, and the
    lookalike U+00B4 / U+02CA). Everything is folded to base letter + U+0301 so
    that string comparison and stress counting stay meaningful.
    """
    text = text.replace("´", STRESS).replace("ˊ", STRESS)
    # NFD splits precomposed accented vowels, NFC then recomposes only the
    # characters that have a canonical composition (Cyrillic vowels do not),
    # leaving stress as a standalone combining mark.
    return unicodedata.normalize("NFC", unicodedata.normalize("NFD", text))


def strip_stress(text: str) -> str:
    """Remove all stress marks. This is the form used for lookup and indexing."""
    return normalize(text).replace(STRESS, "")


def fold_yo(text: str) -> str:
    """Collapse ё to е for search purposes (ё is optional in written Russian)."""
    return text.replace("ё", "е").replace("Ё", "Е")


def search_key(text: str) -> str:
    """Return the canonical lookup key: stressless, ё-folded, lowercase."""
    return fold_yo(strip_stress(text)).lower()


def count_vowels(text: str) -> int:
    return sum(1 for ch in text if ch in VOWELS)


def stress_index(text: str) -> int | None:
    """Return the index of the stressed vowel, or ``None`` if unmarked.

    For a word containing ё the ё itself carries the stress, unless an explicit
    mark says otherwise (compound words may have a secondary vowel marked).
    """
    text = normalize(text)
    pos = text.find(STRESS)
    if pos > 0:
        return pos - 1
    for i, ch in enumerate(text):
        if ch in INHERENTLY_STRESSED:
            return i
    return None


def validate(text: str, *, field: str = "form") -> str:
    """Validate stress marking and return the normalised string.

    Rules:

    1. A stress mark must directly follow a vowel.
    2. At most one stress mark per word.
    3. Every polysyllabic Cyrillic word must be stressed, either by an explicit
       mark or by containing ё.

    Monosyllabic words are exempt -- marking them adds noise and the position is
    unambiguous anyway. So is a word following a marked stress-attracting
    preposition, which really is pronounced without stress. Non-Cyrillic tokens
    (digits, Latin, punctuation) are skipped so that examples may mix scripts.
    """
    text = normalize(text)

    for i, ch in enumerate(text):
        if ch == STRESS and (i == 0 or text[i - 1] not in VOWELS):
            raise StressError(
                f"{field}: stress mark not attached to a vowel in {text!r}"
            )

    words = _cyrillic_words(text)
    for i, word in enumerate(words):
        marks = word.count(STRESS)
        if marks > 1:
            raise StressError(f"{field}: {marks} stress marks in one word {word!r}")
        if count_vowels(word) > 1 and stress_index(word) is None:
            if i > 0 and _is_marked_proclitic(words[i - 1]):
                continue
            raise StressError(f"{field}: unstressed polysyllabic word {word!r}")

    return text


def _is_marked_proclitic(word: str) -> bool:
    return (
        STRESS in word and strip_stress(word).lower() in STRESS_ATTRACTING_PREPOSITIONS
    )


def _cyrillic_words(text: str) -> list[str]:
    """Split into words, keeping only those made of Cyrillic letters."""
    words: list[str] = []
    current: list[str] = []
    for ch in text:
        if ch in CYRILLIC or ch == STRESS or ch == "-":
            current.append(ch)
        else:
            if current:
                words.append("".join(current))
                current = []
    if current:
        words.append("".join(current))
    # A hyphenated compound is stressed per part (кто́-то, из-за).
    parts: list[str] = []
    for word in words:
        parts.extend(p for p in word.split("-") if any(c in CYRILLIC for c in p))
    return parts


def agrees_with_lemma(stressed: str, lemma: str) -> bool:
    """Check that a stressed spelling matches its lemma once marks are removed."""
    return strip_stress(stressed) == strip_stress(lemma)
