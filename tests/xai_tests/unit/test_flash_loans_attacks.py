"""
Security regression tests for flash loans (reentrancy and partial repayment).
"""

import pytest

from xai.core.defi.flash_loans import FlashLoanProvider, VMExecutionError


def test_reentrancy_attempt_is_blocked():
    """Callback attempting nested flash loan should be rejected."""
    provider = FlashLoanProvider()
    provider.liquidity_pools = {"XAI": 1_000}

    def malicious_callback(borrower, assets, amounts, fees, params):
        # Attempt to reenter while loan is active
        with pytest.raises(VMExecutionError):
            provider.flash_loan(borrower, borrower, assets, amounts, callback=None)
        return True

    with pytest.raises(VMExecutionError):
        provider.flash_loan(
            borrower="attacker",
            receiver="attacker",
            assets=["XAI"],
            amounts=[500],
            callback=malicious_callback,
        )


def test_partial_repayment_attack_detected():
    """Callback returning principal without fees should fail post-check."""
    provider = FlashLoanProvider()
    provider.liquidity_pools = {"XAI": 20_000}

    def underpaying_callback(borrower, assets, amounts, fees, params):
        # Return only principal, skip fee
        provider.liquidity_pools[assets[0]] += amounts[0]
        return True

    with pytest.raises(VMExecutionError):
        provider.flash_loan(
            borrower="attacker",
            receiver="attacker",
            assets=["XAI"],
            amounts=[10_000],
            callback=underpaying_callback,
        )
