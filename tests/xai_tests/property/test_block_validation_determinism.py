from xai.core.blockchain import Blockchain


def test_block_validation_deterministic_on_same_input(tmp_path):
    bc1 = Blockchain(data_dir=str(tmp_path / "a"))
    bc2 = Blockchain(data_dir=str(tmp_path / "b"))

    blk = bc1.chain[-1]
    ok1 = bc1.validate_chain([blk])[0] if isinstance(bc1.validate_chain([blk]), tuple) else bc1.validate_chain([blk])
    ok2 = bc2.validate_chain([blk])[0] if isinstance(bc2.validate_chain([blk]), tuple) else bc2.validate_chain([blk])

    assert ok1 == ok2
