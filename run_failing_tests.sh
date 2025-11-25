#!/bin/bash
# Run each failing test and capture errors
TESTS=(
"tests/xai_tests/integration/test_chain_reorg_comprehensive.py::TestTransactionHandlingDuringReorg::test_double_spend_prevented_after_reorg"
"tests/xai_tests/integration/test_multi_node_consensus.py::TestMultiNodeConsensus::test_double_spend_prevention"
"tests/xai_tests/unit/test_advanced_consensus_coverage.py::TestDynamicDifficultyAdjustmentComprehensive::test_should_adjust_difficulty_true"
"tests/xai_tests/unit/test_advanced_consensus_coverage.py::TestDynamicDifficultyAdjustmentComprehensive::test_get_difficulty_stats"
)

for test in "${TESTS[@]}"; do
    echo "=== TESTING: $test ==="
    .venv313/Scripts/pytest.exe "$test" -xvs 2>&1 | tail -30
    echo ""
done
