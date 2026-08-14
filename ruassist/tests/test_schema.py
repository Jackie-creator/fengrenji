"""Tests for the entry schema.

The point of these is that a bad entry must fail loudly at build time rather
than reach a learner. Each test corresponds to a mistake that is easy to make
while authoring by hand.
"""

import pytest
from pydantic import ValidationError

from ruassist.schema import LexEntry


def entry(**overrides):
    base = {
        "lemma": "рука",
        "stress": "рука́",
        "pos": "noun",
        "gender": "femn",
        "animacy": "inan",
        "zaliznyak": "ж 3d",
        "senses": [{"zh": "手"}],
    }
    return base | overrides


class TestIdentity:
    def test_minimal_entry_is_valid(self):
        assert LexEntry.model_validate(entry()).lemma == "рука"

    def test_lemma_must_not_carry_stress(self):
        with pytest.raises(ValidationError, match="must not carry stress"):
            LexEntry.model_validate(entry(lemma="рука́"))

    def test_stress_must_match_lemma(self):
        with pytest.raises(ValidationError, match="does not match lemma"):
            LexEntry.model_validate(entry(stress="ного́й"))

    def test_unstressed_stress_field_rejected(self):
        with pytest.raises(ValidationError, match="unstressed polysyllabic"):
            LexEntry.model_validate(entry(stress="рука"))

    def test_homonyms_get_distinct_keys(self):
        a = LexEntry.model_validate(entry(lemma="мир", stress="мир", homonym_id=1))
        b = LexEntry.model_validate(entry(lemma="мир", stress="мир", homonym_id=2))
        assert a.key != b.key


class TestRequiredByPos:
    def test_noun_requires_gender(self):
        data = entry()
        del data["gender"]
        with pytest.raises(ValidationError, match="requires gender"):
            LexEntry.model_validate(data)

    def test_noun_requires_animacy(self):
        data = entry()
        del data["animacy"]
        with pytest.raises(ValidationError, match="requires animacy"):
            LexEntry.model_validate(data)

    def test_verb_requires_aspect(self):
        with pytest.raises(ValidationError, match="requires aspect"):
            LexEntry.model_validate(
                {
                    "lemma": "читать",
                    "stress": "чита́ть",
                    "pos": "verb",
                    "transitivity": "trans",
                    "zaliznyak": "нсв 1a",
                    "senses": [{"zh": "读"}],
                }
            )

    def test_open_class_needs_a_paradigm_or_overrides(self):
        """A noun with neither an index nor hand-written forms cannot inflect."""
        data = entry()
        del data["zaliznyak"]
        with pytest.raises(ValidationError, match="zaliznyak index or explicit"):
            LexEntry.model_validate(data)


class TestMorphologyHooks:
    def test_malformed_zaliznyak_rejected(self):
        with pytest.raises(ValidationError, match="malformed Zaliznyak"):
            LexEntry.model_validate(entry(zaliznyak="feminine-3d"))

    @pytest.mark.parametrize(
        "index", ["м 1c(1)", "ж 3*d", "с 1*d", "п 3a*", "нсв 6°b", "св 4c", "п 4a/c"]
    )
    def test_real_indices_accepted(self, index):
        assert LexEntry.model_validate(entry(zaliznyak=index)).zaliznyak == index

    def test_unknown_grammeme_rejected(self):
        with pytest.raises(ValidationError, match="unknown grammemes"):
            LexEntry.model_validate(entry(form_overrides={"sing,dative": "руке́"}))

    def test_override_form_must_be_stressed(self):
        with pytest.raises(ValidationError, match="unstressed polysyllabic"):
            LexEntry.model_validate(entry(form_overrides={"sing,accs": "руку"}))

    def test_valid_override_accepted(self):
        e = LexEntry.model_validate(entry(form_overrides={"sing,accs": "ру́ку"}))
        assert e.form_overrides["sing,accs"] == "ру́ку"

    def test_entries_never_declare_forms_directly(self):
        """`forms` is generated, never authored -- extra keys must be rejected."""
        with pytest.raises(ValidationError):
            LexEntry.model_validate(entry(forms=["рука́", "руки́"]))


class TestLexicography:
    def test_unknown_level_rejected(self):
        with pytest.raises(ValidationError, match="unknown level tags"):
            LexEntry.model_validate(entry(level=["HSK4"]))

    def test_unknown_style_label_rejected(self):
        with pytest.raises(ValidationError, match="unknown style labels"):
            LexEntry.model_validate(entry(senses=[{"zh": "手", "labels": ["古语"]}]))

    def test_example_must_be_stressed(self):
        with pytest.raises(ValidationError, match="unstressed polysyllabic"):
            LexEntry.model_validate(
                entry(senses=[{"zh": "手", "examples": [{"ru": "Это рука.", "zh": "这是手。"}]}])
            )

    def test_collocations_must_be_stressed(self):
        with pytest.raises(ValidationError, match="unstressed polysyllabic"):
            LexEntry.model_validate(
                entry(senses=[{"zh": "手", "collocations": ["правая рука́"]}])
            )

    def test_at_least_one_sense_required(self):
        with pytest.raises(ValidationError):
            LexEntry.model_validate(entry(senses=[]))

    def test_reference_fields_must_be_plain(self):
        with pytest.raises(ValidationError, match="must be a plain lemma"):
            LexEntry.model_validate(
                {
                    "lemma": "читать",
                    "stress": "чита́ть",
                    "pos": "verb",
                    "aspect": "impf",
                    "transitivity": "trans",
                    "zaliznyak": "нсв 1a",
                    "aspect_pair": "прочита́ть",
                    "senses": [{"zh": "读"}],
                }
            )
