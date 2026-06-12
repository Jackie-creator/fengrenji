"""DXF export for laser cutters / plotters. Document units are millimetres
($INSUNITS = 4) and coordinates are written 1:1, y-up (DXF native).

Layers:
- CUT    : cut outlines and interior cutouts (continuous, white)
- STITCH : stitch lines (dashed, blue)
- MARK   : punch start/end dots, fold chamfers, fold guide lines (orange)
- TEXT   : piece labels (grey) — can be switched off before cutting
"""

from __future__ import annotations

import io

import ezdxf
from ezdxf.document import Drawing

from ..geometry.core import Pattern, Piece

PIECE_GAP_MM = 15.0
PUNCH_DOT_RADIUS_MM = 0.6
TEXT_HEIGHT_MM = 4.0
LABEL_LINE_SPACING_MM = 6.0

LAYERS = (
    ("CUT", 7, "CONTINUOUS"),
    ("STITCH", 5, "DASHED"),
    ("MARK", 30, "CONTINUOUS"),
    ("TEXT", 8, "CONTINUOUS"),
)


def _shifted(coords, dx: float, dy: float) -> list[tuple[float, float]]:
    return [(x + dx, y + dy) for x, y in coords]


def _add_piece(msp, piece: Piece, dx: float, dy: float) -> None:
    msp.add_lwpolyline(
        _shifted(piece.cut_outline.exterior.coords, dx, dy),
        close=True,
        dxfattribs={"layer": "CUT"},
    )
    for cutout in piece.cutouts:
        msp.add_lwpolyline(
            _shifted(cutout.exterior.coords, dx, dy),
            close=True,
            dxfattribs={"layer": "CUT"},
        )
    for line in piece.stitch_lines:
        msp.add_lwpolyline(_shifted(line.coords, dx, dy), dxfattribs={"layer": "STITCH"})
    for ref in piece.punch_refs:
        for pt in (ref.start, ref.end):
            msp.add_circle(
                (pt.x + dx, pt.y + dy), PUNCH_DOT_RADIUS_MM, dxfattribs={"layer": "MARK"}
            )
    for mark in piece.fold_marks:
        msp.add_lwpolyline(_shifted(mark.coords, dx, dy), dxfattribs={"layer": "MARK"})
    for guide in piece.guide_lines:
        msp.add_lwpolyline(
            _shifted(guide.coords, dx, dy),
            dxfattribs={"layer": "MARK", "linetype": "DASHDOT"},
        )

    net_w, net_h = piece.net_size
    labels = [
        f"{piece.name} x{piece.quantity}",
        f"net {net_w:.1f}x{net_h:.1f}mm  t={piece.suggested_thickness_mm}mm",
    ]
    minx, miny, _, _ = piece.cut_outline.bounds
    for i, text in enumerate(labels):
        msp.add_text(
            text,
            height=TEXT_HEIGHT_MM,
            dxfattribs={"layer": "TEXT"},
        ).set_placement((minx + dx, miny + dy - LABEL_LINE_SPACING_MM * (i + 1.2)))


def pattern_to_dxf(pattern: Pattern) -> Drawing:
    """Lay out all pieces left-to-right (bottom-aligned at y=0) and return
    an ezdxf document in millimetres.
    """
    doc = ezdxf.new("R2010", setup=True)  # setup loads DASHED/DASHDOT linetypes
    doc.header["$INSUNITS"] = 4  # 4 = millimetres
    doc.header["$MEASUREMENT"] = 1  # metric
    for name, color, linetype in LAYERS:
        doc.layers.add(name, color=color, linetype=linetype)

    msp = doc.modelspace()
    x = 0.0
    for piece in pattern.pieces:
        minx, miny, _, _ = piece.cut_outline.bounds
        # Place the piece's cut bbox lower-left corner at (x, 0).
        _add_piece(msp, piece, dx=x - minx, dy=-miny)
        x += piece.cut_size[0] + PIECE_GAP_MM
    return doc


def pattern_to_dxf_str(pattern: Pattern) -> str:
    """DXF as text (R2010 ASCII DXF), ready to be served as a download."""
    stream = io.StringIO()
    pattern_to_dxf(pattern).write(stream)
    return stream.getvalue()
