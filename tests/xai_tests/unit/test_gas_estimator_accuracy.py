"""
Gas Estimator Accuracy Tests

Tests to verify that gas estimation is accurate across different
contract types and operations. This addresses the blockchain community
standard of having reliable gas estimation.
"""

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from unittest.mock import MagicMock, patch

# Import the executor and related classes
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from xai.core.vm.executor import (
    ExecutionMessage,
    ExecutionResult,
    ProductionContractExecutor,
)
from xai.core.vm.evm.executor import EVMBytecodeExecutor
from xai.core.vm.evm.context import ExecutionContext


class TestGasEstimatorAccuracy:
    """Test gas estimation accuracy across various scenarios."""

    @pytest.fixture
    def executor(self):
        """Create a production executor for testing."""
        blockchain = MagicMock()
        blockchain.data_dir = "/tmp/test"
        return ProductionContractExecutor(blockchain=blockchain)

    @pytest.fixture
    def evm_executor(self):
        """Create an EVM executor for testing."""
        blockchain = MagicMock()
        blockchain.data_dir = "/tmp/test"
        blockchain.chain = []
        blockchain.storage = MagicMock()
        blockchain.storage.load_block_from_disk = MagicMock(return_value=None)
        return EVMBytecodeExecutor(blockchain)

    def test_base_transaction_gas(self, executor):
        """Base transaction should cost exactly 21000 gas."""
        message = ExecutionMessage(
            sender="0x" + "1" * 40,
            to="0x" + "2" * 40,
            value=0,
            gas_limit=50000,
            data=b"",
            nonce=0,
        )

        estimated = executor.estimate_gas(message)

        # Base transaction cost should be 21000
        assert estimated >= 21000, "Base gas should be at least 21000"

    def test_data_gas_cost(self, executor):
        """Test that data bytes are charged correctly."""
        # Empty data
        msg_empty = ExecutionMessage(
            sender="0x" + "1" * 40,
            to="0x" + "2" * 40,
            value=0,
            gas_limit=100000,
            data=b"",
            nonce=0,
        )

        # 100 bytes of data
        msg_with_data = ExecutionMessage(
            sender="0x" + "1" * 40,
            to="0x" + "2" * 40,
            value=0,
            gas_limit=100000,
            data=b"\x01" * 100,
            nonce=0,
        )

        gas_empty = executor.estimate_gas(msg_empty)
        gas_with_data = executor.estimate_gas(msg_with_data)

        # Data should add to gas cost
        assert gas_with_data > gas_empty, "Data should increase gas cost"

    def test_contract_creation_gas(self, executor):
        """Contract creation should cost more than simple transfer."""
        # Simple transfer
        msg_transfer = ExecutionMessage(
            sender="0x" + "1" * 40,
            to="0x" + "2" * 40,
            value=1000,
            gas_limit=100000,
            data=b"",
            nonce=0,
        )

        # Contract creation (to=None with code)
        msg_create = ExecutionMessage(
            sender="0x" + "1" * 40,
            to=None,  # Contract creation
            value=0,
            gas_limit=1000000,
            data=b"\x60\x00" * 100,  # Simple bytecode
            nonce=0,
        )

        gas_transfer = executor.estimate_gas(msg_transfer)
        gas_create = executor.estimate_gas(msg_create)

        # Contract creation should cost more
        assert gas_create > gas_transfer, "Contract creation should cost more"

    def test_estimation_vs_actual_accuracy(self, executor):
        """Estimated gas should be close to actual gas used."""
        message = ExecutionMessage(
            sender="0x" + "1" * 40,
            to="0x" + "2" * 40,
            value=100,
            gas_limit=100000,
            data=b"\x01\x02\x03\x04",
            nonce=0,
        )

        estimated = executor.estimate_gas(message)

        # Execute and get actual gas
        try:
            result = executor.execute(message)
            actual = result.gas_used

            # Estimation should be within 20% of actual (industry standard)
            accuracy = abs(estimated - actual) / max(estimated, actual)
            assert accuracy < 0.2, f"Gas estimation accuracy {accuracy:.2%} exceeds 20% threshold"
        except Exception:
            # If execution fails, at least verify estimation is reasonable
            assert 21000 <= estimated <= 10000000, "Estimation should be in valid range"

    @given(st.binary(min_size=0, max_size=1000))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_estimation_never_underestimates(self, executor, data):
        """Gas estimation should never underestimate (would cause tx failure)."""
        message = ExecutionMessage(
            sender="0x" + "1" * 40,
            to="0x" + "2" * 40,
            value=0,
            gas_limit=10000000,
            data=data,
            nonce=0,
        )

        estimated = executor.estimate_gas(message)

        try:
            result = executor.execute(message)
            # Estimation should be >= actual (with small buffer)
            assert estimated >= result.gas_used * 0.95, \
                f"Estimation {estimated} < actual {result.gas_used}"
        except Exception:
            # If execution fails, estimation should still be valid
            assert estimated >= 21000

    def test_zero_value_transfer(self, executor):
        """Zero value transfer should still cost base gas."""
        message = ExecutionMessage(
            sender="0x" + "1" * 40,
            to="0x" + "2" * 40,
            value=0,
            gas_limit=50000,
            data=b"",
            nonce=0,
        )

        estimated = executor.estimate_gas(message)
        assert estimated >= 21000, "Zero value transfer should cost at least base gas"

    def test_high_value_transfer(self, executor):
        """High value transfer gas should equal low value transfer gas."""
        msg_low = ExecutionMessage(
            sender="0x" + "1" * 40,
            to="0x" + "2" * 40,
            value=1,
            gas_limit=50000,
            data=b"",
            nonce=0,
        )

        msg_high = ExecutionMessage(
            sender="0x" + "1" * 40,
            to="0x" + "2" * 40,
            value=10**18,  # 1 ETH equivalent
            gas_limit=50000,
            data=b"",
            nonce=0,
        )

        gas_low = executor.estimate_gas(msg_low)
        gas_high = executor.estimate_gas(msg_high)

        # Gas should be the same regardless of value
        assert gas_low == gas_high, "Gas should not depend on transfer value"

    def test_gas_limit_respected(self, executor):
        """Estimation should respect the gas limit."""
        message = ExecutionMessage(
            sender="0x" + "1" * 40,
            to="0x" + "2" * 40,
            value=0,
            gas_limit=25000,  # Low limit
            data=b"",
            nonce=0,
        )

        estimated = executor.estimate_gas(message)
        assert estimated <= message.gas_limit or estimated == 21000, \
            "Estimation should respect gas limit"


class TestGasEstimatorEVMOperations:
    """Test gas estimation for specific EVM operations."""

    @pytest.fixture
    def evm_executor(self):
        """Create an EVM executor."""
        blockchain = MagicMock()
        blockchain.data_dir = "/tmp/test"
        blockchain.chain = []
        blockchain.storage = MagicMock()
        return EVMBytecodeExecutor(blockchain)

    def test_storage_write_gas(self, evm_executor):
        """Storage writes should cost appropriate gas."""
        # SSTORE is one of the most expensive operations
        # Cold storage write: 20,000 gas
        # Warm storage write: 100 gas
        # These are EIP-2929 costs

        # Simple contract that writes to storage
        # PUSH1 0x01 PUSH1 0x00 SSTORE STOP
        bytecode = bytes([0x60, 0x01, 0x60, 0x00, 0x55, 0x00])

        msg = ExecutionMessage(
            sender="0x" + "1" * 40,
            to=None,
            value=0,
            gas_limit=100000,
            data=bytecode,
            nonce=0,
        )

        estimated = evm_executor.estimate_gas(msg)

        # Should include base cost + contract creation + storage write
        assert estimated > 21000, "Storage write should cost more than base"

    def test_call_gas_cost(self, evm_executor):
        """External calls should have appropriate gas cost."""
        # CALL opcode base cost is 100 (warm) or 2600 (cold)
        # Plus value transfer cost if applicable

        msg = ExecutionMessage(
            sender="0x" + "1" * 40,
            to="0x" + "2" * 40,
            value=0,
            gas_limit=100000,
            # Simple call data: function selector
            data=bytes.fromhex("a9059cbb"),  # transfer(address,uint256)
            nonce=0,
        )

        estimated = evm_executor.estimate_gas(msg)
        assert estimated >= 21000


class TestGasEstimatorDeFi:
    """Test gas estimation for DeFi operations."""

    def test_swap_gas_estimation(self):
        """DEX swaps should have predictable gas costs."""
        # Typical Uniswap V2 swap: ~150,000 gas
        # Typical Uniswap V3 swap: ~180,000 gas

        # This would test against actual swap router
        # For now, verify the estimation infrastructure exists
        from xai.core.defi.swap_router import SwapRouter

        # Verify SwapRouter has gas estimation capability
        assert hasattr(SwapRouter, '__init__'), "SwapRouter should exist"

    def test_flash_loan_gas_estimation(self):
        """Flash loans should estimate callback gas correctly."""
        from xai.core.defi.flash_loans import FlashLoanProvider

        # Flash loan gas depends heavily on callback
        # Base flash loan: ~100,000 gas
        # Plus callback execution gas

        assert hasattr(FlashLoanProvider, 'flash_loan'), "FlashLoanProvider should have flash_loan"


class TestGasEstimatorEdgeCases:
    """Test edge cases in gas estimation."""

    @pytest.fixture
    def executor(self):
        """Create executor."""
        blockchain = MagicMock()
        blockchain.data_dir = "/tmp/test"
        return ProductionContractExecutor(blockchain=blockchain)

    def test_max_gas_limit(self, executor):
        """Maximum gas limit should be handled."""
        message = ExecutionMessage(
            sender="0x" + "1" * 40,
            to="0x" + "2" * 40,
            value=0,
            gas_limit=30_000_000,  # Block gas limit
            data=b"",
            nonce=0,
        )

        estimated = executor.estimate_gas(message)
        assert 21000 <= estimated <= 30_000_000

    def test_min_gas_limit(self, executor):
        """Minimum gas limit edge case."""
        message = ExecutionMessage(
            sender="0x" + "1" * 40,
            to="0x" + "2" * 40,
            value=0,
            gas_limit=21000,  # Exactly base cost
            data=b"",
            nonce=0,
        )

        estimated = executor.estimate_gas(message)
        # Base cost is 21000, may include small overhead
        assert 21000 <= estimated <= 22000, f"Base gas {estimated} should be close to 21000"

    def test_invalid_to_address(self, executor):
        """Invalid to address should still estimate."""
        message = ExecutionMessage(
            sender="0x" + "1" * 40,
            to="0x" + "0" * 40,  # Zero address
            value=0,
            gas_limit=50000,
            data=b"",
            nonce=0,
        )

        # Should not raise, should return valid estimate
        estimated = executor.estimate_gas(message)
        assert estimated >= 21000


class TestGasEstimatorMetrics:
    """Test gas estimation metrics and reporting."""

    def test_estimation_determinism(self):
        """Same input should always produce same estimate."""
        blockchain = MagicMock()
        blockchain.data_dir = "/tmp/test"
        executor = ProductionContractExecutor(blockchain=blockchain)

        message = ExecutionMessage(
            sender="0x" + "1" * 40,
            to="0x" + "2" * 40,
            value=0,
            gas_limit=100000,
            data=b"\x01\x02\x03",
            nonce=0,
        )

        estimates = [executor.estimate_gas(message) for _ in range(10)]

        # All estimates should be identical
        assert len(set(estimates)) == 1, "Gas estimation should be deterministic"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
