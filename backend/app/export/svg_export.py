"""SVG export: 1 mm = 1 SVG user unit, y-axis flipped to screen convention.

The generated document carries physical width/height in mm so that a 100%
print is true to scale; a 10 mm grid background and a 50 mm scale bar let
the user verify the print was not rescaled.
"""

from __future__ import annotations

from shapely.geometry import LineString, Polygon

from ..geometry.core import Pattern, Piece

BLEED_MM = 5.0          # margin around the drawing, required by spec
PIECE_GAP_MM = 15.0     # spacing between pieces in the layout
FOOTER_MM = 22.0        # reserved strip for scale bar + pattern info
GRID_MM = 10.0
SCALE_BAR_MM = 50.0
PUNCH_DOT_RADIUS_MM = 0.6
FONT_MM = 3.2

CUT_STYLE = 'fill="none" stroke="#111" stroke-width="0.4"'
STITCH_STYLE = 'fill="none" stroke="#1565c0" stroke-width="0.3" stroke-dasharray="2.5 1.5"'
FOLD_STYLE = 'fill="none" stroke="#e65100" stroke-width="0.3"'
PUNCH_STYLE = 'fill="#1565c0"'
GRAIN_STYLE = 'stroke="#2e7d32" stroke-width="0.35" fill="none"'


def _fmt(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s else "0"


def _poly_points(poly: Polygon, ox: float, oy_bottom: float) -> str:
    """Transform polygon exterior from piece-local y-up coords to SVG y-down.

    (ox, oy_bottom) is the SVG position of the piece-local origin's column /
    bottom row: svg_x = ox + x, svg_y = oy_bottom - y.
    """
    return " ".join(f"{_fmt(ox + x)},{_fmt(oy_bottom - y)}" for x, y in poly.exterior.coords)


def _line_points(line: LineString, ox: float, oy_bottom: float) -> str:
    return " ".join(f"{_fmt(ox + x)},{_fmt(oy_bottom - y)}" for x, y in line.coords)


def _piece_svg(piece: Piece, ox: float, oy_bottom: float) -> list[str]:
    """Render one piece with its cut/stitch lines, marks and labels.

    The piece's cut-outline bounding box is placed with its min-x at `ox`
    and its min-y sitting on `oy_bottom` (SVG y grows downward).
    """
    minx, miny, _, _ = piece.cut_outline.bounds
    # Shift so the cut bbox's lower-left corner lands at (ox, oy_bottom).
    tx = ox - minx
    ty = oy_bottom - (-miny)  # local y=miny maps to svg oy_bottom

    out = [f'<polygon points="{_poly_points(piece.cut_outline, tx, ty)}" {CUT_STYLE}/>']
    for line in piece.stitch_lines:
        out.append(f'<polyline points="{_line_points(line, tx, ty)}" {STITCH_STYLE}/>')
    for ref in piece.punch_refs:
        for pt in (ref.start, ref.end):
            out.append(
                f'<circle cx="{_fmt(tx + pt.x)}" cy="{_fmt(ty - pt.y)}" '
                f'r="{PUNCH_DOT_RADIUS_MM}" {PUNCH_STYLE}/>'
            )
    for mark in piece.fold_marks:
        out.append(f'<polyline points="{_line_points(mark, tx, ty)}" {FOLD_STYLE}/>')

    # Grain (stretch) direction arrow: drawn vertically in the piece centre
    # (templates currently always use 90 degrees = vertical).
    net_minx, net_miny, net_maxx, net_maxy = piece.net_outline.bounds
    cx = tx + (net_minx + net_maxx) / 2
    cy = ty - (net_miny + net_maxy) / 2
    half = min(10.0, (net_maxy - net_miny) / 4)
    out.append(
        f'<g {GRAIN_STYLE}>'
        f'<line x1="{_fmt(cx)}" y1="{_fmt(cy + half)}" x2="{_fmt(cx)}" y2="{_fmt(cy - half)}"/>'
        f'<polyline points="{_fmt(cx - 1.5)},{_fmt(cy - half + 2.5)} {_fmt(cx)},{_fmt(cy - half)} '
        f'{_fmt(cx + 1.5)},{_fmt(cy - half + 2.5)}"/></g>'
    )

    net_w, net_h = piece.net_size
    cut_w, cut_h = piece.cut_size
    labels = [
        f"{piece.name}  ×{piece.quantity}",
        f"净尺寸 {_fmt(net_w)}×{_fmt(net_h)} mm",
        f"裁切 {_fmt(cut_w)}×{_fmt(cut_h)} mm",
        f"建议皮厚 {_fmt(piece.suggested_thickness_mm)} mm",
    ]
    ly = cy + half + FONT_MM + 1.5
    for i, text in enumerate(labels):
        out.append(
            f'<text x="{_fmt(cx)}" y="{_fmt(ly + i * (FONT_MM + 1.0))}" font-size="{FONT_MM}" '
            f'text-anchor="middle" fill="#333" font-family="sans-serif">{text}</text>'
        )
    return out


def pattern_to_svg(pattern: Pattern) -> str:
    """Lay out all pieces left-to-right (bottom-aligned) and return a full
    standalone SVG document, 1 mm = 1 user unit.
    """
    cut_sizes = [piece.cut_size for piece in pattern.pieces]
    row_w = sum(w for w, _ in cut_sizes) + PIECE_GAP_MM * (len(cut_sizes) - 1)
    row_h = max(h for _, h in cut_sizes)

    total_w = row_w + 2 * BLEED_MM
    total_h = row_h + FOOTER_MM + 2 * BLEED_MM
    baseline = BLEED_MM + row_h  # SVG y of the pieces' bottom edge

    body: list[str] = []
    x = BLEED_MM
    for piece, (cut_w, _) in zip(pattern.pieces, cut_sizes):
        body.extend(_piece_svg(piece, x, baseline))
        x += cut_w + PIECE_GAP_MM

    # 50 mm scale bar with end ticks, in the footer strip.
    bar_y = baseline + 10.0
    body.append(
        f'<g stroke="#111" stroke-width="0.4">'
        f'<line x1="{BLEED_MM}" y1="{bar_y}" x2="{BLEED_MM + SCALE_BAR_MM}" y2="{bar_y}"/>'
        f'<line x1="{BLEED_MM}" y1="{bar_y - 2}" x2="{BLEED_MM}" y2="{bar_y + 2}"/>'
        f'<line x1="{BLEED_MM + SCALE_BAR_MM}" y1="{bar_y - 2}" '
        f'x2="{BLEED_MM + SCALE_BAR_MM}" y2="{bar_y + 2}"/></g>'
    )
    body.append(
        f'<text x="{BLEED_MM + SCALE_BAR_MM + 3}" y="{_fmt(bar_y + 1.2)}" font-size="{FONT_MM}" '
        f'fill="#111" font-family="sans-serif">50 mm（打印后请校验此长度）</text>'
    )
    info = (
        f"{pattern.name} ｜ 缝份 {_fmt(pattern.seam_allowance_mm)} mm ｜ "
        f"孔距 {_fmt(pattern.stitch_pitch_mm)} mm ｜ 皮厚 {_fmt(pattern.leather_thickness_mm)} mm ｜ "
        f"收边 {pattern.edge_finish.value}"
    )
    body.append(
        f'<text x="{BLEED_MM}" y="{_fmt(bar_y + 9)}" font-size="{FONT_MM}" '
        f'fill="#555" font-family="sans-serif">{info}</text>'
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_fmt(total_w)}mm" '
        f'height="{_fmt(total_h)}mm" viewBox="0 0 {_fmt(total_w)} {_fmt(total_h)}">\n'
        f'<defs><pattern id="grid" width="{_fmt(GRID_MM)}" height="{_fmt(GRID_MM)}" '
        f'patternUnits="userSpaceOnUse">'
        f'<path d="M {_fmt(GRID_MM)} 0 L 0 0 0 {_fmt(GRID_MM)}" fill="none" stroke="#d7d7d7" '
        f'stroke-width="0.15"/></pattern></defs>\n'
        f'<rect width="100%" height="100%" fill="#ffffff"/>\n'
        f'<rect width="100%" height="100%" fill="url(#grid)"/>\n'
        + "\n".join(body)
        + "\n</svg>\n"
    )
