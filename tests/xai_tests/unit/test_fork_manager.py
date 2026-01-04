"""
Unit tests for ForkManager helpers (work calculation, pruning, WAL).
"""

import json
import os
from types import SimpleNamespace

from xai.core.chain.fork_manager import ForkManager


class DummyBlockchain:
    """Minimal blockchain stub to satisfy ForkManager dependencies."""

    def __init__(self, wal_path: str):
        self.orphan_blocks = {}
        self.max_orphan_blocks = 2
        self.reorg_wal_path = wal_path
        self._max_pow_target = int("f" * 64, 16)
        self.storage = SimpleNamespace(load_block_from_disk=lambda idx: None)
        self.state_manager = SimpleNamespace(add_block_to_chain=lambda block: True)


def test_calculate_chain_work_handles_headers_and_wrappers(tmp_path):
    """Work calculation sums 2**difficulty across mixed block-like items."""
    bc = DummyBlockchain(str(tmp_path / "wal.json"))
    fm = ForkManager(bc)

    chain = [
        SimpleNamespace(difficulty=1),
        SimpleNamespace(header=SimpleNamespace(difficulty=2)),
        SimpleNamespace(difficulty=3),
    ]

    work = fm._calculate_chain_work(chain)

    def expected_work(diff: int) -> int:
        shift_bits = min(diff * 4, 256)
        target = 0 if shift_bits >= 256 else bc._max_pow_target >> shift_bits
        return bc._max_pow_target // max(target + 1, 1)

    expected = sum(expected_work(item.header.difficulty if hasattr(item, "header") else item.difficulty)
                  for item in chain)
    assert work == expected


def test_prune_orphans_respects_maximum(tmp_path):
    """Orphan pruning drops oldest indices when above limit."""
    bc = DummyBlockchain(str(tmp_path / "wal.json"))
    bc.orphan_blocks = {
        1: [SimpleNamespace(hash="a"), SimpleNamespace(hash="b")],
        2: [SimpleNamespace(hash="c")],
    }
    fm = ForkManager(bc)

    fm._prune_orphans()

    remaining = sum(len(v) for v in bc.orphan_blocks.values())
    assert remaining <= bc.max_orphan_blocks
    assert 2 in bc.orphan_blocks  # newest index preserved


def test_write_commit_and_rollback_wal(tmp_path):
    """WAL entries are written, committed, and rolled back from disk."""
    wal_path = tmp_path / "wal.json"
    bc = DummyBlockchain(str(wal_path))
    fm = ForkManager(bc)

    wal_entry = fm._write_reorg_wal("old", "new", 5)
    with wal_path.open() as f:
        data = json.load(f)
    assert data["status"] == "in_progress"
    assert wal_entry["new_tip"] == "new"

    fm._commit_reorg_wal(wal_entry)
    with wal_path.open() as f:
        data = json.load(f)
    assert data["status"] == "committed"

    fm._rollback_reorg_wal(wal_entry)
    assert not os.path.exists(wal_path)
