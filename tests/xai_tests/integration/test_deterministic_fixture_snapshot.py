import itertools
import json
from pathlib import Path
from unittest.mock import patch

from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet
from xai.core.p2p_security import P2PSecurityConfig
from xai.core.crypto_utils import deterministic_keypair_from_seed


def _time_generator(start: int = 1_700_000_000, step: int = 7):
    """Yield deterministic timestamps to stabilize mining and snapshots."""
    for val in itertools.count(start, step):
        yield float(val)


def test_deterministic_snapshot_matches_fixture(tmp_path):
    fixture_path = Path(__file__).resolve().parents[3] / "tests" / "data_test" / "deterministic_snapshot.json"
    fixture = json.loads(fixture_path.read_text())

    time_iter = _time_generator()
    with patch("time.time", side_effect=lambda: float(next(time_iter))):
        chain = Blockchain(data_dir=str(tmp_path))
        chain.difficulty = 1
        miner_priv, miner_pub = deterministic_keypair_from_seed(b"deterministic-fixture-seed-0001")
        miner = Wallet(private_key=miner_priv)
        identity = {"private_key": miner_priv, "public_key": miner_pub}
        chain.mine_pending_transactions(miner.address, identity)
        chain.mine_pending_transactions(miner.address, identity)
        snapshot = chain.compute_state_snapshot()

    assert len(chain.chain) == fixture["height"]
    assert snapshot["utxo_digest"] == fixture["utxo_digest"]
    assert [blk.hash for blk in chain.chain] == fixture["block_hashes"]
    assert str(P2PSecurityConfig.PROTOCOL_VERSION) == fixture["protocol_version"]
