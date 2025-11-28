#!/usr/bin/env python3
"""
Run crypto microbenchmarks and emit a JSON report for tracking in CI.
"""
import json
import time
from pathlib import Path

from scripts.tools.bench_crypto import bench_block_header_serialize, bench_verify_signatures


def main() -> int:
    sig_seconds = bench_verify_signatures()
    ser_seconds = bench_block_header_serialize()
    report = {
        "timestamp": time.time(),
        "benchmarks": {
            "signature_verify_avg_ms": sig_seconds * 1000,
            "block_header_serialize_avg_ms": ser_seconds * 1000,
        },
    }
    out = Path("benchmarks/crypto_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(f"Wrote {out}")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
