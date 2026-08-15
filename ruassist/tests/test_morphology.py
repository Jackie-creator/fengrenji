"""Tests for paradigm generation.

Expected forms are written out by hand, the way the geometry project writes its
arithmetic into test comments. A paradigm that agrees with pymorphy3 but not
with the grammar book is still wrong, so the reference here is the grammar.
"""

import pytest

from ruassist.morphology import canonical_tag as ct
from ruassist.morphology import inflect, parse
from ruassist.morphology.adjectives import is_end_stressed, is_soft
from ruassist.morphology.zaliznyak import ENDING, STEM, noun_stress
from ruassist.schema import LexEntry


def noun(lemma, stress, zaliznyak, gender, animacy="inan", **kw):
    return LexEntry.model_validate(
        {
            "lemma": lemma, "stress": stress, "pos": "noun",
            "gender": gender, "animacy": animacy, "zaliznyak": zaliznyak,
            "senses": [{"zh": "—"}], **kw,
        }
    )


def verb(lemma, stress, zaliznyak, aspect, **kw):
    return LexEntry.model_validate(
        {
            "lemma": lemma, "stress": stress, "pos": "verb",
            "aspect": aspect, "transitivity": "trans", "zaliznyak": zaliznyak,
            "senses": [{"zh": "—"}], **kw,
        }
    )


def adj(lemma, stress, zaliznyak, **kw):
    return LexEntry.model_validate(
        {
            "lemma": lemma, "stress": stress, "pos": "adj",
            "zaliznyak": zaliznyak, "senses": [{"zh": "—"}], **kw,
        }
    )


def cells(entry, *tagsets):
    paradigm = inflect(entry)
    return [paradigm.cells[ct(set(t))].text for t in tagsets]


SG = [("sing", c) for c in ("nomn", "gent", "datv", "accs", "ablt", "loct")]
PL = [("plur", c) for c in ("nomn", "gent", "datv", "accs", "ablt", "loct")]


class TestIndexParsing:
    def test_full_index(self):
        index = parse("ж 3*d")
        assert (index.grammatical_class, index.type, index.scheme) == ("ж", 3, "d")
        assert index.fleeting and not index.acc_sg_stem

    def test_plural_marker(self):
        assert parse("м 1c(1)").nominative_plural_in_a
        assert not parse("м 1b").nominative_plural_in_a

    def test_verb_class(self):
        assert parse("нсв 6°b").irregular
        assert parse("нсв 1a").is_verb

    @pytest.mark.parametrize("bad", ["3d", "ж3d", "ж 3z", "feminine"])
    def test_malformed_rejected(self, bad):
        with pytest.raises(ValueError):
            parse(bad)


class TestStressSchemes:
    def test_scheme_c_moves_to_the_ending_in_the_plural(self):
        # го́род / го́рода ... but города́ / городо́в
        index = parse("м 1c(1)")
        assert noun_stress(index, "sing", "gent") is STEM
        assert noun_stress(index, "plur", "gent") is ENDING

    def test_scheme_d_is_the_mirror_image(self):
        # рука́ / руки́ ... but ру́ки / рук
        index = parse("ж 3d")
        assert noun_stress(index, "sing", "gent") is ENDING
        assert noun_stress(index, "plur", "nomn") is STEM

    def test_scheme_e_splits_the_plural(self):
        # но́чи (nom) but ноче́й / ноча́м
        index = parse("ж 8e")
        assert noun_stress(index, "plur", "nomn") is STEM
        assert noun_stress(index, "plur", "gent") is ENDING


class TestNouns:
    def test_hard_masculine_end_stressed(self):
        # стол «м 1b»: stress on the ending throughout, invisible in the
        # nominative because the ending is zero.
        entry = noun("стол", "стол", "м 1b", "masc")
        assert cells(entry, *SG) == [
            "стол", "стола́", "столу́", "стол", "столо́м", "столе́",
        ]
        assert cells(entry, *PL) == [
            "столы́", "столо́в", "стола́м", "столы́", "стола́ми", "стола́х",
        ]

    def test_velar_stem_spells_and_not_y(self):
        # кни́га «ж 3a»: after г the ending -ы is written -и.
        entry = noun("книга", "кни́га", "ж 3a", "femn")
        assert cells(entry, ("sing", "gent")) == ["кни́ги"]
        assert cells(entry, ("plur", "nomn")) == ["кни́ги"]

    def test_mobile_stress_with_accusative_exception(self):
        # рука́ «ж 3d»: singular takes the ending (руки́, руко́й) except the
        # accusative, which retracts to the stem: ру́ку. Plural is stem-stressed
        # in the nominative and genitive, ending-stressed below.
        entry = noun("рука", "рука́", "ж 3d", "femn", form_overrides={"sing,accs": "ру́ку"})
        assert cells(entry, *SG) == [
            "рука́", "руки́", "руке́", "ру́ку", "руко́й", "руке́",
        ]
        assert cells(entry, ("plur", "nomn"), ("plur", "gent")) == ["ру́ки", "рук"]

    def test_fleeting_vowel_appears_in_genitive_plural(self):
        # окно́ «с 1*d»: the * marks a vowel that surfaces when the ending is
        # zero -- о́кон, not *окн.
        entry = noun("окно", "окно́", "с 1*d", "neut")
        assert cells(entry, ("plur", "gent")) == ["о́кон"]

    def test_fleeting_vowel_drops_in_masculine_obliques(self):
        # оте́ц «м 5*b»: the е disappears the moment an ending is added.
        entry = noun("отец", "оте́ц", "м 5*b", "masc", animacy="anim")
        assert cells(entry, ("sing", "gent"), ("sing", "ablt")) == ["отца́", "отцо́м"]

    def test_soft_feminine_genitive_plural_takes_a_soft_sign(self):
        # неде́ля «ж 2a» -> неде́ль
        entry = noun("неделя", "неде́ля", "ж 2a", "femn")
        assert cells(entry, ("plur", "gent")) == ["неде́ль"]

    def test_animacy_drives_the_accusative(self):
        """The accusative copies the nominative or the genitive, never its own."""
        inanimate = noun("стол", "стол", "м 1b", "masc")
        animate = noun("отец", "оте́ц", "м 5*b", "masc", animacy="anim")
        assert cells(inanimate, ("sing", "accs")) == cells(inanimate, ("sing", "nomn"))
        assert cells(animate, ("sing", "accs")) == cells(animate, ("sing", "gent"))

    def test_nominative_plural_in_a(self):
        # го́род «м 1c(1)»: the (1) marker gives города́, not *го́роды.
        entry = noun("город", "го́род", "м 1c(1)", "masc")
        assert cells(entry, ("plur", "nomn"), ("plur", "gent")) == ["города́", "городо́в"]

    def test_stressed_instrumental_of_a_soft_stem_uses_yo(self):
        # день «м 2*b» -> днём, not *днем
        entry = noun("день", "день", "м 2*b", "masc")
        assert cells(entry, ("sing", "ablt")) == ["днём"]

    def test_hushing_stem_keeps_o_when_stressed(self):
        # каранда́ш «м 4b»: карандашо́м (stressed о) but genitive plural -ей.
        entry = noun("карандаш", "каранда́ш", "м 4b", "masc")
        assert cells(entry, ("sing", "ablt"), ("plur", "gent")) == [
            "карандашо́м", "карандаше́й",
        ]

    def test_indeclinable_noun_has_one_shape(self):
        entry = LexEntry.model_validate(
            {
                "lemma": "метро", "stress": "метро́", "pos": "noun",
                "gender": "neut", "animacy": "inan", "indeclinable": True,
                "senses": [{"zh": "地铁"}],
            }
        )
        assert set(cells(entry, *SG, *PL)) == {"метро́"}


class TestAdjectives:
    def test_hard_paradigm(self):
        entry = adj("новый", "но́вый", "п 1a")
        assert cells(
            entry,
            ("adjf", "sing", "masc", "nomn"),
            ("adjf", "sing", "femn", "nomn"),
            ("adjf", "sing", "neut", "nomn"),
            ("adjf", "plur", "nomn"),
        ) == ["но́вый", "но́вая", "но́вое", "но́вые"]

    def test_soft_paradigm(self):
        entry = adj("синий", "си́ний", "п 4a")
        assert cells(
            entry,
            ("adjf", "sing", "masc", "nomn"),
            ("adjf", "sing", "femn", "nomn"),
            ("adjf", "sing", "neut", "nomn"),
            ("adjf", "plur", "nomn"),
        ) == ["си́ний", "си́няя", "си́нее", "си́ние"]

    def test_end_stressed_masculine_takes_oy(self):
        # большо́й, not *бо́льший; and the stressed genitive keeps its о.
        entry = adj("большой", "большо́й", "п 1b")
        assert cells(
            entry,
            ("adjf", "sing", "masc", "nomn"),
            ("adjf", "sing", "masc", "gent"),
        ) == ["большо́й", "большо́го"]

    def test_hushing_stem_uses_e_when_unstressed(self):
        # хоро́шего, because the ending is unstressed -- contrast большо́го.
        entry = adj("хороший", "хоро́ший", "п 4a")
        assert cells(entry, ("adjf", "sing", "masc", "gent")) == ["хоро́шего"]

    def test_softness_is_read_from_spelling_not_the_index(self):
        """хоро́ший and си́ний share the index «п 4a» but decline differently."""
        assert is_soft("синий") and is_soft("последний")
        assert not is_soft("хороший")  # hushing stem, declines hard
        assert not is_soft("русский")  # velar stem, declines hard

    def test_scheme_letter_describes_short_forms_only(self):
        """весёлый is «п 1*b» because of весела́, but весёлый itself is stem-stressed."""
        assert not is_end_stressed("весёлый")
        assert is_end_stressed("большой")
        entry = adj("весёлый", "весёлый", "п 1*b")
        assert cells(entry, ("adjf", "sing", "masc", "nomn")) == ["весёлый"]


class TestVerbs:
    def test_first_conjugation(self):
        entry = verb("читать", "чита́ть", "нсв 1a", "impf")
        assert cells(
            entry,
            ("pres", "1per", "sing"), ("pres", "2per", "sing"), ("pres", "3per", "plur"),
        ) == ["чита́ю", "чита́ешь", "чита́ют"]
        assert cells(entry, ("impr", "sing"), ("impr", "plur")) == ["чита́й", "чита́йте"]

    def test_second_conjugation_end_stressed(self):
        entry = verb("говорить", "говори́ть", "нсв 4b", "impf")
        assert cells(
            entry,
            ("pres", "1per", "sing"), ("pres", "2per", "sing"), ("pres", "3per", "plur"),
        ) == ["говорю́", "говори́шь", "говоря́т"]

    def test_scheme_c_retracts_after_the_first_person(self):
        # пишу́ but пи́шешь -- the single most-mispronounced pattern.
        entry = verb("писать", "писа́ть", "нсв 6c", "impf")
        assert cells(
            entry, ("pres", "1per", "sing"), ("pres", "2per", "sing")
        ) == ["пишу́", "пи́шешь"]

    def test_labial_takes_epenthetic_l_in_the_first_person_only(self):
        entry = verb("любить", "люби́ть", "нсв 4c", "impf")
        assert cells(
            entry, ("pres", "1per", "sing"), ("pres", "2per", "sing")
        ) == ["люблю́", "лю́бишь"]

    def test_consonant_alternation_in_the_first_person(self):
        # ходи́ть -> хожу́ (д -> ж), but хо́дишь keeps the д.
        entry = verb("ходить", "ходи́ть", "нсв 4c", "impf", transitivity="intrans")
        assert cells(
            entry, ("pres", "1per", "sing"), ("pres", "2per", "sing")
        ) == ["хожу́", "хо́дишь"]

    def test_hushing_stem_takes_u_and_at(self):
        entry = verb("слышать", "слы́шать", "нсв 5a", "impf")
        assert cells(
            entry, ("pres", "1per", "sing"), ("pres", "3per", "plur")
        ) == ["слы́шу", "слы́шат"]

    def test_perfective_conjugates_into_the_future(self):
        entry = verb("купить", "купи́ть", "св 4c", "perf")
        paradigm = inflect(entry)
        assert ct({"futr", "1per", "sing"}) in paradigm.cells
        assert ct({"pres", "1per", "sing"}) not in paradigm.cells

    def test_imperative_takes_i_after_a_consonant_cluster(self):
        # е́здить -> е́зди, not *е́здь, even though the stem is stressed.
        entry = verb("ездить", "е́здить", "нсв 4a", "impf", transitivity="intrans")
        assert cells(entry, ("impr", "sing"), ("impr", "plur")) == ["е́зди", "е́здите"]

    def test_imperative_takes_soft_sign_after_a_single_consonant(self):
        entry = verb("ответить", "отве́тить", "св 4a", "perf", transitivity="intrans")
        assert cells(entry, ("impr", "sing"), ("impr", "plur")) == ["отве́ть", "отве́тьте"]

    def test_past_tense_from_the_infinitive_stem(self):
        entry = verb("читать", "чита́ть", "нсв 1a", "impf")
        assert cells(
            entry, ("past", "masc"), ("past", "femn"), ("past", "plur")
        ) == ["чита́л", "чита́ла", "чита́ли"]


class TestEngineContract:
    def test_every_generated_form_is_stressed(self):
        """Rule 1 of docs/SCHEMA.md, enforced rather than trusted."""
        entry = noun("книга", "кни́га", "ж 3a", "femn")
        for form in inflect(entry).forms:
            assert form.text

    def test_overrides_replace_generated_cells(self):
        entry = noun(
            "город", "го́род", "м 1c(1)", "masc",
            form_overrides={"plur,nomn": "городя́"},
        )
        assert cells(entry, ("plur", "nomn")) == ["городя́"]

    def test_overrides_land_before_the_accusative_is_derived(self):
        """я́блоко's hand-written plural must propagate into the accusative."""
        entry = noun(
            "яблоко", "я́блоко", "с 3a", "neut",
            form_overrides={"plur,nomn": "я́блоки", "plur,gent": "я́блок"},
        )
        assert cells(entry, ("plur", "accs")) == ["я́блоки"]

    def test_suppletive_entry_reports_why_it_was_not_generated(self):
        entry = LexEntry.model_validate(
            {
                "lemma": "идти", "stress": "идти́", "pos": "verb",
                "aspect": "impf", "transitivity": "intrans",
                "form_overrides": {"past,masc": "шёл", "past,femn": "шла"},
                "senses": [{"zh": "走"}],
            }
        )
        paradigm = inflect(entry)
        assert not paradigm.generated
        assert "suppletive" in paradigm.reason
        assert paradigm.cells[ct({"past", "masc"})].text == "шёл"


class TestReflexiveVerbs:
    """-ся verbs are conjugated as their plain stem, then the postfix returns."""

    def test_postfix_alternates_by_preceding_sound(self):
        # -сь after a vowel, -ся after a consonant or soft sign.
        entry = verb(
            "заниматься", "занима́ться", "нсв 1a", "impf",
            transitivity="intrans", reflexive=True,
        )
        assert cells(
            entry,
            ("pres", "1per", "sing"),   # vowel -> -сь
            ("pres", "2per", "sing"),   # soft sign -> -ся
            ("pres", "3per", "sing"),   # consonant -> -ся
            ("pres", "2per", "plur"),   # vowel -> -сь
        ) == ["занима́юсь", "занима́ешься", "занима́ется", "занима́етесь"]

    def test_past_tense_takes_the_postfix_too(self):
        entry = verb(
            "заниматься", "занима́ться", "нсв 1a", "impf",
            transitivity="intrans", reflexive=True,
        )
        assert cells(entry, ("past", "masc"), ("past", "femn")) == [
            "занима́лся", "занима́лась",
        ]

    def test_infinitive_is_left_alone(self):
        entry = verb(
            "нравиться", "нра́виться", "нсв 4a", "impf",
            transitivity="intrans", reflexive=True,
        )
        assert inflect(entry).cells[ct({"infn"})].text == "нра́виться"

    def test_monosyllabic_base_gains_a_stress_mark(self):
        """нравь carries no mark alone, but нра́вься is polysyllabic."""
        entry = verb(
            "нравиться", "нра́виться", "нсв 4a", "impf",
            transitivity="intrans", reflexive=True,
        )
        assert cells(entry, ("impr", "sing")) == ["нра́вься"]

    def test_first_person_alternation_still_applies(self):
        entry = verb(
            "находиться", "находи́ться", "нсв 4c", "impf",
            transitivity="intrans", reflexive=True,
        )
        assert cells(entry, ("pres", "1per", "sing")) == ["нахожу́сь"]


class TestDeclensionGender:
    """Grammatical gender governs agreement; the ending shape governs declension."""

    def test_masculine_noun_in_a_declines_like_a_feminine(self):
        # мужчи́на is masculine -- "молодо́й мужчи́на" -- but declines in -а.
        entry = noun("мужчина", "мужчи́на", "м 1a", "masc", animacy="anim")
        assert cells(entry, ("sing", "nomn"), ("sing", "gent"), ("sing", "accs")) == [
            "мужчи́на", "мужчи́ны", "мужчи́ну",
        ]

    def test_its_grammatical_gender_is_untouched(self):
        entry = noun("мужчина", "мужчи́на", "м 1a", "masc", animacy="anim")
        assert entry.gender.value == "masc"

    def test_ordinary_masculine_is_unaffected(self):
        entry = noun("стол", "стол", "м 1b", "masc")
        assert cells(entry, ("sing", "gent")) == ["стола́"]

    def test_animacy_still_drives_the_plural_accusative(self):
        entry = noun("мужчина", "мужчи́на", "м 1a", "masc", animacy="anim")
        assert cells(entry, ("plur", "accs")) == cells(entry, ("plur", "gent"))


class TestSoftStemNouns:
    """Types 6 and 7 differ in one cell, and that cell is a frequent one."""

    def test_type_7_feminine_takes_i_where_type_6_takes_e(self):
        # исто́рия -> в исто́рии, but иде́я -> об иде́е.
        seven = noun("история", "исто́рия", "ж 7a", "femn")
        six = noun("идея", "иде́я", "ж 6a", "femn")
        assert cells(seven, ("sing", "datv"), ("sing", "loct")) == ["исто́рии", "исто́рии"]
        assert cells(six, ("sing", "datv"), ("sing", "loct")) == ["иде́е", "иде́е"]

    def test_type_7_neuter_prepositional_is_ii(self):
        # мне́ние -> о мне́нии, not *о мне́ние.
        entry = noun("мнение", "мне́ние", "с 7a", "neut")
        assert cells(entry, ("sing", "loct")) == ["мне́нии"]

    def test_soft_stems_take_soft_plural_endings(self):
        entry = noun("идея", "иде́я", "ж 6a", "femn")
        assert cells(entry, ("plur", "gent"), ("plur", "datv")) == ["иде́й", "иде́ям"]


class TestNumberOnly:
    """A noun with only one number must not have cells in the other."""

    def test_singular_only_noun_has_no_plural(self):
        entry = noun("здоровье", "здоро́вье", "с 6a", "neut", number_only="sing")
        paradigm = inflect(entry)
        assert not [t for t in paradigm.cells if "plur" in t]

    def test_plural_only_noun_has_no_singular(self):
        entry = noun(
            "деньги", "де́ньги", "ж 3a", "femn", number_only="plur",
            form_overrides={"plur,gent": "де́нег"},
        )
        paradigm = inflect(entry)
        assert not [t for t in paradigm.cells if "sing" in t]


class TestMasculineInJa:
    def test_takes_the_masculine_genitive_plural(self):
        # дя́дя declines as a soft feminine but keeps дя́дей, not *дядь.
        entry = noun("дядя", "дя́дя", "м 2a", "masc", animacy="anim")
        assert cells(entry, ("plur", "gent")) == ["дя́дей"]

    def test_hard_masculine_in_a_matches_the_feminine_ending(self):
        entry = noun("мужчина", "мужчи́на", "м 1a", "masc", animacy="anim")
        assert cells(entry, ("plur", "gent")) == ["мужчи́н"]


class TestClassTwoVerbs:
    """-овать loses its suffix and gains -у-: the class borrowed verbs join."""

    def test_present_stem_replaces_ova_with_u(self):
        entry = verb("советовать", "сове́товать", "нсв 2a", "impf")
        assert cells(
            entry, ("pres", "1per", "sing"), ("pres", "2per", "sing"),
        ) == ["сове́тую", "сове́туешь"]

    def test_stress_follows_the_shortened_stem(self):
        # интересова́ть is end-stressed, and the stress lands on the new -у-.
        entry = verb(
            "интересоваться", "интересова́ться", "нсв 2a", "impf",
            transitivity="intrans", reflexive=True,
        )
        assert cells(entry, ("pres", "1per", "sing")) == ["интересу́юсь"]

    def test_imperative_takes_j_after_the_vowel_stem(self):
        entry = verb("советовать", "сове́товать", "нсв 2a", "impf")
        assert cells(entry, ("impr", "plur")) == ["сове́туйте"]


def test_stressed_verb_ending_uses_yo():
    """смею́сь but смеёшься -- a stressed е at the head of an ending is ё."""
    entry = verb(
        "смеяться", "смея́ться", "нсв 6b", "impf",
        transitivity="intrans", reflexive=True,
    )
    assert cells(entry, ("pres", "2per", "sing")) == ["смеёшься"]
