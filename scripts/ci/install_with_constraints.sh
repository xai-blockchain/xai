#!/usr/bin/env bash
# Install project (dev) dependencies pinned by constraints.txt. Intended for CI.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

CONSTRAINTS="${CONSTRAINTS_FILE:-constraints.txt}"

if [[ ! -f "$CONSTRAINTS" ]]; then
  echo "[ERROR] Constraints file not found: $CONSTRAINTS"
  exit 1
fi

python -m pip install --upgrade pip
python -m pip install -c "$CONSTRAINTS" -e ".[dev]"
