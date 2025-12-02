# UTXO / Merkle Audits

Use `scripts/tools/utxo_audit.py` to compute the current UTXO snapshot and tip hash, compare against a baseline, and emit JSON for schedulers/CI.

## Usage

```bash
# Compare current state to a known-good baseline
python scripts/tools/utxo_audit.py --data-dir ~/.xai --baseline tests/data_test/deterministic_snapshot.json

# Write a fresh baseline (e.g., after a release)
python scripts/tools/utxo_audit.py --data-dir ~/.xai --write-baseline /tmp/utxo-baseline.json
```

## Scheduling
- Run hourly via cron in staging to detect drift: non-zero exit signals mismatch.
- Alert on mismatch and perform a manual reconciliation (load latest checkpoints, inspect orphan pool, re-run audit).

## CI Smoke Test
- Deterministic fixture-based audit is exercised in tests to ensure the tool works and outputs stable digests.
