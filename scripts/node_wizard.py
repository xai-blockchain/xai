"""
Interactive wizard for beginner-friendly node onboarding.

Prompts for the miner address and ports, creates the data directory,
writes `node_config.json`, optionally registers discovery info, and prints
the commands/audio for starting the node, mining, and checking health.
"""

from __future__ import annotations

import logging
from pathlib import Path

from scripts.node_profile import ensure_path, register_peer, write_node_config

# Configure module logger
logger = logging.getLogger(__name__)

def prompt(text: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    if not value and default is not None:
        return default
    return value

def confirm(text: str, default: bool = True) -> bool:
    suffix = "Y/n" if default else "y/N"
    answer = input(f"{text} ({suffix}): ").strip().lower()
    if not answer:
        return default
    return answer.startswith("y")

def main():
    logger.info("Starting XAI Node Wizard")
    print("\n== XAI Node Wizard ==")
    miner = prompt("Miner address (XAI1...)", "")
    if not miner:
        logger.error("Node wizard failed: miner address is required")
        print("Miner address is required.")
        return

    data_dir = Path(prompt("Data directory", "./data/node01")).expanduser()
    rpc_port = int(prompt("RPC/Web API port", "18545"))
    p2p_port = int(prompt("P2P port", "18544"))
    register = confirm("Register you in peer discovery?", True)

    logger.info("Node configuration: miner=%s, data_dir=%s, rpc_port=%d, p2p_port=%d",
                miner, data_dir, rpc_port, p2p_port)

    ensure_path(data_dir)
    node_payload = {
        "miner": miner,
        "rpc_port": rpc_port,
        "p2p_port": p2p_port,
        "data_dir": str(data_dir.resolve()),
        "network": "testnet",
    }

    config_path = write_node_config(data_dir, node_payload)
    logger.info("Node config written to: %s", config_path)

    if register:
        peer_path = register_peer(data_dir, node_payload)
        logger.info("Peer discovery record written to: %s", peer_path)
        print(f"Peer discovery record persisted to {peer_path}")

    logger.info("Node wizard completed successfully")
    print("\nDone! Here are your next steps:")
    print(
        f"1) Start the node:\n   python core/node.py --miner {miner} --data-dir {data_dir} --rpc-port {rpc_port} --p2p-port {p2p_port}"
    )
    print(
        f'2) Hit the mining API:\n   curl -X POST http://localhost:{rpc_port}/mining/start -H \'Content-Type: application/json\' -d \'{{"miner_address":"{miner}","threads":2}}\''
    )
    print(f"3) Watch metrics: http://localhost:{rpc_port}/metrics")
    print(f"4) Monitor Time Capsules: http://localhost:{rpc_port}/time-capsule/pending")
    print(
        "\nKeep this terminal open to see logs, and point your Grafana at /metrics for live status."
    )

if __name__ == "__main__":
    main()
