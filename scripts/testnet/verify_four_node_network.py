#!/usr/bin/env python3
"""Automated health/consensus verification for the Docker four-node testnet."""

from __future__ import annotations

import argparse
import json
import sys

from xai.testnet.verification import NodeTarget, TestnetVerifier

DEFAULT_NODES = [
    ("bootstrap", "http://localhost:12001"),
    ("node1", "http://localhost:12011"),
    ("node2", "http://localhost:12021"),
    ("node3", "http://localhost:12031"),
]

def parse_node_definitions(raw_defs: Iterable[str]) -> list[NodeTarget]:
    """Parse command-line definitions (name=url) into NodeTarget objects."""
    targets: list[NodeTarget] = []
    for raw in raw_defs:
        if "=" not in raw:
            raise ValueError(f"Invalid node definition '{raw}'. Use name=http://host:port")
        name, url = raw.split("=", 1)
        name = name.strip()
        url = url.strip()
        if not name or not url:
            raise ValueError(f"Invalid node definition '{raw}'. Name and URL required")
        targets.append(NodeTarget(name=name, base_url=url))
    return targets

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the Docker four-node testnet is healthy, in consensus, and reporting live tips via /block/latest.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--node",
        action="append",
        dest="nodes",
        metavar="NAME=URL",
        help="Node definition (can be specified multiple times). Defaults to the docker compose ports.",
    )
    parser.add_argument(
        "--min-peers",
        type=int,
        default=3,
        help="Minimum peer count each node must report.",
    )
    parser.add_argument(
        "--explorer-url",
        default="http://localhost:12080",
        help="Explorer base URL for health verification.",
    )
    parser.add_argument(
        "--skip-explorer",
        action="store_true",
        help="Skip explorer health verification.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=3.0,
        help="HTTP request timeout per endpoint (seconds).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON summary instead of formatted text.",
    )
    return parser

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    node_defs = args.nodes or [f"{name}={url}" for name, url in DEFAULT_NODES]
    try:
        node_targets = parse_node_definitions(node_defs)
    except ValueError as exc:
        parser.error(str(exc))

    explorer_url = None if args.skip_explorer else args.explorer_url
    verifier = TestnetVerifier(
        node_targets,
        min_peer_count=args.min_peers,
        explorer_url=explorer_url,
        request_timeout=args.timeout,
    )
    result = verifier.verify()

    if args.json:
        json.dump(result.to_dict(), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        print(verifier.render_text(result))

    return 0 if result.ok else 2

if __name__ == "__main__":
    sys.exit(main())
