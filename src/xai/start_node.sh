#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    if command -v python >/dev/null 2>&1; then
        PYTHON_BIN="python"
    else
        echo "Python executable not found. Set PYTHON_BIN to a valid interpreter." >&2
        exit 1
    fi
fi

if [[ -n "${PYTHONPATH:-}" ]]; then
    export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
else
    export PYTHONPATH="$PROJECT_ROOT/src"
fi
LOG_FILE="$LOG_DIR/node.log"

echo "Starting XAI node..."
nohup "$PYTHON_BIN" -m xai.core.node "$@" >"$LOG_FILE" 2>&1 &
PID=$!
echo "Node started with PID $PID. Logs: $LOG_FILE"
