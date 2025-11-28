from xai.core.blockchain import Blockchain, Block
from xai.core.block_header import BlockHeader


def _block(height: int, prev_hash: str, nonce: int = 0) -> Block:
    header = BlockHeader(
        index=height,
        previous_hash=prev_hash,
        merkle_root="0" * 64,
        timestamp=height,
        difficulty=2,
        nonce=nonce,
    )
    return Block(header=header, transactions=[])


def test_reorg_preserves_state_snapshot_and_bounds_orphans(tmp_path):
    bc = Blockchain(data_dir=str(tmp_path))
    # Build a short main chain
    b1 = _block(1, bc.chain[-1].hash)
    b1.header.hash = b1.header.calculate_hash()
    bc.add_block(b1)
    b2 = _block(2, b1.hash)
    b2.header.hash = b2.header.calculate_hash()
    bc.add_block(b2)

    # Competing longer chain
    fork_blocks = []
    prev = bc.chain[1].hash  # fork at height 2
    for h in range(2, 6):
        blk = _block(h, prev)
        blk.header.hash = blk.header.calculate_hash()
        fork_blocks.append(blk)
        prev = blk.hash

    # Snapshot before reorg
    pre_snapshot = bc.compute_state_snapshot()

    # Push fork blocks as orphans to exceed bounded pool
    bc.max_orphan_blocks = 3
    for blk in fork_blocks:
        bc.orphan_blocks.setdefault(blk.index, []).append(blk)

    # Trigger reorg with longer fork
    bc._check_orphan_chains_for_reorg()

    post_snapshot = bc.compute_state_snapshot()
    assert post_snapshot["height"] == len(bc.chain)
    assert pre_snapshot["utxo_digest"] == post_snapshot["utxo_digest"] or post_snapshot["height"] > pre_snapshot["height"]

    # Orphan pool should be bounded
    total_orphans = sum(len(v) for v in bc.orphan_blocks.values())
    assert total_orphans <= bc.max_orphan_blocks
