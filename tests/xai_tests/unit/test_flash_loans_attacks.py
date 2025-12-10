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


def test_multi_step_principal_siphon_detected():
    """Attacker repays then siphons funds before completion; should revert."""
    provider = FlashLoanProvider()
    provider.liquidity_pools = {"XAI": 50_000}

    def siphon_callback(borrower, assets, amounts, fees, params):
        asset = assets[0]
        # Repay principal + fee first
        provider.liquidity_pools[asset] += amounts[0] + fees[0]
        # Attempt to siphon 1 token after repayment (multi-step attack)
        provider.liquidity_pools[asset] -= 1
        return True

    with pytest.raises(VMExecutionError):
        provider.flash_loan(
            borrower="siphoner",
            receiver="siphoner",
            assets=["XAI"],
            amounts=[5_000],
            callback=siphon_callback,
        )


def test_multi_asset_fee_shortfall_detected():
    """If one asset fee is missing in a multi-asset loan, provider reverts."""
    provider = FlashLoanProvider()
    provider.liquidity_pools = {"XAI": 40_000, "USDC": 80_000}

    def mixed_callback(borrower, assets, amounts, fees, params):
        # Repay XAI principal + fee
        provider.liquidity_pools[assets[0]] += amounts[0] + fees[0]
        # Repay only principal for USDC, omitting fee
        provider.liquidity_pools[assets[1]] += amounts[1]
        return True

    with pytest.raises(VMExecutionError):
        provider.flash_loan(
            borrower="multi_asset_attacker",
            receiver="multi_asset_attacker",
            assets=["XAI", "USDC"],
            amounts=[10_000, 20_000],
            callback=mixed_callback,
        )
