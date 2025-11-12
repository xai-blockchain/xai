from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


def ensure_path(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_node_config(data_dir: Path, payload: Dict[str, any]) -> Path:
    config_path = data_dir / "node_config.json"
    with open(config_path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2)
    return config_path


def register_peer(data_dir: Path, payload: Dict[str, any]) -> Path:
    discovery_dir = Path("data") / "discovery"
    ensure_path(discovery_dir)
    peer_file = discovery_dir / "nodes.json"
    existing = []
    if peer_file.exists():
        try:
            existing = json.loads(peer_file.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    existing = [entry for entry in existing if entry.get("miner") != payload["miner"]]
    existing.append(payload)
    with open(peer_file, "w", encoding="utf-8") as fp:
        json.dump(existing, fp, indent=2)
    return peer_file
