#!/usr/bin/env python3
"""State snapshot utility for capturing, verifying, and restoring node data."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from xai.core.blockchain import Blockchain  # noqa: E402
from xai.core.config import Config  # noqa: E402

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def load_blockchain(data_dir: Path) -> Blockchain:
    return Blockchain(data_dir=str(data_dir))

def collect_metadata(blockchain: Blockchain, data_dir: Path, label: str) -> dict[str, Any]:
    chain_height = len(blockchain.chain) - 1 if blockchain.chain else -1
    latest_hash = blockchain.chain[-1].hash if blockchain.chain else None
    genesis_hash = blockchain.chain[0].hash if blockchain.chain else None
    blocks_dir = data_dir / "blocks"
    block_hashes: list[dict[str, Any]] = []
    if blocks_dir.exists():
        for block_file in sorted(blocks_dir.glob("block_*.json"), key=lambda p: int(p.stem.split("_")[1])):
            block_hashes.append(
                {
                    "file": block_file.name,
                    "sha256": sha256_file(block_file),
                }
            )
    timestamp = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    metadata = {
        "created_at": timestamp,
        "label": label,
        "network": getattr(Config, "NETWORK_TYPE", "unknown"),
        "data_dir": str(data_dir),
        "height": chain_height,
        "genesis_hash": genesis_hash,
        "latest_hash": latest_hash,
        "utxo_set": sha256_file(data_dir / "utxo_set.json") if (data_dir / "utxo_set.json").exists() else None,
        "pending_tx": sha256_file(data_dir / "pending_transactions.json")
        if (data_dir / "pending_transactions.json").exists()
        else None,
        "block_files": block_hashes,
    }
    return metadata

def create_snapshot(args: argparse.Namespace) -> int:
    data_dir = Path(args.data_dir).resolve()
    if not data_dir.exists():
        print(f"[snapshot] data directory not found: {data_dir}", file=sys.stderr)
        return 1
    blockchain = load_blockchain(data_dir)
    metadata = collect_metadata(blockchain, data_dir, args.label or "")
    output_path = Path(args.output or f"state_snapshot_{dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.tar.gz").resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output_path, "w:gz") as archive:
        archive.add(str(data_dir), arcname="data")
    metadata["snapshot_file"] = str(output_path)
    metadata["snapshot_sha256"] = sha256_file(output_path)
    manifest_path = Path(args.manifest) if args.manifest else Path(str(output_path) + ".json")
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)
    print(json.dumps({"snapshot": str(output_path), "manifest": str(manifest_path), "height": metadata["height"]}))
    return 0

def load_manifest(manifest_path: Path) -> dict[str, Any]:
    with manifest_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)

def verify_snapshot(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).resolve()
    if not manifest_path.exists():
        print(f"[verify] manifest not found: {manifest_path}", file=sys.stderr)
        return 1
    manifest = load_manifest(manifest_path)
    snapshot_path = Path(args.snapshot or manifest.get("snapshot_file", "")).resolve()
    if not snapshot_path.exists():
        print(f"[verify] snapshot not found: {snapshot_path}", file=sys.stderr)
        return 1
    snapshot_hash = sha256_file(snapshot_path)
    if snapshot_hash != manifest.get("snapshot_sha256"):
        print("[verify] snapshot hash mismatch", file=sys.stderr)
        return 2
    for entry in manifest.get("block_files", []):
        block_path = Path(manifest["data_dir"]) / "blocks" / entry["file"]
        if not block_path.exists():
            print(f"[verify] missing block file {block_path}", file=sys.stderr)
            return 3
        if sha256_file(block_path) != entry["sha256"]:
            print(f"[verify] block hash mismatch for {block_path}", file=sys.stderr)
            return 4
    print(json.dumps({"snapshot": str(snapshot_path), "status": "verified", "height": manifest.get("height")}))
    return 0

def describe_snapshot(args: argparse.Namespace) -> int:
    manifest = load_manifest(Path(args.manifest).resolve())
    print(json.dumps(manifest, indent=2))
    return 0

def restore_snapshot(args: argparse.Namespace) -> int:
    snapshot_path = Path(args.snapshot).resolve()
    if not snapshot_path.exists():
        print(f"[restore] snapshot not found: {snapshot_path}", file=sys.stderr)
        return 1
    target_dir = Path(args.target).resolve()
    if target_dir.exists() and any(target_dir.iterdir()):
        if not args.force:
            print(f"[restore] target {target_dir} is not empty (use --force)", file=sys.stderr)
            return 2
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with tarfile.open(snapshot_path, "r:gz") as archive:
            archive.extractall(tmp_path)
        extracted = tmp_path / "data"
        if not extracted.exists():
            print("[restore] extracted archive missing data directory", file=sys.stderr)
            return 3
        for item in extracted.iterdir():
            dest = target_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
    print(json.dumps({"restored_to": str(target_dir), "snapshot": str(snapshot_path)}))
    return 0

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage blockchain state snapshots.")
    sub = parser.add_subparsers(dest="command", required=True)

    create_p = sub.add_parser("create", help="Create a snapshot archive + manifest.")
    create_p.add_argument("--data-dir", default="data", help="Path to the node data directory.")
    create_p.add_argument("--output", help="Snapshot archive path (default: state_snapshot_<timestamp>.tar.gz).")
    create_p.add_argument("--manifest", help="Manifest path (default: <snapshot>.json).")
    create_p.add_argument("--label", default="", help="Human-friendly label stored in the manifest.")

    verify_p = sub.add_parser("verify", help="Verify archive and tracked file hashes.")
    verify_p.add_argument("--snapshot", help="Snapshot archive path (defaults to manifest reference).")
    verify_p.add_argument("--manifest", required=True, help="Manifest JSON generated during snapshot creation.")

    describe_p = sub.add_parser("describe", help="Print manifest metadata.")
    describe_p.add_argument("--manifest", required=True, help="Manifest JSON path.")

    restore_p = sub.add_parser("restore", help="Restore a snapshot into a target data directory.")
    restore_p.add_argument("--snapshot", required=True, help="Snapshot archive to extract.")
    restore_p.add_argument("--target", default="data", help="Destination data directory.")
    restore_p.add_argument("--force", action="store_true", help="Overwrite existing target directory.")

    return parser

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "create":
        return create_snapshot(args)
    if args.command == "verify":
        return verify_snapshot(args)
    if args.command == "describe":
        return describe_snapshot(args)
    if args.command == "restore":
        return restore_snapshot(args)
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
