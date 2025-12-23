# Smart Contract Security Guide

This guide covers security best practices for developing and deploying smart contracts on the XAI blockchain. XAI provides a Python-based EVM-compatible environment with comprehensive security features for DeFi protocols, token standards, and decentralized applications.

## Table of Contents

- [Core Security Principles](#core-security-principles)
- [Access Control](#access-control)
- [Arithmetic Safety](#arithmetic-safety)
- [Reentrancy Protection](#reentrancy-protection)
- [Contract Upgradability](#contract-upgradability)
- [DeFi Security Patterns](#defi-security-patterns)
- [Testing and Auditing](#testing-and-auditing)

## Core Security Principles

### 1. Checks-Effects-Interactions Pattern

Always follow this pattern to prevent reentrancy attacks:

```python
def withdraw(self, caller: str, amount: int) -> bool:
    # CHECKS: Validate inputs and conditions
    if amount <= 0:
        raise VMExecutionError("Amount must be positive")

    balance = self.balances.get(caller, 0)
    if amount > balance:
        raise VMExecutionError("Insufficient balance")

    # EFFECTS: Update state before external calls
    self.balances[caller] = balance - amount
    self.total_supply -= amount

    # INTERACTIONS: External calls last
    self._transfer_native(self.address, caller, amount)

    return True
```

**Why this matters:** External calls can trigger malicious code. By updating state first, you prevent reentrancy attacks where the attacker calls back into your contract before state changes complete.

### 2. Input Validation

Validate all inputs before processing:

```python
from ..core.input_validation_schemas import validate_address, validate_amount

def transfer(self, from_addr: str, to_addr: str, amount: int) -> bool:
    # Validate addresses
    validate_address(from_addr, "from_address")
    validate_address(to_addr, "to_address")

    # Validate amount
    validate_amount(amount, "transfer_amount", min_value=1)

    # Additional business logic validation
    if from_addr == to_addr:
        raise VMExecutionError("Cannot transfer to self")

    # Proceed with transfer...
```

### 3. Fail-Fast Principle

Reject invalid states immediately with clear error messages:

```python
def stake(self, caller: str, amount: int) -> bool:
    # Explicit validation
    SafeMath.require_positive(amount, "stake_amount")
    SafeMath.require_lte(amount, self.max_stake_per_user, "stake_amount", "max_stake")

    # Early return on edge cases
    if amount == 0:
        return True  # No-op for zero amount

    # Continue with staking logic...
```

## Access Control

XAI provides cryptographic access control using ECDSA signatures. **Never** rely on address string matching alone.

### Signature-Based Authentication

```python
from ..core.defi.access_control import AccessControl, SignedRequest

class MyContract:
    def __init__(self, owner: str):
        self.owner = owner
        self.access_control = AccessControl()

    def privileged_operation(self, request: SignedRequest, params: dict) -> bool:
        """
        Only callable by owner with valid signature.

        Args:
            request: Cryptographically signed request proving ownership
            params: Operation parameters
        """
        # Verify caller has owner's private key
        self.access_control.verify_caller_simple(request, self.owner)

        # Proceed with privileged operation
        return self._execute_privileged_operation(params)
```

### Role-Based Access Control (RBAC)

For contracts with multiple permission levels:

```python
from ..core.defi.access_control import RoleBasedAccessControl, Role, SignedRequest

class DeFiProtocol:
    def __init__(self, admin: str):
        self.rbac = RoleBasedAccessControl(admin_address=admin)

    def grant_price_feeder_role(self, admin_request: SignedRequest, feeder: str) -> bool:
        """Grant price oracle role."""
        return self.rbac.grant_role(admin_request, Role.PRICE_FEEDER.value, feeder)

    def update_price(self, feeder_request: SignedRequest, asset: str, price: int) -> bool:
        """Update oracle price (price feeders only)."""
        # Verify caller has PRICE_FEEDER role with valid signature
        self.rbac.verify_role_simple(feeder_request, Role.PRICE_FEEDER.value)

        # Update price
        self.prices[asset] = price
        return True
```

**Security properties:**
- ECDSA signature verification prevents impersonation
- Nonce tracking prevents replay attacks
- Timestamp validation prevents stale requests
- Audit trail for all privileged operations

## Arithmetic Safety

XAI provides `SafeMath` to prevent integer overflow/underflow vulnerabilities.

### Basic Operations

```python
from ..core.defi.safe_math import SafeMath, MAX_SUPPLY, MAX_DEBT

def deposit(self, caller: str, amount: int) -> bool:
    # Safe addition with overflow protection
    current_balance = self.balances.get(caller, 0)
    new_balance = SafeMath.safe_add(
        current_balance,
        amount,
        MAX_SUPPLY,
        "user_balance"
    )

    # Safe subtraction with underflow protection
    remaining = SafeMath.safe_sub(
        self.available_liquidity,
        amount,
        "available_liquidity"
    )

    self.balances[caller] = new_balance
    self.available_liquidity = remaining
    return True
```

### Fixed-Point Arithmetic

For DeFi calculations requiring precision:

```python
from ..core.defi.safe_math import SafeMath, WAD, RAY

def calculate_interest(self, principal: int, rate: int, time: int) -> int:
    """
    Calculate interest using WAD (18 decimal) precision.

    Args:
        principal: Principal amount in WAD
        rate: Annual rate in WAD (e.g., 0.05e18 for 5%)
        time: Time in seconds

    Returns:
        Interest amount in WAD
    """
    # interest = principal * rate * time / SECONDS_PER_YEAR
    temp = SafeMath.wad_mul(principal, rate)
    temp = SafeMath.safe_mul(temp, time, MAX_DEBT, "interest_calc")
    interest = SafeMath.safe_div(temp, 31536000, "interest")  # seconds per year

    return interest
```

### Percentage Calculations

```python
from ..core.defi.safe_math import SafeMath, BASIS_POINTS

def calculate_fee(self, amount: int, fee_bp: int) -> int:
    """
    Calculate fee in basis points.

    Args:
        amount: Transaction amount
        fee_bp: Fee in basis points (e.g., 30 = 0.3%)

    Returns:
        Fee amount
    """
    return SafeMath.percentage(amount, fee_bp)

# Example: 0.3% fee on 1000 tokens
fee = self.calculate_fee(1000 * WAD, 30)  # Returns 3 * WAD
```

## Reentrancy Protection

XAI flash loans demonstrate defense-in-depth reentrancy protection:

### Single Lock Pattern

```python
import threading
from dataclasses import field

class SecureContract:
    _execution_lock: threading.Lock = field(default_factory=threading.Lock)
    _reentrancy_guard: dict = field(default_factory=dict)

    def critical_operation(self, caller: str, amount: int) -> bool:
        # Defense layer 1: Explicit reentrancy guard
        self._require_no_reentry(caller)

        try:
            # Defense layer 2: Hold lock for entire operation
            with self._execution_lock:
                # CHECKS
                self._validate_inputs(caller, amount)

                # EFFECTS (state changes before external calls)
                balance_before = self.balances[caller]
                self.balances[caller] -= amount

                # INTERACTIONS (external calls)
                self._external_call(caller, amount)

                # VERIFICATION (post-call checks)
                balance_after = self.balances[caller]
                assert balance_after == balance_before - amount

                return True
        finally:
            # Clear guard after lock is released
            self._clear_reentry_guard(caller)

    def _require_no_reentry(self, caller: str) -> None:
        if self._reentrancy_guard.get(caller, False):
            raise VMExecutionError(f"Reentrancy detected: {caller}")
        self._reentrancy_guard[caller] = True

    def _clear_reentry_guard(self, caller: str) -> None:
        self._reentrancy_guard[caller] = False
```

### Flash Loan Security

XAI's flash loan implementation shows production-grade reentrancy protection:

```python
# From src/xai/core/defi/flash_loans.py

def flash_loan(self, borrower: str, receiver: str, assets: List[str],
               amounts: List[int], callback: Callable) -> bool:
    """
    Flash loan with comprehensive security checks.
    """
    # Check reentrancy FIRST (outside lock)
    self._require_no_reentry(borrower)

    try:
        with self._execution_lock:  # Hold lock for ENTIRE operation
            # Record balances before
            balances_before = {asset: self.liquidity_pools[asset] for asset in assets}

            # EFFECTS: Update state
            loan_id = self._create_loan_record(borrower, assets, amounts)
            for asset, amount in zip(assets, amounts):
                self.liquidity_pools[asset] -= amount

            # INTERACTIONS: External callback
            callback(borrower, assets, amounts, fee_amounts, params)

            # VERIFICATION: Ensure repayment
            for asset, amount, fee in zip(assets, amounts, fee_amounts):
                current = self.liquidity_pools[asset]
                required = balances_before[asset] + fee

                if current < required:
                    raise VMExecutionError(
                        f"Flash loan not repaid: {asset} "
                        f"expected {required}, got {current}"
                    )

            return True
    finally:
        self._clear_reentry_guard(borrower)
```

## Contract Upgradability

XAI supports multiple proxy patterns for safe contract upgrades.

### Transparent Proxy (EIP-1967)

```python
from ..core.contracts.proxy import TransparentProxy

# Deploy proxy
proxy = TransparentProxy(
    admin="0xAdminAddress",
    implementation="0xImplementationV1"
)

# Upgrade to V2 (admin only)
proxy.upgrade_to(
    caller="0xAdminAddress",
    new_implementation="0xImplementationV2",
    data=initialization_calldata  # Optional
)

# Admin cannot call implementation functions (safety feature)
# Non-admin calls are delegated to implementation
```

### UUPS Proxy (Upgrade Logic in Implementation)

```python
from ..core.contracts.proxy import UUPSProxy, UUPSImplementation

class MyImplementation(UUPSImplementation):
    def __init__(self, owner: str):
        self.owner = owner

    def authorize_upgrade(self, caller: str, new_impl: str) -> bool:
        # Custom authorization logic
        if caller != self.owner:
            return False

        # Additional validation (e.g., verify new implementation is valid)
        if not self._is_valid_implementation(new_impl):
            return False

        return True

# Deploy UUPS proxy
proxy = UUPSProxy(implementation="0xMyImplementation")

# Upgrade (authorization in implementation)
proxy.upgrade_to(
    caller="0xOwner",
    new_implementation="0xNewImplementation",
    authorize_upgrade=implementation.authorize_upgrade
)
```

### Beacon Proxy (Shared Upgrades)

```python
from ..core.contracts.proxy import UpgradeableBeacon, BeaconProxy

# Deploy beacon
beacon = UpgradeableBeacon(
    owner="0xOwner",
    implementation="0xTokenImplementation"
)

# Deploy multiple proxies using same beacon
token1 = BeaconProxy(beacon=beacon.address)
token2 = BeaconProxy(beacon=beacon.address)
token3 = BeaconProxy(beacon=beacon.address)

# Single upgrade affects all proxies
beacon.upgrade_to(
    caller="0xOwner",
    new_implementation="0xTokenImplementationV2"
)
# Now token1, token2, token3 all use V2 implementation
```

## DeFi Security Patterns

### Oracle Manipulation Protection

```python
from ..blockchain.twap_oracle import TWAPOracle

class DeFiProtocol:
    def __init__(self):
        # Use TWAP (Time-Weighted Average Price) oracle
        self.oracle = TWAPOracle(window_size=3600)  # 1 hour TWAP

    def get_safe_price(self, asset: str) -> int:
        """Get manipulation-resistant price."""
        # TWAP is resistant to flash loan price manipulation
        return self.oracle.get_twap(asset)
```

### Flash Loan Protection

```python
from ..blockchain.flash_loan_protection import FlashLoanProtector

class LendingPool:
    def __init__(self):
        self.flash_loan_protector = FlashLoanProtector()

    def borrow(self, caller: str, amount: int) -> bool:
        # Detect if caller is currently executing flash loan
        if self.flash_loan_protector.is_flash_loan_active(caller):
            raise VMExecutionError("Flash loan exploitation attempt detected")

        # Proceed with normal borrow
        return self._process_borrow(caller, amount)
```

### Circuit Breaker

```python
from ..core.defi.circuit_breaker import CircuitBreaker

class Exchange:
    def __init__(self):
        self.circuit_breaker = CircuitBreaker(
            threshold_percent=10,  # Trip if 10% price change
            cooldown_period=300    # 5 minute cooldown
        )

    def execute_trade(self, pair: str, amount: int, price: int) -> bool:
        # Check if circuit breaker is tripped
        if not self.circuit_breaker.is_operational(pair):
            raise VMExecutionError(f"Trading halted for {pair}: circuit breaker tripped")

        # Check for excessive price movement
        if not self.circuit_breaker.check_price_change(pair, price):
            raise VMExecutionError(f"Excessive price movement detected for {pair}")

        # Execute trade
        return self._process_trade(pair, amount, price)
```

### Front-Running Protection

```python
from ..blockchain.front_running_protection import FrontRunningProtector

class DEX:
    def __init__(self):
        self.fr_protector = FrontRunningProtector()

    def swap(self, caller: str, amount_in: int, min_amount_out: int, deadline: int) -> bool:
        # Verify deadline hasn't passed
        if time.time() > deadline:
            raise VMExecutionError("Transaction expired")

        # Calculate expected output
        amount_out = self._calculate_output(amount_in)

        # Enforce slippage tolerance
        if amount_out < min_amount_out:
            raise VMExecutionError(
                f"Slippage exceeded: expected {min_amount_out}, got {amount_out}"
            )

        # Commit-reveal or fair ordering can be added here
        return self._execute_swap(caller, amount_in, amount_out)
```

## Testing and Auditing

### Comprehensive Test Coverage

```python
# tests/test_lending.py

import pytest
from xai.core.defi.lending import LendingPool
from xai.core.vm.exceptions import VMExecutionError

class TestLendingPool:
    def test_deposit_overflow_protection(self):
        """Test SafeMath prevents overflow attacks."""
        pool = LendingPool()

        # Attempt to overflow total supply
        with pytest.raises(VMExecutionError, match="overflow"):
            pool.deposit("0xAttacker", MAX_SUPPLY + 1)

    def test_withdraw_reentrancy_protection(self):
        """Test reentrancy guard prevents attacks."""
        pool = LendingPool()
        pool.deposit("0xUser", 1000)

        # Attempt reentrancy attack
        with pytest.raises(VMExecutionError, match="Reentrancy"):
            pool._simulate_reentrant_withdraw("0xUser", 500)

    def test_access_control_signature_required(self):
        """Test privileged functions require valid signatures."""
        pool = LendingPool(admin="0xAdmin")

        # Invalid signature should fail
        fake_request = SignedRequest(
            address="0xAttacker",
            signature="0x" + "00" * 64,
            message="malicious",
            timestamp=int(time.time()),
            nonce=1,
            public_key="0x" + "00" * 64
        )

        with pytest.raises(VMExecutionError, match="invalid signature"):
            pool.pause(fake_request)
```

### Security Checklist

Before deploying contracts to mainnet:

- [ ] **Access Control**: All privileged functions use signature verification
- [ ] **Arithmetic**: All calculations use `SafeMath` with appropriate bounds
- [ ] **Reentrancy**: Critical functions use locks and follow checks-effects-interactions
- [ ] **Input Validation**: All external inputs are validated
- [ ] **Oracle Security**: Price feeds use TWAP or other manipulation-resistant methods
- [ ] **Flash Loan Protection**: Lending/borrowing protected against flash loan attacks
- [ ] **Circuit Breakers**: Emergency pause mechanisms in place
- [ ] **Upgrade Safety**: Proxy patterns properly implemented with admin controls
- [ ] **Test Coverage**: >90% code coverage with security-focused tests
- [ ] **Audit**: External security audit completed

### Running Security Scans

XAI includes automated security scanning in CI:

```bash
# Run Bandit (Python security scanner)
bandit -r src/ -ll

# Run Semgrep (static analysis)
semgrep --config p/security-audit --config p/python src/

# Run pytest with coverage
pytest tests/ -v --cov=src --cov-report=html

# Check for known vulnerabilities
pip-audit
```

## Common Vulnerabilities

### ❌ DON'T: String-based access control

```python
# VULNERABLE: String comparison can be bypassed
def admin_function(self, caller: str):
    if caller == self.owner:  # WRONG!
        # Attacker can just pass owner's address string
```

### ✅ DO: Cryptographic access control

```python
# SECURE: Requires private key proof
def admin_function(self, request: SignedRequest):
    self.access_control.verify_caller_simple(request, self.owner)
```

### ❌ DON'T: Unchecked arithmetic

```python
# VULNERABLE: Can overflow
def transfer(self, to: str, amount: int):
    self.balances[to] = self.balances[to] + amount  # WRONG!
```

### ✅ DO: SafeMath operations

```python
# SECURE: Overflow protected
def transfer(self, to: str, amount: int):
    current = self.balances.get(to, 0)
    self.balances[to] = SafeMath.safe_add(current, amount, MAX_SUPPLY, "balance")
```

### ❌ DON'T: External calls before state changes

```python
# VULNERABLE: Reentrancy attack
def withdraw(self, amount: int):
    self._send_tokens(msg.sender, amount)  # WRONG ORDER!
    self.balances[msg.sender] -= amount
```

### ✅ DO: Checks-Effects-Interactions

```python
# SECURE: State updated first
def withdraw(self, amount: int):
    # CHECKS
    if amount > self.balances[msg.sender]:
        raise VMExecutionError("Insufficient balance")

    # EFFECTS
    self.balances[msg.sender] -= amount

    # INTERACTIONS
    self._send_tokens(msg.sender, amount)
```

## Resources

- **XAI Examples**: `/src/xai/core/defi/` - Production-grade DeFi implementations
- **Security Scanning**: See `docs/security/audits.md` for CI/CD security tools
- **Wallet Security**: See `docs/security/wallets.md` for key management
- **OpenZeppelin Patterns**: https://docs.openzeppelin.com/contracts/
- **SWC Registry**: https://swcregistry.io/ - Smart contract weakness classification

---

**Last Updated**: January 2025
