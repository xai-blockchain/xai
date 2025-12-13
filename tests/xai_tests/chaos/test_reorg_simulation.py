import time

import pytest

from xai.core.blockchain import Blockchain, Block, BlockHeader, Transaction
from xai.core.reorg_simulator import ReorgSimulator


def _make_block(index: int, prev_hash: str, txs: list[Transaction]) -> Block:
    header = BlockHeader(
        index=index,
        previous_hash=prev_hash,
        timestamp=time.time(),
        difficulty=0,
        merkle_root="",
        nonce=0,
        miner_pubkey="miner",
    )
    header.hash = header.calculate_hash()
    return Block(header, txs)


@pytest.mark.security
@pytest.mark.parametrize("fork_len", [1, 2])
def test_reorg_simulator_tracks_utxo_digest(fork_len, tmp_path):
    chain = Blockchain(data_dir=str(tmp_path))
    chain.verify_block_signature = lambda header: True  # simplify test harness
    simulator = ReorgSimulator(chain)

    # Mine a few blocks on the main chain (height = 4)
    genesis = chain.chain[0] if chain.chain else None
    prev_hash = genesis.hash if genesis else "0"
    for i in range(1, 4):
        blk = _make_block(i, prev_hash, [])
        chain._add_block_to_chain(blk)
        prev_hash = blk.hash

    pre_snapshot = chain.compute_state_snapshot()

    # Build a fork with higher height (fork after block 1)
    fork_blocks = []
    fork_prev = chain.chain[1].hash
    for i in range(2, 2 + fork_len + 2):  # ensure fork is longer than main by at least 1
        blk = _make_block(i, fork_prev, [])
        fork_blocks.append(blk)
        fork_prev = blk.hash

    # Candidate chain is genesis + block1 + fork branch
    candidate_chain = [chain.chain[0], chain.chain[1]] + fork_blocks

    replaced, pre, post = simulator.simulate_reorg(candidate_chain)

    assert replaced is True
    assert pre["tip"] == pre_snapshot["tip"]
    assert post["height"] >= pre["height"]
    assert isinstance(post["utxo_digest"], str)
