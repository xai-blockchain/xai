#!/usr/bin/env python3
"""
UTXO/Merkle audit helper.

Computes the current UTXO snapshot and tip hash for a data directory, compares
against an expected baseline, and can emit JSON for schedulers/CI.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from xai.core.blockchain import Blockchain
from xai.core.config import Config

def audit_snapshot(data_dir: str) -> dict[str, Any]:
    chain = Blockchain(data_dir=data_dir)
    snapshot = chain.compute_state_snapshot()
    tip = chain.chain[-1] if chain.chain else None
    return {
        "height": snapshot.get("height", len(chain.chain)),
        "utxo_digest": snapshot.get("utxo_digest"),
        "tip_hash": getattr(tip, "hash", None),
    }

def compare_to_baseline(current: dict[str, Any], baseline_path: Path) -> bool:
    if not baseline_path.exists():
        raise FileNotFoundError(f"Baseline not found: {baseline_path}")
    baseline = json.loads(baseline_path.read_text())
    keys = ("height", "utxo_digest", "tip_hash")
    return all(current.get(k) == baseline.get(k) for k in keys)

def run(data_dir: str, baseline: str | None = None, write_baseline: str | None = None) -> int:
    result = audit_snapshot(data_dir)
    if write_baseline:
        path = Path(write_baseline)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2))
        print(f"[INFO] Baseline written to {path}")

    if baseline:
        ok = compare_to_baseline(result, Path(baseline))
        if not ok:
            print("[ERROR] Snapshot mismatch vs baseline.")
            print(json.dumps({"current": result}, indent=2))
            return 1
        print("[INFO] Snapshot matches baseline.")

    print(json.dumps(result, indent=2))
    return 0

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="UTXO/Merkle audit tool.")
    parser.add_argument("--data-dir", default=os.getenv("XAI_DATA_DIR", os.path.expanduser("~/.xai")), help="Blockchain data directory.")
    parser.add_argument("--baseline", help="Baseline JSON to compare against.")
    parser.add_argument("--write-baseline", help="Path to write current snapshot as new baseline.")
    return parser

def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    return run(args.data_dir, baseline=args.baseline, write_baseline=args.write_baseline)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
