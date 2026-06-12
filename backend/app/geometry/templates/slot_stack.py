"""Shared card-slot stack logic, used by CardHolder and BifoldWallet.

Confirmed construction rules (see card_holder.py for the full model):
- slot pieces are bottom-aligned; the piece nearest the cavity is the
  shortest, each deeper piece is taller by the stagger amount;
- a piece wrapping `d` inner layers gets `d * t * pi/2` extra length at
  EACH sewn edge (two side edges for width, the bottom edge for height).
"""

from __future__ import annotations

from ..core import (
    CARD_EASE_MM,
    CARD_HEIGHT_MM,
    CARD_WIDTH_MM,
    Edge,
    EdgeFinish,
    Piece,
    build_rect_piece,
    thickness_compensation_mm,
)

#: Default height of the shortest (cavity-side) slot piece.
DEFAULT_TOP_SLOT_HEIGHT_MM = 40.0
#: Default clearance between the tallest card top and the panel mouth.
DEFAULT_TOP_MARGIN_MM = 10.0

#: Stitch-to-stitch interior width that clears a card plus ease.
SLOT_NET_WIDTH_MM = CARD_WIDTH_MM + CARD_EASE_MM

SEWN_EDGES = (Edge.LEFT, Edge.BOTTOM, Edge.RIGHT)


def slot_required_height_mm(slots: int, stagger_mm: float, top_margin_mm: float) -> float:
    """Net panel height needed so no card peeks out of the panel housing
    `slots` stacked slots (excluding any thickness compensation):
    stagger * (slots-1) + card height + top margin.
    """
    if slots <= 0:
        return 0.0
    return stagger_mm * (slots - 1) + CARD_HEIGHT_MM + top_margin_mm


def build_slot_pieces(
    *,
    slots: int,
    name_prefix: str = "卡位片",
    leather_thickness_mm: float,
    seam_allowance_mm: float,
    stagger_mm: float,
    top_slot_height_mm: float = DEFAULT_TOP_SLOT_HEIGHT_MM,
    edge_finish: EdgeFinish = EdgeFinish.BURNISHED,
    stitch_pitch_mm: float,
) -> list[Piece]:
    """Build the slot pieces of one stack, i = 1 (cavity side) .. slots."""
    pieces: list[Piece] = []
    for i in range(1, slots + 1):
        wrapped = i - 1  # layers between this slot and the stack centre
        comp = thickness_compensation_mm(wrapped, leather_thickness_mm)
        pieces.append(
            build_rect_piece(
                name=f"{name_prefix} {i}",
                quantity=1,
                net_width_mm=SLOT_NET_WIDTH_MM + 2 * comp,
                net_height_mm=top_slot_height_mm + (i - 1) * stagger_mm + comp,
                seam_allowance_mm=seam_allowance_mm,
                sewn_edges=SEWN_EDGES,
                edge_finish=edge_finish,
                stitch_pitch_mm=stitch_pitch_mm,
                suggested_thickness_mm=leather_thickness_mm,
                notes=f"自腔体侧起第 {i} 层；顶边为插卡口",
            )
        )
    return pieces
