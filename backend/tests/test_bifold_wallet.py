"""Acceptance tests for the BifoldWallet template.

Hand calculation for the default bifold wallet
(slots 3/3, leather t=1.2 mm, seam sa=3.5 mm, stagger=12 mm, top slot
 height=40 mm, top margin=10 mm, bill 77 mm (euro) + 5 mm clearance,
 fold factor=3, burnished):

  comp(k) = k * t * pi/2:
    comp(1) = 1.884956   comp(3) = 5.654867   comp(4) = 7.539822

  base net height = max(slot requirement, bill requirement)
    slot req  = 12*2 + 54 + 10 = 88
    bill req  = 77 + 5        = 82          -> base = 88

  LINING (each side, wraps its 3 slots, d = 3):
    net width  = 87.1 + 2*comp(3) = 98.409734
    net height = 88 + comp(3)     = 93.654867 (bottom seam only)

  FOLD-ZONE COMPENSATION (confirmed: single, thicker side's interior
  layers x t x factor):
    (1 lining + 3 slots) * 1.2 * 3 = 14.4

  SHELL (wraps lining + slots of the thicker side at the bottom, d = 4):
    net length = 98.409734 * 2 + 14.4 = 211.219467
    net height = 88 + comp(4)         = 95.539822
    cut size   = 218.219467 x 102.539822
    fold guide lines at x = 98.409734 and x = 113.809734 - 1 = 112.809734
"""

import math

import pytest

from app.geometry.templates.bifold_wallet import BifoldWallet, BifoldWalletParams

T = 1.2
COMP1 = T * math.pi / 2
COMP3 = 3 * COMP1
COMP4 = 4 * COMP1
SLOT_NET_W = 85.6 + 1.5
LINING_W = SLOT_NET_W + 2 * COMP3


@pytest.fixture
def default_pattern():
    return BifoldWallet().build()


class TestDefaultBifold:
    def test_piece_inventory(self, default_pattern):
        # shell + 2 linings + 3 slots per side.
        assert len(default_pattern.pieces) == 9
        names = [p.name for p in default_pattern.pieces]
        assert names[0] == "外壳"
        assert "内衬（左）" in names and "内衬（右）" in names

    def test_shell_matches_hand_calculation(self, default_pattern):
        shell = default_pattern.pieces[0]
        assert shell.net_size == pytest.approx((2 * LINING_W + 14.4, 88 + COMP4))
        assert shell.cut_size == pytest.approx((218.219467, 102.539822), abs=1e-5)

    def test_lining_matches_hand_calculation(self, default_pattern):
        lining = default_pattern.pieces[1]
        assert lining.net_size == pytest.approx((LINING_W, 88 + COMP3))

    def test_fold_guide_lines_bound_the_fold_zone(self, default_pattern):
        shell = default_pattern.pieces[0]
        assert len(shell.guide_lines) == 2
        xs = sorted(line.coords[0][0] for line in shell.guide_lines)
        assert xs[0] == pytest.approx(LINING_W)
        assert xs[1] == pytest.approx(LINING_W + 14.4)
        # Guide lines span the full shell height.
        assert shell.guide_lines[0].length == pytest.approx(88 + COMP4)


class TestFoldCompensation:
    def test_single_side_layers_rule(self):
        # Confirmed rule: thicker side's interior layers (lining + slots).
        assert BifoldWallet().fold_compensation_mm() == pytest.approx((1 + 3) * 1.2 * 3)

    def test_asymmetric_uses_thicker_side(self):
        wallet = BifoldWallet(BifoldWalletParams(slots_left=3, slots_right=1))
        assert wallet.fold_compensation_mm() == pytest.approx((1 + 3) * 1.2 * 3)

    def test_factor_configurable(self):
        wallet = BifoldWallet(BifoldWalletParams(fold_factor=2.5))
        assert wallet.fold_compensation_mm() == pytest.approx(4 * 1.2 * 2.5)

    def test_thickness_drives_compensation(self):
        wallet = BifoldWallet(BifoldWalletParams(leather_thickness_mm=1.0))
        assert wallet.fold_compensation_mm() == pytest.approx(4 * 1.0 * 3)


class TestAsymmetricSlots:
    def test_shell_width_sums_both_linings(self):
        # 3/1 slots: right lining wraps only 1 layer.
        pattern = BifoldWallet(BifoldWalletParams(slots_left=3, slots_right=1)).build()
        shell, lining_l, lining_r = pattern.pieces[:3]
        assert lining_l.net_size[0] == pytest.approx(LINING_W)
        assert lining_r.net_size[0] == pytest.approx(SLOT_NET_W + 2 * COMP1)
        assert shell.net_size[0] == pytest.approx(
            LINING_W + SLOT_NET_W + 2 * COMP1 + 14.4
        )

    def test_slot_piece_count(self):
        pattern = BifoldWallet(BifoldWalletParams(slots_left=2, slots_right=0)).build()
        # shell + 2 linings + 2 left slots.
        assert len(pattern.pieces) == 5


class TestBillCompartment:
    def test_bill_height_governs_when_few_slots(self):
        # 1/1 slots: slot requirement 54+10 = 64 < bill 77+5 = 82.
        pattern = BifoldWallet(BifoldWalletParams(slots_left=1, slots_right=1)).build()
        lining = pattern.pieces[1]
        assert lining.net_size[1] == pytest.approx(82 + COMP1)

    def test_bill_height_configurable(self):
        # USD note 66.3 mm: requirement 71.3 < slot requirement 88.
        tall = BifoldWallet(BifoldWalletParams(slots_left=0, slots_right=0)).build()
        usd = BifoldWallet(
            BifoldWalletParams(slots_left=0, slots_right=0, bill_height_mm=66.3)
        ).build()
        assert tall.pieces[0].net_size[1] > usd.pieces[0].net_size[1]


class TestValidation:
    def test_slot_bounds(self):
        with pytest.raises(ValueError):
            BifoldWallet(BifoldWalletParams(slots_left=4))

    def test_fold_factor_positive(self):
        with pytest.raises(ValueError):
            BifoldWallet(BifoldWalletParams(fold_factor=0))
