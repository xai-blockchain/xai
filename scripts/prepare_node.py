"""
Utility to prepare a ready-to-run node profile.

Creates data directories, emits `node_config.json`, and prints workshop commands
for launching the node, starting mining, and querying Time Capsules.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Dict

from scripts.node_profile import ensure_path, register_peer, write_node_config

DEFAULT_RPC_PORT = 18545
DEFAULT_P2P_PORT = 18544
DEFAULT_DATA_DIR = "./data/node01"


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare an XAI node profile.")
    parser.add_argument("--miner", required=True, help="Miner address (XAI1...)")
    parser.add_argument("--rpc-port", type=int, default=DEFAULT_RPC_PORT, help="RPC/Web API port")
    parser.add_argument(
        "--p2p-port", type=int, default=DEFAULT_P2P_PORT, help="P2P port for the node"
    )
    parser.add_argument(
        "--data-dir", default=DEFAULT_DATA_DIR, help="Directory to host blockchain data"
    )
    parser.add_argument(
        "--register-peer", action="store_true", help="Emit a discovery file for explorers"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    data_dir = ensure_path(Path(args.data_dir).expanduser())
    node_payload = {
        "miner": args.miner,
        "rpc_port": args.rpc_port,
        "p2p_port": args.p2p_port,
        "data_dir": str(data_dir.resolve()),
        "network": os.getenv("XAI_NETWORK", "testnet"),
    }

    config_path = write_node_config(data_dir, node_payload)

    if args.register_peer:
        peer_path = register_peer(data_dir, node_payload)
        print(f"Peer discovery record persisted to {peer_path}")

    print("\nYour node profile is ready!")
    print(f"  Data directory: {data_dir}")
    print(f"  Node config: {config_path}")
    print("\nStart the node:")
    print(
        f"  python core/node.py --miner {args.miner} "
        f"--data-dir {data_dir} --rpc-port {args.rpc_port} --p2p-port {args.p2p_port}"
    )
    print("\nStart mining via the API:")
    print(
        f"  curl -X POST http://localhost:{args.rpc_port}/mining/start "
        f'-H \'Content-Type: application/json\' -d \'{{"miner_address":"{args.miner}","threads":2}}\''
    )
    print("\nTrack metrics or Time Capsules:")
    print(f"  Prometheus: http://localhost:{args.rpc_port}/metrics")
    print(f"  Pending Time Capsules: http://localhost:{args.rpc_port}/time-capsule/pending")


if __name__ == "__main__":
    main()
