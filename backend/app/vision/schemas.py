"""Pydantic schemas for the vision analysis layer.

This is the contract between any vision backend (Claude today, possibly a
fine-tuned model on another platform later) and the geometry engine: the
model only ever produces this structured JSON; every drawing coordinate is
computed deterministically downstream.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Category(str, Enum):
    CARD_HOLDER = "card_holder"
    BIFOLD_WALLET = "bifold_wallet"
    ZIPPER_POUCH = "zipper_pouch"
    UNSUPPORTED = "unsupported"


class EdgeFinishGuess(str, Enum):
    BURNISHED = "burnished"
    FOLDED = "folded"
    BOUND = "bound"
    UNKNOWN = "unknown"


class EstimatedDimensions(BaseModel):
    """Overall product dimensions in mm. All fields are null unless a known
    scale reference (bank card, coin) was detected in the photos — the model
    must never fabricate dimensions.
    """

    model_config = ConfigDict(extra="ignore")

    width: float | None = None
    height: float | None = None
    depth: float | None = None


class Structure(BaseModel):
    model_config = ConfigDict(extra="ignore")

    card_slots_left: int = Field(default=0, ge=0, le=10)
    card_slots_right: int = Field(default=0, ge=0, le=10)
    has_bill_compartment: bool = False
    has_zipper_pocket: bool = False
    edge_finish: EdgeFinishGuess = EdgeFinishGuess.UNKNOWN


class AnalysisResult(BaseModel):
    """Validated output of one vision analysis call."""

    model_config = ConfigDict(extra="ignore")

    category: Category
    confidence: float = Field(ge=0.0, le=1.0)
    estimated_dimensions_mm: EstimatedDimensions = Field(default_factory=EstimatedDimensions)
    scale_reference_detected: bool = False
    structure: Structure = Field(default_factory=Structure)
    #: Chinese, user-facing: what was recognised and what is uncertain.
    notes_for_user: str = ""
    #: When category is "unsupported": the closest of the 3 templates, so the
    #: frontend can offer it for manual selection.
    closest_template: Category | None = None
    #: Reserved for future irregular-shape support: normalised outline key
    #: points ([[x, y], ...], 0-1 range). Always null in the MVP; the
    #: geometry engine — not the model — will fit and offset curves from it.
    outline_hint: list[list[float]] | None = None
