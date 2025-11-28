#!/usr/bin/env python3
"""
Automate trust-store rotation:
- Merge existing and new keys/fingerprints
- Write updated ConfigMap snippets
- Optionally drop deprecated entries after rollout
"""
import argparse
import sys
from pathlib import Path


def load_entries(path: Path) -> list[str]:
    if not path.exists():
        return []
    entries = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        entries.append(line)
    return entries


def write_entries(path: Path, entries: list[str]) -> None:
    lines = ["# Managed by trust_store_rotate.py"]
    lines += entries
    path.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Rotate trust stores safely.")
    parser.add_argument("--current-pubkeys", type=Path, required=True)
    parser.add_argument("--current-certs", type=Path, required=True)
    parser.add_argument("--new-pubkeys", type=Path, required=False)
    parser.add_argument("--new-certs", type=Path, required=False)
    parser.add_argument("--drop-old", action="store_true", help="Drop entries not in new sets")
    parser.add_argument("--out-pubkeys", type=Path, required=True)
    parser.add_argument("--out-certs", type=Path, required=True)
    args = parser.parse_args(argv)

    current_pub = set(load_entries(args.current_pubkeys))
    current_certs = set(load_entries(args.current_certs))
    new_pub = set(load_entries(args.new_pubkeys)) if args.new_pubkeys else set()
    new_certs = set(load_entries(args.new_certs)) if args.new_certs else set()

    if args.drop_old:
        merged_pub = new_pub or current_pub
        merged_certs = new_certs or current_certs
    else:
        merged_pub = current_pub | new_pub
        merged_certs = current_certs | new_certs

    write_entries(args.out_pubkeys, sorted(merged_pub))
    write_entries(args.out_certs, sorted(merged_certs))
    print(f"Wrote updated pubkeys to {args.out_pubkeys}")
    print(f"Wrote updated cert fingerprints to {args.out_certs}")


if __name__ == "__main__":
    sys.exit(main())
