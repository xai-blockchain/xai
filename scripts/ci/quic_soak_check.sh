#!/usr/bin/env bash
# Run QUIC soak/latency check (requires aioquic). Skips if dependency missing.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if ! python - <<'PY' >/dev/null 2>&1
import importlib
import sys
sys.exit(0 if importlib.util.find_spec("aioquic") else 1)
PY
then
  echo "[INFO] aioquic not installed; skipping QUIC soak check."
  exit 0
fi

echo "[INFO] Running QUIC latency soak test..."
PYTHONPATH=src pytest tests/xai_tests/integration/test_quic_latency_soak.py -q
