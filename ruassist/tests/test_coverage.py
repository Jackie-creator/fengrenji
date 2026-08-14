"""Tests for wordlist coverage reporting."""

from pathlib import Path

import pytest

from ruassist.coverage import load_wordlist
from ruassist.lexicon import load_dir
from ruassist.stress import STRESS, normalize, search_key

ROOT = Path(__file__).resolve().parents[1]
WORDLIST = ROOT / "data" / "wordlists" / "core_a1.yaml"


@pytest.fixture(scope="module")
def wordlist():
    return load_wordlist(WORDLIST)


@pytest.fixture(scope="module")
def lexicon():
    lex, issues = load_dir(ROOT / "data" / "lexicon")
    assert not issues
    return lex


def test_wordlist_is_flagged_unofficial(wordlist):
    """Until an official syllabus is obtained, the list must not claim to be one."""
    assert wordlist.official is False


def test_wordlist_lemmas_carry_no_stress(wordlist):
    """Wordlist entries are lookup keys, so they carry no stress marks.

    They do keep ё (самолёт), which search_key folds away -- so this compares
    stress marks only, not the full search key.
    """
    for lemma in wordlist.lemmas:
        assert STRESS not in normalize(lemma), f"{lemma} carries a stress mark"
        assert lemma == lemma.lower(), f"{lemma} is not lowercase"


def test_wordlist_has_no_duplicates_within_a_theme(wordlist):
    for theme, words in wordlist.themes.items():
        assert len(words) == len(set(words)), f"duplicate lemma in theme {theme}"


def test_a1_wordlist_fully_covered(wordlist, lexicon):
    """The A1 target list is complete; regressions here mean an entry was lost."""
    have = {search_key(e.lemma) for e in lexicon.entries}
    missing = [w for w in wordlist.lemmas if search_key(w) not in have]
    assert not missing, f"missing entries: {missing}"
