"""ZipperPouch template: a flat zipper coin pouch, two body pieces.

Two zipper installation styles (confirmed: support both, default window):

- WINDOW   : the front piece gets a stadium-shaped zipper window cut out
             near its top edge; the zipper tape is sewn behind it along a
             stitch line running `ZIPPER_STITCH_MARGIN_MM` outside the
             window. Both pieces are sewn together around all four edges.
- TOP_SEAM : the zipper is sandwiched between the top edges of the two
             pieces; no window is cut. The workshop slot-length formula
             (nominal zipper length + 6 mm) gives the zipper segment that
             is marked centred on the top edge; rounded ends do not apply.

In both styles: slot length = nominal zipper length + 6 mm installation
margin, slot width 4 mm (window style only).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from shapely.geometry import LineString

from ..core import (
    DEFAULT_SEAM_ALLOWANCE_MM,
    DEFAULT_STITCH_PITCH_MM,
    ZIPPER_SLOT_EXTRA_LENGTH_MM,
    ZIPPER_SLOT_WIDTH_MM,
    ZIPPER_STITCH_MARGIN_MM,
    Edge,
    EdgeFinish,
    Pattern,
    build_rect_piece,
    offset_outline,
    punch_reference,
    stadium_polygon,
)

#: Minimum distance between the window end and the side stitch line.
MIN_WINDOW_SIDE_MARGIN_MM = 5.0


class ZipperStyle(str, Enum):
    WINDOW = "window"
    TOP_SEAM = "top_seam"


@dataclass
class ZipperPouchParams:
    body_width_mm: float = 120.0
    body_height_mm: float = 85.0
    zipper_length_mm: float = 100.0  # nominal zipper length
    style: ZipperStyle = ZipperStyle.WINDOW
    #: Distance from the top net edge down to the window centreline.
    window_top_offset_mm: float = 12.0
    leather_thickness_mm: float = 1.2
    seam_allowance_mm: float = DEFAULT_SEAM_ALLOWANCE_MM
    edge_finish: EdgeFinish = EdgeFinish.BURNISHED
    stitch_pitch_mm: float = DEFAULT_STITCH_PITCH_MM

    @property
    def slot_length_mm(self) -> float:
        """Zipper slot length = nominal length + installation margin."""
        return self.zipper_length_mm + ZIPPER_SLOT_EXTRA_LENGTH_MM

    def validate(self) -> None:
        if self.body_width_mm <= 0 or self.body_height_mm <= 0:
            raise ValueError("body dimensions must be positive")
        if self.leather_thickness_mm <= 0:
            raise ValueError("leather thickness must be positive")
        if self.style == ZipperStyle.WINDOW:
            margin = (self.body_width_mm - self.slot_length_mm) / 2
            if margin < MIN_WINDOW_SIDE_MARGIN_MM:
                raise ValueError(
                    f"zipper slot ({self.slot_length_mm} mm) leaves only "
                    f"{margin:.1f} mm to the side stitch lines; need >= "
                    f"{MIN_WINDOW_SIDE_MARGIN_MM} mm — use a shorter zipper "
                    f"or a wider body"
                )
            if self.window_top_offset_mm < ZIPPER_SLOT_WIDTH_MM:
                raise ValueError("zipper window sits too close to the top edge")
        else:
            if self.slot_length_mm > self.body_width_mm:
                raise ValueError(
                    "zipper (nominal + 6 mm) is longer than the pouch body"
                )


class ZipperPouch:
    """Parametric zipper pouch pattern generator."""

    def __init__(self, params: ZipperPouchParams | None = None) -> None:
        self.params = params or ZipperPouchParams()
        self.params.validate()

    def build(self) -> Pattern:
        p = self.params
        style_label = "开窗式" if p.style == ZipperStyle.WINDOW else "顶边夹缝式"

        if p.style == ZipperStyle.WINDOW:
            sewn = (Edge.LEFT, Edge.BOTTOM, Edge.RIGHT, Edge.TOP)
            front = self._body_piece("前片（拉链开窗）", sewn)
            self._add_zipper_window(front)
            back = self._body_piece("后片", sewn)
            pieces = [front, back]
        else:
            # Zipper sandwiched in the top seam: perimeter sewn on the other
            # three edges; the zipper segment is marked on the top edge.
            sewn = (Edge.LEFT, Edge.BOTTOM, Edge.RIGHT)
            front = self._body_piece("前片", sewn)
            back = self._body_piece("后片", sewn)
            for piece in (front, back):
                self._add_top_seam_zipper_mark(piece)
            pieces = [front, back]

        return Pattern(
            name=f"拉链零钱包（{style_label}）",
            pieces=pieces,
            leather_thickness_mm=p.leather_thickness_mm,
            seam_allowance_mm=p.seam_allowance_mm,
            edge_finish=p.edge_finish,
            stitch_pitch_mm=p.stitch_pitch_mm,
        )

    def _body_piece(self, name: str, sewn_edges: tuple[Edge, ...]):
        p = self.params
        return build_rect_piece(
            name=name,
            quantity=1,
            net_width_mm=p.body_width_mm,
            net_height_mm=p.body_height_mm,
            seam_allowance_mm=p.seam_allowance_mm,
            sewn_edges=sewn_edges,
            edge_finish=p.edge_finish,
            stitch_pitch_mm=p.stitch_pitch_mm,
            suggested_thickness_mm=p.leather_thickness_mm,
        )

    def _add_zipper_window(self, piece) -> None:
        """Cut a stadium window near the top edge and add the zipper stitch
        line running ZIPPER_STITCH_MARGIN_MM outside it.
        """
        p = self.params
        window = stadium_polygon(
            p.slot_length_mm,
            ZIPPER_SLOT_WIDTH_MM,
            center=(p.body_width_mm / 2, p.body_height_mm - p.window_top_offset_mm),
        )
        piece.cutouts.append(window)
        stitch_ring = LineString(offset_outline(window, ZIPPER_STITCH_MARGIN_MM).exterior.coords)
        piece.stitch_lines.append(stitch_ring)
        piece.punch_refs.append(punch_reference(stitch_ring, p.stitch_pitch_mm))
        piece.notes = "开窗两端半圆收口；拉链自背面贴缝"

    def _add_top_seam_zipper_mark(self, piece) -> None:
        """Mark the zipper segment (nominal + 6 mm, centred) on the top edge."""
        p = self.params
        x0 = (p.body_width_mm - p.slot_length_mm) / 2
        segment = LineString([(x0, p.body_height_mm), (x0 + p.slot_length_mm, p.body_height_mm)])
        piece.stitch_lines.append(segment)
        piece.punch_refs.append(punch_reference(segment, p.stitch_pitch_mm))
        piece.notes = "顶边居中段为拉链夹缝区"
