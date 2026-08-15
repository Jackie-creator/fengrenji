"""Noun declension.

Endings are tabulated per declension type; stress comes from the scheme letter.
Two orthographic rules are applied after assembly rather than baked into every
table, because they are exceptionless:

    и/ы  after к г х ж ш ч щ, ы is written и
    о/е  after ж ш ч щ ц, an unstressed о is written е

Accusative is never generated directly. It is copied from nominative or
genitive according to animacy, which is the actual rule and keeps the stress
correct for free.
"""

from __future__ import annotations

from ..schema import Animacy, Gender, LexEntry
from ..stress import count_vowels, strip_stress, stress_index
from .forms import (
    Form,
    canonical_tag,
    parse_tag,
    place_stress,
    stress_on_ending,
    stress_on_stem,
)
from .zaliznyak import ENDING, STEM, Index, UnsupportedIndex, noun_stress, parse

CASES = ("nomn", "gent", "datv", "ablt", "loct")
VELAR = frozenset("кгх")
HUSHING = frozenset("жшчщ")
HUSHING_OR_TS = HUSHING | {"ц"}

# endings[gender][type] -> {"sing": {case: ending}, "plur": {case: ending}}
# Accusative is omitted deliberately; see module docstring.
_MASC_HARD_SG = {"nomn": "", "gent": "а", "datv": "у", "ablt": "ом", "loct": "е"}
_MASC_SOFT_SG = {"nomn": "ь", "gent": "я", "datv": "ю", "ablt": "ем", "loct": "е"}
_MASC_J_SG = {"nomn": "й", "gent": "я", "datv": "ю", "ablt": "ем", "loct": "е"}

_FEM_A_SG = {"nomn": "а", "gent": "ы", "datv": "е", "accs": "у", "ablt": "ой", "loct": "е"}
_FEM_JA_SG = {"nomn": "я", "gent": "и", "datv": "е", "accs": "ю", "ablt": "ей", "loct": "е"}
_FEM_SOFT_SG = {"nomn": "ь", "gent": "и", "datv": "и", "accs": "ь", "ablt": "ью", "loct": "и"}

_NEUT_O_SG = {"nomn": "о", "gent": "а", "datv": "у", "ablt": "ом", "loct": "е"}
_NEUT_E_SG = {"nomn": "е", "gent": "я", "datv": "ю", "ablt": "ем", "loct": "е"}

_HARD_PL = {"nomn": "ы", "datv": "ам", "ablt": "ами", "loct": "ах"}
_SOFT_PL = {"nomn": "и", "datv": "ям", "ablt": "ями", "loct": "ях"}

#: Genitive plural per gender and declension type -- the cell with the least
#: regularity in the whole nominal system.
_GEN_PL = {
    (Gender.MASC, 1): "ов",
    (Gender.MASC, 2): "ей",
    (Gender.MASC, 3): "ов",
    (Gender.MASC, 4): "ей",
    (Gender.MASC, 5): "ов",
    (Gender.MASC, 6): "ев",
    (Gender.FEMN, 1): "",
    (Gender.FEMN, 2): "ь",
    (Gender.FEMN, 3): "",
    (Gender.FEMN, 4): "",
    (Gender.FEMN, 5): "",
    (Gender.FEMN, 8): "ей",
    (Gender.NEUT, 1): "",
    (Gender.NEUT, 2): "ей",
    (Gender.NEUT, 3): "",
}


def inflect_noun(entry: LexEntry) -> dict[str, Form]:
    """Expand a noun entry into its full paradigm."""
    if entry.indeclinable:
        return _indeclinable(entry)
    if entry.zaliznyak is None:
        raise UnsupportedIndex(f"{entry.lemma}: no paradigm index")

    index = parse(entry.zaliznyak)
    lemma = strip_stress(entry.lemma)
    # Declension shape, which may differ from grammatical gender (мужчи́на).
    gender = declension_gender(lemma, entry.gender)
    stem = _stem(lemma, entry.gender, index)
    stem_ordinal = _stem_stress_ordinal(entry, stem)
    oblique_stem = _drop_fleeting(stem) if index.fleeting and gender is Gender.MASC else stem

    cells: dict[str, Form] = {}
    for number in ("sing", "plur"):
        for case in CASES:
            ending = _ending(gender, index, number, case)
            if ending is None:
                continue
            use_stem = stem if (number == "sing" and case == "nomn") else oblique_stem
            # The genitive plural has no vowel of its own (zero, or a bare ь for
            # soft feminines), so a fleeting vowel surfaces in the stem:
            # окно́ -> о́кон, ку́хня -> ку́хонь.
            if (
                number == "plur"
                and case == "gent"
                and index.fleeting
                and count_vowels(ending) == 0
            ):
                use_stem = _insert_fleeting(stem)
            text = _assemble(
                entry.lemma, use_stem, ending, index, number, case, stem_ordinal
            )
            tags = {number, case}
            cells[canonical_tag(tags)] = Form.make(text, tags)

        # Feminine -а/-я has its own accusative singular; everything else copies.
        if number == "sing" and gender is Gender.FEMN:
            acc_ending = _ending(gender, index, "sing", "accs")
            if acc_ending is not None and acc_ending not in ("ь",):
                text = _assemble(
                    entry.lemma, stem, acc_ending, index, "sing", "accs", stem_ordinal
                )
                cells[canonical_tag({"sing", "accs"})] = Form.make(
                    text, {"sing", "accs"}
                )

    # Overrides must land before the accusative is derived: я́блоко's plural is
    # hand-written (я́блоки), and the accusative has to copy that, not the
    # regular form the table would have produced.
    for tag, text in entry.form_overrides.items():
        tags = parse_tag(tag)
        cells[canonical_tag(tags)] = Form.make(text, tags)

    _derive_accusative(cells, entry.animacy)
    return cells


def _indeclinable(entry: LexEntry) -> dict[str, Form]:
    """метро, кофе: one shape in every cell."""
    cells: dict[str, Form] = {}
    for number in ("sing", "plur"):
        for case in (*CASES, "accs"):
            tags = {number, case}
            cells[canonical_tag(tags)] = Form.make(entry.stress, tags)
    return cells


def declension_gender(lemma: str, gender: Gender) -> Gender:
    """Which ending set to use, which is not always the grammatical gender.

    мужчи́на, па́па and де́душка are masculine -- adjectives agree with them in
    the masculine -- but they decline exactly like feminine -а nouns. Grammatical
    gender governs agreement; the ending shape governs declension, and here the
    two come apart.
    """
    if gender is Gender.MASC and lemma[-1] in "ая":
        return Gender.FEMN
    return gender


def _stem(lemma: str, gender: Gender, index: Index) -> str:
    """Strip the nominative-singular ending to get the stem."""
    gender = declension_gender(lemma, gender)
    if gender is Gender.MASC:
        return lemma[:-1] if lemma[-1] in "ьй" else lemma
    if gender is Gender.FEMN:
        return lemma[:-1] if lemma[-1] in "аяь" else lemma
    return lemma[:-1] if lemma[-1] in "оея" else lemma


def _ending(gender: Gender, index: Index, number: str, case: str) -> str | None:
    if number == "plur":
        if case == "gent":
            return _GEN_PL.get((gender, index.type))
        soft = _is_soft(gender, index)
        table = _SOFT_PL if soft else _HARD_PL
        if case == "nomn":
            if gender is Gender.MASC and index.nominative_plural_in_a:
                return "я" if soft else "а"
            if gender is Gender.NEUT:
                return "я" if soft else "а"
            return table["nomn"]
        return table.get(case)

    if gender is Gender.MASC:
        if index.type == 6:
            return _MASC_J_SG.get(case)
        if index.type == 2:
            return _MASC_SOFT_SG.get(case)
        return _MASC_HARD_SG.get(case)
    if gender is Gender.FEMN:
        if index.type == 8:
            return _FEM_SOFT_SG.get(case)
        if index.type == 2:
            return _FEM_JA_SG.get(case)
        return _FEM_A_SG.get(case)
    if index.type == 2:
        return _NEUT_E_SG.get(case)
    return _NEUT_O_SG.get(case)


def _is_soft(gender: Gender, index: Index) -> bool:
    if gender is Gender.MASC:
        return index.type in (2, 6, 7)
    if gender is Gender.FEMN:
        return index.type in (2, 7, 8)
    return index.type in (2, 7)


def _assemble(
    lemma: str,
    stem: str,
    ending: str,
    index: Index,
    number: str,
    case: str,
    stem_ordinal: int | None,
) -> str:
    where = noun_stress(index, number, case)
    ending = _spell(
        stem, ending, stressed=where is ENDING, case=case, number=number
    )
    if where is STEM:
        if stem_ordinal is None:
            raise UnsupportedIndex(
                f"{lemma}: stem stress position unknown for scheme {index.scheme!r}; "
                f"add a stem-stressed form_override"
            )
        return stress_on_stem(stem, ending, stem_ordinal)
    return stress_on_ending(stem, ending)


def _spell(stem: str, ending: str, *, stressed: bool, case: str = "", number: str = "") -> str:
    """Apply Russian's orthographic rules for endings.

    ы -> и and я/ю -> а/у after a velar or hushing stem are purely graphic. The
    о/е alternation after hushings and ц is stress-driven (карандашо́м but
    ме́сяцем), and a stressed instrumental -ем becomes -ём (день -> днём).
    """
    if not stem or not ending:
        return ending
    last = stem[-1]

    if ending[0] == "ы" and last in VELAR | HUSHING:
        ending = "и" + ending[1:]
    if ending[0] in "яю" and last in HUSHING:
        ending = {"я": "а", "ю": "у"}[ending[0]] + ending[1:]
    if ending[0] == "о" and last in HUSHING_OR_TS and not stressed:
        ending = "е" + ending[1:]
    if ending == "ем" and stressed and case == "ablt" and number == "sing":
        ending = "ём"
    return ending


def _drop_fleeting(stem: str) -> str:
    """отец -> отц-, день -> дн-: the last о/е/ё before the final consonant goes."""
    for i in range(len(stem) - 1, -1, -1):
        if stem[i] in "оеё" and i == len(stem) - 2:
            return stem[:i] + stem[i + 1 :]
    return stem


def _insert_fleeting(stem: str) -> str:
    """окн -> окон, ручк -> ручек: a vowel appears in the zero-ending genitive."""
    if len(stem) < 2:
        return stem
    before, after = stem[-2], stem[-1]
    if before in "аеёиоуыэюя" or after in "аеёиоуыэюя":
        return stem
    vowel = "е" if before in HUSHING_OR_TS or before in "ьй" else "о"
    return stem[:-1] + vowel + after


def _stem_stress_ordinal(entry: LexEntry, stem: str) -> int | None:
    """Which stem vowel carries the stress when the scheme says "stem".

    Three sources, in order of reliability:

    1. The marked lemma, when the lemma itself is stem-stressed (го́род).
    2. A single-vowel stem, where the position is unambiguous (рук- -> ру́ку).
    3. A hand-written stem-stressed override, which is precisely what the
       accusative overrides on рука́/нога́/голова́ record.

    Returns None when the position genuinely cannot be determined; the caller
    raises only if a stem-stressed cell actually needs it, so ending-stressed
    paradigms (scheme b) never trip over this.
    """
    stem_vowels = count_vowels(stem)
    if stem_vowels == 0:
        return None

    at = stress_index(entry.stress)
    if at is not None:
        ordinal = count_vowels(strip_stress(entry.stress)[:at])
        if ordinal < stem_vowels:
            return ordinal

    if stem_vowels == 1:
        return 0

    for form in entry.form_overrides.values():
        at = stress_index(form)
        if at is None:
            continue
        ordinal = count_vowels(strip_stress(form)[:at])
        if ordinal < stem_vowels:
            return ordinal

    return None


def _derive_accusative(cells: dict[str, Form], animacy: Animacy | None) -> None:
    """Accusative = nominative for inanimates, genitive for animates."""
    source_case = "gent" if animacy is Animacy.ANIM else "nomn"
    for number in ("sing", "plur"):
        key = canonical_tag({number, "accs"})
        if key in cells:
            continue
        source = cells.get(canonical_tag({number, source_case}))
        if source is not None:
            tags = {number, "accs"}
            cells[key] = Form.make(source.text, tags)


__all__ = ["inflect_noun", "place_stress"]
