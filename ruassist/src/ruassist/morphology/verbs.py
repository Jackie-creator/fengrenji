"""Verb conjugation for the productive Zaliznyak classes.

Covered: 1 (-ать/-ять), 4 (-ить), 5 (-еть/-ать, second conjugation) and
6 (-ать with stem alternation). Between them these account for the great
majority of Russian verbs.

Everything else -- быть, хотеть, дать, есть, идти and friends -- is genuinely
suppletive and supplied through ``form_overrides``. That is the intended
division of labour, not a gap: no paradigm index can generate шёл from идти.

Aspect decides which tense the personal forms carry: an imperfective conjugates
into the present, a perfective into the simple future. The two never coexist.
"""

from __future__ import annotations

from ..schema import Aspect, LexEntry
from ..stress import count_vowels, strip_stress, stress_index
from .forms import (
    Form,
    canonical_tag,
    place_stress,
    stress_on_ending,
    stress_on_stem,
)
from .zaliznyak import ENDING, Index, UnsupportedIndex, parse, verb_present_stress

HUSHING = frozenset("жшчщ")
VOWELS = frozenset("аеёиоуыэюя")

#: Classes taking first-conjugation endings.
_FIRST_CONJUGATION = (1, 2, 6)

#: 1st conjugation (classes 1, 2 and 6).
_FIRST = {
    ("1per", "sing"): "ю",
    ("2per", "sing"): "ешь",
    ("3per", "sing"): "ет",
    ("1per", "plur"): "ем",
    ("2per", "plur"): "ете",
    ("3per", "plur"): "ют",
}

#: 2nd conjugation (classes 4 and 5).
_SECOND = {
    ("1per", "sing"): "ю",
    ("2per", "sing"): "ишь",
    ("3per", "sing"): "ит",
    ("1per", "plur"): "им",
    ("2per", "plur"): "ите",
    ("3per", "plur"): "ят",
}

#: Consonant alternations before a front vowel.
_ALTERNATIONS = {
    "ст": "щ", "ск": "щ",
    "д": "ж", "т": "ч", "з": "ж", "с": "ш",
    "к": "ч", "г": "ж", "х": "ш",
}

#: Labials take an epenthetic л: люби́ть -> люблю́, купи́ть -> куплю́.
_LABIALS = frozenset("бпвфм")

SUPPORTED_CLASSES = (1, 2, 4, 5, 6)


def inflect_verb(entry: LexEntry) -> dict[str, Form]:
    if entry.zaliznyak is None:
        raise UnsupportedIndex(f"{entry.lemma}: no paradigm index (suppletive)")

    index = parse(entry.zaliznyak)
    if index.type not in SUPPORTED_CLASSES or index.irregular:
        raise UnsupportedIndex(
            f"{entry.lemma}: conjugation class {index.type} not generated"
        )

    lemma = strip_stress(entry.lemma)
    # Reflexives are conjugated as their plain stem, then the postfix goes back
    # on: занима́ться -> занима́ю -> занима́юсь. Doing it the other way round
    # would need every rule above to know about -ся.
    reflexive = lemma.endswith(("ся", "сь"))
    if reflexive:
        lemma = lemma[:-2]
    if not lemma.endswith("ть"):
        raise UnsupportedIndex(f"{entry.lemma}: infinitive does not end in -ть")

    infinitive_ordinal = _stress_ordinal(entry.stress)
    cells: dict[str, Form] = {
        canonical_tag({"infn"}): Form.make(entry.stress, {"infn"})
    }
    cells |= _personal(entry, index, lemma, infinitive_ordinal)
    cells |= _past(entry, lemma, infinitive_ordinal)
    cells |= _imperative(entry, index, lemma)

    if reflexive:
        cells = {
            tag: Form.make(_add_postfix(form.text), form.tags)
            for tag, form in cells.items()
            if tag != canonical_tag({"infn"})
        } | {canonical_tag({"infn"}): Form.make(entry.stress, {"infn"})}
    return cells


def _add_postfix(form: str) -> str:
    """-сь after a vowel, -ся after a consonant or soft sign.

    занима́юсь / занима́ешься / занима́ется / занима́емся / занима́етесь /
    занима́ются -- the alternation is purely phonetic and exceptionless.

    A monosyllabic base carries no stress mark by convention, but the postfix
    makes it polysyllabic, so the mark has to be added: нравь -> нра́вься.
    """
    plain = strip_stress(form)
    result = form + ("сь" if plain[-1] in VOWELS else "ся")
    if count_vowels(plain) == 1 and "ё" not in plain:
        return place_stress(result, 0)
    return result


# --- Personal forms ---------------------------------------------------------

def _personal(
    entry: LexEntry, index: Index, lemma: str, infinitive_ordinal: int
) -> dict[str, Form]:
    tense = "pres" if entry.aspect is Aspect.IMPF else "futr"
    base = _present_stem(lemma, index)
    endings = _FIRST if index.type in _FIRST_CONJUGATION else _SECOND

    cells: dict[str, Form] = {}
    for (person, number), ending in endings.items():
        stem = base
        if index.type in (4, 5) and person == "1per" and number == "sing":
            stem = _alternate(base)
        where = verb_present_stress(index, person, number)
        ending = _spell(stem, ending, stressed=where is ENDING)
        if where is ENDING:
            text = stress_on_ending(stem, ending)
        else:
            text = stress_on_stem(stem, ending, _stem_ordinal(entry, stem, index))
        tags = {tense, person, number}
        cells[canonical_tag(tags)] = Form.make(text, tags)
    return cells


def _present_stem(lemma: str, index: Index) -> str:
    """Strip the infinitive suffix; classes 2 and 6 also reshape the stem."""
    if index.type == 1:
        return lemma[:-2]  # чита-ть -> чита-
    if index.type == 2:
        # -овать/-евать loses the suffix and gains -у-: сове́товать -> сове́ту-,
        # интересова́ть -> интересу-. A very productive class, and the one that
        # borrowed verbs join.
        return lemma[:-5] + "у"
    if index.type in (4, 5):
        return lemma[:-3]  # говор-ить -> говор-, вид-еть -> вид-
    return _alternate(lemma[:-3])  # пис-ать -> пиш-


def _alternate(stem: str) -> str:
    """Apply the consonant alternation, or add the epenthetic л."""
    if stem and stem[-1] in _LABIALS:
        return stem + "л"
    for cluster, replacement in _ALTERNATIONS.items():
        if stem.endswith(cluster):
            return stem[: -len(cluster)] + replacement
    return stem


def _spell(stem: str, ending: str, *, stressed: bool = False) -> str:
    """Orthographic adjustments to a personal ending.

    After a hushing consonant ю/я are written у/а. And a stressed е at the head
    of an ending is written ё: смею́сь but смеёшься, живёшь, идёшь. Unstressed it
    stays е (чита́ешь), which is why the stress decision has to come first.
    """
    if stressed and ending[0] == "е":
        ending = "ё" + ending[1:]
    if not stem or stem[-1] not in HUSHING:
        return ending
    return {"ю": "у", "я": "а"}.get(ending[0], ending[0]) + ending[1:]


# --- Past and imperative ----------------------------------------------------

def _past(entry: LexEntry, lemma: str, ordinal: int) -> dict[str, Form]:
    """Past tense is built from the infinitive stem: чита-ть -> чита-л."""
    stem = lemma[:-2]
    cells: dict[str, Form] = {}
    for suffix, extra in (("л", "masc"), ("ла", "femn"), ("ло", "neut"), ("ли", "plur")):
        tags = {"past", extra}
        cells[canonical_tag(tags)] = Form.make(
            stress_on_stem(stem, suffix, ordinal), tags
        )
    return cells


def _imperative(entry: LexEntry, index: Index, lemma: str) -> dict[str, Form]:
    """Vowel stem -> -й; consonant stem -> -и when end-stressed, else -ь."""
    # The imperative is built on the unalternated present stem: люби́ть -> люби́,
    # not *люблі, even though the 1sg is люблю́.
    stem = _present_stem(lemma, index)
    if not stem:
        raise UnsupportedIndex(f"{entry.lemma}: empty present stem")

    if stem[-1] in VOWELS:
        suffix, end_stressed = "й", False
    elif _has_stressed_vy_prefix(entry, lemma):
        # вы- takes the stress but the rest of the paradigm behaves as if it had
        # not: учи́ть -> учи́, so вы́учить -> вы́учи, never *вы́учь. The imperative
        # keeps the base verb's -и while the stress stays on the prefix.
        suffix, end_stressed = "и", False
    elif index.scheme in ("b", "c"):
        suffix, end_stressed = "и", True
    elif _ends_in_cluster(stem):
        # A stem-stressed verb still takes -и after a consonant cluster:
        # е́здить -> е́зди (not *е́здь), ко́нчить -> ко́нчи.
        suffix, end_stressed = "и", False
    else:
        suffix, end_stressed = "ь", False

    # Each number is stressed from the stem up, not by appending -те to the
    # singular: е́здь is monosyllabic and carries no mark, but е́здьте needs one.
    ordinal = _stem_ordinal(entry, stem, index)
    cells = {}
    for plural_suffix, tags in (("", {"impr", "sing"}), ("те", {"impr", "plur"})):
        ending = suffix + plural_suffix
        text = (
            stress_on_ending(stem, ending)
            if end_stressed
            else stress_on_stem(stem, ending, ordinal)
        )
        cells[canonical_tag(tags)] = Form.make(text, tags)
    return cells


# --- Stress helpers ---------------------------------------------------------

def _stress_ordinal(marked: str) -> int:
    at = stress_index(marked)
    if at is None:
        return 0
    return count_vowels(strip_stress(marked)[:at])


def _stem_ordinal(entry: LexEntry, stem: str, index: Index) -> int:
    """Stem-stressed cells of scheme c take the syllable before the ending.

    писа́ть -> пишу́ but пи́шешь: the stress retracts onto the last stem vowel.
    For schemes a and b the infinitive already shows the position.
    """
    ordinal = _stress_ordinal(entry.stress)
    stem_vowels = count_vowels(stem)
    if ordinal < stem_vowels:
        return ordinal
    return max(stem_vowels - 1, 0)


def _has_stressed_vy_prefix(entry: LexEntry, lemma: str) -> bool:
    """A вы- perfective whose stress the prefix has pulled onto itself."""
    return (
        entry.aspect is Aspect.PERF
        and lemma.startswith("вы")
        and _stress_ordinal(entry.stress) == 0
    )


def _ends_in_cluster(stem: str) -> bool:
    """Two or more consonants at the end of the stem."""
    return len(stem) >= 2 and stem[-1] not in VOWELS and stem[-2] not in VOWELS
