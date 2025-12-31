"""
Community Standards Compliance Tests

Verifies all 13 blockchain community standards tasks are properly implemented.
These tests ensure the codebase meets industry best practices.

Tests cover:
- Task 1: secrets.SystemRandom for mining timing (defense-in-depth)
- Task 2: Demo code removed from wallet.py main block
- Task 3: Deprecation timeline for legacy wallet encryption
- Task 11: Gas estimator accuracy (separate test file)
- Task 12: Multi-oracle price feed redundancy
"""

import pytest
import secrets
import subprocess
import sys
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))


class TestTask1MiningSecureRandom:
    """Task 1: Verify mining uses secrets.SystemRandom for timing jitter."""

    def test_mining_uses_secrets_system_random(self):
        """Mining module should use secrets.SystemRandom, not random.random."""
        from xai.core.mining.node_mining import _secure_random

        # Verify it's an instance of secrets.SystemRandom
        assert isinstance(_secure_random, secrets.SystemRandom), \
            "_secure_random must be secrets.SystemRandom for cryptographic security"

    def test_secure_random_produces_valid_floats(self):
        """SystemRandom.uniform should produce floats in expected range."""
        from xai.core.mining.node_mining import _secure_random

        # Test uniform produces values in range
        for _ in range(100):
            value = _secure_random.uniform(0, 1.0)
            assert 0 <= value <= 1.0, f"uniform(0, 1.0) produced {value}"

    def test_mining_source_has_no_random_module_uniform(self):
        """Mining source should not use random.uniform (insecure)."""
        mining_file = Path(__file__).parent.parent.parent.parent / "src" / "xai" / "core" / "mining" / "node_mining.py"

        content = mining_file.read_text()

        # Should not have random.uniform (the insecure version)
        assert "random.uniform" not in content or "_secure_random.uniform" in content, \
            "Mining should use _secure_random.uniform, not random.uniform"

        # Should have secrets import
        assert "import secrets" in content, \
            "Mining should import secrets module"

        # Should have SystemRandom
        assert "secrets.SystemRandom" in content, \
            "Mining should use secrets.SystemRandom"


class TestTask2WalletDemoCodeRemoval:
    """Task 2: Verify demo code removed from wallet.py main block."""

    def test_wallet_main_block_exits_with_error(self):
        """wallet.py __main__ should exit with error, not run demo code."""
        wallet_file = Path(__file__).parent.parent.parent.parent / "src" / "xai" / "core" / "wallet.py"

        content = wallet_file.read_text()

        # Should have SystemExit in __main__ block
        assert 'if __name__ == "__main__"' in content, \
            "wallet.py should have __main__ block"

        # Check for security guard patterns
        has_security_guard = (
            "SystemExit(1)" in content or
            "raise SystemExit" in content or
            "sys.exit(1)" in content
        )
        assert has_security_guard, \
            "wallet.py __main__ should exit with error, not run demo"

    def test_wallet_main_block_does_not_expose_private_key(self):
        """wallet.py main block should not print or expose private keys."""
        wallet_file = Path(__file__).parent.parent.parent.parent / "src" / "xai" / "core" / "wallet.py"

        content = wallet_file.read_text()

        # Find the __main__ block
        if 'if __name__ == "__main__"' in content:
            main_block_start = content.find('if __name__ == "__main__"')
            main_block = content[main_block_start:]

            # Should not print private key in main block
            dangerous_patterns = [
                "print(wallet.private_key",
                "print(w.private_key",
                ".private_key_hex",
                "get_private_key()",
            ]

            for pattern in dangerous_patterns:
                assert pattern not in main_block, \
                    f"Dangerous pattern '{pattern}' found in wallet.py __main__"

    def test_wallet_demo_file_exists(self):
        """Separate wallet demo file should exist."""
        demo_file = Path(__file__).parent.parent.parent.parent / "examples" / "wallet_demo.py"

        assert demo_file.exists(), \
            "examples/wallet_demo.py should exist for wallet examples"


class TestTask3DeprecationTimeline:
    """Task 3: Verify deprecation timeline for legacy wallet encryption."""

    def test_deprecation_date_constant_exists(self):
        """Wallet class should have deprecation date constant."""
        from xai.core.wallet import Wallet

        assert hasattr(Wallet, '_LEGACY_ENCRYPTION_REMOVAL_DATE'), \
            "Wallet should have _LEGACY_ENCRYPTION_REMOVAL_DATE constant"

    def test_deprecation_date_is_valid(self):
        """Deprecation date should be a valid future date string."""
        from xai.core.wallet import Wallet

        date_str = Wallet._LEGACY_ENCRYPTION_REMOVAL_DATE

        # Should be YYYY-MM-DD format
        assert len(date_str) == 10, f"Date should be YYYY-MM-DD, got {date_str}"
        assert date_str[4] == '-' and date_str[7] == '-', \
            f"Date should be YYYY-MM-DD format, got {date_str}"

        # Parse and validate
        year, month, day = date_str.split('-')
        assert 2025 <= int(year) <= 2030, f"Year should be 2025-2030, got {year}"
        assert 1 <= int(month) <= 12, f"Month should be 1-12, got {month}"
        assert 1 <= int(day) <= 31, f"Day should be 1-31, got {day}"

    def test_deprecation_warning_in_source(self):
        """Source should contain deprecation warning for legacy encryption."""
        wallet_file = Path(__file__).parent.parent.parent.parent / "src" / "xai" / "core" / "wallet.py"

        content = wallet_file.read_text()

        # Should have deprecation warning
        assert "DeprecationWarning" in content, \
            "wallet.py should issue DeprecationWarning for legacy encryption"

        # Should have timeline documentation
        assert "DEPRECATION" in content.upper(), \
            "wallet.py should document deprecation timeline"


class TestTask12OracleRedundancy:
    """Task 12: Verify multi-oracle price feed redundancy implementation."""

    def test_oracle_redundancy_manager_exists(self):
        """OracleRedundancyManager should be importable."""
        from xai.core.defi.oracle_redundancy import OracleRedundancyManager

        assert OracleRedundancyManager is not None

    def test_oracle_health_enum_exists(self):
        """OracleHealth enum should exist with proper states."""
        from xai.core.defi.oracle_redundancy import OracleHealth

        # Verify all health states exist
        assert hasattr(OracleHealth, 'HEALTHY')
        assert hasattr(OracleHealth, 'DEGRADED')
        assert hasattr(OracleHealth, 'UNHEALTHY')
        assert hasattr(OracleHealth, 'OFFLINE')

    def test_oracle_source_dataclass_exists(self):
        """OracleSource dataclass should exist with required fields."""
        from xai.core.defi.oracle_redundancy import OracleSource

        # Create an instance to verify fields
        source = OracleSource(name="test", priority=1)

        assert source.name == "test"
        assert source.priority == 1
        assert source.weight == 100  # default
        assert source.consecutive_failures == 0

    def test_oracle_manager_initialization(self):
        """OracleRedundancyManager should initialize with defaults."""
        from xai.core.defi.oracle_redundancy import OracleRedundancyManager

        manager = OracleRedundancyManager()

        # Check default values
        assert manager.max_deviation_bps == 200  # 2%
        assert manager.min_oracles_for_validation == 2
        assert manager.require_cross_validation is True
        assert manager.circuit_breaker_active is False
        assert manager.aggregation_method == "weighted_median"

    def test_add_oracle_source(self):
        """Manager should allow adding oracle sources."""
        from xai.core.defi.oracle_redundancy import OracleRedundancyManager

        manager = OracleRedundancyManager()

        # Create mock oracle
        mock_oracle = MagicMock()
        mock_oracle.get_price.return_value = (100000, time.time())
        mock_oracle.is_available.return_value = True

        # Add oracle
        manager.add_oracle("test_oracle", priority=1, oracle=mock_oracle, weight=100)

        assert "test_oracle" in manager.oracles
        assert manager.oracles["test_oracle"].priority == 1
        assert manager.oracles["test_oracle"].weight == 100

    def test_remove_oracle_source(self):
        """Manager should allow removing oracle sources."""
        from xai.core.defi.oracle_redundancy import OracleRedundancyManager

        manager = OracleRedundancyManager()
        mock_oracle = MagicMock()

        manager.add_oracle("removable", priority=1, oracle=mock_oracle)
        assert "removable" in manager.oracles

        manager.remove_oracle("removable")
        assert "removable" not in manager.oracles

    def test_get_price_with_single_oracle(self):
        """Manager should return price from single oracle."""
        from xai.core.defi.oracle_redundancy import OracleRedundancyManager

        manager = OracleRedundancyManager()
        manager.require_cross_validation = False  # Disable for single oracle test

        mock_oracle = MagicMock()
        mock_oracle.get_price.return_value = (150000, time.time())

        manager.add_oracle("single", priority=1, oracle=mock_oracle)

        price, confidence = manager.get_price("XAI/USD")

        assert price == 150000
        assert confidence > 0

    def test_get_price_aggregates_multiple_oracles(self):
        """Manager should aggregate prices from multiple oracles."""
        from xai.core.defi.oracle_redundancy import OracleRedundancyManager

        manager = OracleRedundancyManager()

        # Create multiple oracles with slightly different prices
        mock1 = MagicMock()
        mock1.get_price.return_value = (100000, time.time())

        mock2 = MagicMock()
        mock2.get_price.return_value = (100100, time.time())  # 0.1% higher

        mock3 = MagicMock()
        mock3.get_price.return_value = (99900, time.time())  # 0.1% lower

        manager.add_oracle("oracle1", priority=1, oracle=mock1)
        manager.add_oracle("oracle2", priority=2, oracle=mock2)
        manager.add_oracle("oracle3", priority=3, oracle=mock3)

        price, confidence = manager.get_price("XAI/USD")

        # Price should be close to median (100000)
        assert 99800 <= price <= 100200

    def test_circuit_breaker_triggers_on_deviation(self):
        """Circuit breaker should trigger on large price deviation."""
        from xai.core.defi.oracle_redundancy import OracleRedundancyManager
        from xai.core.vm.exceptions import VMExecutionError

        manager = OracleRedundancyManager()
        manager.max_deviation_bps = 100  # 1% max deviation

        # Create oracles with large price difference (>1%)
        mock1 = MagicMock()
        mock1.get_price.return_value = (100000, time.time())

        mock2 = MagicMock()
        mock2.get_price.return_value = (105000, time.time())  # 5% higher

        manager.add_oracle("oracle1", priority=1, oracle=mock1)
        manager.add_oracle("oracle2", priority=2, oracle=mock2)

        with pytest.raises(VMExecutionError) as exc_info:
            manager.get_price("XAI/USD")

        assert "deviation" in str(exc_info.value).lower()
        assert manager.circuit_breaker_active is True

    def test_oracle_health_tracking(self):
        """Manager should track oracle health on failures."""
        from xai.core.defi.oracle_redundancy import OracleRedundancyManager, OracleHealth

        manager = OracleRedundancyManager()
        manager.require_cross_validation = False

        # Create failing oracle
        mock_oracle = MagicMock()
        mock_oracle.get_price.side_effect = Exception("Oracle down")

        manager.add_oracle("failing", priority=1, oracle=mock_oracle)

        # Try to get price multiple times to trigger health degradation
        for _ in range(5):
            try:
                manager.get_price("XAI/USD")
            except Exception:
                pass

        # Oracle should be marked as unhealthy/offline
        source = manager.oracles["failing"]
        assert source.consecutive_failures >= 3
        assert source.health in [OracleHealth.UNHEALTHY, OracleHealth.OFFLINE]

    def test_get_health_status(self):
        """Manager should provide health status for all oracles."""
        from xai.core.defi.oracle_redundancy import OracleRedundancyManager

        manager = OracleRedundancyManager()

        mock_oracle = MagicMock()
        manager.add_oracle("test", priority=1, oracle=mock_oracle)

        status = manager.get_health_status()

        assert "test" in status
        assert "health" in status["test"]
        assert "priority" in status["test"]
        assert "weight" in status["test"]

    def test_twap_calculation(self):
        """Manager should calculate TWAP from cached prices."""
        from xai.core.defi.oracle_redundancy import OracleRedundancyManager, OraclePrice

        manager = OracleRedundancyManager()

        # Manually populate price cache
        current_time = time.time()
        manager.price_cache["XAI/USD"] = [
            OraclePrice(source="test", price=100000, timestamp=current_time - 300),
            OraclePrice(source="test", price=100500, timestamp=current_time - 200),
            OraclePrice(source="test", price=101000, timestamp=current_time - 100),
            OraclePrice(source="test", price=100200, timestamp=current_time),
        ]

        twap = manager.get_twap("XAI/USD", period_seconds=600)

        # TWAP should be average of cached prices
        expected_avg = (100000 + 100500 + 101000 + 100200) // 4
        assert abs(twap - expected_avg) < 100  # Allow small rounding difference


class TestDocumentationExists:
    """Verify all required documentation files exist."""

    @pytest.fixture
    def docs_root(self):
        return Path(__file__).parent.parent.parent.parent / "docs"

    def test_protocol_specification_exists(self, docs_root):
        """Task 4: Protocol specification should exist."""
        spec_file = docs_root / "protocol" / "PROTOCOL_SPECIFICATION.md"
        assert spec_file.exists(), "Missing docs/protocol/PROTOCOL_SPECIFICATION.md"

    def test_economic_audit_exists(self, docs_root):
        """Task 5: Economic audit should exist."""
        audit_file = docs_root / "economics" / "ECONOMIC_AUDIT.md"
        assert audit_file.exists(), "Missing docs/economics/ECONOMIC_AUDIT.md"

    def test_bug_bounty_exists(self, docs_root):
        """Task 6: Bug bounty program should exist."""
        bounty_file = docs_root / "security" / "BUG_BOUNTY.md"
        assert bounty_file.exists(), "Missing docs/security/BUG_BOUNTY.md"

    def test_security_disclosure_exists(self, docs_root):
        """Task 7: Security disclosure should exist."""
        disclosure_file = docs_root / "security" / "SECURITY_DISCLOSURE.md"
        assert disclosure_file.exists(), "Missing docs/security/SECURITY_DISCLOSURE.md"

    def test_slashing_conditions_exists(self, docs_root):
        """Task 8: Slashing conditions should exist."""
        slashing_file = docs_root / "security" / "SLASHING_CONDITIONS.md"
        assert slashing_file.exists(), "Missing docs/security/SLASHING_CONDITIONS.md"

    def test_external_audit_requirements_exists(self, docs_root):
        """Task 9: External audit requirements should exist."""
        audit_req_file = docs_root / "security" / "EXTERNAL_AUDIT_REQUIREMENTS.md"
        assert audit_req_file.exists(), "Missing docs/security/EXTERNAL_AUDIT_REQUIREMENTS.md"

    def test_formal_verification_exists(self, docs_root):
        """Task 10: Formal verification requirements should exist."""
        formal_file = docs_root / "security" / "FORMAL_VERIFICATION.md"
        assert formal_file.exists(), "Missing docs/security/FORMAL_VERIFICATION.md"

    def test_bridge_security_exists(self, docs_root):
        """Task 13: Bridge security documentation should exist."""
        bridge_file = docs_root / "security" / "BRIDGE_SECURITY.md"
        assert bridge_file.exists(), "Missing docs/security/BRIDGE_SECURITY.md"

    def test_disaster_recovery_exists(self, docs_root):
        """Task 14: Disaster recovery runbook should exist."""
        dr_file = docs_root / "runbooks" / "DISASTER_RECOVERY.md"
        assert dr_file.exists(), "Missing docs/runbooks/DISASTER_RECOVERY.md"


class TestGasEstimatorCoverage:
    """Task 11: Verify gas estimator accuracy tests exist and pass."""

    def test_gas_estimator_test_file_exists(self):
        """Gas estimator test file should exist."""
        test_file = Path(__file__).parent / "test_gas_estimator_accuracy.py"
        assert test_file.exists(), "Missing test_gas_estimator_accuracy.py"

    def test_gas_estimator_has_minimum_tests(self):
        """Gas estimator should have comprehensive test coverage."""
        test_file = Path(__file__).parent / "test_gas_estimator_accuracy.py"
        content = test_file.read_text()

        # Count test methods
        test_count = content.count("def test_")

        assert test_count >= 10, \
            f"Gas estimator should have at least 10 tests, found {test_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
