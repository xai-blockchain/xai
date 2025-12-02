#!/usr/bin/env python3
"""
Compare current perf report against a baseline and fail on regression.
Usage: python scripts/ci/perf_compare.py --baseline benchmarks/baseline.json --current benchmarks/crypto_report.json
"""
import argparse
import json
from pathlib import Path

DEFAULT_THRESHOLD = 0.5  # 50% regression allowed before failing


def load_report(path: Path) -> dict:
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    args = parser.parse_args()

    base = load_report(args.baseline)
    curr = load_report(args.current)

    base_sig = base["benchmarks"]["signature_verify_avg_ms"]
    base_ser = base["benchmarks"]["block_header_serialize_avg_ms"]
    curr_sig = curr["benchmarks"]["signature_verify_avg_ms"]
    curr_ser = curr["benchmarks"]["block_header_serialize_avg_ms"]

    regressions = []
    if base_sig > 0 and (curr_sig - base_sig) / base_sig > args.threshold:
        regressions.append(f"Signature verify regression: {curr_sig:.4f} ms vs {base_sig:.4f} ms")
    if base_ser > 0 and (curr_ser - base_ser) / base_ser > args.threshold:
        regressions.append(f"Block serialize regression: {curr_ser:.6f} ms vs {base_ser:.6f} ms")

    if regressions:
        for r in regressions:
            print(f"[REGRESSION] {r}")
        raise SystemExit(1)
    print("[INFO] Perf within threshold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
