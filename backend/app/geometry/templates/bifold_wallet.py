"""BifoldWallet template: shell + left/right linings + card slot stacks.

Construction model (confirmed with the product owner):

- One outer shell folds in half around a central fold zone. Inside, a left
  and a right lining panel each carry a stack of 0-3 card slots. The bill
  compartment is the space between the shell and the linings (linings are
  sewn to the shell along their outer side edge and the bottom; their
  inner edges stay free so bills slide across the full interior width).
  No separate bill-compartment piece is cut.
- Shell length follows the workshop rule verbatim:
      shell net length = left lining width + right lining width
                         + fold-zone compensation
      fold-zone compensation = single-side stacked thickness x factor
  where the single-side stacked thickness is the THICKER side's interior
  layers (lining + its slots) x leather thickness, and the factor defaults
  to 3 (empirical, configurable). Confirmed: only one side's layers count.
- Panel height: net base height = max(slot requirement per side, bill
  height + top clearance); confirmed bill reference is the euro note
  (50 EUR = 140 x 77 mm). Per-edge thickness compensation is then added at
  the bottom seam: linings wrap their slot stack (d = slots), the shell
  wraps lining + slots of the thicker side (d = 1 + max slots).
- The shell carries two dash-dot fold guide lines bounding the fold zone.
"""

from __future__ import annotations

from dataclasses import dataclass

from shapely.geometry import LineString

from ..core import (
    BIFOLD_FOLD_COMPENSATION_FACTOR,
    BILL_TOP_CLEARANCE_MM,
    DEFAULT_BILL_HEIGHT_MM,
    DEFAULT_SEAM_ALLOWANCE_MM,
    DEFAULT_SLOT_STAGGER_MM,
    DEFAULT_STITCH_PITCH_MM,
    SLOT_STAGGER_RANGE_MM,
    Edge,
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
class BifoldWalletParams:
    slots_left: int = 3
    slots_right: int = 3
    leather_thickness_mm: float = 1.2
    seam_allowance_mm: float = DEFAULT_SEAM_ALLOWANCE_MM
    stagger_mm: float = DEFAULT_SLOT_STAGGER_MM
    top_slot_height_mm: float = DEFAULT_TOP_SLOT_HEIGHT_MM
    top_margin_mm: float = DEFAULT_TOP_MARGIN_MM
    bill_height_mm: float = DEFAULT_BILL_HEIGHT_MM
    bill_clearance_mm: float = BILL_TOP_CLEARANCE_MM
    fold_factor: float = BIFOLD_FOLD_COMPENSATION_FACTOR
    edge_finish: EdgeFinish = EdgeFinish.BURNISHED
    stitch_pitch_mm: float = DEFAULT_STITCH_PITCH_MM

    def validate(self) -> None:
        if not (0 <= self.slots_left <= 3 and 0 <= self.slots_right <= 3):
            raise ValueError("bifold wallet supports 0-3 slots per side")
        if not (SLOT_STAGGER_RANGE_MM[0] <= self.stagger_mm <= SLOT_STAGGER_RANGE_MM[1]):
            raise ValueError(
                f"slot stagger {self.stagger_mm} mm outside allowed range "
                f"{SLOT_STAGGER_RANGE_MM}"
            )
        if self.leather_thickness_mm <= 0:
            raise ValueError("leather thickness must be positive")
        if self.fold_factor <= 0:
            raise ValueError("fold compensation factor must be positive")


class BifoldWallet:
    """Parametric bifold wallet pattern generator."""

    def __init__(self, params: BifoldWalletParams | None = None) -> None:
        self.params = params or BifoldWalletParams()
        self.params.validate()

    def fold_compensation_mm(self) -> float:
        """Fold-zone compensation: thicker side's interior layers (lining +
        slots) x leather thickness x empirical factor (default 3).
        """
        p = self.params
        layers = 1 + max(p.slots_left, p.slots_right)
        return layers * p.leather_thickness_mm * p.fold_factor

    def _lining_net_width_mm(self, slots: int) -> float:
        # The lining wraps its slot stack at each side seam (d = slots).
        comp = thickness_compensation_mm(slots, self.params.leather_thickness_mm)
        return SLOT_NET_WIDTH_MM + 2 * comp

    def build(self) -> Pattern:
        p = self.params
        t = p.leather_thickness_mm

        # Net base height before per-piece bottom compensation: tall enough
        # for the deepest slot stack AND the banknote.
        base_h = max(
            slot_required_height_mm(p.slots_left, p.stagger_mm, p.top_margin_mm),
            slot_required_height_mm(p.slots_right, p.stagger_mm, p.top_margin_mm),
            p.bill_height_mm + p.bill_clearance_mm,
        )

        lining_w_left = self._lining_net_width_mm(p.slots_left)
        lining_w_right = self._lining_net_width_mm(p.slots_right)
        fold_comp = self.fold_compensation_mm()

        # --- Shell --------------------------------------------------------
        shell_comp = thickness_compensation_mm(1 + max(p.slots_left, p.slots_right), t)
        shell_net_w = lining_w_left + lining_w_right + fold_comp
        shell_net_h = base_h + shell_comp  # bottom seam only; top is bill mouth
        shell = build_rect_piece(
            name="外壳",
            quantity=1,
            net_width_mm=shell_net_w,
            net_height_mm=shell_net_h,
            seam_allowance_mm=p.seam_allowance_mm,
            sewn_edges=SEWN_EDGES,
            edge_finish=p.edge_finish,
            stitch_pitch_mm=p.stitch_pitch_mm,
            suggested_thickness_mm=t,
            notes="顶边为钞票口；中部点划线之间为折叠区",
        )
        # Fold guide lines bounding the fold zone (net coordinates).
        shell.guide_lines = [
            LineString([(lining_w_left, 0), (lining_w_left, shell_net_h)]),
            LineString([(lining_w_left + fold_comp, 0), (lining_w_left + fold_comp, shell_net_h)]),
        ]

        # --- Linings (sewn along outer side + bottom; inner edge free) ----
        linings = []
        for side, slots_n, lining_w, outer_edge in (
            ("左", p.slots_left, lining_w_left, Edge.LEFT),
            ("右", p.slots_right, lining_w_right, Edge.RIGHT),
        ):
            comp = thickness_compensation_mm(slots_n, t)
            linings.append(
                build_rect_piece(
                    name=f"内衬（{side}）",
                    quantity=1,
                    net_width_mm=lining_w,
                    net_height_mm=base_h + comp,  # bottom seam only
                    seam_allowance_mm=p.seam_allowance_mm,
                    sewn_edges=(outer_edge, Edge.BOTTOM),
                    edge_finish=p.edge_finish,
                    stitch_pitch_mm=p.stitch_pitch_mm,
                    suggested_thickness_mm=t,
                    notes="靠书脊一侧的竖边不缝合，钞票仓贯通",
                )
            )

        # --- Card slot stacks ---------------------------------------------
        slot_pieces = []
        for side, slots_n in (("左", p.slots_left), ("右", p.slots_right)):
            slot_pieces.extend(
                build_slot_pieces(
                    slots=slots_n,
                    name_prefix=f"{side}卡位片",
                    leather_thickness_mm=t,
                    seam_allowance_mm=p.seam_allowance_mm,
                    stagger_mm=p.stagger_mm,
                    top_slot_height_mm=p.top_slot_height_mm,
                    edge_finish=p.edge_finish,
                    stitch_pitch_mm=p.stitch_pitch_mm,
                )
            )

        return Pattern(
            name=f"二折短夹（左 {p.slots_left} / 右 {p.slots_right} 卡位）",
            pieces=[shell, *linings, *slot_pieces],
            leather_thickness_mm=t,
            seam_allowance_mm=p.seam_allowance_mm,
            edge_finish=p.edge_finish,
            stitch_pitch_mm=p.stitch_pitch_mm,
        )
