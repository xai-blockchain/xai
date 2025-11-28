#!/usr/bin/env bash
# Run P2P hardening checks and security-focused tests. Intended for CI/pre-merge.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[INFO] Running P2P hardening check..."
scripts/ci/p2p_hardening_check.sh

echo "[INFO] Running P2P security test subset..."
scripts/ci/test_p2p_security.sh "$@"

echo "[INFO] P2P checks completed successfully."
