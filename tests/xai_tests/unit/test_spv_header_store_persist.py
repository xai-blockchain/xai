"""
Persistence tests for SPVHeaderStore.
"""

from xai.core.spv_header_store import SPVHeaderStore, Header


def test_save_and_load_roundtrip(tmp_path):
    store = SPVHeaderStore()
    genesis = Header(height=0, block_hash="00" * 16, prev_hash="", bits=0x1f00ffff)
    h1 = Header(height=1, block_hash="00" * 15 + "11", prev_hash=genesis.block_hash, bits=0x1f00ffff)
    store.add_header(genesis)
    store.add_header(h1)

    path = tmp_path / "headers.json"
    store.save(str(path))

    loaded = SPVHeaderStore.load(str(path))
    assert loaded.get_best_tip().block_hash == h1.block_hash
    assert loaded.get_header(genesis.block_hash) is not None
    assert loaded.has_height(1) is True
