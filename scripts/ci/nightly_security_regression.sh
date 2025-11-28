#!/usr/bin/env bash
# Nightly security regression suite: installs with constraints, runs P2P hardening checks and security tests.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[INFO] Installing with constraints..."
scripts/ci/install_with_constraints.sh

echo "[INFO] Running P2P hardening checks and security tests..."
scripts/ci/run_p2p_checks.sh "$@"

echo "[INFO] Nightly security regression completed."
