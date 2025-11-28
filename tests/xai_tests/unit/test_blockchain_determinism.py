import shutil
from pathlib import Path

from xai.core.blockchain import Blockchain


def test_blockchain_genesis_deterministic(tmp_path):
    """
    Ensure genesis load produces deterministic tip hash across clean data dirs.
    """
    # Create two separate data dirs seeded with the same genesis file
    data1 = tmp_path / "node1"
    data2 = tmp_path / "node2"
    data1.mkdir()
    data2.mkdir()

    # Copy genesis file to both to enforce same starting point
    genesis_src = Path("src/xai/core/genesis.json")
    shutil.copy(genesis_src, data1 / "genesis.json")
    shutil.copy(genesis_src, data2 / "genesis.json")

    bc1 = Blockchain(data_dir=str(data1))
    bc2 = Blockchain(data_dir=str(data2))

    assert bc1.chain[0].hash == bc2.chain[0].hash
    assert bc1.compute_state_snapshot()["utxo_digest"] == bc2.compute_state_snapshot()["utxo_digest"]
