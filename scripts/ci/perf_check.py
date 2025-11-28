#!/usr/bin/env python3
"""
Performance guardrails for crypto-heavy paths.
Fails if averages exceed generous thresholds to catch regressions.
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from scripts.tools.bench_crypto import bench_block_header_serialize, bench_verify_signatures

# Thresholds chosen to be generous on CI hardware while catching regressions.
SIG_VERIFY_MAX_MS = 20.0   # ms per verify
HEADER_SERIALIZE_MAX_MS = 5.0  # ms per serialize


def main() -> int:
    sig_ms = bench_verify_signatures() * 1000
    ser_ms = bench_block_header_serialize() * 1000
    print(f"[PERF] Signature verify avg: {sig_ms:.4f} ms (limit {SIG_VERIFY_MAX_MS} ms)")
    print(f"[PERF] Block header serialize avg: {ser_ms:.4f} ms (limit {HEADER_SERIALIZE_MAX_MS} ms)")
    if sig_ms > SIG_VERIFY_MAX_MS:
        raise SystemExit(f"Signature verification too slow: {sig_ms:.2f} ms")
    if ser_ms > HEADER_SERIALIZE_MAX_MS:
        raise SystemExit(f"Block header serialization too slow: {ser_ms:.2f} ms")
    try:
        # Emit a JSON report for optional artifact capture
        from scripts.tools.bench_crypto_report import main as report_main
        report_main()
    except Exception as exc:  # pragma: no cover
        print(f"[WARN] Failed to write benchmark report: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
