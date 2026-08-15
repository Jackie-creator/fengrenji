"""Tests for tiered fuzzy lookup."""

from pathlib import Path

import pytest

from ruassist.index import FormIndex
from ruassist.lexicon import load_dir
from ruassist.search import MatchKind, Search, _bounded_levenshtein

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def search():
    lexicon, issues = load_dir(ROOT / "data" / "lexicon")
    assert not issues
    return Search(FormIndex.build(lexicon))


class TestTiers:
    def test_exact_match_wins(self, search):
        results = search.lookup("книга")
        assert results[0].kind is MatchKind.EXACT
        assert results[0].lemma == "книга"

    def test_inflected_form_is_still_exact(self, search):
        """книге is an exact hit on a paradigm cell, not a fuzzy one."""
        results = search.lookup("книге")
        assert results[0].kind is MatchKind.EXACT
        assert results[0].lemma == "книга"

    def test_latin_input_is_transliterated(self, search):
        results = search.lookup("gorod")
        assert results[0].kind is MatchKind.TRANSLITERATED
        assert results[0].lemma == "город"

    def test_prefix_completes_a_partial_word(self, search):
        results = search.lookup("говор")
        assert results[0].kind is MatchKind.PREFIX
        assert "говорить" in {r.lemma for r in results}

    def test_typo_falls_through_to_fuzzy(self, search):
        results = search.lookup("челавек")
        assert results[0].kind is MatchKind.FUZZY
        assert results[0].lemma == "человек"

    def test_exact_is_never_displaced_by_a_closer_short_word(self, search):
        """Ranking by distance alone would bury an exact hit; tiers prevent that."""
        assert all(r.kind is MatchKind.EXACT for r in search.lookup("стали"))

    def test_ambiguity_survives_the_search_layer(self, search):
        assert {r.lemma for r in search.lookup("стали")} == {"стать", "сталь"}

    def test_unknown_word_returns_nothing(self, search):
        assert search.lookup("ъъъъъъ") == []

    def test_empty_query(self, search):
        assert search.lookup("") == []


class TestRanking:
    def test_one_result_per_entry(self, search):
        """Many cells of рука match "рукк"; the user wants the word once."""
        results = search.lookup("рукк")
        lemmas = [r.lemma for r in results]
        assert len(lemmas) == len(set(lemmas))

    def test_closest_first(self, search):
        results = search.lookup("рукк")
        assert [r.distance for r in results] == sorted(r.distance for r in results)

    def test_limit_respected(self, search):
        assert len(search.lookup("к", limit=3)) <= 3


class TestLevenshtein:
    @pytest.mark.parametrize(
        "a,b,budget,expected",
        [
            ("рука", "рука", 2, 0),
            ("рука", "руки", 2, 1),
            ("челавек", "человек", 2, 1),
            ("рука", "нога", 1, None),      # exceeds the budget
            ("рука", "руководство", 2, None),  # length gap alone rules it out
        ],
    )
    def test_bounded(self, a, b, budget, expected):
        assert _bounded_levenshtein(a, b, budget) == expected
