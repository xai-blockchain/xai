import json
import os

from xai.core.blockchain_persistence import BlockchainStorage, BlockchainStorageConfig


def test_save_and_load_round_trip_creates_checkpoint(tmp_path):
    storage = BlockchainStorage(data_dir=tmp_path.as_posix())
    data = {"chain": [1] * BlockchainStorageConfig.CHECKPOINT_INTERVAL}

    success, msg = storage.save_to_disk(data)
    assert success
    assert "checksum" in msg

    # Ensure checkpoint exists for interval boundary
    checkpoints = list((tmp_path / "checkpoints").glob("checkpoint_*.json"))
    assert checkpoints, "checkpoint should be created at interval height"

    loaded_success, loaded_data, _ = storage.load_from_disk()
    assert loaded_success
    assert loaded_data == data


def test_corrupted_main_file_recovers_from_backup(tmp_path):
    storage = BlockchainStorage(data_dir=tmp_path.as_posix())

    original = {"chain": [1, 2, 3]}
    updated = {"chain": [1, 2, 3, 4]}

    # First save creates baseline
    assert storage.save_to_disk(original)[0]

    # Second save creates backup of original before overwrite
    assert storage.save_to_disk(updated, create_backup=True)[0]

    # Corrupt primary file checksum
    corrupted_package = {"metadata": {"checksum": "deadbeef"}, "blockchain": updated}
    (tmp_path / "blockchain.json").write_text(json.dumps(corrupted_package))

    success, recovered, msg = storage.load_from_disk()
    assert success
    # Should recover from backup (original chain height 3)
    assert recovered == original
    assert "Recovered" in msg
