"""CardHolder template: a simple flat card holder.

Construction model (confirmed with the product owner):

- Two identical main panels (front + back) form the outer shell; between
  them sits a stack of 1-3 card slot pieces, all bottom-aligned, sewn
  together with the panels along the LEFT, BOTTOM and RIGHT edges. The TOP
  edge is the open mouth.
- Slot pieces cascade: the piece closest to the centre cavity is the
  shortest (its opening is the lowest); each piece behind it is taller by
  the stagger amount. Slot piece heights therefore accumulate as
  `top_slot_height + (i-1) * stagger`, and the slot-group total height is
  `top_slot_height + (slots-1) * stagger`.
- Thickness compensation: a piece that wraps `d` inner layers at a sewn
  edge needs `d * t * pi/2` extra length AT EACH such edge (confirmed:
  per-edge, not per-direction). Width has two sewn edges (left + right),
  height has one (bottom). The slot piece nearest the cavity wraps nothing
  (d = 0); the deepest slot wraps d = slots-1 layers; each main panel wraps
  the full slot stack (d = slots). Both panels are cut to the same
  (compensated) size so the pattern stays symmetric.
- Main panel net height guarantees cards never peek out of the shell:
  `stagger * (slots-1) + card_height + top_margin` (+ bottom-edge
  thickness compensation).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core import (
    DEFAULT_SEAM_ALLOWANCE_MM,
    DEFAULT_SLOT_STAGGER_MM,
    DEFAULT_STITCH_PITCH_MM,
    SLOT_STAGGER_RANGE_MM,
    EdgeFinish,
    Pattern,
    build_rect_piece,
    thickness_compensation_mm,
)
from .slot_stack import (
    DEFAULT_TOP_MARGIN_MM,
    DEFAULT_TOP_SLOT_HEIGHT_MM,
    SEWN_EDGES,
    SLOT_NET_WIDTH_MM,
    build_slot_pieces,
    slot_required_height_mm,
)


@dataclass
class CardHolderParams:
    slots: int = 3
    leather_thickness_mm: float = 1.2
    seam_allowance_mm: float = DEFAULT_SEAM_ALLOWANCE_MM
    stagger_mm: float = DEFAULT_SLOT_STAGGER_MM
    top_slot_height_mm: float = DEFAULT_TOP_SLOT_HEIGHT_MM
    top_margin_mm: float = DEFAULT_TOP_MARGIN_MM
    edge_finish: EdgeFinish = EdgeFinish.BURNISHED
    stitch_pitch_mm: float = DEFAULT_STITCH_PITCH_MM

    def validate(self) -> None:
        if not 1 <= self.slots <= 3:
            raise ValueError("card holder supports 1-3 slots")
        if not (SLOT_STAGGER_RANGE_MM[0] <= self.stagger_mm <= SLOT_STAGGER_RANGE_MM[1]):
            raise ValueError(
                f"slot stagger {self.stagger_mm} mm outside allowed range "
                f"{SLOT_STAGGER_RANGE_MM}"
            )
        if self.leather_thickness_mm <= 0:
            raise ValueError("leather thickness must be positive")


class CardHolder:
    """Parametric card holder pattern generator."""

    def __init__(self, params: CardHolderParams | None = None) -> None:
        self.params = params or CardHolderParams()
        self.params.validate()

    def build(self) -> Pattern:
        p = self.params
        t = p.leather_thickness_mm

        # --- Main panels (front + back, cut identical) -------------------
        panel_comp = thickness_compensation_mm(p.slots, t)  # wraps whole stack
        panel_net_w = SLOT_NET_WIDTH_MM + 2 * panel_comp    # left + right seams
        panel_net_h = (
            slot_required_height_mm(p.slots, p.stagger_mm, p.top_margin_mm)
            + panel_comp                                    # bottom seam only
        )
        panel = build_rect_piece(
            name="主体片（前/后）",
            quantity=2,
            net_width_mm=panel_net_w,
            net_height_mm=panel_net_h,
            seam_allowance_mm=p.seam_allowance_mm,
            sewn_edges=SEWN_EDGES,
            edge_finish=p.edge_finish,
            stitch_pitch_mm=p.stitch_pitch_mm,
            suggested_thickness_mm=t,
            notes="前后两片裁切尺寸相同；顶边为开口",
        )

        slots = build_slot_pieces(
            slots=p.slots,
            leather_thickness_mm=t,
            seam_allowance_mm=p.seam_allowance_mm,
            stagger_mm=p.stagger_mm,
            top_slot_height_mm=p.top_slot_height_mm,
            edge_finish=p.edge_finish,
            stitch_pitch_mm=p.stitch_pitch_mm,
        )

        return Pattern(
            name=f"卡包（{p.slots} 卡位）",
            pieces=[panel, *slots],
            leather_thickness_mm=t,
            seam_allowance_mm=p.seam_allowance_mm,
            edge_finish=p.edge_finish,
            stitch_pitch_mm=p.stitch_pitch_mm,
        )
