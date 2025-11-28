"""
Comprehensive tests for smart contract gas metering and limits

Tests out-of-gas scenarios, gas refunds, operation costs,
infinite loop prevention, and accurate gas accounting.
"""

import pytest
from unittest.mock import Mock, patch


class GasMetering:
    """Mock gas metering system for testing"""

    # Gas costs for different operations
    GAS_COSTS = {
        'ADD': 3,
        'SUB': 3,
        'MUL': 5,
        'DIV': 5,
        'STORE': 20,
        'LOAD': 5,
        'JUMP': 8,
        'CALL': 40,
    }

    def __init__(self, gas_limit):
        self.gas_limit = gas_limit
        self.gas_used = 0
        self.gas_refund = 0

    def consume_gas(self, operation):
        """Consume gas for an operation"""
        cost = self.GAS_COSTS.get(operation, 1)
        if self.gas_used + cost > self.gas_limit:
            raise OutOfGasError(f"Out of gas: used {self.gas_used}, limit {self.gas_limit}")
        self.gas_used += cost
        return True

    def refund_gas(self, amount):
        """Refund gas (e.g., from storage deletion)"""
        self.gas_refund += amount

    def get_remaining_gas(self):
        """Get remaining gas"""
        return self.gas_limit - self.gas_used

    def get_gas_refund(self):
        """Calculate final gas refund (capped at 50% of used gas)"""
        max_refund = self.gas_used // 2
        return min(self.gas_refund, max_refund)


class OutOfGasError(Exception):
    """Raised when contract runs out of gas"""
    pass


class TestContractGas:
    """Tests for smart contract gas system"""

    def test_out_of_gas_scenario(self):
        """Test contract execution fails when out of gas"""
        gas_meter = GasMetering(gas_limit=10)

        # Execute operations
        gas_meter.consume_gas('ADD')  # 3 gas
        gas_meter.consume_gas('ADD')  # 3 gas
        gas_meter.consume_gas('ADD')  # 3 gas (total: 9)

        # Next operation should fail
        with pytest.raises(OutOfGasError):
            gas_meter.consume_gas('ADD')  # Would exceed limit

    def test_gas_refund_calculation(self):
        """Test gas refund for storage deletion"""
        gas_meter = GasMetering(gas_limit=1000)

        # Use some gas
        gas_meter.consume_gas('STORE')  # 20 gas
        gas_meter.consume_gas('STORE')  # 20 gas
        gas_meter.consume_gas('LOAD')   # 5 gas
        # Total used: 45 gas

        # Refund gas (e.g., from deleting storage)
        gas_meter.refund_gas(15)

        # Refund should be capped at 50% of used gas
        refund = gas_meter.get_gas_refund()
        max_allowed = gas_meter.gas_used // 2  # 22

        assert refund == min(15, max_allowed)

    def test_gas_cost_add_operation(self):
        """Test gas cost for ADD operation"""
        gas_meter = GasMetering(gas_limit=100)
        gas_meter.consume_gas('ADD')

        assert gas_meter.gas_used == 3

    def test_gas_cost_mul_operation(self):
        """Test gas cost for MUL operation"""
        gas_meter = GasMetering(gas_limit=100)
        gas_meter.consume_gas('MUL')

        assert gas_meter.gas_used == 5

    def test_gas_cost_store_operation(self):
        """Test gas cost for STORE operation (expensive)"""
        gas_meter = GasMetering(gas_limit=100)
        gas_meter.consume_gas('STORE')

        assert gas_meter.gas_used == 20

    def test_gas_cost_call_operation(self):
        """Test gas cost for CALL operation"""
        gas_meter = GasMetering(gas_limit=100)
        gas_meter.consume_gas('CALL')

        assert gas_meter.gas_used == 40

    def test_infinite_loop_prevention_via_gas(self):
        """Test infinite loops are prevented by gas limit"""
        gas_meter = GasMetering(gas_limit=100)

        iterations = 0
        try:
            while True:
                gas_meter.consume_gas('ADD')
                iterations += 1
        except OutOfGasError:
            pass

        # Loop should have been stopped by gas limit
        assert iterations < 100
        # With ADD costing 3 gas, should do ~33 iterations
        assert 30 <= iterations <= 35

    def test_accurate_gas_metering_complex_operations(self):
        """Test accurate gas tracking across complex operations"""
        gas_meter = GasMetering(gas_limit=1000)

        # Execute sequence
        gas_meter.consume_gas('ADD')    # 3
        gas_meter.consume_gas('MUL')    # 5
        gas_meter.consume_gas('STORE')  # 20
        gas_meter.consume_gas('LOAD')   # 5
        gas_meter.consume_gas('DIV')    # 5
        gas_meter.consume_gas('JUMP')   # 8

        expected_total = 3 + 5 + 20 + 5 + 5 + 8
        assert gas_meter.gas_used == expected_total

    def test_gas_limit_enforcement(self):
        """Test gas limit is strictly enforced"""
        gas_meter = GasMetering(gas_limit=50)

        # Use almost all gas
        gas_meter.consume_gas('CALL')   # 40 gas
        gas_meter.consume_gas('ADD')    # 3 gas (total: 43)

        remaining = gas_meter.get_remaining_gas()
        assert remaining == 7

        # Operation that would exceed limit should fail
        with pytest.raises(OutOfGasError):
            gas_meter.consume_gas('STORE')  # Would need 20 gas

    def test_gas_refund_capped_at_50_percent(self):
        """Test gas refund is capped at 50% of used gas"""
        gas_meter = GasMetering(gas_limit=1000)

        # Use 100 gas
        for _ in range(5):
            gas_meter.consume_gas('STORE')  # 20 gas each

        assert gas_meter.gas_used == 100

        # Try to refund 75 gas
        gas_meter.refund_gas(75)

        # Should be capped at 50 gas (50% of 100)
        refund = gas_meter.get_gas_refund()
        assert refund == 50

    def test_multiple_gas_refunds_accumulate(self):
        """Test multiple refunds accumulate correctly"""
        gas_meter = GasMetering(gas_limit=1000)

        # Use gas
        gas_meter.consume_gas('STORE')  # 20
        gas_meter.consume_gas('STORE')  # 20
        # Total: 40 gas used

        # Multiple refunds
        gas_meter.refund_gas(5)
        gas_meter.refund_gas(5)
        gas_meter.refund_gas(5)

        # Should accumulate to 15
        assert gas_meter.gas_refund == 15
        # But final refund capped at 50% of 40 = 20
        assert gas_meter.get_gas_refund() == 15

    def test_zero_gas_limit_fails_immediately(self):
        """Test contract with zero gas limit fails immediately"""
        gas_meter = GasMetering(gas_limit=0)

        with pytest.raises(OutOfGasError):
            gas_meter.consume_gas('ADD')

    def test_exact_gas_usage_no_failure(self):
        """Test using exactly gas limit succeeds"""
        gas_meter = GasMetering(gas_limit=15)

        gas_meter.consume_gas('ADD')  # 3
        gas_meter.consume_gas('ADD')  # 3
        gas_meter.consume_gas('ADD')  # 3
        gas_meter.consume_gas('ADD')  # 3
        gas_meter.consume_gas('ADD')  # 3
        # Total: 15 gas (exact limit)

        assert gas_meter.gas_used == 15
        assert gas_meter.get_remaining_gas() == 0

        # Next operation should fail
        with pytest.raises(OutOfGasError):
            gas_meter.consume_gas('ADD')
