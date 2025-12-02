#!/usr/bin/env bash
# Deterministic UTXO/Merkle audit smoke test for CI.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP_DIR="$(mktemp -d)"
DATA_DIR="$TMP_DIR/audit"
export DATA_DIR

python - <<'PY'
import itertools
import os
from pathlib import Path
from unittest.mock import patch

from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet
from xai.core.crypto_utils import deterministic_keypair_from_seed

data_dir = Path(os.environ["DATA_DIR"])
data_dir.mkdir(parents=True, exist_ok=True)

time_iter = itertools.count(1_700_000_000, 7)
with patch("time.time", side_effect=lambda: float(next(time_iter))):
    chain = Blockchain(data_dir=str(data_dir))
    chain.difficulty = 1
    priv, pub = deterministic_keypair_from_seed(b"deterministic-fixture-seed-0001")
    miner = Wallet(private_key=priv)
    identity = {"private_key": priv, "public_key": pub}
    chain.mine_pending_transactions(miner.address, identity)
    chain.mine_pending_transactions(miner.address, identity)

print("[INFO] Generated deterministic chain at", data_dir)
PY

PYTHONPATH="$ROOT_DIR/src" python "$ROOT_DIR/scripts/tools/utxo_audit.py" \
  --data-dir "$DATA_DIR" \
  --baseline "$ROOT_DIR/tests/data_test/deterministic_snapshot.json"
