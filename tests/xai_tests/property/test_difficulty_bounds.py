import math

from xai.core.blockchain import Block, Blockchain
from xai.core.block_header import BlockHeader


def _build_block(index: int, ts: float, difficulty: int) -> Block:
    header = BlockHeader(
        index=index,
        previous_hash="0" * 64,
        merkle_root="1" * 64,
        timestamp=ts,
        difficulty=difficulty,
        nonce=0,
    )
    return Block(header=header, transactions=[])


def test_difficulty_adjustment_bounds_simple():
    """
    Ensure calculate_next_difficulty respects bounds when interval condition is met.
    """
    bc = Blockchain()
    bc.difficulty = 100
    bc.max_difficulty_change = 4  # allow up to 4x change
    bc.difficulty_adjustment_interval = 1
    bc.target_block_time = 100

    # Replace chain with two blocks so interval condition is satisfied
    bc.chain = [
        _build_block(index=0, ts=0, difficulty=100),
        _build_block(index=1, ts=400, difficulty=100),  # took 4x target time
    ]

    new_diff = bc.calculate_next_difficulty()

    assert new_diff >= 1
    assert new_diff <= math.ceil(100 * bc.max_difficulty_change)
    assert new_diff >= max(1, math.floor(100 / bc.max_difficulty_change))
