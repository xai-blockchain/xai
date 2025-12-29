import os
import sys
import shutil
import tempfile
from pathlib import Path
from decimal import Decimal

import pytest

# Ensure both the project root (for namespace-style imports like `src.xai`) and
# the src directory (for `xai.*`) are on the Python path before collection runs.
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Add stubs directory to path for test stubs
stubs = Path(__file__).parent / "stubs"
if stubs.exists():
    sys.path.insert(0, str(stubs))


@pytest.fixture
def temp_blockchain_dir():
    """Create a temporary directory for blockchain data during tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def blockchain(temp_blockchain_dir):
    """Create a clean blockchain instance for testing"""
    from xai.core.blockchain import Blockchain

    return Blockchain(data_dir=temp_blockchain_dir)


# Security Testing Fixtures

@pytest.fixture
def security_validator():
    """Create a SecurityValidator instance for testing"""
    from xai.core.security.security_validation import SecurityValidator
    return SecurityValidator()


@pytest.fixture
def transaction_validator(blockchain):
    """Create a TransactionValidator instance for testing"""
    from xai.core.consensus.transaction_validator import TransactionValidator
    return TransactionValidator(blockchain)


@pytest.fixture
def funded_wallet(blockchain):
    """Create a wallet with funds for testing"""
    from xai.core.wallet import Wallet
    wallet = Wallet()
    blockchain.mine_pending_transactions(wallet.address)
    return wallet


@pytest.fixture
def funded_wallets(blockchain):
    """Create multiple wallets with funds for testing"""
    from xai.core.wallet import Wallet
    wallets = []
    for _ in range(3):
        wallet = Wallet()
        blockchain.mine_pending_transactions(wallet.address)
        wallets.append(wallet)
    return wallets


@pytest.fixture
def attack_simulator():
    """Create an AttackSimulator instance for testing"""
    from tests.xai_tests.security.security_test_utils import AttackSimulator
    return AttackSimulator()


@pytest.fixture
def malicious_input_generator():
    """Create a MaliciousInputGenerator instance for testing"""
    from tests.xai_tests.security.security_test_utils import MaliciousInputGenerator
    return MaliciousInputGenerator()


@pytest.fixture
def mock_attacker():
    """Create a MockAttacker instance for testing"""
    from tests.xai_tests.security.security_test_utils import MockAttacker
    return MockAttacker()


@pytest.fixture
def reorganization_protection(temp_blockchain_dir):
    """Create a ReorganizationProtection instance for testing"""
    import os
    from xai.core.security.blockchain_security import ReorganizationProtection
    reorg = ReorganizationProtection()
    reorg.checkpoint_file = os.path.join(temp_blockchain_dir, "checkpoints.json")
    return reorg


@pytest.fixture
def supply_validator():
    """Create a SupplyValidator instance for testing"""
    from xai.core.security.blockchain_security import SupplyValidator
    return SupplyValidator()


@pytest.fixture
def overflow_protection():
    """Create an OverflowProtection instance for testing"""
    from xai.core.security.blockchain_security import OverflowProtection
    return OverflowProtection()


@pytest.fixture
def mempool_manager():
    """Create a MempoolManager instance for testing"""
    from xai.core.security.blockchain_security import MempoolManager
    return MempoolManager()


@pytest.fixture
def p2p_security_manager():
    """Create a P2PSecurityManager instance for testing"""
    from xai.core.security.p2p_security import P2PSecurityManager
    return P2PSecurityManager()


@pytest.fixture
def peer_reputation():
    """Create a PeerReputation instance for testing"""
    from xai.core.security.p2p_security import PeerReputation
    return PeerReputation()


@pytest.fixture
def message_rate_limiter():
    """Create a MessageRateLimiter instance for testing"""
    from xai.core.security.p2p_security import MessageRateLimiter
    return MessageRateLimiter()


@pytest.fixture
def prefund_exchange_accounts():
    """
    Provide deterministic funding for MatchingEngine tests by seeding balances
    in the in-memory provider prior to settlement attempts.
    """

    def _prefund(engine, allocations):
        provider = getattr(engine, "balance_provider", None)
        if provider is None or not hasattr(provider, "set_balance"):
            raise AssertionError("MatchingEngine balance provider cannot be pre-funded")
        for address, assets in allocations.items():
            for asset, amount in assets.items():
                value = amount if isinstance(amount, Decimal) else Decimal(str(amount))
                provider.set_balance(address, asset, value)
        return provider

    return _prefund
