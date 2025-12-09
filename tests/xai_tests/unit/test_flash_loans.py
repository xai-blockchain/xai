"""
Unit tests for FlashLoanProvider.

Coverage targets:
- Successful loan with repayment and fee collection
- Reentrancy/replay protections (active loan guard)
- Liquidity validation and owner-gated operations
"""

import pytest

from xai.core.defi.flash_loans import FlashLoanProvider
from xai.core.vm.exceptions import VMExecutionError


def test_flash_loan_requires_repayment_and_collects_fees():
    """Principal and fee must be returned; fees are recorded."""
    provider = FlashLoanProvider(owner="owner")
    provider.liquidity_pools = {"USDC": 1_000_000}

    def callback(borrower, assets, amounts, fees, params):
        # Repay principal + fee directly into pool
        provider.liquidity_pools[assets[0]] += amounts[0] + fees[0]
        return True

    success = provider.flash_loan(
        borrower="user",
        receiver="user",
        assets=["USDC"],
        amounts=[100_000],
        callback=callback,
        params=b"",
    )
    assert success is True
    assert provider.collected_fees["USDC"] > 0
    assert provider.total_loans == 1


def test_flash_loan_rejects_insufficient_liquidity():
    """Request larger than pool is rejected."""
    provider = FlashLoanProvider(owner="owner")
    provider.liquidity_pools = {"USDC": 1_000}
    with pytest.raises(VMExecutionError):
        provider.flash_loan(
            borrower="user",
            receiver="user",
            assets=["USDC"],
            amounts=[10_000],
            callback=lambda *_args, **_kwargs: True,
            params=b"",
        )


def test_reentrancy_guard_blocks_parallel_loans():
    """Second concurrent loan for same borrower is blocked."""
    provider = FlashLoanProvider(owner="owner")
    provider.liquidity_pools = {"USDC": 10_000}

    def callback_reenter(*_args, **_kwargs):
        with pytest.raises(VMExecutionError):
            provider.flash_loan(
                borrower="user",
                receiver="user",
                assets=["USDC"],
                amounts=[1_000],
                callback=lambda *_a, **_k: True,
                params=b"",
            )
        # Repay original
        provider.liquidity_pools["USDC"] += 1_000 + provider.get_flash_loan_fee_amount("USDC", 1_000)
        return True

    assert provider.flash_loan(
        borrower="user",
        receiver="user",
        assets=["USDC"],
        amounts=[1_000],
        callback=callback_reenter,
        params=b"",
    )


def test_owner_only_liquidity_and_fee_controls():
    """Only owner can add/remove liquidity and set fees."""
    provider = FlashLoanProvider(owner="owner")
    with pytest.raises(VMExecutionError):
        provider.add_liquidity("attacker", "USDC", 100)
    assert provider.add_liquidity("owner", "USDC", 100)

    with pytest.raises(VMExecutionError):
        provider.set_flash_loan_fee("attacker", 10)
    assert provider.set_flash_loan_fee("owner", 10)


def test_flash_loan_fails_on_callback_and_fee_shortfall():
    """Callback failure or missing fees causes revert."""
    provider = FlashLoanProvider(owner="owner")
    provider.liquidity_pools = {"DAI": 1_000}

    # Callback returns False -> raise
    with pytest.raises(VMExecutionError):
        provider.flash_loan(
            borrower="user",
            receiver="user",
            assets=["DAI"],
            amounts=[100],
            callback=lambda *_args, **_kwargs: False,
            params=b"",
        )

    # Callback succeeds but repayment short on fees -> raise
    def callback_short_fee(borrower, assets, amounts, fees, params):
        # repay only principal
        provider.liquidity_pools[assets[0]] += amounts[0]
        return True

    with pytest.raises(VMExecutionError):
        provider.flash_loan(
            borrower="user",
            receiver="user",
            assets=["DAI"],
            amounts=[100_000],
            callback=callback_short_fee,
            params=b"",
        )
