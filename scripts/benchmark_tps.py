#!/usr/bin/env python3
"""
TPS Benchmark Script for CI

Measures transaction throughput and outputs results in JSON format.
Designed to be lightweight and run in CI pipelines.
"""

import json
import sys
import tempfile
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet


def benchmark_tx_creation(blockchain: Blockchain, count: int = 100) -> dict:
    """Benchmark transaction creation speed."""
    senders = [Wallet() for _ in range(min(10, count // 10 or 1))]

    # Fund senders
    for sender in senders:
        blockchain.mine_pending_transactions(sender.address)

    start = time.perf_counter()
    created = 0

    for i in range(count):
        sender = senders[i % len(senders)]
        try:
            tx = blockchain.create_transaction(
                sender.address,
                Wallet().address,
                0.1,
                0.01,
                sender.private_key,
                sender.public_key
            )
            blockchain.add_transaction(tx)
            created += 1
        except Exception:
            pass  # Skip failed transactions

    duration = time.perf_counter() - start
    tps = created / duration if duration > 0 else 0

    return {
        "operation": "tx_creation",
        "count": created,
        "duration_seconds": round(duration, 3),
        "tps": round(tps, 2)
    }


def benchmark_block_mining(blockchain: Blockchain, blocks: int = 5) -> dict:
    """Benchmark block mining speed."""
    miner = Wallet()

    start = time.perf_counter()
    for _ in range(blocks):
        blockchain.mine_pending_transactions(miner.address)
    duration = time.perf_counter() - start

    blocks_per_sec = blocks / duration if duration > 0 else 0

    return {
        "operation": "block_mining",
        "blocks": blocks,
        "duration_seconds": round(duration, 3),
        "blocks_per_second": round(blocks_per_sec, 2)
    }


def benchmark_balance_lookups(blockchain: Blockchain, count: int = 1000) -> dict:
    """Benchmark balance lookup speed."""
    wallet = Wallet()
    blockchain.mine_pending_transactions(wallet.address)

    start = time.perf_counter()
    for _ in range(count):
        blockchain.get_balance(wallet.address)
    duration = time.perf_counter() - start

    lookups_per_sec = count / duration if duration > 0 else 0

    return {
        "operation": "balance_lookup",
        "count": count,
        "duration_seconds": round(duration, 3),
        "lookups_per_second": round(lookups_per_sec, 2)
    }


def run_benchmarks(tx_count: int = 50, blocks: int = 3, lookups: int = 500) -> dict:
    """Run all benchmarks with conservative defaults for CI."""
    with tempfile.TemporaryDirectory() as tmpdir:
        blockchain = Blockchain(data_dir=tmpdir)

        results = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "benchmarks": []
        }

        # Run benchmarks
        results["benchmarks"].append(benchmark_tx_creation(blockchain, tx_count))
        results["benchmarks"].append(benchmark_block_mining(blockchain, blocks))
        results["benchmarks"].append(benchmark_balance_lookups(blockchain, lookups))

        # Summary
        tx_result = results["benchmarks"][0]
        results["summary"] = {
            "tps": tx_result["tps"],
            "status": "pass" if tx_result["tps"] > 10 else "warn"
        }

        return results


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="XAI TPS Benchmark")
    parser.add_argument("--tx-count", type=int, default=50, help="Transactions to create")
    parser.add_argument("--blocks", type=int, default=3, help="Blocks to mine")
    parser.add_argument("--lookups", type=int, default=500, help="Balance lookups")
    parser.add_argument("--output", type=str, help="Output file (JSON)")
    parser.add_argument("--quiet", action="store_true", help="Only output JSON")
    args = parser.parse_args()

    if not args.quiet:
        print("Running XAI TPS Benchmarks...")
        print(f"  Transactions: {args.tx_count}")
        print(f"  Blocks: {args.blocks}")
        print(f"  Lookups: {args.lookups}")
        print()

    results = run_benchmarks(args.tx_count, args.blocks, args.lookups)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        if not args.quiet:
            print(f"Results written to {args.output}")

    # Print results
    if not args.quiet:
        print("Results:")
        for bench in results["benchmarks"]:
            op = bench["operation"]
            if op == "tx_creation":
                print(f"  TX Creation: {bench['tps']} TPS ({bench['count']} txs)")
            elif op == "block_mining":
                print(f"  Block Mining: {bench['blocks_per_second']:.2f} blocks/sec")
            elif op == "balance_lookup":
                print(f"  Balance Lookup: {bench['lookups_per_second']:.0f} ops/sec")
        print()
        print(f"Summary: TPS={results['summary']['tps']} [{results['summary']['status'].upper()}]")
    else:
        print(json.dumps(results, indent=2))

    # Exit with error if TPS is too low
    return 0 if results["summary"]["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
