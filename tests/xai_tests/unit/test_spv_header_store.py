"""
Tests for SPVHeaderStore chain selection.
"""

from xai.core.spv_header_store import SPVHeaderStore, Header


def test_add_header_and_best_tip():
    store = SPVHeaderStore()
    # bits chosen so that small hashes satisfy target
    genesis = Header(height=0, block_hash="00" * 16, prev_hash="", bits=0x1f00ffff)
    assert store.add_header(genesis) is True

    h1 = Header(height=1, block_hash="00" * 16 + "11", prev_hash=genesis.block_hash, bits=0x1f00ffff)
    h2 = Header(height=2, block_hash="00" * 16 + "22", prev_hash=h1.block_hash, bits=0x1f00ffff)
    assert store.add_header(h1) is True
    assert store.add_header(h2) is True

    best = store.get_best_tip()
    assert best.block_hash == h2.block_hash
    assert best.cumulative_work > 0


def test_reject_orphan_and_choose_heavier_fork():
    store = SPVHeaderStore()
    genesis = Header(height=0, block_hash="00" * 16, prev_hash="", bits=0x1f00ffff)
    store.add_header(genesis)

    # main chain
    h1 = Header(height=1, block_hash="00" * 16 + "a1", prev_hash=genesis.block_hash, bits=0x1f00fffe)
    h2 = Header(height=2, block_hash="00" * 16 + "a2", prev_hash=h1.block_hash, bits=0x1f00fffe)
    store.add_header(h1)
    store.add_header(h2)

    # fork with higher work at same height
    f1 = Header(height=1, block_hash="00" * 16 + "b1", prev_hash=genesis.block_hash, bits=0x2000fffe)
    f2 = Header(height=2, block_hash="00" * 16 + "b2", prev_hash=f1.block_hash, bits=0x2000fffe)
    store.add_header(f1)
    store.add_header(f2)

    best = store.get_best_tip()
    assert best.block_hash == f2.block_hash
    assert best.cumulative_work > store.get_header(h2.block_hash).cumulative_work

    # Orphan rejected
    orphan = Header(height=3, block_hash="ff" * 16, prev_hash="missing", bits=0x1f00ffff)
    assert store.add_header(orphan) is False


def test_invalid_pow_rejected():
    store = SPVHeaderStore()
    # bits make target small; hash too large
    bad = Header(height=0, block_hash="ff" * 16, prev_hash="", bits=0x01020304)
    assert store.add_header(bad) is False
