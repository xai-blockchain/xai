"""Unit tests for SwapRouter sandwich attack detection."""

from xai.core.defi.swap_router import SwapRouter


def test_detects_same_caller_bracketing_swaps():
    """Router should flag identical callers bracketing the same pair."""
    router = SwapRouter()
    pending = [
        ("0xabc", "ETH>USDC", 100),
        ("0xdef", "ETH>USDC", 200),
        ("0xabc", "ETH>USDC", 50),
    ]

    suspicious = router.detect_sandwich_attack(pending)

    assert suspicious
    attacker, victim = suspicious[0]
    assert attacker.startswith("0xabc:ETH>USDC")
    assert victim.startswith("victim:ETH>USDC")


def test_no_flag_when_callers_differ():
    """Different callers on a pair should not trigger detection."""
    router = SwapRouter()
    pending = [
        ("0xaaa", "ETH>USDT", 10),
        ("0xbbb", "ETH>USDT", 20),
        ("0xccc", "ETH>USDT", 30),
    ]

    assert router.detect_sandwich_attack(pending) == []


def test_multiple_pairs_report_independently():
    """Multiple token pairs should be analyzed independently."""
    router = SwapRouter()
    pending = [
        ("0xaaa", "ETH>DAI", 10),
        ("0xaaa", "ETH>DAI", 20),
        ("0xbbb", "WBTC>USDC", 5),
        ("0xbbb", "WBTC>USDC", 6),
    ]

    suspicious = router.detect_sandwich_attack(pending)

    assert len(suspicious) == 2
    pairs = {entry[0].split(":")[1] for entry in suspicious}
    assert pairs == {"ETH>DAI", "WBTC>USDC"}
