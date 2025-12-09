"""
Unit tests for atomic swap fee calculation helper.
"""

from decimal import Decimal

import pytest

from xai.core.aixn_blockchain.atomic_swap_11_coins import CrossChainVerifier


class TestAtomicSwapFeeCalc:
    """Validate fee calculation boundaries and rounding."""

    def test_fee_clamped_between_min_and_max(self):
        fee = CrossChainVerifier.calculate_atomic_swap_fee(amount=1, fee_rate_per_byte=0.00000001, tx_size_bytes=200)
        assert fee >= Decimal("0.0001")
        assert fee <= Decimal("0.25")

    def test_fee_uses_safety_buffer(self):
        fee = CrossChainVerifier.calculate_atomic_swap_fee(
            amount=10, fee_rate_per_byte=Decimal("0.00000002"), tx_size_bytes=300, safety_buffer_bps=50
        )
        # network fee: 0.00000002 * 300 = 0.000006 -> rounded up
        # safety: 10 * 0.005 = 0.05 -> dominates
        assert fee.quantize(Decimal("0.00000001")) == Decimal("0.05000600")

    def test_invalid_inputs_raise(self):
        with pytest.raises(ValueError):
            CrossChainVerifier.calculate_atomic_swap_fee(amount=0, fee_rate_per_byte=1)
        with pytest.raises(ValueError):
            CrossChainVerifier.calculate_atomic_swap_fee(amount=1, fee_rate_per_byte=0)
        with pytest.raises(ValueError):
            CrossChainVerifier.calculate_atomic_swap_fee(amount="abc", fee_rate_per_byte=1)

    def test_fee_capped_at_max(self):
        fee = CrossChainVerifier.calculate_atomic_swap_fee(
            amount=1000, fee_rate_per_byte=1, tx_size_bytes=1000, max_fee=Decimal("0.1"), safety_buffer_bps=10000
        )
        assert fee == Decimal("0.1")
