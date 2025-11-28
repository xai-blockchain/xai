#!/usr/bin/env bash
set -euo pipefail

PYTEST=${PYTEST:-./venv/bin/pytest}

BATCHES=(
  "tests/xai_tests/performance/test_stress.py::TestBlockchainScalability tests/xai_tests/performance/test_stress.py::TestTransactionThroughput tests/xai_tests/performance/test_stress.py::TestConcurrency"
  "tests/xai_tests/performance/test_stress.py::TestMemoryUsage tests/xai_tests/performance/test_stress.py::TestStressConditions tests/xai_tests/performance/test_stress.py::TestLongRunning"
  "tests/xai_tests/performance/test_network_stress_comprehensive.py::TestTransactionThroughputStress tests/xai_tests/performance/test_network_stress_comprehensive.py::TestBlockPropagationStress"
  "tests/xai_tests/performance/test_network_stress_comprehensive.py::TestNetworkResilienceStress tests/xai_tests/performance/test_network_stress_comprehensive.py::TestConcurrentOperationsStress"
)

for batch in "${BATCHES[@]}"; do
  echo
  echo "==== Running: ${batch} ===="
  ${PYTEST} ${batch}
done
