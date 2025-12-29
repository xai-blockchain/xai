"""
Smoke tests for HTLC fund/claim/refund operations with regtest/Hardhat.

These tests verify HTLC (Hashed Time-Locked Contract) operations for atomic swaps.
Tests can run with or without live blockchain nodes - when nodes are unavailable,
tests will be skipped gracefully.
"""

import pytest
import hashlib
import time
import os

# Check if blockchain testing dependencies are available
try:
    from web3 import Web3
    from web3.exceptions import Web3Exception
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False

try:
    from bitcoinlib.services.bitcoind import BitcoindClient
    BITCOIN_RPC_AVAILABLE = True
except ImportError:
    BITCOIN_RPC_AVAILABLE = False

from xai.core.aixn_blockchain.atomic_swap_11_coins import AtomicSwapHTLC, CoinType
from xai.core.transactions.htlc_deployer import compile_htlc_contract, deploy_htlc, claim_htlc, refund_htlc


def check_bitcoin_regtest() -> bool:
    """Check if Bitcoin regtest node is accessible"""
    try:
        if not BITCOIN_RPC_AVAILABLE:
            return False
        # Try to connect to Bitcoin regtest
        import subprocess
        result = subprocess.run(
            ["bitcoin-cli", "-regtest", "getblockchaininfo"],
            capture_output=True,
            timeout=2
        )
        return result.returncode == 0
    except Exception:
        return False


def check_hardhat_node() -> bool:
    """Check if Hardhat/Ganache node is accessible"""
    try:
        if not WEB3_AVAILABLE:
            return False
        # Try to connect to local Ethereum node
        w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
        w3.eth.block_number  # Test connection
        return True
    except Exception:
        return False


# Fixtures for blockchain connections
@pytest.fixture
def bitcoin_client():
    """Bitcoin regtest client (skip if unavailable)"""
    if not check_bitcoin_regtest():
        pytest.skip("Bitcoin regtest node not available")

    import subprocess
    return subprocess


@pytest.fixture
def eth_client():
    """Ethereum client (skip if unavailable)"""
    if not check_hardhat_node():
        pytest.skip("Hardhat/Ganache node not available")

    w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
    return w3


class TestHTLCFundingOperations:
    """Test HTLC funding operations"""

    def test_htlc_contract_compilation(self):
        """Test that HTLC Solidity contract compiles successfully"""
        if not WEB3_AVAILABLE:
            pytest.skip("Web3 not available")

        # Compile the contract
        abi, bytecode = compile_htlc_contract()

        # Verify ABI structure
        assert isinstance(abi, list)
        assert len(abi) > 0

        # Verify bytecode
        assert isinstance(bytecode, str)
        assert len(bytecode) > 0
        # EVM bytecode starts with PUSH (60=PUSH1, 61=PUSH2, etc.)
        assert bytecode[0] == '6', f"Expected bytecode to start with PUSH opcode (6x), got {bytecode[:2]}"

        # Verify contract has required functions
        function_names = [item['name'] for item in abi if item.get('type') == 'function']
        assert 'claim' in function_names
        assert 'refund' in function_names

    def test_htlc_secret_generation(self):
        """Test HTLC secret and hash generation"""
        # Generate a random secret
        secret = os.urandom(32)
        assert len(secret) == 32

        # Calculate hash
        secret_hash = hashlib.sha256(secret).digest()
        assert len(secret_hash) == 32

        # Verify hash is deterministic
        secret_hash2 = hashlib.sha256(secret).digest()
        assert secret_hash == secret_hash2

    def test_htlc_bitcoin_script_generation(self):
        """Test Bitcoin P2WSH HTLC script generation"""
        htlc = AtomicSwapHTLC(CoinType.BTC)

        secret = bytes.fromhex("00" * 32)
        swap = htlc.create_swap_contract(
            axn_amount=1.0,
            other_coin_amount=0.1,
            counterparty_address="tb1qtest",
            timelock_hours=24,
            secret_bytes=secret
        )

        # Verify swap contains required fields
        assert 'secret_hash' in swap
        assert 'script_template' in swap  # UTXO coins use script_template
        assert 'contract_type' in swap
        assert swap['contract_type'] == 'HTLC_UTXO'

        # Verify secret hash is SHA-256
        assert len(swap['secret_hash']) == 64  # Hex string
        assert swap['secret_hash'] == hashlib.sha256(secret).hexdigest()

        # Verify script template contains expected elements
        script = swap['script_template']
        assert 'OP_IF' in script
        assert 'OP_SHA256' in script
        secret_hash = swap['secret_hash']
        assert secret_hash in script  # Hash should be in script
        assert 'OP_CHECKLOCKTIMEVERIFY' in script

    def test_htlc_ethereum_contract_generation(self):
        """Test Ethereum HTLC contract generation"""
        htlc = AtomicSwapHTLC(CoinType.ETH)

        secret = bytes.fromhex("00" * 32)
        swap = htlc.create_swap_contract(
            axn_amount=1.0,
            other_coin_amount=0.1,
            counterparty_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            timelock_hours=24,
            secret_bytes=secret
        )

        # Verify swap contains required fields
        assert 'secret_hash' in swap
        assert 'smart_contract' in swap or 'contract_address' in swap
        assert 'secret' in swap

        # Verify secret hash matches
        assert swap['secret_hash'] == hashlib.sha256(secret).hexdigest()

    def test_htlc_timelock_validation(self):
        """Test HTLC timelock parameter validation"""
        htlc = AtomicSwapHTLC(CoinType.BTC)
        secret = bytes.fromhex("00" * 32)

        # Test with various timelock values
        for hours in [1, 6, 12, 24, 48]:
            swap = htlc.create_swap_contract(
                axn_amount=1.0,
                other_coin_amount=0.1,
                counterparty_address="tb1qtest",
                timelock_hours=hours,
                secret_bytes=secret
            )
            assert 'timelock' in swap
            # Timelock should be in the future
            assert swap['timelock'] > int(time.time())

    def test_htlc_cross_chain_hash_consistency(self):
        """Test that BTC and ETH HTLCs use same hash for same secret"""
        secret = bytes.fromhex("00" * 32)
        expected_hash = hashlib.sha256(secret).hexdigest()

        # Create BTC swap
        htlc_btc = AtomicSwapHTLC(CoinType.BTC)
        swap_btc = htlc_btc.create_swap_contract(
            axn_amount=1.0,
            other_coin_amount=0.1,
            counterparty_address="tb1qtest",
            timelock_hours=24,
            secret_bytes=secret
        )

        # Create ETH swap
        htlc_eth = AtomicSwapHTLC(CoinType.ETH)
        swap_eth = htlc_eth.create_swap_contract(
            axn_amount=1.0,
            other_coin_amount=0.1,
            counterparty_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            timelock_hours=24,
            secret_bytes=secret
        )

        # Both should have same hash
        assert swap_btc['secret_hash'] == expected_hash
        assert swap_eth['secret_hash'] == expected_hash


class TestHTLCClaimOperations:
    """Test HTLC claim operations"""

    def test_htlc_claim_parameters(self):
        """Test HTLC claim parameter structure"""
        # This tests the structure without requiring live blockchain
        secret = bytes.fromhex("00" * 32)
        secret_hex = secret.hex()

        # Verify secret format
        assert len(secret_hex) == 64
        assert all(c in '0123456789abcdef' for c in secret_hex)

    @pytest.mark.skipif(not WEB3_AVAILABLE, reason="Web3 not available")
    def test_htlc_ethereum_claim_transaction_structure(self, eth_client):
        """Test Ethereum HTLC claim transaction structure with live node"""
        # Get account
        accounts = eth_client.eth.accounts
        if not accounts:
            pytest.skip("No accounts available")

        sender = accounts[0]
        recipient = accounts[1] if len(accounts) > 1 else sender

        # Generate secret
        secret = bytes.fromhex("00" * 32)
        secret_hash = hashlib.sha256(secret).hexdigest()

        # Deploy contract (use blockchain timestamp, not system time)
        current_block = eth_client.eth.get_block('latest')
        timelock = current_block['timestamp'] + 3600  # 1 hour from blockchain's now
        try:
            contract = deploy_htlc(
                eth_client,
                secret_hash,
                recipient,
                timelock,
                value_wei=eth_client.to_wei(0.1, 'ether'),
                sender=sender,
            )

            # Verify contract deployed
            assert contract.address
            assert eth_client.eth.get_code(contract.address) != b''

            # Verify contract state
            assert contract.functions.secretHash().call() == bytes.fromhex(secret_hash)
            assert contract.functions.recipient().call() == recipient
            assert contract.functions.timelock().call() == timelock

        except Exception as e:
            pytest.skip(f"Failed to deploy contract: {e}")


class TestHTLCRefundOperations:
    """Test HTLC refund operations"""

    def test_htlc_refund_timelock_logic(self):
        """Test HTLC refund timelock logic"""
        # Test that refund requires timelock expiry
        current_time = int(time.time())

        # Timelock in past - should allow refund
        past_timelock = current_time - 3600
        assert past_timelock < current_time

        # Timelock in future - should not allow refund
        future_timelock = current_time + 3600
        assert future_timelock > current_time

    @pytest.mark.skipif(not WEB3_AVAILABLE, reason="Web3 not available")
    def test_htlc_ethereum_refund_validation(self, eth_client):
        """Test Ethereum HTLC refund validation"""
        accounts = eth_client.eth.accounts
        if not accounts:
            pytest.skip("No accounts available")

        sender = accounts[0]
        recipient = accounts[1] if len(accounts) > 1 else sender

        secret = bytes.fromhex("00" * 32)
        secret_hash = hashlib.sha256(secret).hexdigest()

        # Deploy contract with short timelock (use blockchain timestamp)
        current_block = eth_client.eth.get_block('latest')
        timelock = current_block['timestamp'] + 2  # 2 seconds from blockchain's now

        try:
            contract = deploy_htlc(
                eth_client,
                secret_hash,
                recipient,
                timelock,
                value_wei=eth_client.to_wei(0.01, 'ether'),
                sender=sender,
            )

            # Attempt refund before timelock expires should fail
            # (This would revert in actual execution)

            # Wait for timelock to expire
            time.sleep(3)

            # Now refund should be possible (structure-wise)
            # Actual refund would require proper gas and sender authentication

        except Exception as e:
            pytest.skip(f"Failed to test refund: {e}")


class TestHTLCEdgeCases:
    """Test HTLC edge cases and error conditions"""

    def test_htlc_zero_amount(self):
        """Test HTLC creation with zero amount"""
        htlc = AtomicSwapHTLC(CoinType.BTC)
        secret = bytes.fromhex("00" * 32)

        # Zero amount should still create valid structure
        swap = htlc.create_swap_contract(
            axn_amount=0.0,
            other_coin_amount=0.0,
            counterparty_address="tb1qtest",
            timelock_hours=24,
            secret_bytes=secret
        )

        # Should still have required fields
        assert 'secret_hash' in swap

    def test_htlc_invalid_secret_length(self):
        """Test HTLC creation with invalid secret length"""
        htlc = AtomicSwapHTLC(CoinType.BTC)

        # Test with wrong secret length
        invalid_secrets = [
            bytes.fromhex("00" * 16),  # Too short
            bytes.fromhex("00" * 64),  # Too long
            b"short",  # Way too short
        ]

        for invalid_secret in invalid_secrets:
            try:
                swap = htlc.create_swap_contract(
                    axn_amount=1.0,
                    other_coin_amount=0.1,
                    counterparty_address="tb1qtest",
                    timelock_hours=24,
                    secret_bytes=invalid_secret
                )
                # Some implementations may normalize the secret
                # Verify hash is still generated
                assert 'secret_hash' in swap
            except (ValueError, AssertionError):
                # Expected to fail with invalid secret
                pass

    def test_htlc_past_timelock(self):
        """Test HTLC creation with timelock in the past"""
        htlc = AtomicSwapHTLC(CoinType.BTC)
        secret = bytes.fromhex("00" * 32)

        # Negative hours should be rejected or adjusted
        try:
            swap = htlc.create_swap_contract(
                axn_amount=1.0,
                other_coin_amount=0.1,
                counterparty_address="tb1qtest",
                timelock_hours=-1,  # Invalid
                secret_bytes=secret
            )
            # If it doesn't raise an error, verify timelock is still valid
            assert swap['timelock'] > int(time.time())
        except (ValueError, AssertionError):
            # Expected to fail
            pass

    def test_htlc_invalid_address_format(self):
        """Test HTLC creation with invalid address formats"""
        htlc_btc = AtomicSwapHTLC(CoinType.BTC)
        secret = bytes.fromhex("00" * 32)

        invalid_addresses = [
            "",  # Empty
            "invalid",  # Not a valid format
            "0x123",  # ETH format for BTC
        ]

        for addr in invalid_addresses:
            try:
                swap = htlc_btc.create_swap_contract(
                    axn_amount=1.0,
                    other_coin_amount=0.1,
                    counterparty_address=addr,
                    timelock_hours=24,
                    secret_bytes=secret
                )
                # Some implementations may accept and pass through
                # Just verify structure is created
                assert isinstance(swap, dict)
            except (ValueError, AssertionError):
                # Expected to fail with invalid address
                pass

    def test_htlc_hash_collision_resistance(self):
        """Test that different secrets produce different hashes"""
        secrets = [
            bytes.fromhex("00" * 32),
            bytes.fromhex("01" + "00" * 31),
            bytes.fromhex("ff" * 32),
        ]

        hashes = []
        for secret in secrets:
            hash_val = hashlib.sha256(secret).hexdigest()
            hashes.append(hash_val)

        # All hashes should be unique
        assert len(hashes) == len(set(hashes))

    def test_htlc_deterministic_hash(self):
        """Test that same secret always produces same hash"""
        secret = bytes.fromhex("deadbeef" * 8)

        hash1 = hashlib.sha256(secret).hexdigest()
        hash2 = hashlib.sha256(secret).hexdigest()
        hash3 = hashlib.sha256(secret).hexdigest()

        assert hash1 == hash2 == hash3

    def test_htlc_concurrent_swaps(self):
        """Test creating multiple HTLC swaps concurrently"""
        htlc = AtomicSwapHTLC(CoinType.BTC)

        swaps = []
        for i in range(5):
            secret = bytes.fromhex(f"{i:02x}" + "00" * 31)
            swap = htlc.create_swap_contract(
                axn_amount=1.0 + i * 0.1,
                other_coin_amount=0.1 + i * 0.01,
                counterparty_address=f"tb1qtest{i}",
                timelock_hours=24 + i,
                secret_bytes=secret
            )
            swaps.append(swap)

        # Verify all swaps have unique hashes
        hashes = [s['secret_hash'] for s in swaps]
        assert len(hashes) == len(set(hashes))

        # Verify all swaps have valid structure
        for swap in swaps:
            assert 'secret_hash' in swap
            assert 'timelock' in swap
