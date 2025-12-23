# XAI Blockchain - Remaining Test Coverage

This document identifies modules lacking test coverage and provides detailed instructions for AI agents to write comprehensive tests.

## Quick Stats

- **Total core modules**: 139
- **Modules with dedicated tests**: 65
- **Modules needing tests**: 74+

## Test Writing Guidelines

### Environment Setup

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests
pytest tests/xai_tests/unit/ -v

# Run specific test file
pytest tests/xai_tests/unit/test_<module>.py -v

# Run with coverage
pytest tests/xai_tests/unit/ --cov=src/xai/core --cov-report=term-missing
```

### Test File Conventions

1. **Location**: Place tests in `tests/xai_tests/unit/test_<module_name>.py`
2. **Imports**: Use absolute imports from `xai.core.<module>`
3. **Fixtures**: Use `tmp_path` for temporary directories, create fixtures for blockchain instances
4. **Docstrings**: Every test class and method must have a docstring

### Test Pattern Template

```python
"""
Unit tests for <module_name> functionality.

Tests cover:
- <list main areas>
"""

import pytest
import tempfile
from pathlib import Path

from xai.core.<module_name> import <MainClass>
from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet


class Test<MainClass>Initialization:
    """Test <class> initialization and configuration."""

    @pytest.fixture
    def temp_blockchain(self, tmp_path):
        """Create temporary blockchain for testing."""
        return Blockchain(data_dir=str(tmp_path))

    def test_initialization(self, tmp_path):
        """Test basic initialization."""
        instance = <MainClass>(...)
        assert instance is not None

    def test_initialization_with_invalid_params(self):
        """Test initialization with invalid parameters raises errors."""
        with pytest.raises(ValueError):
            <MainClass>(invalid_param=...)


class Test<MainClass>CoreFunctions:
    """Test <class> core functionality."""

    def test_<function_name>_success(self):
        """Test <function> with valid inputs."""
        pass

    def test_<function_name>_edge_cases(self):
        """Test <function> edge cases."""
        pass

    def test_<function_name>_error_handling(self):
        """Test <function> error handling."""
        pass


class Test<MainClass>Security:
    """Test <class> security properties."""

    def test_input_validation(self):
        """Test input validation prevents injection."""
        pass

    def test_authentication_required(self):
        """Test operations require proper authentication."""
        pass
```

---

## Priority 1: Critical Security Modules (HIGH)

These modules handle security-critical operations and MUST have comprehensive tests.

### 1. `src/xai/security/csprng.py`
**Purpose**: Cryptographically Secure Pseudo-Random Number Generator

**Test requirements**:
- Test entropy sources are properly seeded
- Test output randomness (statistical tests)
- Test thread safety
- Test deterministic mode for testing
- Test fallback behavior when hardware RNG unavailable

```python
# tests/xai_tests/unit/test_csprng.py
from xai.security.csprng import CSPRNG

class TestCSPRNG:
    def test_random_bytes_length(self):
        """Test random_bytes returns correct length."""
        rng = CSPRNG()
        for length in [16, 32, 64, 128]:
            result = rng.random_bytes(length)
            assert len(result) == length

    def test_randomness_uniqueness(self):
        """Test each call produces unique output."""
        rng = CSPRNG()
        results = [rng.random_bytes(32) for _ in range(1000)]
        assert len(set(results)) == 1000  # All unique

    def test_thread_safety(self):
        """Test concurrent access is safe."""
        import threading
        rng = CSPRNG()
        results = []
        def worker():
            results.append(rng.random_bytes(32))
        threads = [threading.Thread(target=worker) for _ in range(100)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert len(set(results)) == 100
```

### 2. `src/xai/security/hsm.py`
**Purpose**: Hardware Security Module integration

**Test requirements**:
- Test HSM connection/disconnection
- Test key generation in HSM
- Test signing operations
- Test fallback when HSM unavailable
- Test key import/export restrictions

### 3. `src/xai/security/mpc_dkg.py`
**Purpose**: Multi-Party Computation Distributed Key Generation

**Test requirements**:
- Test key share generation
- Test threshold signature assembly
- Test malicious participant detection
- Test incomplete threshold handling
- Test key refresh protocol

### 4. `src/xai/security/tss.py` and `tss_production.py`
**Purpose**: Threshold Signature Schemes

**Test requirements**:
- Test signature generation with n-of-m threshold
- Test invalid share rejection
- Test signature verification
- Test recovery from share loss

### 5. `src/xai/security/two_factor_auth.py`
**Purpose**: Two-Factor Authentication

**Test requirements**:
- Test TOTP generation/verification
- Test backup codes
- Test rate limiting
- Test clock drift tolerance
- Test recovery flow

---

## Priority 2: Network Security (HIGH)

### 1. `src/xai/network/ddos_protector.py`
**Purpose**: DDoS protection and rate limiting

**Test requirements**:
- Test rate limiting per IP
- Test request throttling
- Test blacklist management
- Test whitelist bypass
- Test adaptive thresholds

```python
# tests/xai_tests/unit/test_ddos_protector.py
from xai.network.ddos_protector import DDoSProtector

class TestDDoSProtector:
    def test_rate_limit_enforcement(self):
        """Test requests beyond limit are rejected."""
        protector = DDoSProtector(max_requests_per_second=10)
        ip = "192.168.1.100"
        for _ in range(10):
            assert protector.allow_request(ip) is True
        assert protector.allow_request(ip) is False

    def test_whitelist_bypass(self):
        """Test whitelisted IPs bypass rate limits."""
        protector = DDoSProtector(max_requests_per_second=10)
        protector.add_to_whitelist("10.0.0.1")
        for _ in range(100):
            assert protector.allow_request("10.0.0.1") is True
```

### 2. `src/xai/network/eclipse_protector.py`
**Purpose**: Eclipse attack protection

**Test requirements**:
- Test peer diversity requirements
- Test ASN/IP diversity checks
- Test connection limits per subnet
- Test new peer acceptance criteria

### 3. `src/xai/network/gossip_validator.py`
**Purpose**: Gossip protocol message validation

**Test requirements**:
- Test message signature verification
- Test message deduplication
- Test message expiry
- Test peer reputation impact

### 4. `src/xai/network/packet_filter.py`
**Purpose**: Network packet filtering

**Test requirements**:
- Test malformed packet rejection
- Test protocol version validation
- Test payload size limits

### 5. `src/xai/network/partition_detector.py`
**Purpose**: Network partition detection

**Test requirements**:
- Test partition detection accuracy
- Test recovery handling
- Test false positive avoidance

---

## Priority 3: Blockchain Components (MEDIUM-HIGH)

### 1. `src/xai/blockchain/double_sign_detector.py`
**Purpose**: Detect double-signing by validators

**Test requirements**:
- Test detection of conflicting signatures
- Test evidence storage
- Test slashing trigger
- Test false positive prevention

### 2. `src/xai/blockchain/fraud_proofs.py`
**Purpose**: Generate and verify fraud proofs

**Test requirements**:
- Test proof generation for invalid blocks
- Test proof verification
- Test proof submission to chain
- Test challenge period handling

### 3. `src/xai/blockchain/fork_detector.py`
**Purpose**: Fork detection and handling

**Test requirements**:
- Test fork detection at various depths
- Test fork resolution rules
- Test chain reorganization safety

### 4. `src/xai/blockchain/slashing_manager.py`
**Purpose**: Validator slashing management

**Test requirements**:
- Test slashing for downtime
- Test slashing for double signing
- Test slashing amount calculation
- Test jail/unjail mechanics

### 5. `src/xai/blockchain/twap_oracle.py`
**Purpose**: Time-Weighted Average Price oracle

**Test requirements**:
- Test price accumulator updates
- Test TWAP calculation accuracy
- Test manipulation resistance
- Test multi-period queries

### 6. `src/xai/blockchain/wash_trading_detection.py`
**Purpose**: Detect wash trading patterns

**Test requirements**:
- Test self-trade detection
- Test circular trade detection
- Test volume spike detection
- Test flagging accuracy

---

## Priority 4: Core Blockchain Mixins (MEDIUM)

### 1. `src/xai/core/blockchain_components/consensus_mixin.py`
**Purpose**: Consensus-related blockchain methods

**Test requirements**:
- Test block validation rules
- Test chain tip selection
- Test consensus state transitions

### 2. `src/xai/core/blockchain_components/mempool_mixin.py`
**Purpose**: Mempool management methods

**Test requirements**:
- Test transaction addition/removal
- Test fee ordering
- Test transaction eviction
- Test replacement policies

### 3. `src/xai/core/blockchain_components/mining_mixin.py`
**Purpose**: Mining-related blockchain methods

**Test requirements**:
- Test block construction
- Test coinbase creation
- Test difficulty adjustment
- Test reward calculation

---

## Priority 5: DeFi Modules (MEDIUM)

### 1. `src/xai/core/defi/flash_loans.py`
**Purpose**: Flash loan implementation

**Test requirements**:
- Test loan execution in single transaction
- Test repayment enforcement
- Test fee calculation
- Test reentrancy protection
- Test callback validation

```python
# tests/xai_tests/unit/test_flash_loans.py
from xai.core.defi.flash_loans import FlashLoanProvider

class TestFlashLoans:
    def test_loan_must_be_repaid(self):
        """Test loan without repayment reverts."""
        provider = FlashLoanProvider(...)
        with pytest.raises(FlashLoanNotRepaidError):
            provider.execute_flash_loan(
                amount=1000,
                callback=lambda: None  # No repayment
            )

    def test_fee_calculation(self):
        """Test fee is calculated correctly."""
        provider = FlashLoanProvider(fee_bps=9)  # 0.09%
        fee = provider.calculate_fee(10000)
        assert fee == 9  # 10000 * 0.0009
```

### 2. `src/xai/core/defi/safe_math.py`
**Purpose**: Safe math operations for DeFi

**Test requirements**:
- Test overflow protection
- Test underflow protection
- Test division by zero
- Test precision loss handling

### 3. `src/xai/core/defi/access_control.py`
**Purpose**: DeFi access control

**Test requirements**:
- Test role assignment
- Test permission checks
- Test admin operations
- Test role revocation

---

## Priority 6: Token Contracts (MEDIUM)

### 1. `src/xai/core/contracts/erc20.py`
**Purpose**: ERC-20 token standard implementation

**Test requirements**:
- Test transfer
- Test transferFrom with allowance
- Test approve
- Test balance tracking
- Test totalSupply accuracy
- Test overflow protection

### 2. `src/xai/core/contracts/erc721.py`
**Purpose**: ERC-721 NFT standard implementation

**Test requirements**:
- Test mint
- Test transfer
- Test approve
- Test ownership tracking
- Test tokenURI

### 3. `src/xai/core/contracts/erc1155.py`
**Purpose**: ERC-1155 multi-token standard

**Test requirements**:
- Test single transfer
- Test batch transfer
- Test balanceOf
- Test balanceOfBatch
- Test URI management

---

## Priority 7: Core Infrastructure (MEDIUM)

### 1. `src/xai/core/governance_execution.py`
**Purpose**: Execute approved governance proposals

**Test requirements**:
- Test parameter change execution
- Test feature activation
- Test treasury allocation
- Test execution authorization
- Test execution logging

### 2. `src/xai/core/fork_manager.py`
**Purpose**: Fork management and resolution

**Test requirements**:
- Test fork detection
- Test best chain selection
- Test orphan block handling
- Test rollback safety

### 3. `src/xai/core/state_manager.py`
**Purpose**: Blockchain state management

**Test requirements**:
- Test state snapshots
- Test state restoration
- Test state pruning
- Test concurrent access

### 4. `src/xai/core/fraud_detection.py`
**Purpose**: Transaction fraud detection

**Test requirements**:
- Test pattern detection
- Test anomaly scoring
- Test alert generation
- Test false positive handling

---

## Priority 8: API and Integration (LOWER)

### 1. `src/xai/core/api_security.py`
**Purpose**: API security middleware

**Test requirements**:
- Test authentication
- Test authorization
- Test rate limiting
- Test input sanitization

### 2. `src/xai/core/burning_api_endpoints.py`
**Purpose**: Token burning API

**Test requirements**:
- Test burn endpoint
- Test burn proof verification
- Test burn authorization

### 3. `src/xai/core/time_capsule_api.py`
**Purpose**: Time capsule API endpoints

**Test requirements**:
- Test capsule creation
- Test capsule retrieval
- Test unlock timing

---

## Priority 9: Utilities and Helpers (LOWER)

### 1. `src/xai/core/logging_config.py`
**Purpose**: Logging configuration

**Test requirements**:
- Test log level configuration
- Test log format
- Test file rotation

### 2. `src/xai/core/structured_logger.py`
**Purpose**: Structured logging output

**Test requirements**:
- Test JSON output format
- Test field inclusion
- Test context propagation

### 3. `src/xai/core/anonymous_logger.py`
**Purpose**: Privacy-preserving logging

**Test requirements**:
- Test PII stripping
- Test hash anonymization
- Test log retention

### 4. `src/xai/core/metrics.py` and `prometheus_metrics.py`
**Purpose**: Metrics collection

**Test requirements**:
- Test counter increments
- Test gauge updates
- Test histogram observations
- Test label handling

---

## Priority 10: Token Economics (LOWER)

### 1. `src/xai/core/xai_token_manager.py`
**Purpose**: Token management operations

**Test requirements**:
- Test minting
- Test burning
- Test transfer restrictions
- Test supply tracking

### 2. `src/xai/core/xai_token_vesting.py`
**Purpose**: Token vesting schedules

**Test requirements**:
- Test vesting schedule creation
- Test cliff handling
- Test linear unlock
- Test revocation

### 3. `src/xai/core/token_burning_engine.py`
**Purpose**: Automated token burning

**Test requirements**:
- Test burn triggers
- Test burn amounts
- Test burn verification

### 4. `src/xai/core/timelock_releases.py`
**Purpose**: Timelocked token releases

**Test requirements**:
- Test timelock creation
- Test release timing
- Test cancellation

---

## VM and EVM Tests

### 1. `src/xai/core/vm/precompiles.py`
**Purpose**: EVM precompiled contracts

**Test requirements**:
- Test ecrecover
- Test sha256
- Test ripemd160
- Test identity
- Test modexp
- Test ecAdd, ecMul, ecPairing

### 2. `src/xai/core/vm/tx_processor.py`
**Purpose**: Transaction processing in VM

**Test requirements**:
- Test gas calculation
- Test state changes
- Test revert handling
- Test event emission

### 3. `src/xai/core/vm/evm/stack.py`
**Purpose**: EVM stack implementation

**Test requirements**:
- Test push/pop
- Test stack limits (1024)
- Test overflow handling
- Test underflow handling

### 4. `src/xai/core/vm/evm/context.py`
**Purpose**: EVM execution context

**Test requirements**:
- Test context initialization
- Test call depth tracking
- Test gas accounting

---

## Test Categories

### Security Tests
Place in `tests/xai_tests/security/` for:
- Input validation
- Authentication bypass attempts
- Authorization checks
- Injection attacks
- Overflow/underflow

### Fuzz Tests
Place in `tests/xai_tests/fuzz/` for:
- Random input testing
- Boundary conditions
- Edge cases

### Property Tests
Place in `tests/xai_tests/property/` for:
- Invariant testing with Hypothesis
- Stateful testing
- Round-trip properties

### Integration Tests
Place in `tests/xai_tests/integration/` for:
- Multi-component interactions
- Network simulations
- Full workflow tests

---

## Running Tests

```bash
# Run all unit tests
pytest tests/xai_tests/unit/ -v

# Run with coverage report
pytest tests/xai_tests/unit/ --cov=src/xai --cov-report=html

# Run specific category
pytest tests/xai_tests/security/ -v

# Run tests matching pattern
pytest -k "test_security" -v

# Run with verbose output and show locals on failure
pytest -vvl --tb=long
```

---

## Checklist for Each Test Module

Before submitting tests, ensure:

- [ ] All public methods have at least one test
- [ ] Edge cases are covered
- [ ] Error conditions are tested
- [ ] Thread safety is tested (if applicable)
- [ ] Input validation is tested
- [ ] Each test has a descriptive docstring
- [ ] Tests are independent (no shared state)
- [ ] Fixtures properly clean up resources
- [ ] Tests run in < 1 second each (unless marked @pytest.mark.slow)

---

## Example: Complete Test File

See `tests/xai_tests/unit/test_wallet.py` for a well-structured example that covers:
- Initialization tests
- Core functionality tests
- Error handling tests
- Security tests
- File operation tests

---

## Contributing

When adding tests:

1. Create test file following naming convention
2. Add docstrings explaining test coverage
3. Run `pytest` to verify all tests pass
4. Run `pytest --cov` to verify coverage improved
5. Commit with message: `test(<module>): add tests for <feature>`
