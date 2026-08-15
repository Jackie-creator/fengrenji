"""Regression guard on agreement with OpenCorpora.

The engine's whole claim is that generated forms are correct. This pins that
claim to an external authority so a refactor cannot quietly break it.
"""

from pathlib import Path

import pytest

from ruassist.crosscheck import Report, check_entry, comparable_for
from ruassist.lexicon import load_dir
from ruassist.morphology import INFLECTED
from ruassist.schema import POS

pymorphy3 = pytest.importorskip("pymorphy3")

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def report():
    lexicon, issues = load_dir(ROOT / "data" / "lexicon")
    assert not issues
    morph = pymorphy3.MorphAnalyzer()
    result = Report()
    for entry in lexicon.entries:
        if entry.pos in INFLECTED:
            check_entry(morph, entry, result)
    return result


def test_no_unexplained_mismatches(report):
    detail = "\n".join(
        f"{m.lemma} {m.tag}: ours={m.ours} theirs={sorted(m.theirs)}"
        for m in report.mismatches
    )
    assert not report.mismatches, detail


def test_comparison_is_broad_enough_to_be_meaningful(report):
    """A passing check on three cells would prove nothing."""
    assert report.cells > 1500


def test_gender_is_dropped_only_for_nouns(report):
    """Nouns carry inherent gender; adjectives agree in it."""
    assert "masc" not in comparable_for(POS.NOUN)
    assert "masc" in comparable_for(POS.ADJ)
