"""Unit tests for generic geometry helpers in app.geometry.core."""

import math

import pytest
from shapely.geometry import LineString

from app.geometry.core import (
    Edge,
    EdgeFinish,
    build_rect_piece,
    fold_corner_marks,
    offset_outline,
    punch_reference,
    rect_polygon,
    thickness_compensation_mm,
)


class TestOffset:
    def test_outward_offset_keeps_square_corners(self):
        # 50x30 rect buffered outward 3.5 mm with mitre joins must be a
        # 57x37 rect: bounds grow by 3.5 on every side and the area matches
        # the full rectangle (rounded corners would lose ~ (4-pi)*r^2).
        poly = offset_outline(rect_polygon(50, 30), 3.5)
        assert poly.bounds == pytest.approx((-3.5, -3.5, 53.5, 33.5))
        assert poly.area == pytest.approx(57 * 37)

    def test_inward_offset(self):
        poly = offset_outline(rect_polygon(50, 30), -3.5)
        assert poly.bounds == pytest.approx((3.5, 3.5, 46.5, 26.5))

    def test_collapsing_offset_raises(self):
        with pytest.raises(ValueError):
            offset_outline(rect_polygon(5, 5), -10)


class TestThicknessCompensation:
    def test_quarter_arc_per_layer(self):
        # One wrapped layer of 1.2 mm leather: 1.2 * pi/2 = 1.88496 mm.
        assert thickness_compensation_mm(1, 1.2) == pytest.approx(1.2 * math.pi / 2)
        # Three layers accumulate linearly: 5.65487 mm.
        assert thickness_compensation_mm(3, 1.2) == pytest.approx(3 * 1.2 * math.pi / 2)

    def test_zero_layers_no_compensation(self):
        assert thickness_compensation_mm(0, 1.2) == 0.0

    def test_negative_layers_rejected(self):
        with pytest.raises(ValueError):
            thickness_compensation_mm(-1, 1.2)


class TestPunchReference:
    def test_default_pitch_4mm(self):
        # 40 mm seam at 4 mm pitch: holes at 0,4,...,40 -> 11 holes, end
        # dot exactly at the line end.
        ref = punch_reference(LineString([(0, 0), (40, 0)]), 4.0)
        assert ref.hole_count == 11
        assert (ref.start.x, ref.start.y) == pytest.approx((0, 0))
        assert (ref.end.x, ref.end.y) == pytest.approx((40, 0))

    def test_non_multiple_length_ends_on_last_hole(self):
        # 41 mm line: last hole that fits is at 40 mm, not at the endpoint.
        ref = punch_reference(LineString([(0, 0), (41, 0)]), 4.0)
        assert ref.hole_count == 11
        assert ref.end.x == pytest.approx(40)

    def test_french_iron_pitch_configurable(self):
        # 3.85 mm French irons over 40 mm: floor(40/3.85)=10 -> 11 holes,
        # last at 38.5 mm.
        ref = punch_reference(LineString([(0, 0), (40, 0)]), 3.85)
        assert ref.hole_count == 11
        assert ref.end.x == pytest.approx(38.5)

    def test_invalid_pitch(self):
        with pytest.raises(ValueError):
            punch_reference(LineString([(0, 0), (40, 0)]), 0)


class TestFoldCornerMarks:
    def test_marks_are_45_degree_chamfers(self):
        cut = rect_polygon(60, 40)
        marks = fold_corner_marks(cut, [Edge.TOP, Edge.RIGHT, Edge.BOTTOM, Edge.LEFT], 8.0)
        assert len(marks) == 4
        for mark in marks:
            (x1, y1), (x2, y2) = mark.coords
            # A 45-degree chamfer: |dx| == |dy| == fold allowance.
            assert abs(x2 - x1) == pytest.approx(8.0)
            assert abs(y2 - y1) == pytest.approx(8.0)

    def test_only_corners_touching_folded_edges(self):
        cut = rect_polygon(60, 40)
        # Only the TOP edge folded -> the two top corners get marks.
        marks = fold_corner_marks(cut, [Edge.TOP], 8.0)
        assert len(marks) == 2


class TestBuildRectPiece:
    def test_burnished_cut_is_net_plus_seam(self):
        piece = build_rect_piece(
            name="t", quantity=1, net_width_mm=80, net_height_mm=60,
            seam_allowance_mm=3.5, edge_finish=EdgeFinish.BURNISHED,
        )
        assert piece.net_size == pytest.approx((80, 60))
        assert piece.cut_size == pytest.approx((87, 67))
        assert piece.fold_marks == []
        # Default sewn edges: left, bottom, right -> 3 stitch lines with
        # punch start/end references each.
        assert len(piece.stitch_lines) == 3
        assert len(piece.punch_refs) == 3

    def test_folded_adds_8mm_per_edge_and_marks_corners(self):
        piece = build_rect_piece(
            name="t", quantity=1, net_width_mm=80, net_height_mm=60,
            seam_allowance_mm=3.5, edge_finish=EdgeFinish.FOLDED,
        )
        # Folded finish: every edge grows seam 3.5 + fold 8 = 11.5 mm.
        assert piece.cut_size == pytest.approx((80 + 23, 60 + 23))
        assert len(piece.fold_marks) == 4

    def test_seam_allowance_range_enforced(self):
        with pytest.raises(ValueError):
            build_rect_piece(
                name="t", quantity=1, net_width_mm=80, net_height_mm=60,
                seam_allowance_mm=2.0,
            )
