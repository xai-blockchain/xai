"""
Export the latest checkpoint into a deterministic payload JSON for partial sync.

Usage:
    python scripts/tools/checkpoint_export.py --data-dir data --output checkpoint_payload.json

The payload includes UTXO snapshot and metadata and computes a SHA-256 hash
over the JSON-serialized data to allow integrity verification.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict

from xai.core.checkpoints import CheckpointManager
from xai.core.checkpoint_payload import CheckpointPayload


def _build_payload_dict(checkpoint: Any) -> Dict[str, Any]:
    data = {
        "utxo_snapshot": getattr(checkpoint, "utxo_snapshot", {}),
        "timestamp": getattr(checkpoint, "timestamp", None),
        "difficulty": getattr(checkpoint, "difficulty", None),
        "total_supply": getattr(checkpoint, "total_supply", None),
        "merkle_root": getattr(checkpoint, "merkle_root", None),
        "nonce": getattr(checkpoint, "nonce", None),
    }
    return {
        "height": getattr(checkpoint, "height", None),
        "block_hash": getattr(checkpoint, "block_hash", None),
        "state_hash": CheckpointPayload(
            height=checkpoint.height,
            block_hash=checkpoint.block_hash,
            state_hash="",
            data=data,
        ).state_hash,
        "data": data,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export latest checkpoint payload.")
    parser.add_argument("--data-dir", required=True, help="Blockchain data directory containing checkpoints/")
    parser.add_argument("--output", required=True, help="Output payload JSON path")
    args = parser.parse_args()

    cm = CheckpointManager(data_dir=args.data_dir)
    checkpoint = cm.load_latest_checkpoint()
    if not checkpoint:
        print("No checkpoint found in data_dir", file=sys.stderr)
        return 1

    payload = _build_payload_dict(checkpoint)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    print(f"Wrote checkpoint payload to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
