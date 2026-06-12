"""Tests for the DXF exporter: millimetre units, layers, true dimensions."""

import io

import ezdxf
import pytest

from app.export.dxf_export import pattern_to_dxf, pattern_to_dxf_str
from app.geometry.templates.bifold_wallet import BifoldWallet
from app.geometry.templates.card_holder import CardHolder
from app.geometry.templates.zipper_pouch import ZipperPouch


def _bbox(lwpolyline):
    pts = lwpolyline.get_points("xy")
    xs = [x for x, _ in pts]
    ys = [y for _, y in pts]
    return min(xs), min(ys), max(xs), max(ys)


def test_units_are_millimetres():
    doc = pattern_to_dxf(CardHolder().build())
    assert doc.header["$INSUNITS"] == 4  # 4 = mm
    assert doc.header["$MEASUREMENT"] == 1  # metric


def test_layers_exist():
    doc = pattern_to_dxf(CardHolder().build())
    for layer in ("CUT", "STITCH", "MARK", "TEXT"):
        assert layer in doc.layers


def test_one_cut_polyline_per_piece():
    doc = pattern_to_dxf(CardHolder().build())
    cuts = doc.modelspace().query('LWPOLYLINE[layer=="CUT"]')
    assert len(cuts) == 4  # panel + 3 slots


def test_cut_dimensions_match_pattern():
    pattern = CardHolder().build()
    doc = pattern_to_dxf(pattern)
    cuts = doc.modelspace().query('LWPOLYLINE[layer=="CUT"]')
    minx, miny, maxx, maxy = _bbox(cuts[0])
    # First piece (main panel) cut size: 105.409734 x 100.654867 mm.
    assert (maxx - minx, maxy - miny) == pytest.approx(pattern.pieces[0].cut_size)
    assert (maxx - minx) == pytest.approx(105.409734, abs=1e-5)


def test_zipper_window_is_a_second_cut_entity():
    doc = pattern_to_dxf(ZipperPouch().build())
    cuts = doc.modelspace().query('LWPOLYLINE[layer=="CUT"]')
    assert len(cuts) == 3  # front + window cutout + back


def test_bifold_fold_guides_on_mark_layer_dashdot():
    doc = pattern_to_dxf(BifoldWallet().build())
    guides = [
        e
        for e in doc.modelspace().query('LWPOLYLINE[layer=="MARK"]')
        if e.dxf.linetype == "DASHDOT"
    ]
    assert len(guides) == 2


def test_punch_dots_are_circles_on_mark_layer():
    pattern = CardHolder().build()
    doc = pattern_to_dxf(pattern)
    circles = doc.modelspace().query('CIRCLE[layer=="MARK"]')
    expected = sum(2 * len(p.punch_refs) for p in pattern.pieces)
    assert len(circles) == expected


def test_dxf_string_round_trips():
    text = pattern_to_dxf_str(CardHolder().build())
    doc = ezdxf.read(io.StringIO(text))
    assert doc.header["$INSUNITS"] == 4
    assert len(doc.modelspace().query('LWPOLYLINE[layer=="CUT"]')) == 4
