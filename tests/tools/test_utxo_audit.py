import itertools
from pathlib import Path
from unittest.mock import patch

from scripts.tools import utxo_audit
from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet
from xai.core.crypto_utils import deterministic_keypair_from_seed


def _seed_chain(tmp_path: Path) -> Path:
    data_dir = tmp_path / "chain"
    data_dir.mkdir(parents=True, exist_ok=True)
    time_iter = itertools.count(1_700_000_000, 5)
    with patch("time.time", side_effect=lambda: float(next(time_iter))):
        chain = Blockchain(data_dir=str(data_dir))
        chain.difficulty = 1
        miner_priv, miner_pub = deterministic_keypair_from_seed(b"utxo-audit-seed-01")
        miner = Wallet(private_key=miner_priv)
        identity = {"private_key": miner_priv, "public_key": miner_pub}
        chain.mine_pending_transactions(miner.address, identity)
        chain.mine_pending_transactions(miner.address, identity)
    return data_dir


def test_utxo_audit_matches_written_baseline(tmp_path):
    data_dir = _seed_chain(tmp_path)
    baseline_path = tmp_path / "baseline.json"

    result = utxo_audit.audit_snapshot(str(data_dir))
    utxo_audit.run(str(data_dir), write_baseline=str(baseline_path))

    assert baseline_path.exists()
    assert utxo_audit.compare_to_baseline(result, baseline_path) is True
