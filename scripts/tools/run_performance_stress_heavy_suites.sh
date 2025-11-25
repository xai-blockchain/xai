#!/usr/bin/env bash
set -euo pipefail

PYTEST=${PYTEST:-./venv/bin/pytest}

BATCHES=(
  "tests/xai_tests/performance/test_network_stress_comprehensive.py::TestMemoryAndResourceStress"
  "tests/xai_tests/performance/test_network_stress_comprehensive.py::TestChainReorganizationStress"
)

for batch in "${BATCHES[@]}"; do
  echo
  echo "==== Running heavy-suite: ${batch} ===="
  ${PYTEST} ${batch}
done
