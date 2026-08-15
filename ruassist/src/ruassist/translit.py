"""Latin -> Cyrillic input.

Chinese users do not have a Cyrillic keyboard, so typing the word is the first
place a Russian dictionary loses them. `privet` must find привет.

This is deliberately forgiving rather than a standard: it accepts the informal
spellings people actually type (shch/sch, ya/ja, yo/jo, x for х) instead of
insisting on GOST or ISO 9. Ambiguity is resolved toward the commoner reading --
`e` is е, not э -- and the fuzzy search layer in M2 absorbs the rest.
"""

from __future__ import annotations

#: Ordered longest-first so multi-character sequences win.
_RULES: list[tuple[str, str]] = [
    ("shch", "щ"), ("sch", "щ"), ("shh", "щ"),
    ("yo", "ё"), ("jo", "ё"), ("yu", "ю"), ("ju", "ю"),
    ("ya", "я"), ("ja", "я"), ("ye", "е"), ("je", "е"),
    ("zh", "ж"), ("kh", "х"), ("ts", "ц"), ("ch", "ч"), ("sh", "ш"),
    ("a", "а"), ("b", "б"), ("v", "в"), ("g", "г"), ("d", "д"),
    ("e", "е"), ("z", "з"), ("i", "и"), ("j", "й"), ("k", "к"),
    ("l", "л"), ("m", "м"), ("n", "н"), ("o", "о"), ("p", "п"),
    ("r", "р"), ("s", "с"), ("t", "т"), ("u", "у"), ("f", "ф"),
    ("h", "х"), ("x", "х"), ("c", "ц"), ("w", "в"), ("y", "ы"),
    ("'", "ь"), ("`", "ъ"), ('"', "ъ"),
]

_MAX_RULE = max(len(latin) for latin, _ in _RULES)
_LOOKUP = dict(_RULES)


def is_latin(text: str) -> bool:
    """True when the text contains Latin letters and no Cyrillic ones."""
    has_latin = any("a" <= ch.lower() <= "z" for ch in text)
    has_cyrillic = any("а" <= ch.lower() <= "я" or ch.lower() == "ё" for ch in text)
    return has_latin and not has_cyrillic


def to_cyrillic(text: str) -> str:
    """Transliterate Latin input, leaving anything else untouched."""
    if not is_latin(text):
        return text

    lowered = text.lower()
    out: list[str] = []
    i = 0
    while i < len(lowered):
        for size in range(_MAX_RULE, 0, -1):
            chunk = lowered[i : i + size]
            if chunk in _LOOKUP:
                out.append(_LOOKUP[chunk])
                i += size
                break
        else:
            out.append(lowered[i])
            i += 1
    return "".join(out)
