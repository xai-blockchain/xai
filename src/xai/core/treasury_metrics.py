"""
Fee treasury instrumentation for the XAI blockchain.

Provides Prometheus metrics that track how much XAI is collected
and how much is held in the fee treasury, with helper functions that
are safe to call from the settlement path.
"""

from __future__ import annotations

from typing import Any, Optional
from prometheus_client import Counter, Gauge

fee_collection_counter = Counter(
    "xai_trade_fee_collected_total", "Total XAI collected from wallet trade fees", ["currency"]
)

fee_transfer_events = Counter(
    "xai_trade_fee_transfer_events_total",
    "Total number of fee transfer events emitted by the treasury",
    ["direction"],
)

treasury_balance_gauge = Gauge(
    "xai_fee_treasury_balance", "Current balance of the fee treasury", ["address", "currency"]
)


def record_fee_collection(currency: str, amount: float) -> None:
    """Increment the fee counters for the specified currency."""
    if amount <= 0:
        return

    fee_collection_counter.labels(currency=currency).inc(amount)
    fee_transfer_events.labels(direction="collected").inc()


def update_fee_treasury_balance(blockchain: Any, fee_address: str, currency: str = "XAI") -> None:
    """Refresh the treasury balance gauge from on-chain UTXOs."""
    if not blockchain or not fee_address:
        return

    balance = blockchain.get_balance(fee_address)
    treasury_balance_gauge.labels(address=fee_address, currency=currency).set(balance)
