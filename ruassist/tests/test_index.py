"""Tests for form lookup and transliterated input."""

from pathlib import Path

import pytest

from ruassist.index import FormIndex
from ruassist.lexicon import load_dir
from ruassist.translit import is_latin, to_cyrillic

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def index():
    lexicon, issues = load_dir(ROOT / "data" / "lexicon")
    assert not issues
    return FormIndex.build(lexicon)


class TestLookup:
    def test_lemma_lookup(self, index):
        assert [c.entry.lemma for c in index.lookup("книга")] == ["книга"]

    def test_inflected_form_finds_its_lemma(self, index):
        """The whole point: a learner types what they read, not the lemma."""
        assert "книга" in {c.entry.lemma for c in index.lookup("книге")}
        assert "город" in {c.entry.lemma for c in index.lookup("городах")}
        assert "рука" in {c.entry.lemma for c in index.lookup("руку")}

    def test_suppletive_form_finds_its_lemma(self, index):
        assert "идти" in {c.entry.lemma for c in index.lookup("шёл")}
        assert "человек" in {c.entry.lemma for c in index.lookup("людей")}
        assert "ребёнок" in {c.entry.lemma for c in index.lookup("детьми")}

    def test_stress_marks_are_optional_in_the_query(self, index):
        assert index.lookup("рука́") == index.lookup("рука")

    def test_yo_may_be_written_as_e(self, index):
        """Real Russian text writes е for ё, so lookup must accept both."""
        assert {c.entry.lemma for c in index.lookup("шел")} == {
            c.entry.lemma for c in index.lookup("шёл")
        }

    def test_ambiguity_returns_every_candidate(self, index):
        """ста́ли is стать (past plural) and сталь (genitive singular)."""
        lemmas = {c.entry.lemma for c in index.lookup("стали")}
        assert {"стать", "сталь"} <= lemmas

    def test_homonyms_both_returned(self, index):
        entries = index.lookup("мир")
        assert {c.entry.homonym_id for c in entries if c.entry.lemma == "мир"} == {1, 2}

    def test_lemma_readings_sort_first(self, index):
        assert index.lookup("мир")[0].is_lemma

    def test_unknown_word_returns_nothing(self, index):
        assert index.lookup("абракадабра") == []

    def test_index_is_much_larger_than_the_lexicon(self, index):
        """Paradigm expansion is what makes the dictionary usable at all."""
        assert len(index) > 1000


class TestTranslit:
    @pytest.mark.parametrize(
        "latin,cyrillic",
        [
            ("privet", "привет"),
            ("ruka", "рука"),
            ("stali", "стали"),
            ("kniga", "книга"),
            ("chto", "что"),
            ("zhena", "жена"),
            ("shchi", "щи"),
            ("yazyk", "язык"),
            ("khorosho", "хорошо"),
        ],
    )
    def test_transliteration(self, latin, cyrillic):
        assert to_cyrillic(latin) == cyrillic

    def test_cyrillic_input_untouched(self):
        assert to_cyrillic("рука́") == "рука́"

    def test_is_latin(self):
        assert is_latin("privet")
        assert not is_latin("привет")
        assert not is_latin("123")

    def test_transliterated_query_finds_the_word(self, index):
        assert index.lookup(to_cyrillic("ruka"))
