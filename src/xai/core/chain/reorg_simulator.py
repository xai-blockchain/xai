"""
Reorganization and partition simulation harness.

Provides repeatable hooks to exercise reorg paths while capturing state integrity
snapshots (height, tip hash, UTXO digest) before and after.
"""

from __future__ import annotations

from typing import Any


class ReorgSimulator:
    """Lightweight harness to drive chain reorg scenarios with integrity snapshots."""

    def __init__(self, blockchain: Any) -> None:
        if not hasattr(blockchain, "replace_chain") or not hasattr(blockchain, "compute_state_snapshot"):
            raise TypeError("blockchain must expose replace_chain() and compute_state_snapshot()")
        self.blockchain = blockchain

    def snapshot(self, label: str = "snapshot") -> dict[str, Any]:
        snap = self.blockchain.compute_state_snapshot()
        snap["label"] = label
        return snap

    def simulate_reorg(self, candidate_chain: list[Any]) -> tuple[bool, dict[str, Any], dict[str, Any]]:
        """
        Attempt a reorg against the supplied candidate chain.

        Returns:
            (replaced, pre_snapshot, post_snapshot)
        """
        pre = self.snapshot("pre-reorg")
        result = self.blockchain.replace_chain(candidate_chain)
        post = self.snapshot("post-reorg")
        replaced = bool(result) or post.get("height", 0) > pre.get("height", 0)
        return replaced, pre, post
