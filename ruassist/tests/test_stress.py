"""Tests for stress-mark handling.

Every assertion here encodes a rule the lexicon depends on. Stress is the field
most likely to carry authoring errors, so these tests are the first line of
defence.
"""

import pytest

from ruassist import stress as st


class TestStripAndFold:
    def test_strip_removes_marks(self):
        assert st.strip_stress("чита́ть") == "читать"
        assert st.strip_stress("рука́") == "рука"

    def test_strip_is_idempotent(self):
        assert st.strip_stress(st.strip_stress("вода́")) == "вода"

    def test_yo_folded_for_search_only(self):
        # Display keeps ё; the search index collapses it, because Russian text
        # routinely writes е for ё.
        assert st.fold_yo("ребёнок") == "ребенок"
        assert st.search_key("ребёнок") == "ребенок"
        assert st.search_key("Ребёнок") == "ребенок"

    def test_search_key_ignores_stress_and_case(self):
        assert st.search_key("Чита́ть") == st.search_key("читать")

    def test_precomposed_accent_normalised(self):
        """U+00B4 and precomposed vowels must fold to base + U+0301."""
        assert st.strip_stress("чита´ть") == "читать"


class TestStressIndex:
    def test_marked_vowel(self):
        assert st.stress_index("рука́") == 3  # р-у-к-а, the а

    def test_yo_is_inherently_stressed(self):
        assert st.stress_index("ребёнок") == 3

    def test_unmarked_returns_none(self):
        assert st.stress_index("рука") is None


class TestValidate:
    @pytest.mark.parametrize(
        "text",
        [
            "чита́ть",
            "дом",  # monosyllabic, exempt
            "ребёнок",  # ё carries the stress
            "Я чита́ю кни́гу.",
            "по-ру́сски",  # hyphen parts stressed separately
            "Он взял меня́ за́ руку.",  # proclitic pulls stress off руку
        ],
    )
    def test_accepts_valid(self, text):
        assert st.validate(text) == st.normalize(text)

    def test_rejects_unstressed_polysyllable(self):
        with pytest.raises(st.StressError, match="unstressed polysyllabic"):
            st.validate("читать")

    def test_rejects_double_stress_in_one_word(self):
        with pytest.raises(st.StressError, match="stress marks in one word"):
            st.validate("чи́та́ть")

    def test_rejects_mark_on_consonant(self):
        with pytest.raises(st.StressError, match="not attached to a vowel"):
            st.validate("чита́т́ь")

    def test_unmarked_preposition_does_not_excuse_next_word(self):
        """Only a *marked* proclitic explains a stressless neighbour."""
        with pytest.raises(st.StressError):
            st.validate("за руку")

    def test_marked_proclitic_excuses_next_word(self):
        assert st.validate("за́ руку")

    def test_non_cyrillic_ignored(self):
        assert st.validate("ГОСТ 7.79-2000")


def test_agrees_with_lemma():
    assert st.agrees_with_lemma("рука́", "рука")
    assert not st.agrees_with_lemma("руки́", "рука")
