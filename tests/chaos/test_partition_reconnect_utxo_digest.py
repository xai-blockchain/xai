import random

import pytest

from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet


def identity_from_wallet(wallet: Wallet) -> dict:
    return {"private_key": wallet.private_key, "public_key": wallet.public_key}


def populate_and_mine(
    chain: Blockchain,
    miner: Wallet,
    recipients: list[Wallet],
    tx_count: int,
    fee: float = 0.01,
) -> object:
    """
    Create a burst of signed transactions then mine them into a block.
    """
    rng = random.Random(1337 + tx_count + len(recipients))
    for idx in range(tx_count):
        recipient = recipients[idx % len(recipients)]
        amount = round(0.5 + rng.random() * 0.25, 6)
        tx = chain.create_transaction(
            miner.address,
            recipient.address,
            amount,
            fee,
            miner.private_key,
            miner.public_key,
        )
        assert tx is not None, "Failed to build signed transaction during chaos partition load"
        assert chain.add_transaction(tx)

    mined = chain.mine_pending_transactions(miner.address, identity_from_wallet(miner))
    assert mined is not None
    return mined


def test_partition_reconnect_keeps_utxo_digest_stable(tmp_path):
    """
    Simulate a partition with competing signed transactions and ensure that after
    reconnection/reorg every node converges on the same UTXO digest.
    """
    node_dirs = [tmp_path / f"node-{i}" for i in range(3)]
    for path in node_dirs:
        path.mkdir(parents=True, exist_ok=True)

    chains = [Blockchain(data_dir=str(path)) for path in node_dirs]
    miner = Wallet()
    miner_id = identity_from_wallet(miner)

    # Pre-fund the miner and sync all nodes before partition.
    initial_blocks = []
    for _ in range(3):
        block = chains[0].mine_pending_transactions(miner.address, miner_id)
        initial_blocks.append(block)
    for peer in chains[1:]:
        peer.replace_chain(chains[0].chain)

    baseline_height = len(chains[0].chain)
    baseline_digest = chains[0].utxo_manager.snapshot_digest()
    assert all(chain.utxo_manager.snapshot_digest() == baseline_digest for chain in chains[1:])

    recipients = [Wallet() for _ in range(6)]

    # Partition: group A (chains[0], chains[1]) vs group B (chains[2])
    # Group A mines two blocks with signed transactions under load.
    block_a1 = populate_and_mine(chains[0], miner, recipients[:3], tx_count=8)
    chains[1].replace_chain(chains[0].chain)
    block_a2 = populate_and_mine(chains[0], miner, recipients[:3], tx_count=6)
    chains[1].replace_chain(chains[0].chain)

    # Group B races ahead with a longer chain under heavier signed TX load.
    block_b1 = populate_and_mine(chains[2], miner, recipients[3:], tx_count=10)
    block_b2 = populate_and_mine(chains[2], miner, recipients[3:], tx_count=10)
    block_b3 = populate_and_mine(chains[2], miner, recipients[3:], tx_count=10)

    assert len(chains[2].chain) > len(chains[0].chain)

    # Reconnect: deliver the longer chain from group B to group A nodes to trigger reorg.
    for peer in [chains[0], chains[1]]:
        peer.replace_chain(chains[2].chain)

    # All nodes should converge on the group B tip and UTXO digest.
    digests = [chain.compute_state_snapshot()["utxo_digest"] for chain in chains]
    assert digests[0] == digests[1] == digests[2]
    assert chains[0].chain[-1].hash == chains[2].chain[-1].hash
    assert len(chains[0].chain) == len(chains[2].chain)
