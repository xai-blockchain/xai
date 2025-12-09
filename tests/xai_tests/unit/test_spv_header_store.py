"""
Tests for SPVHeaderStore chain selection.
"""

from xai.core.spv_header_store import SPVHeaderStore, Header


def test_add_header_and_best_tip():
    store = SPVHeaderStore()
    genesis = Header(height=0, block_hash="h0", prev_hash="", bits=1)
    assert store.add_header(genesis) is True

    h1 = Header(height=1, block_hash="h1", prev_hash="h0", bits=2)
    h2 = Header(height=2, block_hash="h2", prev_hash="h1", bits=2)
    assert store.add_header(h1) is True
    assert store.add_header(h2) is True

    best = store.get_best_tip()
    assert best.block_hash == "h2"
    assert best.cumulative_work > 0


def test_reject_orphan_and_choose_heavier_fork():
    store = SPVHeaderStore()
    genesis = Header(height=0, block_hash="h0", prev_hash="", bits=1)
    store.add_header(genesis)

    # main chain
    h1 = Header(height=1, block_hash="h1", prev_hash="h0", bits=2)
    h2 = Header(height=2, block_hash="h2", prev_hash="h1", bits=2)
    store.add_header(h1)
    store.add_header(h2)

    # fork with higher work at same height
    f1 = Header(height=1, block_hash="f1", prev_hash="h0", bits=5)
    f2 = Header(height=2, block_hash="f2", prev_hash="f1", bits=5)
    store.add_header(f1)
    store.add_header(f2)

    best = store.get_best_tip()
    assert best.block_hash == "f2"
    assert best.cumulative_work > store.get_header("h2").cumulative_work

    # Orphan rejected
    orphan = Header(height=3, block_hash="orphan", prev_hash="missing", bits=10)
    assert store.add_header(orphan) is False
