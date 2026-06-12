"""Core geometry primitives for LeatherPattern AI.

All dimensions are in millimetres. All coordinates use a mathematical
convention (+x right, +y up); exporters are responsible for flipping the
y-axis when a target format requires it (e.g. SVG).

Terminology used throughout the codebase:

- "net outline"  : the stitch-line outline of a piece. Per workshop rule,
                   the seam runs `seam_allowance` inside the cut edge, so
                   net dimensions are stitch-to-stitch dimensions.
- "cut outline"  : net outline + seam allowance on every edge, plus an
                   extra fold allowance on folded-finish edges.
- "thickness compensation": extra length an outer layer needs to wrap
                   around inner layers at a sewn edge, approximated by a
                   quarter-circle arc per wrapped layer (t * pi / 2).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from shapely.geometry import LineString, Point, Polygon, box

# ---------------------------------------------------------------------------
# Workshop constants (mm). Values marked "configurable" are defaults that
# template parameter objects expose to the user.
# ---------------------------------------------------------------------------

#: Default hand-stitching seam allowance (distance stitch line -> cut edge).
DEFAULT_SEAM_ALLOWANCE_MM = 3.5
#: Allowed user range for seam allowance.
SEAM_ALLOWANCE_RANGE_MM = (3.0, 5.0)

#: Default pricking pitch for diamond chisels. French pricking irons are
#: typically 3.85 mm; the pitch is configurable per pattern.
DEFAULT_STITCH_PITCH_MM = 4.0

#: Extra material folded over on a folded-finish edge.
FOLD_ALLOWANCE_MM = 8.0

#: ISO/IEC 7810 ID-1 card (credit/bank card).
CARD_WIDTH_MM = 85.6
CARD_HEIGHT_MM = 54.0
#: Lateral ease so a card slides in and out of a slot freely.
CARD_EASE_MM = 1.5

#: Visible lip of each stacked card slot (configurable 10-14 mm).
DEFAULT_SLOT_STAGGER_MM = 12.0
SLOT_STAGGER_RANGE_MM = (10.0, 14.0)

#: Empirical multiplier for the fold-zone compensation of a bifold shell:
#: shell length = 2 * lining width + (total stacked thickness * this factor).
#: This is a workshop rule of thumb, not derived geometry; kept configurable
#: so makers can tune it for stiffer or softer leathers.
BIFOLD_FOLD_COMPENSATION_FACTOR = 3.0

#: Zipper slot: opening length = nominal zipper length + this installation
#: margin; the slot is a stadium shape (rounded ends) of the width below.
ZIPPER_SLOT_EXTRA_LENGTH_MM = 6.0
ZIPPER_SLOT_WIDTH_MM = 4.0
#: Distance between a zipper window's edge and the stitch line around it.
ZIPPER_STITCH_MARGIN_MM = 2.5

#: Default banknote reference (confirmed: euro; a 50 EUR note is 140x77 mm).
#: Used to size the bifold bill compartment; configurable per pattern.
DEFAULT_BILL_LENGTH_MM = 140.0
DEFAULT_BILL_HEIGHT_MM = 77.0
#: Clearance between the bill's top edge and the compartment mouth.
BILL_TOP_CLEARANCE_MM = 5.0


class EdgeFinish(str, Enum):
    """How raw edges are finished on the final product."""

    BURNISHED = "burnished"  # 油边: edge painted/burnished, no extra material
    FOLDED = "folded"        # 折边: edge folded over, +8 mm allowance
    BOUND = "bound"          # 包边: edge bound with a strip (no expansion in MVP)


class Edge(str, Enum):
    """Named edges of an axis-aligned rectangular piece."""

    TOP = "top"
    RIGHT = "right"
    BOTTOM = "bottom"
    LEFT = "left"


ALL_EDGES = (Edge.TOP, Edge.RIGHT, Edge.BOTTOM, Edge.LEFT)


def thickness_compensation_mm(wrapped_layers: int, leather_thickness_mm: float) -> float:
    """Extra length needed at ONE sewn edge to wrap `wrapped_layers` inner
    layers of leather, approximated as a quarter-circle arc per layer.

    Per confirmed workshop rule this is applied once per sewn edge, so a
    piece wrapped at both its left and right seams gets 2x this amount in
    the width direction.
    """
    if wrapped_layers < 0:
        raise ValueError("wrapped_layers must be >= 0")
    return wrapped_layers * leather_thickness_mm * math.pi / 2.0


def rect_polygon(width_mm: float, height_mm: float) -> Polygon:
    """Axis-aligned rectangle with its lower-left corner at the origin."""
    if width_mm <= 0 or height_mm <= 0:
        raise ValueError("rectangle dimensions must be positive")
    return box(0.0, 0.0, width_mm, height_mm)


def offset_outline(outline: Polygon, distance_mm: float) -> Polygon:
    """Offset a closed outline outward (positive) or inward (negative).

    Uses a mitred buffer so rectangular corners stay square instead of
    being rounded, which is what a cutting pattern needs.
    """
    result = outline.buffer(distance_mm, join_style="mitre")
    if result.is_empty:
        raise ValueError(f"offset of {distance_mm} mm collapsed the outline")
    return result


def expand_rect(outline: Polygon, per_edge_mm: dict[Edge, float]) -> Polygon:
    """Expand an axis-aligned rectangle by a (possibly different) amount on
    each edge. Used to build cut outlines where, e.g., a folded edge grows
    more than a burnished one.
    """
    minx, miny, maxx, maxy = outline.bounds
    return box(
        minx - per_edge_mm.get(Edge.LEFT, 0.0),
        miny - per_edge_mm.get(Edge.BOTTOM, 0.0),
        maxx + per_edge_mm.get(Edge.RIGHT, 0.0),
        maxy + per_edge_mm.get(Edge.TOP, 0.0),
    )


def rect_edge_line(outline: Polygon, edge: Edge) -> LineString:
    """Return one edge of an axis-aligned rectangle as a LineString."""
    minx, miny, maxx, maxy = outline.bounds
    lines = {
        Edge.TOP: LineString([(minx, maxy), (maxx, maxy)]),
        Edge.RIGHT: LineString([(maxx, miny), (maxx, maxy)]),
        Edge.BOTTOM: LineString([(minx, miny), (maxx, miny)]),
        Edge.LEFT: LineString([(minx, miny), (minx, maxy)]),
    }
    return lines[edge]


def stadium_polygon(length_mm: float, width_mm: float,
                    center: tuple[float, float] = (0.0, 0.0)) -> Polygon:
    """Horizontal stadium (rectangle with semicircular ends), used for
    zipper window slots. `length_mm` is the overall end-to-end length.
    """
    if length_mm <= width_mm:
        raise ValueError("stadium length must exceed its width")
    cx, cy = center
    half_seg = (length_mm - width_mm) / 2.0
    spine = LineString([(cx - half_seg, cy), (cx + half_seg, cy)])
    # quad_segs=16 keeps the semicircular ends smooth enough for cutting.
    return spine.buffer(width_mm / 2.0, quad_segs=16)


def fold_corner_marks(cut_outline: Polygon, folded_edges: list[Edge],
                      fold_allowance_mm: float = FOLD_ALLOWANCE_MM) -> list[LineString]:
    """45-degree chamfer marks at corners of the folded zone.

    For every cut-outline corner where at least one adjacent edge is folded,
    draw a diagonal line connecting the two points `fold_allowance` along
    each adjacent edge from the corner. The maker cuts this chamfer so the
    folded flaps do not overlap at the corner.
    """
    minx, miny, maxx, maxy = cut_outline.bounds
    a = fold_allowance_mm
    corners = {
        (Edge.TOP, Edge.LEFT): LineString([(minx, maxy - a), (minx + a, maxy)]),
        (Edge.TOP, Edge.RIGHT): LineString([(maxx - a, maxy), (maxx, maxy - a)]),
        (Edge.BOTTOM, Edge.RIGHT): LineString([(maxx, miny + a), (maxx - a, miny)]),
        (Edge.BOTTOM, Edge.LEFT): LineString([(minx + a, miny), (minx, miny + a)]),
    }
    folded = set(folded_edges)
    return [line for (e1, e2), line in corners.items() if e1 in folded or e2 in folded]


@dataclass(frozen=True)
class PunchReference:
    """Start/end reference dots of a pricking run along one stitch line.

    The pattern only marks where the first and last hole go; the maker walks
    the chisel between them. `hole_count` is informational (shown in labels).
    """

    start: Point
    end: Point
    hole_count: int
    pitch_mm: float


def punch_reference(stitch_line: LineString, pitch_mm: float = DEFAULT_STITCH_PITCH_MM) -> PunchReference:
    """Compute pricking start/end dots for a stitch line.

    Holes are laid out from the start of the line every `pitch_mm`; the last
    hole is the final position that still fits on the line, so the count is
    floor(length / pitch) + 1 and the marked end dot sits exactly on the
    last hole, not necessarily on the line's endpoint.
    """
    if pitch_mm <= 0:
        raise ValueError("stitch pitch must be positive")
    length = stitch_line.length
    hole_count = int(length // pitch_mm) + 1
    last_offset = (hole_count - 1) * pitch_mm
    return PunchReference(
        start=stitch_line.interpolate(0.0),
        end=stitch_line.interpolate(last_offset),
        hole_count=hole_count,
        pitch_mm=pitch_mm,
    )


@dataclass
class Piece:
    """One cut piece of a pattern, fully resolved in millimetres."""

    name: str
    quantity: int
    net_outline: Polygon
    cut_outline: Polygon
    stitch_lines: list[LineString] = field(default_factory=list)
    punch_refs: list[PunchReference] = field(default_factory=list)
    fold_marks: list[LineString] = field(default_factory=list)
    #: Interior holes to cut out (e.g. a zipper window).
    cutouts: list[Polygon] = field(default_factory=list)
    #: Non-cut reference lines (e.g. bifold fold lines), drawn dash-dot.
    guide_lines: list[LineString] = field(default_factory=list)
    #: Grain (stretch) direction arrow, degrees CCW from +x. Leather should
    #: be cut so its stretch direction matches this arrow.
    grain_angle_deg: float = 90.0
    suggested_thickness_mm: float = 1.2
    notes: str = ""

    @property
    def net_size(self) -> tuple[float, float]:
        minx, miny, maxx, maxy = self.net_outline.bounds
        return (maxx - minx, maxy - miny)

    @property
    def cut_size(self) -> tuple[float, float]:
        minx, miny, maxx, maxy = self.cut_outline.bounds
        return (maxx - minx, maxy - miny)


def build_rect_piece(
    *,
    name: str,
    quantity: int,
    net_width_mm: float,
    net_height_mm: float,
    seam_allowance_mm: float = DEFAULT_SEAM_ALLOWANCE_MM,
    sewn_edges: tuple[Edge, ...] = (Edge.LEFT, Edge.BOTTOM, Edge.RIGHT),
    edge_finish: EdgeFinish = EdgeFinish.BURNISHED,
    fold_allowance_mm: float = FOLD_ALLOWANCE_MM,
    stitch_pitch_mm: float = DEFAULT_STITCH_PITCH_MM,
    grain_angle_deg: float = 90.0,
    suggested_thickness_mm: float = 1.2,
    notes: str = "",
) -> Piece:
    """Build a rectangular piece with cut outline, stitch lines, punch dots
    and (for folded finish) corner chamfer marks.

    Cut outline = net + seam allowance on all edges; folded-finish pieces
    additionally grow `fold_allowance_mm` on every edge (the fold is applied
    to every raw edge of the piece before assembly).
    """
    if not (SEAM_ALLOWANCE_RANGE_MM[0] <= seam_allowance_mm <= SEAM_ALLOWANCE_RANGE_MM[1]):
        raise ValueError(
            f"seam allowance {seam_allowance_mm} mm outside allowed range "
            f"{SEAM_ALLOWANCE_RANGE_MM}"
        )

    net = rect_polygon(net_width_mm, net_height_mm)

    folded_edges: list[Edge] = list(ALL_EDGES) if edge_finish == EdgeFinish.FOLDED else []
    per_edge = {
        edge: seam_allowance_mm + (fold_allowance_mm if edge in folded_edges else 0.0)
        for edge in ALL_EDGES
    }
    cut = expand_rect(net, per_edge)

    stitch_lines = [rect_edge_line(net, edge) for edge in sewn_edges]
    punch_refs = [punch_reference(line, stitch_pitch_mm) for line in stitch_lines]
    fold_marks = fold_corner_marks(cut, folded_edges, fold_allowance_mm) if folded_edges else []

    return Piece(
        name=name,
        quantity=quantity,
        net_outline=net,
        cut_outline=cut,
        stitch_lines=stitch_lines,
        punch_refs=punch_refs,
        fold_marks=fold_marks,
        grain_angle_deg=grain_angle_deg,
        suggested_thickness_mm=suggested_thickness_mm,
        notes=notes,
    )


@dataclass
class Pattern:
    """A complete pattern: a named set of pieces plus shared metadata."""

    name: str
    pieces: list[Piece]
    leather_thickness_mm: float
    seam_allowance_mm: float
    edge_finish: EdgeFinish
    stitch_pitch_mm: float
