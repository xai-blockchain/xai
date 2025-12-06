import time

from xai.core.blockchain import Block, BlockHeader, Blockchain
from xai.core.transaction import Transaction


def _make_transaction(nonce: int) -> Transaction:
    return Transaction(
        sender="XAI" + "a" * 40,
        recipient="XAI" + "b" * 40,
        amount=1.0,
        fee=0.001,
        nonce=nonce,
    )


def test_block_estimate_size_bytes_includes_transactions():
    tx1 = _make_transaction(1)
    tx2 = _make_transaction(2)
    header = BlockHeader(
        index=1,
        previous_hash="0" * 64,
        merkle_root="0" * 64,
        timestamp=time.time(),
        difficulty=4,
        nonce=0,
    )
    block = Block(header, [tx1, tx2])

    estimated_size = block.estimate_size_bytes()

    assert estimated_size >= tx1.get_size() + tx2.get_size()
    assert estimated_size > tx1.get_size()


def test_chain_work_prefers_higher_difficulty(tmp_path):
    blockchain = Blockchain(data_dir=str(tmp_path))

    base_hash = blockchain.chain[-1].hash if blockchain.chain else "0" * 64
    header_low = BlockHeader(
        index=1,
        previous_hash=base_hash,
        merkle_root="0" * 64,
        timestamp=time.time(),
        difficulty=4,
        nonce=1,
    )
    header_high = BlockHeader(
        index=2,
        previous_hash=base_hash,
        merkle_root="0" * 64,
        timestamp=time.time(),
        difficulty=8,
        nonce=2,
    )

    low_work = blockchain._calculate_chain_work([header_low])
    high_work = blockchain._calculate_chain_work([header_high])
    combined_work = blockchain._calculate_chain_work([header_low, header_high])

    assert high_work > low_work
    assert combined_work == low_work + high_work
