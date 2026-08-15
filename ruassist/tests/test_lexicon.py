"""Regression tests over the shipped lexicon.

These treat the hand-authored data as code: if an entry is edited into an
inconsistent state, the suite fails rather than the learner seeing a wrong
declension.
"""

from pathlib import Path

import pytest

from ruassist.lexicon import check, load_dir
from ruassist.schema import POS, Aspect, MotionGroup
from ruassist.stress import search_key

LEXICON_DIR = Path(__file__).resolve().parents[1] / "data" / "lexicon"


@pytest.fixture(scope="module")
def lexicon():
    lex, issues = load_dir(LEXICON_DIR)
    assert not issues, "\n".join(str(i) for i in issues)
    return lex


def test_lexicon_has_no_issues(lexicon):
    assert check(lexicon) == []


def test_sample_size(lexicon):
    """The M0 sample is meant to be ~50 entries covering the hard cases."""
    assert len(lexicon) >= 50


def test_every_entry_has_a_chinese_gloss(lexicon):
    """The Chinese gloss is the whole point of the project -- never empty."""
    for entry in lexicon.entries:
        for sense in entry.senses:
            assert sense.zh.strip(), f"{entry.lemma}: empty Chinese gloss"


def test_aspect_pairs_are_reciprocal(lexicon):
    verbs = [e for e in lexicon.entries if e.pos is POS.VERB and e.aspect_pair]
    assert verbs, "sample must contain aspect pairs"
    for verb in verbs:
        for partner in lexicon.by_lemma(verb.aspect_pair):
            assert search_key(partner.aspect_pair) == search_key(verb.lemma)
            assert partner.aspect != verb.aspect


def test_motion_verbs_pair_uni_with_multi(lexicon):
    pairs = [e for e in lexicon.entries if e.motion_partner]
    assert pairs, "sample must contain motion verbs"
    for verb in pairs:
        for partner in lexicon.by_lemma(verb.motion_partner):
            assert {verb.motion_group, partner.motion_group} == {
                MotionGroup.UNI,
                MotionGroup.MULTI,
            }


def test_perfective_verbs_have_no_present_tense(lexicon):
    """A perfective verb conjugates into the future, never the present."""
    for entry in lexicon.entries:
        if entry.pos is POS.VERB and entry.aspect is Aspect.PERF:
            present = [t for t in entry.form_overrides if "pres" in t]
            assert not present, f"{entry.lemma}: perfective with present-tense forms"


def test_imperfective_overrides_use_present_not_future(lexicon):
    """Imperfectives build the future analytically (бу́ду + infinitive).

    быть is the single exception in Russian: it is imperfective yet has a real
    simple future (бу́ду / бу́дешь / …), which is precisely what every other
    imperfective borrows to form its own future.
    """
    for entry in lexicon.entries:
        if entry.pos is POS.VERB and entry.aspect is Aspect.IMPF:
            if entry.lemma == "быть":
                continue
            future = [t for t in entry.form_overrides if "futr" in t]
            assert not future, f"{entry.lemma}: imperfective with simple future forms"


def test_only_byt_has_an_irregular_simple_future(lexicon):
    """Pin the exception above: if another verb claims one, it needs review."""
    claimants = {
        e.lemma
        for e in lexicon.entries
        if e.aspect is Aspect.IMPF
        and any("futr" in t for t in e.form_overrides)
    }
    assert claimants == {"быть"}


def test_animate_nouns_are_marked(lexicon):
    """Animacy drives the accusative, so it must be right on people-nouns."""
    people = {"мать", "дочь", "сестра", "человек", "ребёнок"}
    for entry in lexicon.entries:
        if entry.lemma in people:
            assert entry.animacy.value == "anim", f"{entry.lemma} must be animate"


def test_homonyms_are_distinguished(lexicon):
    mir = lexicon.by_lemma("мир")
    assert len(mir) == 2, "мир (world/peace) must be two entries"
    assert {e.homonym_id for e in mir} == {1, 2}


def test_lemmatisation_ambiguity_is_representable(lexicon):
    """стали resolves to both стать (verb) and сталь (noun) -- both must exist."""
    assert lexicon.by_lemma("стать"), "стать missing"
    assert lexicon.by_lemma("сталь"), "сталь missing"


def test_pending_cross_checks_are_declared(lexicon):
    """Entries whose Zaliznyak index I could not verify must say so."""
    unverified = {e.lemma for e in lexicon.entries if e.verify}
    # These are the mobile-stress paradigms flagged for OpenCorpora comparison.
    assert {"рука", "нога", "голова"} <= unverified


def test_sample_covers_the_a1_core(lexicon):
    """After the batch-1 push the lexicon is well past the 55-entry sample."""
    assert len(lexicon) >= 200


def test_indeclinable_nouns_have_no_paradigm(lexicon):
    """метро/кофе never inflect, so they must not carry a Zaliznyak index."""
    for entry in lexicon.entries:
        if entry.indeclinable:
            assert entry.zaliznyak is None, f"{entry.lemma}: indeclinable with a paradigm"


def test_pluralia_tantum_have_no_singular_forms(lexicon):
    """деньги has no singular, so no singular form may be declared."""
    for entry in lexicon.entries:
        if entry.number_only == "plur":
            singular = [t for t in entry.form_overrides if "sing" in t]
            assert not singular, f"{entry.lemma}: plural-only noun with singular forms"


def test_english_glosses_are_strings(lexicon):
    """Guards the YAML 'Norway problem': `en: no` parsing as a boolean."""
    for entry in lexicon.entries:
        for sense in entry.senses:
            assert sense.en is None or isinstance(sense.en, str)


def test_prefixed_motion_verbs_pair_up(lexicon):
    """Each prefixed motion verb needs its aspect partner; half a pair is useless."""
    prefixed = {
        "войти": "входить", "выйти": "выходить", "перейти": "переходить",
        "подойти": "подходить", "зайти": "заходить", "пройти": "проходить",
        "приехать": "приезжать", "уехать": "уезжать",
    }
    for perfective, imperfective in prefixed.items():
        entries = lexicon.by_lemma(perfective)
        assert entries, f"{perfective} missing"
        assert entries[0].aspect_pair == imperfective


def test_days_and_months_are_complete(lexicon):
    """Closed sets: a partial set is worse than none, since the gap is invisible."""
    days = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота",
            "воскресенье"]
    months = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль",
              "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]
    for word in days + months:
        assert lexicon.by_lemma(word), f"{word} missing"
