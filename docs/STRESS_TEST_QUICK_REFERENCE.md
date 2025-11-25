# Network Stress Tests - Quick Reference

## Orchestrator scripts
1. `scripts/tools/run_performance_stress_suites.sh` runs the first four batches (core stress, memory/stress/long-running, transaction throughput/block propagation, resilience/concurrent ops).
2. `scripts/tools/run_performance_stress_heavy_suites.sh` runs the heavy memory/resource and chain reorganization batches that take longer but now complete in isolation.

Both scripts share the grouping logic from the manual commands below, so CI can call them individually or in tandem without hitting the CLI limit.
```bash
./scripts/tools/run_performance_stress_suites.sh
./scripts/tools/run_performance_stress_heavy_suites.sh
```

Set `PYTEST` if you want to pin a different Python interpreter (e.g., CI using `/opt/python/bin/pytest`).

## Manual commands (fallback)
If you prefer to run specific class groups individually:

1. **Core stress pods**
   ```bash
   ./venv/bin/pytest \
     tests/xai_tests/performance/test_stress.py::TestBlockchainScalability \
     tests/xai_tests/performance/test_stress.py::TestTransactionThroughput \
     tests/xai_tests/performance/test_stress.py::TestConcurrency
   ```

2. **Memory / stress / long-running**
   ```bash
   ./venv/bin/pytest \
     tests/xai_tests/performance/test_stress.py::TestMemoryUsage \
     tests/xai_tests/performance/test_stress.py::TestStressConditions \
     tests/xai_tests/performance/test_stress.py::TestLongRunning
   ```

3. **Network throughput + propagation**
   ```bash
   ./venv/bin/pytest \
     tests/xai_tests/performance/test_network_stress_comprehensive.py::TestTransactionThroughputStress \
     tests/xai_tests/performance/test_network_stress_comprehensive.py::TestBlockPropagationStress
   ```

4. **Network resilience + concurrent ops**
   ```bash
   ./venv/bin/pytest \
     tests/xai_tests/performance/test_network_stress_comprehensive.py::TestNetworkResilienceStress \
     tests/xai_tests/performance/test_network_stress_comprehensive.py::TestConcurrentOperationsStress
   ```

5. **Network memory/resource stress**
   ```bash
   ./venv/bin/pytest tests/xai_tests/performance/test_network_stress_comprehensive.py::TestMemoryAndResourceStress
   ```

6. **Chain reorganization**
   ```bash
   ./venv/bin/pytest tests/xai_tests/performance/test_network_stress_comprehensive.py::TestChainReorganizationStress
   ```

## Baselines
- TPS creation: `test_throughput_100_transactions` (>100 TPS)
- Validation speed: `test_transaction_validation_speed` (>50 TPS)
- Block propagation: `<2s` for `test_block_propagation_across_10_nodes`
- Concurrent ops: 50+ threads for `test_concurrent_api_requests`
- Memory/1000 blocks: <100MB via `test_memory_usage_with_large_chain`

## Notes
- These batches were tuned to avoid the CLI timeout; each takes ~2–4 minutes on this workstation.
- The orchestrator script reuses these groupings and can be executed from the repo root in CI or local runs to capture the full chaos/stress coverage.
