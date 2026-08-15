"""Morphological generation: Zaliznyak paradigms expanded into stressed forms."""

from .engine import INFLECTED, Paradigm, inflect
from .forms import Form, canonical_tag, parse_tag
from .zaliznyak import Index, UnsupportedIndex, parse

__all__ = [
    "INFLECTED",
    "Form",
    "Index",
    "Paradigm",
    "UnsupportedIndex",
    "canonical_tag",
    "inflect",
    "parse",
    "parse_tag",
]
