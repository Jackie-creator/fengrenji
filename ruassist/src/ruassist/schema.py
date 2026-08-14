"""Lexicon entry schema -- the executable definition of the data contract.

Design rule inherited from the wider repository: *the author supplies
classification and meaning, the engine supplies word forms.* Concretely, an
entry never stores its inflected forms. It stores a Zaliznyak paradigm index,
and the build step expands that index into the full paradigm. Only genuinely
suppletive or irregular forms that no paradigm can produce are written by hand,
in ``form_overrides``.

This keeps the hand-authored surface small (where authoring errors are
plausible) and the generated surface large (where errors are impossible by
construction).
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from . import stress as st


class POS(StrEnum):
    NOUN = "noun"
    VERB = "verb"
    ADJ = "adj"
    ADV = "adv"
    PRON = "pron"
    NUM = "num"
    PREP = "prep"
    CONJ = "conj"
    PART = "part"
    INTERJ = "interj"
    PREDIC = "predic"  # категория состояния: можно, нужно, жаль


class Gender(StrEnum):
    MASC = "masc"
    FEMN = "femn"
    NEUT = "neut"
    COMMON = "common"  # сирота, коллега -- agrees by referent


class Animacy(StrEnum):
    ANIM = "anim"
    INAN = "inan"


class Aspect(StrEnum):
    IMPF = "impf"
    PERF = "perf"
    BOTH = "both"  # двувидовой: использовать, женить


class Transitivity(StrEnum):
    TRANS = "trans"
    INTRANS = "intrans"


class MotionGroup(StrEnum):
    """Russian motion verbs come in unidirectional/multidirectional pairs."""

    UNI = "uni"  # идти, ехать -- one direction, one occasion
    MULTI = "multi"  # ходить, ездить -- repeated, habitual, round trip
    PREFIXED = "prefixed"  # пойти, поехать -- prefixed perfective


#: Grammeme inventory for ``form_overrides`` keys. Deliberately
#: OpenCorpora-compatible so the morphology engine can consume the same tags.
GRAMMEMES = frozenset(
    {
        # number
        "sing", "plur",
        # case
        "nomn", "gent", "datv", "accs", "ablt", "loct",
        "gen2",  # partitive: чаю, сахару
        "loc2",  # locative: в лесу́, на краю́
        "voct",  # vocative remnant: Бо́же, Госпо́ди
        # gender
        "masc", "femn", "neut",
        # person / tense / mood
        "1per", "2per", "3per",
        "pres", "past", "futr", "infn", "impr",
        # participles and gerunds
        "prtf", "prts", "grnd", "actv", "pssv",
        # adjective forms
        "adjf", "adjs", "comp", "supr",
    }
)

LEVELS = frozenset(
    {
        "A1", "A2", "B1", "B2", "C1", "C2",
        "高考", "专四", "专八",
        "ТРКИ-1", "ТРКИ-2", "ТРКИ-3", "ТРКИ-4",
    }
)

#: Zaliznyak index, e.g. "м 1c(1)", "ж 3*d", "с 1*d", "п 3a*", "нсв 6°b".
#: Only the shape is checked here; the morphology engine in M1 is the component
#: that must interpret it in full.
#:   <pos> <declension>[*|°]<stress-class>[′|*][/<stress-class>][(n)]
ZALIZNYAK_RE = re.compile(
    r"^[а-яё]{1,3} \d{1,2}[*°]?[a-f][′'*]?(/[a-f][′'*]?)?(\(\d\))?$"
)

STYLE_LABELS = frozenset(
    {
        "разг.",   # 口语
        "прост.",  # 俗语
        "книжн.",  # 书面
        "офиц.",   # 公文
        "устар.",  # 旧
        "поэт.",   # 诗歌
        "спец.",   # 专业
        "перен.",  # 转义
        "неодобр.",
    }
)


class Example(BaseModel):
    """A bilingual example. ``ru`` carries stress marks; ``zh`` is the gloss."""

    model_config = ConfigDict(extra="forbid")

    ru: str
    zh: str
    note: str | None = None

    @field_validator("ru")
    @classmethod
    def _check_stress(cls, v: str) -> str:
        return st.validate(v, field="example")


class Sense(BaseModel):
    """One numbered sense of an entry."""

    model_config = ConfigDict(extra="forbid")

    zh: str = Field(description="Chinese gloss -- the core hand-authored value")
    en: str | None = Field(default=None, description="English gloss, used to align with open-source data")
    labels: list[str] = Field(default_factory=list, description="Register/style labels")
    government: str | None = Field(default=None, description="Case government specific to this sense")
    collocations: list[str] = Field(default_factory=list)
    examples: list[Example] = Field(default_factory=list)

    @field_validator("labels")
    @classmethod
    def _check_labels(cls, v: list[str]) -> list[str]:
        unknown = set(v) - STYLE_LABELS
        if unknown:
            raise ValueError(f"unknown style labels: {sorted(unknown)}")
        return v

    @field_validator("collocations")
    @classmethod
    def _check_collocations(cls, v: list[str]) -> list[str]:
        return [st.validate(c, field="collocation") for c in v]


class LexEntry(BaseModel):
    """A single dictionary entry.

    Note the absence of any ``forms`` field: word forms are generated from
    ``zaliznyak`` at build time and are never authored by hand.
    """

    model_config = ConfigDict(extra="forbid")

    # --- identity -------------------------------------------------------
    lemma: str = Field(description="Canonical form, no stress marks")
    stress: str = Field(description="Same form with stress marked")
    pos: POS
    homonym_id: int | None = Field(
        default=None,
        description="Distinguishes same-spelling lexemes: мир¹ world / мир² peace",
    )

    # --- morphology hooks -----------------------------------------------
    zaliznyak: str | None = Field(
        default=None, description="Paradigm index driving form generation"
    )
    form_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Hand-written forms the paradigm cannot generate (suppletion)",
    )
    indeclinable: bool = False

    # --- noun -----------------------------------------------------------
    gender: Gender | None = None
    animacy: Animacy | None = None
    number_only: str | None = Field(default=None, description="'sing' or 'plur' only")
    plural_lemma: str | None = Field(
        default=None, description="Suppletive plural: человек -> люди"
    )

    # --- verb -----------------------------------------------------------
    aspect: Aspect | None = None
    aspect_pair: str | None = None
    transitivity: Transitivity | None = None
    reflexive: bool = False
    government: str | None = Field(default=None, description="что / кого-что / кому / чем")
    motion_group: MotionGroup | None = None
    motion_partner: str | None = None

    # --- adjective ------------------------------------------------------
    short_form: bool | None = None
    comparative: str | None = None
    superlative: str | None = None

    # --- lexicography ---------------------------------------------------
    level: list[str] = Field(default_factory=list)
    freq_rank: int | None = None
    senses: list[Sense] = Field(min_length=1)
    synonyms: list[str] = Field(default_factory=list)
    antonyms: list[str] = Field(default_factory=list)
    word_family: list[str] = Field(default_factory=list)

    # --- teaching notes (the differentiator vs. a plain bilingual dict) ---
    aspect_note: str | None = None
    common_errors: str | None = None
    notes: str | None = None

    # --- provenance -----------------------------------------------------
    verify: list[str] = Field(
        default_factory=list,
        description="Fields to cross-check against OpenCorpora/OpenRussian before shipping",
    )
    audio: str | None = None

    # --- validation -----------------------------------------------------
    @field_validator("stress")
    @classmethod
    def _check_stress(cls, v: str) -> str:
        return st.validate(v, field="stress")

    @field_validator("lemma")
    @classmethod
    def _check_lemma_plain(cls, v: str) -> str:
        if st.STRESS in st.normalize(v):
            raise ValueError(f"lemma must not carry stress marks: {v!r}")
        return v

    @field_validator("aspect_pair", "motion_partner", "plural_lemma")
    @classmethod
    def _check_reference_is_plain(cls, v: str | None) -> str | None:
        """Cross-entry references are keys, so they carry no stress marks."""
        if v is not None and st.STRESS in st.normalize(v):
            raise ValueError(f"reference must be a plain lemma, got {v!r}")
        return v

    @field_validator("comparative", "superlative")
    @classmethod
    def _check_display_form_is_stressed(cls, v: str | None) -> str | None:
        """These are shown to the learner, so they must carry stress."""
        return st.validate(v, field="comparative/superlative") if v else v

    @field_validator("level")
    @classmethod
    def _check_level(cls, v: list[str]) -> list[str]:
        unknown = set(v) - LEVELS
        if unknown:
            raise ValueError(f"unknown level tags: {sorted(unknown)}")
        return v

    @field_validator("zaliznyak")
    @classmethod
    def _check_zaliznyak(cls, v: str | None) -> str | None:
        if v is not None and not ZALIZNYAK_RE.match(v):
            raise ValueError(f"malformed Zaliznyak index: {v!r}")
        return v

    @field_validator("form_overrides")
    @classmethod
    def _check_overrides(cls, v: dict[str, str]) -> dict[str, str]:
        for tag, form in v.items():
            grammemes = {g.strip() for g in tag.split(",")}
            unknown = grammemes - GRAMMEMES
            if unknown:
                raise ValueError(f"unknown grammemes in {tag!r}: {sorted(unknown)}")
            st.validate(form, field=f"form_overrides[{tag}]")
        return v

    @model_validator(mode="after")
    def _check_consistency(self) -> LexEntry:
        if not st.agrees_with_lemma(self.stress, self.lemma):
            raise ValueError(
                f"stress {self.stress!r} does not match lemma {self.lemma!r}"
            )

        if self.pos is POS.NOUN and self.gender is None:
            raise ValueError(f"{self.lemma}: noun requires gender")
        if self.pos is POS.NOUN and self.animacy is None:
            raise ValueError(f"{self.lemma}: noun requires animacy")

        if self.pos is POS.VERB:
            if self.aspect is None:
                raise ValueError(f"{self.lemma}: verb requires aspect")
            if self.transitivity is None:
                raise ValueError(f"{self.lemma}: verb requires transitivity")

        if self.number_only not in (None, "sing", "plur"):
            raise ValueError(f"{self.lemma}: number_only must be 'sing' or 'plur'")

        if not self.indeclinable and self.zaliznyak is None and self.pos in {
            POS.NOUN,
            POS.VERB,
            POS.ADJ,
        }:
            # Pronouns and numerals have closed, hand-listed paradigms; open
            # classes must declare one so the engine can inflect them.
            if not self.form_overrides:
                raise ValueError(
                    f"{self.lemma}: needs a zaliznyak index or explicit form_overrides"
                )

        return self

    @property
    def key(self) -> str:
        """Stable identifier, disambiguated for homonyms."""
        base = st.search_key(self.lemma)
        return f"{base}#{self.pos}" + (f"#{self.homonym_id}" if self.homonym_id else "")
