"""Acceptance tests for the CardHolder template.

The default-parameter hand calculation below is the reference for the
acceptance criterion "main panel dimensions match a manual calculation".
"""

import math

import pytest

from app.geometry.core import EdgeFinish
from app.geometry.templates.card_holder import CardHolder, CardHolderParams

# ---------------------------------------------------------------------------
# Hand calculation for the default card holder
# (slots=3, leather t=1.2 mm, seam allowance sa=3.5 mm, stagger=12 mm,
#  top slot height=40 mm, top margin=10 mm, burnished edges):
#
#   thickness compensation per wrapped layer per sewn edge = t*pi/2
#     comp(1) = 1.2*pi/2          = 1.884956 mm
#     comp(2) = 2*1.2*pi/2        = 3.769911 mm
#     comp(3) = 3*1.2*pi/2        = 5.654867 mm
#
#   slot net width (stitch-to-stitch, must clear card + ease)
#     = 85.6 + 1.5               = 87.1 mm
#
#   MAIN PANEL (wraps the whole 3-layer slot stack, d = 3):
#     net width  = 87.1 + 2*comp(3)            # left + right sewn edges
#                = 87.1 + 11.309734            = 98.409734 mm
#     net height = stagger*(slots-1) + card height + top margin + comp(3)
#                = 12*2 + 54 + 10 + 5.654867   # bottom sewn edge only
#                = 93.654867 mm
#     cut width  = net + 2*sa = 98.409734 + 7  = 105.409734 mm
#     cut height = net + 2*sa = 93.654867 + 7  = 100.654867 mm
#
#   SLOT PIECES (i = 1 nearest cavity, wraps d = i-1 layers):
#     slot 1: net 87.1            x 40           -> cut 94.1      x 47
#     slot 2: net 87.1+2*comp(1)  x 52+comp(1)   -> cut 97.869911 x 60.884956
#     slot 3: net 87.1+2*comp(2)  x 64+comp(2)   -> cut 101.639823x 74.769911
# ---------------------------------------------------------------------------

T = 1.2
SA = 3.5
COMP1 = T * math.pi / 2
COMP2 = 2 * COMP1
COMP3 = 3 * COMP1
SLOT_NET_W = 85.6 + 1.5


@pytest.fixture
def default_pattern():
    return CardHolder().build()


class TestDefaultCardHolder:
    def test_piece_inventory(self, default_pattern):
        # 1 panel entry (cut twice) + 3 slot pieces.
        assert len(default_pattern.pieces) == 4
        panel = default_pattern.pieces[0]
        assert panel.quantity == 2
        assert sum(p.quantity for p in default_pattern.pieces) == 5

    def test_main_panel_matches_hand_calculation(self, default_pattern):
        panel = default_pattern.pieces[0]
        assert panel.net_size == pytest.approx((87.1 + 2 * COMP3, 12 * 2 + 54 + 10 + COMP3))
        assert panel.cut_size == pytest.approx((105.409734, 100.654867), abs=1e-5)

    def test_slot_pieces_match_hand_calculation(self, default_pattern):
        slot1, slot2, slot3 = default_pattern.pieces[1:]
        assert slot1.net_size == pytest.approx((SLOT_NET_W, 40))
        assert slot1.cut_size == pytest.approx((94.1, 47))
        assert slot2.net_size == pytest.approx((SLOT_NET_W + 2 * COMP1, 52 + COMP1))
        assert slot3.net_size == pytest.approx((SLOT_NET_W + 2 * COMP2, 64 + COMP2))

    def test_no_fold_marks_when_burnished(self, default_pattern):
        assert all(p.fold_marks == [] for p in default_pattern.pieces)


class TestSlotStagger:
    def test_stagger_accumulates_per_layer(self):
        # Slot-group height accumulation: removing the per-piece bottom
        # thickness compensation, slot heights must be exactly
        # top_slot_height + (i-1)*stagger: 40, 52, 64 for the defaults.
        pattern = CardHolder().build()
        slots = pattern.pieces[1:]
        for i, slot in enumerate(slots, start=1):
            base_height = slot.net_size[1] - (i - 1) * COMP1
            assert base_height == pytest.approx(40 + (i - 1) * 12)

    def test_configurable_stagger(self):
        pattern = CardHolder(CardHolderParams(stagger_mm=14)).build()
        slot3 = pattern.pieces[-1]
        assert slot3.net_size[1] - COMP2 == pytest.approx(40 + 2 * 14)

    def test_single_slot_has_no_compensation_anywhere(self):
        # One slot wraps nothing; only the panels are compensated (d=1).
        pattern = CardHolder(CardHolderParams(slots=1)).build()
        panel, slot = pattern.pieces
        assert slot.net_size == pytest.approx((SLOT_NET_W, 40))
        assert panel.net_size == pytest.approx((SLOT_NET_W + 2 * COMP1, 54 + 10 + COMP1))


class TestEdgeFinish:
    def test_folded_grows_8mm_per_edge_with_corner_marks(self):
        burnished = CardHolder().build().pieces[0]
        folded = CardHolder(CardHolderParams(edge_finish=EdgeFinish.FOLDED)).build().pieces[0]
        # Net size is identical; cut grows by the 8 mm fold on each edge.
        assert folded.net_size == pytest.approx(burnished.net_size)
        assert folded.cut_size[0] == pytest.approx(burnished.cut_size[0] + 16)
        assert folded.cut_size[1] == pytest.approx(burnished.cut_size[1] + 16)
        assert len(folded.fold_marks) == 4


class TestStitchPitch:
    def test_pitch_propagates_to_punch_refs(self):
        pattern = CardHolder(CardHolderParams(stitch_pitch_mm=3.85)).build()
        for piece in pattern.pieces:
            assert all(ref.pitch_mm == 3.85 for ref in piece.punch_refs)


class TestValidation:
    def test_slot_count_bounds(self):
        with pytest.raises(ValueError):
            CardHolder(CardHolderParams(slots=4))
        with pytest.raises(ValueError):
            CardHolder(CardHolderParams(slots=0))

    def test_stagger_bounds(self):
        with pytest.raises(ValueError):
            CardHolder(CardHolderParams(stagger_mm=9))

    def test_seam_allowance_bounds(self):
        with pytest.raises(ValueError):
            CardHolder(CardHolderParams(seam_allowance_mm=6)).build()
