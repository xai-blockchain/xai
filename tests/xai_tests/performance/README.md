# Performance and Stress Tests

This directory contains comprehensive performance and stress tests for critical XAI blockchain components.

## Overview

Performance tests measure the speed, scalability, and resource usage of blockchain operations under various conditions. These tests help identify bottlenecks, validate performance baselines, and ensure the system can handle production loads.

## Test Suites

### 1. Mempool Load Tests (`test_mempool_load.py`)

Tests mempool behavior under high transaction volumes.

**Key Tests:**
- `test_mempool_10k_transactions_insertion` - Insert 10,000 transactions, measure throughput (target: >100 tx/sec)
- `test_mempool_high_insertion_rate` - Sustained 1000 tx/sec insertion for 10 seconds
- `test_mempool_eviction_performance` - Eviction behavior when mempool exceeds capacity
- `test_mempool_concurrent_access` - Thread safety under concurrent access (10 threads × 100 tx)
- `test_mempool_retrieval_performance` - Query performance with 5000+ transactions
- `test_mempool_memory_scaling` - Memory usage at 1k, 5k, 10k transactions (target: <100KB/tx)
- `test_mempool_fee_based_prioritization` - Fee-based selection from large mempool
- `test_mempool_expiration_performance` - Transaction expiration and pruning

**Metrics:**
- Transaction throughput (tx/sec)
- Memory usage (MB, KB/tx)
- Query latency (ms)
- Eviction performance

### 2. Storage Compaction Tests (`test_storage_compaction.py`)

Tests blockchain storage performance, compaction, and query efficiency.

**Key Tests:**
- `test_storage_growth_over_blocks` - Storage growth at 100, 500, 1000 blocks (target: <100KB/block)
- `test_block_file_rotation` - Block file rotation with 200+ blocks
- `test_utxo_set_growth` - UTXO set size and storage impact
- `test_compaction_performance` - Compaction speed with 500 blocks
- `test_block_index_build_performance` - Index creation for 300 blocks
- `test_query_performance_with_index` - Indexed vs linear search comparison
- `test_pruning_old_blocks` - Pruning performance with 1000 blocks
- `test_transaction_history_pruning` - Old transaction removal
- `test_block_lookup_by_height` - Block height lookup performance
- `test_block_lookup_by_hash` - Block hash lookup performance

**Metrics:**
- Storage size (KB)
- Compaction effectiveness (% reduction)
- Query latency (ms)
- Index build time (sec)

### 3. Network Latency Tests (`test_network_latency.py`)

Tests network protocol latency and throughput.

**Key Tests:**
- `test_tcp_connection_establishment_latency` - WebSocket connection time (target: <100ms)
- `test_tcp_message_roundtrip_latency` - TCP roundtrip time (target: <50ms)
- `test_quic_connection_establishment_latency` - QUIC connection time
- `test_quic_message_latency` - QUIC message send latency
- `test_protocol_latency_comparison` - TCP vs QUIC comparison
- `test_transaction_broadcast_throughput` - Transaction broadcast rate (target: >100 tx/sec)
- `test_block_broadcast_throughput` - Block broadcast rate (target: >10 blocks/sec)
- `test_latency_under_load` - Latency degradation under load (target: <10ms avg)
- `test_bandwidth_utilization` - Bandwidth efficiency

**Metrics:**
- Connection latency (ms)
- Message latency (ms)
- Throughput (tx/sec, blocks/sec, KB/s)
- P50, P95 latencies

### 4. Block Propagation Tests (`test_block_propagation.py`)

Tests block propagation across network topologies.

**Key Tests:**
- `test_block_propagation_single_peer` - Single peer propagation time (target: <100ms)
- `test_block_propagation_multiple_peers` - Parallel propagation to 10 peers
- `test_block_propagation_bandwidth_usage` - Full vs compact block bandwidth
- `test_compact_block_relay_performance` - Compact block speedup (target: >30% reduction)
- `test_propagation_star_topology` - Star network (central node to 20 peers)
- `test_propagation_mesh_topology` - Mesh network (20 nodes, 4 neighbors each)
- `test_network_partition_recovery` - Sync time after partition (target: <10s)
- `test_concurrent_block_propagation` - Multiple blocks simultaneously
- `test_propagation_with_transaction_flood` - Propagation under transaction load

**Metrics:**
- Propagation latency (ms)
- Bandwidth usage (KB)
- Network hops
- Sync time (sec)

## Running the Tests

### Run All Performance Tests

```bash
# Run all performance tests with benchmarking
pytest tests/xai_tests/performance/ -v -m performance

# Run with benchmark output
pytest tests/xai_tests/performance/ -v -m performance --benchmark-only

# Run with benchmark comparison
pytest tests/xai_tests/performance/ -v -m performance --benchmark-compare
```

### Run Specific Test Suite

```bash
# Mempool tests
pytest tests/xai_tests/performance/test_mempool_load.py -v -m performance

# Storage tests
pytest tests/xai_tests/performance/test_storage_compaction.py -v -m performance

# Network tests
pytest tests/xai_tests/performance/test_network_latency.py -v -m performance

# Block propagation tests
pytest tests/xai_tests/performance/test_block_propagation.py -v -m performance
```

### Run Individual Test

```bash
# Run specific test with benchmark details
pytest tests/xai_tests/performance/test_mempool_load.py::TestMempoolLoad::test_mempool_10k_transactions_insertion -v --benchmark-verbose
```

### Generate Performance Reports

```bash
# Generate JSON report
pytest tests/xai_tests/performance/ -m performance --benchmark-json=performance_report.json

# Save benchmark results for comparison
pytest tests/xai_tests/performance/ -m performance --benchmark-save=baseline

# Compare against baseline
pytest tests/xai_tests/performance/ -m performance --benchmark-compare=baseline
```

## Performance Baselines

These are the expected performance baselines. Tests will fail if performance degrades significantly below these targets.

### Mempool
- **Insertion throughput**: >100 tx/sec
- **Memory per transaction**: <100 KB
- **Query latency**: <10 ms (5000 tx mempool)

### Storage
- **Storage per block**: <100 KB (with minimal transactions)
- **Compaction reduction**: >30%
- **Query latency**: <5 ms (indexed)

### Network
- **TCP connection**: <100 ms
- **TCP roundtrip**: <50 ms
- **Transaction broadcast**: >100 tx/sec
- **Block broadcast**: >10 blocks/sec

### Propagation
- **Single peer**: <100 ms
- **Compact block reduction**: >30%
- **Partition recovery**: <10 sec (20 blocks)

## Requirements

Performance tests require additional dependencies:

```bash
pip install pytest-benchmark memory-profiler psutil
```

These are automatically installed if you use the project's `requirements.txt`.

## Memory Profiling

Some tests include memory profiling. To run with detailed memory analysis:

```bash
# Run with memory profiling
pytest tests/xai_tests/performance/test_mempool_load.py::TestMempoolLoad::test_mempool_memory_scaling -v -s
```

## Continuous Performance Monitoring

For CI/CD integration:

```bash
# Run performance tests and save results
pytest tests/xai_tests/performance/ -m performance --benchmark-json=results/$(date +%Y%m%d_%H%M%S).json

# Compare against previous baseline
pytest tests/xai_tests/performance/ -m performance --benchmark-compare=0001 --benchmark-compare-fail=mean:10%
```

## Interpreting Results

### Benchmark Output

```
----------------------------------------- benchmark: 1 tests ----------------------------------------
Name                                              Min      Max     Mean  StdDev  Median     IQR
-------------------------------------------------------------------------------------------------
test_mempool_10k_transactions_insertion       2.5000   3.2000   2.8500  0.2500  2.8000  0.3000
-------------------------------------------------------------------------------------------------
```

- **Min/Max**: Best and worst run times
- **Mean**: Average execution time
- **StdDev**: Standard deviation (lower is more consistent)
- **Median**: Middle value (robust to outliers)
- **IQR**: Interquartile range (spread of middle 50%)

### Memory Usage

Memory usage is reported in MB or KB per transaction/block:
- Monitor for unexpected growth
- Compare against baselines
- Check for memory leaks in long-running tests

## Best Practices

1. **Run on consistent hardware** - Performance varies by CPU, memory, disk
2. **Close other applications** - Minimize background interference
3. **Run multiple times** - Use benchmark rounds for statistical validity
4. **Monitor system resources** - Use `htop`, `iotop` during tests
5. **Set realistic baselines** - Based on production requirements
6. **Track over time** - Detect performance regressions early

## Troubleshooting

### Tests Running Slowly

- Check available system resources (CPU, memory, disk)
- Reduce test scale (fewer transactions/blocks) for debugging
- Run individual tests instead of full suite

### Benchmarks Failing

- Performance baselines may be too aggressive for your hardware
- Adjust thresholds in test assertions
- Compare against previous runs to identify regressions

### Memory Issues

- Large-scale tests may require significant RAM
- Monitor with `psutil` or system tools
- Consider running subsets of tests

### Network Tests Timing Out

- Network tests use localhost and should be fast
- Check for port conflicts
- Ensure async event loop is functioning correctly

## Contributing

When adding new performance tests:

1. Mark with `@pytest.mark.performance`
2. Use `benchmark` fixture for timing
3. Set realistic performance baselines
4. Include memory profiling for resource-intensive tests
5. Document expected metrics and thresholds
6. Add to this README

## Related Documentation

- [Testing Guide](../../INTEGRATION_TESTING_GUIDE.md)
- [Architecture Review](../../../ARCHITECTURE_REVIEW.md)
- [Roadmap](../../../ROADMAP_PRODUCTION.md)
