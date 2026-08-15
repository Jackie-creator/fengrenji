"""Form -> lemma index: the lookup that makes a Russian dictionary usable.

A learner meets `прочитанного` in a text, not `прочитать`. With paradigms
averaging dozens of cells, almost every word encountered is a form the
dictionary does not list under that spelling, so the index is not an
optimisation -- it is the product.

Ambiguity is preserved rather than resolved. `ста́ли` is both стать and сталь,
and a dictionary that silently picks one is worse than useless. Every candidate
comes back, and the caller shows them all.

At build time this becomes the packaged lookup table; nothing here needs to run
on the client.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .lexicon import Lexicon
from .morphology import Form, Paradigm, inflect
from .schema import LexEntry
from .stress import search_key


@dataclass(frozen=True)
class Candidate:
    """One way of reading a surface form."""

    entry: LexEntry
    form: Form

    @property
    def is_lemma(self) -> bool:
        return search_key(self.form.text) == search_key(self.entry.lemma)

    def describe(self) -> str:
        return f"{self.entry.stress} ({self.entry.pos.value}) — {', '.join(sorted(self.form.tags))}"


class FormIndex:
    """Maps every surface form of every entry back to its lemmas."""

    def __init__(self) -> None:
        self._by_form: dict[str, list[Candidate]] = defaultdict(list)
        self._paradigms: dict[int, Paradigm] = {}

    @classmethod
    def build(cls, lexicon: Lexicon) -> FormIndex:
        index = cls()
        for entry in lexicon.entries:
            paradigm = inflect(entry)
            index._paradigms[id(entry)] = paradigm
            seen: set[str] = set()
            for form in paradigm.cells.values():
                # One spelling can fill several cells (nominative and accusative
                # of an inanimate); record the first and keep the index small.
                if form.plain in seen:
                    continue
                seen.add(form.plain)
                index._by_form[form.plain].append(Candidate(entry, form))
        return index

    def lookup(self, query: str) -> list[Candidate]:
        """All readings of a surface form, lemma readings first."""
        candidates = self._by_form.get(search_key(query), [])
        return sorted(candidates, key=lambda c: (not c.is_lemma, c.entry.lemma))

    def paradigm(self, entry: LexEntry) -> Paradigm:
        return self._paradigms[id(entry)]

    @property
    def form_count(self) -> int:
        return sum(len(v) for v in self._by_form.values())

    def __len__(self) -> int:
        return len(self._by_form)

    def keys(self) -> list[str]:
        """Every indexed surface form, as search keys."""
        return list(self._by_form)
