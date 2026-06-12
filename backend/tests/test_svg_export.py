"""Smoke tests for the SVG exporter."""

from app.export.svg_export import pattern_to_svg
from app.geometry.core import EdgeFinish
from app.geometry.templates.card_holder import CardHolder, CardHolderParams


def test_svg_document_basics():
    svg = pattern_to_svg(CardHolder().build())
    # 1 mm = 1 user unit with physical size for true-to-scale printing.
    assert 'width="' in svg and 'mm"' in svg
    assert "viewBox=" in svg
    # 10 mm grid background and the 50 mm verification scale bar.
    assert 'id="grid" width="10" height="10"' in svg
    assert "50 mm" in svg
    # One cut polygon per piece (4 pieces for the default card holder).
    assert svg.count("<polygon") == 4


def test_svg_viewbox_includes_5mm_bleed():
    pattern = CardHolder().build()
    svg = pattern_to_svg(pattern)
    total_w = sum(p.cut_size[0] for p in pattern.pieces) + 15.0 * (len(pattern.pieces) - 1)
    viewbox_w = float(svg.split('viewBox="0 0 ')[1].split()[0])
    # Coordinates are written with 2-decimal precision, hence the tolerance.
    assert abs(viewbox_w - (total_w + 10)) < 0.01  # 5 mm bleed on both sides


def test_svg_contains_fold_marks_when_folded():
    svg = pattern_to_svg(CardHolder(CardHolderParams(edge_finish=EdgeFinish.FOLDED)).build())
    assert 'stroke="#e65100"' in svg  # fold chamfer style present
