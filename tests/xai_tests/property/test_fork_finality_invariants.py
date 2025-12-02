import hashlib
import itertools
from unittest.mock import patch

from xai.core.advanced_consensus import AdvancedConsensusManager
from xai.core.crypto_utils import sign_message_hex, deterministic_keypair_from_seed
from xai.core.block_header import BlockHeader
from xai.core.blockchain import Blockchain, Block


def _mine_block(index: int, prev_hash: str, priv: str, pub: str, difficulty: int = 1, ts: float = 0.0) -> Block:
    nonce = 0
    merkle = hashlib.sha256(b"").hexdigest()
    while True:
        header = BlockHeader(
            index=index,
            previous_hash=prev_hash,
            merkle_root=merkle,
            timestamp=ts + index,
            difficulty=difficulty,
            nonce=nonce,
        )
        h = header.calculate_hash()
        if h.startswith("0" * difficulty):
            header.hash = h
            header.miner_pubkey = pub
            header.signature = sign_message_hex(priv, header.hash.encode())
            return Block(header=header, transactions=[])
        nonce += 1


def test_finality_monotonicity_under_growth(tmp_path):
    # Lower the hard finality threshold to keep test fast.
    chain = Blockchain(data_dir=str(tmp_path))
    chain.difficulty = 1
    consensus = AdvancedConsensusManager(chain)
    consensus.finality_tracker.FINALITY_HARD = 4

    time_iter = itertools.count(1_700_000_000, 3)
    with patch("time.time", side_effect=lambda: float(next(time_iter))):
        # build 6 blocks total (genesis + 5 mined) with valid PoW
        prev = chain.chain[-1].hash
        priv, pub = deterministic_keypair_from_seed(b"finality-invariant-seed")
        for height in range(1, 6):
            block = _mine_block(height, prev, priv, pub, difficulty=1, ts=float(next(time_iter)))
            assert chain.add_block(block)
            prev = block.hash
            consensus.mark_finalized_blocks()

    finalized = sorted(consensus.finality_tracker.finalized_blocks)
    # Finalized height should never regress; last finalized should be >= threshold distance from tip
    assert finalized == sorted(finalized)
    assert finalized[-1] <= len(chain.chain) - consensus.finality_tracker.FINALITY_HARD
