#!/usr/bin/env bash
# Run the P2P security-focused test subset.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "[WARN] No active virtualenv; using system python."
fi

PYTEST_BIN="${PYTEST_BIN:-pytest}"

$PYTEST_BIN tests/chaos/test_partition_reconnect_utxo_digest.py tests/xai_tests/unit/test_p2p_security_probes.py "$@"
