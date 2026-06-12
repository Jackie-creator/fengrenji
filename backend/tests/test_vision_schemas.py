"""Schema validation tests for the vision layer (no API calls)."""

import pytest
from pydantic import ValidationError

from app.vision.schemas import AnalysisResult, Category, EdgeFinishGuess

VALID = {
    "category": "bifold_wallet",
    "confidence": 0.92,
    "estimated_dimensions_mm": {"width": 110.0, "height": 90.0, "depth": None},
    "scale_reference_detected": True,
    "structure": {
        "card_slots_left": 3,
        "card_slots_right": 2,
        "has_bill_compartment": True,
        "has_zipper_pocket": False,
        "edge_finish": "burnished",
    },
    "notes_for_user": "二折短夹，左 3 右 2 卡位。",
    "closest_template": None,
}


def test_valid_payload_parses():
    result = AnalysisResult.model_validate(VALID)
    assert result.category == Category.BIFOLD_WALLET
    assert result.structure.card_slots_left == 3
    assert result.estimated_dimensions_mm.depth is None
    assert result.structure.edge_finish == EdgeFinishGuess.BURNISHED


def test_confidence_bounds_enforced():
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate({**VALID, "confidence": 1.4})
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate({**VALID, "confidence": -0.1})


def test_unknown_category_rejected():
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate({**VALID, "category": "tote_bag"})


def test_unsupported_with_closest_template():
    result = AnalysisResult.model_validate(
        {**VALID, "category": "unsupported", "closest_template": "card_holder"}
    )
    assert result.category == Category.UNSUPPORTED
    assert result.closest_template == Category.CARD_HOLDER


def test_missing_dimensions_default_to_null():
    payload = {k: v for k, v in VALID.items() if k != "estimated_dimensions_mm"}
    result = AnalysisResult.model_validate(payload)
    assert result.estimated_dimensions_mm.width is None


def test_extra_fields_ignored():
    # Forward compatibility: the model adding a field must not break parsing.
    result = AnalysisResult.model_validate({**VALID, "surprise": 42})
    assert result.confidence == 0.92


def test_negative_slot_count_rejected():
    bad = {**VALID, "structure": {**VALID["structure"], "card_slots_left": -1}}
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate(bad)


def test_outline_hint_reserved_field():
    # Reserved for future irregular-shape support; accepts point arrays.
    result = AnalysisResult.model_validate(
        {**VALID, "outline_hint": [[0.0, 0.0], [1.0, 0.5]]}
    )
    assert result.outline_hint == [[0.0, 0.0], [1.0, 0.5]]
