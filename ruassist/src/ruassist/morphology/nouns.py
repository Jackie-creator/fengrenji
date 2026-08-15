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

# Type 7 (-ия / -ие) differs from type 6 (-я / -ье) in exactly one place: where
# the ending would be -е it is -и instead. исто́рия -> в исто́рии, мне́ние -> о
# мне́нии, but иде́я -> об иде́е and здоро́вье -> о здоро́вье.
_FEM_IJA_SG = {"nomn": "я", "gent": "и", "datv": "и", "accs": "ю", "ablt": "ей", "loct": "и"}
_NEUT_IJE_SG = {"nomn": "е", "gent": "я", "datv": "ю", "ablt": "ем", "loct": "и"}

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
    (Gender.FEMN, 6): "й",
    (Gender.FEMN, 7): "й",
    (Gender.FEMN, 8): "ей",
    (Gender.NEUT, 1): "",
    (Gender.NEUT, 2): "ей",
    (Gender.NEUT, 3): "",
    (Gender.NEUT, 5): "",
    (Gender.NEUT, 6): "ий",
    (Gender.NEUT, 7): "й",
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

    # A noun marked singular- or plural-only has no cells in the other number.
    # Generating them anyway would put здоро́вья and де́ньга in the index.
    numbers = ("sing", "plur")
    if entry.number_only == "sing":
        numbers = ("sing",)
    elif entry.number_only == "plur":
        numbers = ("plur",)

    cells: dict[str, Form] = {}
    for number in numbers:
        for case in CASES:
            ending = _ending(gender, index, number, case, entry.gender)
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
                use_stem = _insert_fleeting(
                    stem,
                    soft=_is_soft(gender, index) and lemma not in _HARD_FLEETING_VOWEL,
                )
                if ending == "ь" and not _keeps_soft_sign(lemma, stem):
                    # A -ня stem ending in a consonant has no ь in the genitive
                    # plural: пе́сня -> пе́сен, ба́шня -> ба́шен, тамо́жня ->
                    # тамо́жен. After a vowel the ь stays (пусты́ня -> пусты́нь).
                    ending = ""
            elif ending == "ий" and use_stem.endswith("ь"):
                # здоро́вь- + -ий is written здоро́вий: ь is not kept before и.
                use_stem = use_stem[:-1]
            text = _assemble(
                entry.lemma, use_stem, ending, index, number, case, stem_ordinal
            )
            tags = {number, case}
            cells[canonical_tag(tags)] = Form.make(text, tags)

        # A feminine singular always has its own accusative and never borrows
        # the genitive, animate or not: ло́шадь and мышь are animate but their
        # accusative is ло́шадь / мышь, because the third declension simply has
        # no separate form to distinguish. Animacy only reaches the accusative
        # where the paradigm leaves the choice open.
        if number == "sing" and gender is Gender.FEMN:
            acc_ending = _ending(gender, index, "sing", "accs", entry.gender)
            if acc_ending is not None:
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

    Common-gender nouns (колле́га, сирота́, у́мница) take their agreement from
    the person referred to, so they have no fixed grammatical gender at all --
    but they have exactly one declension, the -а feminine one.
    """
    if gender is Gender.COMMON:
        return Gender.FEMN if lemma[-1] in "ая" else Gender.MASC
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


def _ending(
    gender: Gender,
    index: Index,
    number: str,
    case: str,
    grammatical: Gender | None = None,
) -> str | None:
    if number == "plur":
        if case == "gent":
            # A masculine noun declining as a feminine keeps the masculine
            # genitive plural after a soft or hushing stem: дя́дя -> дя́дей,
            # ю́ноша -> ю́ношей, not *дядь / *юнош. The hard ones (мужчи́на ->
            # мужчи́н, де́душка -> де́душек) coincide with the feminine ending
            # anyway. A real feminine is unaffected: зада́ча -> зада́ч.
            if (
                grammatical is Gender.MASC
                and gender is Gender.FEMN
                and (_is_soft(gender, index) or index.type == 4)
            ):
                return "ей"
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
        if index.type == 7:
            return _FEM_IJA_SG.get(case)
        if index.type in (2, 6):
            return _FEM_JA_SG.get(case)
        return _FEM_A_SG.get(case)
    if index.type == 7:
        return _NEUT_IJE_SG.get(case)
    if index.type in (2, 6):
        return _NEUT_E_SG.get(case)
    return _NEUT_O_SG.get(case)


#: ку́хня takes о where every comparable soft stem takes е (ку́хонь, not
#: *ку́хень). Zaliznyak lists it as an individual irregularity too.
_HARD_FLEETING_VOWEL = frozenset({"кухня"})

#: The -ня nouns that keep the soft sign against the rule below. A short,
#: closed list -- Zaliznyak names them individually too.
_SOFT_SIGN_EXCEPTIONS = frozenset({"кухня", "деревня", "барышня"})


def _keeps_soft_sign(lemma: str, stem: str) -> bool:
    """Whether a -ня noun writes ь in its zero-ending genitive plural.

    The rule keys on what precedes the н: a consonant drops the ь (пе́сня ->
    пе́сен), a vowel keeps it (пусты́ня -> пусты́нь, я́блоня -> я́блонь). Only
    -ня behaves this way; -ля and -ря keep the ь throughout (неде́ль, бурь).
    """
    if not lemma.endswith("ня") or lemma in _SOFT_SIGN_EXCEPTIONS:
        return True
    return len(stem) < 2 or stem[-2] in "аеёиоуыэюя"


def _is_soft(gender: Gender, index: Index) -> bool:
    """Soft stems take я/ю/и endings in the plural rather than а/у/ы."""
    if gender is Gender.MASC:
        return index.type in (2, 6, 7)
    if gender is Gender.FEMN:
        return index.type in (2, 6, 7, 8)
    return index.type in (2, 6, 7)


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
    """отец -> отц-, день -> дн-: the last о/е/ё before the final consonant goes.

    A soft sign is left behind only when the vowel that dropped was е/ё *and*
    the consonant before it was л: па́лец -> па́льца, лёд -> льда. There the л
    was soft and stays soft. A dropped о never softened anything, so переу́лок
    -> переу́лка and у́гол -> угла́ keep the л hard.
    """
    for i in range(len(stem) - 1, -1, -1):
        if stem[i] in "оеёя" and i == len(stem) - 2:
            if i > 0 and stem[i - 1] in "аеёиоуыэюя":
                # After a vowel the fleeting е is spelled й rather than
                # vanishing: кита́ец -> кита́йца, за́яц -> за́йца, бое́ц -> бойца́.
                return stem[:i] + "й" + stem[i + 1 :]
            soft_l = i > 0 and stem[i - 1] == "л" and stem[i] in "её"
            return stem[:i] + ("ь" if soft_l else "") + stem[i + 1 :]
    return stem


def _insert_fleeting(stem: str, *, soft: bool = False) -> str:
    """окн -> окон, ручк -> ручек: a vowel appears in the zero-ending genitive.

    A soft sign in that slot is *replaced* by the vowel rather than kept:
    судьб- -> суде́б, письм- -> пи́сем, свадьб- -> сва́деб. Writing the vowel in
    after the ь would give *судьеб, which is why this case is separated out.
    """
    if len(stem) < 2:
        return stem
    before, after = stem[-2], stem[-1]
    if before in "аеёиоуыэюя" or after in "аеёиоуыэюя":
        return stem
    if before in "ьй":
        # The soft sign or й is *replaced* by the vowel, not written through:
        # судьб- -> суде́б, письм- -> пи́сем, лине́йк- -> лине́ек.
        return stem[:-2] + "е" + after
    # е, not о, next to a soft or hushing consonant on either side:
    # полоте́нце -> полоте́нец, се́рдце -> серде́ц, ру́чка -> ру́чек. A soft stem
    # takes е as well -- пе́сня -> пе́сен, земля́ -> земе́ль -- while the hard
    # stems around them keep о (доска́ -> досо́к, окно́ -> о́кон).
    vowel = "е" if soft or before in HUSHING_OR_TS or after == "ц" else "о"
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
