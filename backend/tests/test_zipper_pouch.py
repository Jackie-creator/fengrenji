"""Tests for the ZipperPouch template (window and top-seam styles)."""

import pytest

from app.geometry.templates.zipper_pouch import (
    ZipperPouch,
    ZipperPouchParams,
    ZipperStyle,
)


class TestWindowStyle:
    def test_two_body_pieces_one_window(self):
        pattern = ZipperPouch().build()
        front, back = pattern.pieces
        assert len(front.cutouts) == 1
        assert back.cutouts == []
        # Both bodies: net 120x85, cut 127x92 with 3.5 mm seam.
        assert front.cut_size == pytest.approx((127, 92))
        assert back.cut_size == pytest.approx((127, 92))

    def test_window_geometry(self):
        # Defaults: zipper 100 -> slot length 100+6 = 106, width 4,
        # centred horizontally, centreline 12 mm below the top net edge:
        # bbox x: 60-53 .. 60+53 = 7..113, y: 73-2 .. 73+2 = 71..75.
        front = ZipperPouch().build().pieces[0]
        window = front.cutouts[0]
        assert window.bounds == pytest.approx((7, 71, 113, 75))

    def test_zipper_stitch_ring_2_5mm_outside_window(self):
        front = ZipperPouch().build().pieces[0]
        # 4 perimeter stitch lines + the ring around the window.
        assert len(front.stitch_lines) == 5
        ring = front.stitch_lines[-1]
        # abs tolerance covers the polygonal approximation of the round ends.
        assert ring.bounds == pytest.approx((4.5, 68.5, 115.5, 77.5), abs=0.01)
        assert len(front.punch_refs) == 5

    def test_window_too_close_to_sides_rejected(self):
        # body 110 wide, slot 106 -> only 2 mm to the side stitch lines.
        with pytest.raises(ValueError, match="side stitch"):
            ZipperPouch(ZipperPouchParams(body_width_mm=110))


class TestTopSeamStyle:
    def test_no_window_zipper_segment_marked(self):
        pattern = ZipperPouch(ZipperPouchParams(style=ZipperStyle.TOP_SEAM)).build()
        for piece in pattern.pieces:
            assert piece.cutouts == []
            # 3 sewn edges + the centred zipper segment on the top edge.
            assert len(piece.stitch_lines) == 4
            segment = piece.stitch_lines[-1]
            (x1, y1), (x2, y2) = segment.coords
            assert (y1, y2) == (85, 85)
            assert (x1, x2) == pytest.approx((7, 113))  # 106 mm centred in 120

    def test_zipper_longer_than_body_rejected(self):
        with pytest.raises(ValueError, match="longer than"):
            ZipperPouch(
                ZipperPouchParams(style=ZipperStyle.TOP_SEAM, zipper_length_mm=120)
            )


def test_slot_length_formula():
    # Slot length = nominal zipper length + 6 mm installation margin.
    assert ZipperPouchParams(zipper_length_mm=80).slot_length_mm == pytest.approx(86)
