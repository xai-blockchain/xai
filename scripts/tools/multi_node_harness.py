#!/usr/bin/env python3
"""Lightweight harness that powers the multi-node integration suite.

It launches several `xai.core.node` instances with isolated storage, wires them
into a mesh, injects a faucet transaction, and asserts consensus/propagation
before shutting everything down.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from xai.core.wallet import Wallet

PYTHON = Path(__file__).resolve().parents[2] / "venv" / "bin" / "python"
NODE_MODULE = ["-m", "xai.core.node"]

@dataclass
class NodeProcess:
    port: int
    data_dir: Path
    miner_address: str
    process: subprocess.Popen | None = None

    def start(self) -> None:
        env = os.environ.copy()
        env["XAI_NETWORK"] = "testnet"
        env["XAI_API_PORT"] = str(self.port)
        env["XAI_API_HOST"] = "127.0.0.1"
        env["XAI_API_AUTH_REQUIRED"] = "0"
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])

        self.data_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(PYTHON),
            *NODE_MODULE,
            "--host",
            "127.0.0.1",
            "--port",
            str(self.port),
            "--miner",
            self.miner_address,
            "--data-dir",
            str(self.data_dir),
        ]

        self.process = subprocess.Popen(
            cmd,
            env=env,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()

def wait_for_health(port: int, timeout: int = 60) -> None:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/health"
    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200 and resp.json().get("status") == "healthy":
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    raise RuntimeError(f"Node on port {port} failed to become healthy")

def call_api(port: int, path: str, method: str = "get", **kwargs: Any) -> requests.Response:
    url = f"http://127.0.0.1:{port}{path}"
    return getattr(requests, method)(url, timeout=5, **kwargs)

def add_peer(port: int, peer_port: int) -> None:
    call_api(port, "/peers/add", method="post", json={"url": f"http://127.0.0.1:{peer_port}"})

def fetch_stats(port: int) -> dict[str, Any]:
    resp = call_api(port, "/stats")
    resp.raise_for_status()
    return resp.json()

def latest_block_hash(port: int) -> str:
    resp = call_api(port, "/blocks?limit=1")
    resp.raise_for_status()
    blocks = resp.json().get("blocks", [])
    if not blocks:
        return ""
    return blocks[0].get("hash", "")

def run_harness(node_count: int, base_port: int) -> None:
    wallet = Wallet()
    addresses = [Wallet().address for _ in range(node_count)]
    base_temp = Path(tempfile.mkdtemp(prefix="xai-multi-node-"))
    nodes: list[NodeProcess] = []

    for idx in range(node_count):
        node = NodeProcess(
            port=base_port + idx,
            data_dir=base_temp / f"node_{idx}",
            miner_address=addresses[idx],
        )
        node.start()
        nodes.append(node)

    try:
        for node in nodes:
            wait_for_health(node.port)

        for node in nodes:
            for peer in nodes:
                if node.port == peer.port:
                    continue
                add_peer(node.port, peer.port)

        faucet_address = Wallet().address
        resp = call_api(nodes[0].port, "/faucet/claim", method="post", json={"address": faucet_address})
        resp.raise_for_status()

        start_heights = [fetch_stats(node.port)["height"] for node in nodes]
        target = max(start_heights) + 1
        deadline = time.time() + 60
        while time.time() < deadline:
            heights = [fetch_stats(node.port)["height"] for node in nodes]
            if len(set(heights)) == 1 and heights[0] >= target:
                break
            time.sleep(1)
        else:
            raise RuntimeError("Nodes failed to reach consensus height")

        hashes = [latest_block_hash(node.port) for node in nodes]
        if len(set(hashes)) != 1:
            raise RuntimeError("Nodes did not synchronize on the same tip")

        print("Multi-node harness succeeded:")
        print(f"  Data roots: {base_temp}")
        print(f"  Node heights: {heights[0]}")
        print(f"  Tip hash: {hashes[0]}")

    finally:
        for node in nodes:
            node.stop()
        print("Stopped all nodes")

def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-node integration harness")
    parser.add_argument("--nodes", type=int, default=3, help="Number of nodes to run")
    parser.add_argument("--base-port", type=int, default=8550, help="First node port")
    args = parser.parse_args()
    run_harness(args.nodes, args.base_port)

if __name__ == "__main__":
    main()
