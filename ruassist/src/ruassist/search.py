"""Fuzzy lookup over the form index.

A learner typing Russian gets it wrong in predictable ways, and each of those is
handled at a different layer:

* missing stress marks -- absorbed by ``search_key`` before we ever get here
* ё written as е       -- likewise
* Latin keyboard       -- :mod:`ruassist.translit`
* actual typos         -- this module

The strategy is exact, then prefix, then edit distance, and the first tier that
produces anything wins. Ranking by edit distance alone would bury an exact match
under a shorter neighbour, which is how dictionary search feels broken.

Candidates for the edit-distance pass are narrowed by length and first letter
before any distance is computed. At 200k forms a brute-force scan would be too
slow to feel instant, and instant is the whole point of an offline dictionary.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import IntEnum

from .index import Candidate, FormIndex
from .stress import search_key
from .translit import is_latin, to_cyrillic


class MatchKind(IntEnum):
    """Lower sorts first."""

    EXACT = 0
    TRANSLITERATED = 1
    PREFIX = 2
    FUZZY = 3


@dataclass
class Result:
    candidate: Candidate
    kind: MatchKind
    distance: int = 0

    @property
    def lemma(self) -> str:
        return self.candidate.entry.lemma


class Search:
    """Tiered lookup: exact, transliterated, prefix, then fuzzy."""

    #: Below this length a single edit changes too much of the word to trust two.
    SHORT_WORD = 4

    def __init__(self, index: FormIndex) -> None:
        self.index = index
        self._buckets: dict[tuple[str, int], list[str]] = defaultdict(list)
        for key in index.keys():
            self._buckets[(key[0], len(key))].append(key)

    def lookup(self, query: str, *, limit: int = 20) -> list[Result]:
        key = search_key(query)
        if not key:
            return []

        exact = self.index.lookup(key)
        if exact:
            return [Result(c, MatchKind.EXACT) for c in exact][:limit]

        if is_latin(query):
            converted = search_key(to_cyrillic(query))
            hits = self.index.lookup(converted)
            if hits:
                return [Result(c, MatchKind.TRANSLITERATED) for c in hits][:limit]
            key = converted

        prefix = self._prefix(key, limit)
        if prefix:
            return prefix

        return self._fuzzy(key, limit)

    def _prefix(self, key: str, limit: int) -> list[Result]:
        """Useful while the user is still typing."""
        if len(key) < 2:
            return []
        results: list[Result] = []
        for form in sorted(self.index.keys()):
            if form.startswith(key) and form != key:
                for candidate in self.index.lookup(form):
                    results.append(Result(candidate, MatchKind.PREFIX, len(form) - len(key)))
        return _best_per_entry(results, limit)

    def _fuzzy(self, key: str, limit: int) -> list[Result]:
        budget = 1 if len(key) < self.SHORT_WORD else 2
        results: list[Result] = []
        seen: set[str] = set()

        for form in self._neighbourhood(key, budget):
            if form in seen:
                continue
            seen.add(form)
            distance = _bounded_levenshtein(key, form, budget)
            if distance is None:
                continue
            for candidate in self.index.lookup(form):
                results.append(Result(candidate, MatchKind.FUZZY, distance))

        return _best_per_entry(results, limit)

    def _neighbourhood(self, key: str, budget: int) -> list[str]:
        """Forms close enough in length and initial letter to be worth measuring.

        A wrong first letter is rare in practice (the learner has usually heard
        the word) and dropping that assumption would cost a full scan, so the
        first letter is allowed to differ only via the explicit variants below.
        """
        lengths = range(len(key) - budget, len(key) + budget + 1)
        initials = {key[0]} | _CONFUSABLE.get(key[0], set())
        forms: list[str] = []
        for initial in initials:
            for length in lengths:
                forms.extend(self._buckets.get((initial, length), ()))
        return forms


#: Letters Chinese learners routinely swap, usually because the sounds are not
#: distinguished in Mandarin or the shapes look alike in Cyrillic.
_CONFUSABLE = {
    "и": {"ы"}, "ы": {"и"},
    "е": {"э", "и"}, "э": {"е"},
    "о": {"а"}, "а": {"о"},
    "ш": {"щ", "с"}, "щ": {"ш"},
    "з": {"с"}, "с": {"з", "ш"},
    "б": {"п"}, "п": {"б"},
    "в": {"ф"}, "ф": {"в"},
    "д": {"т"}, "т": {"д"},
    "г": {"к"}, "к": {"г"},
    "ж": {"ш"}, "ч": {"ц"}, "ц": {"ч"},
}


def _bounded_levenshtein(a: str, b: str, budget: int) -> int | None:
    """Edit distance, abandoning the computation once it exceeds ``budget``."""
    if abs(len(a) - len(b)) > budget:
        return None

    previous = list(range(len(b) + 1))
    for i, ch_a in enumerate(a, start=1):
        current = [i]
        for j, ch_b in enumerate(b, start=1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + (ch_a != ch_b),
                )
            )
        if min(current) > budget:
            return None
        previous = current

    return previous[-1] if previous[-1] <= budget else None


def _best_per_entry(results: list[Result], limit: int) -> list[Result]:
    """Collapse to one hit per entry.

    Several cells of a paradigm can match the same query, but the user wants a
    list of words, not a list of grammatical forms. The closest match wins and
    carries its own form label into the result.
    """
    best: dict[int, Result] = {}
    for result in results:
        key = id(result.candidate.entry)
        current = best.get(key)
        if current is None or result.distance < current.distance:
            best[key] = result
    return sorted(
        best.values(), key=lambda r: (r.distance, len(r.candidate.form.plain), r.lemma)
    )[:limit]
