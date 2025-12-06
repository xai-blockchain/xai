"""Tests for the blockchain-backed balance provider used in exchange settlements."""

from decimal import Decimal
import tempfile
import shutil
import pytest

from xai.core.exchange_wallet import ExchangeWalletManager
from xai.exchange import BlockchainBalanceProvider


class DummyBlockchain:
    """Minimal blockchain stub to capture settlement receipts."""

    def __init__(self):
        self.pending_transactions = []
        self.chain = []

    def add_transaction(self, tx):
        self.pending_transactions.append(tx)
        return True


@pytest.fixture()
def tmp_wallet_dir():
    path = tempfile.mkdtemp(prefix="wallet-test-")
    yield path
    shutil.rmtree(path, ignore_errors=True)


def _wallet_manager(tmp_wallet_dir):
    manager = ExchangeWalletManager(data_dir=tmp_wallet_dir)
    manager.deposit("alice", "USDT", 1000.0, deposit_type="test")
    return manager


def test_blockchain_balance_provider_records_receipts(tmp_wallet_dir):
    wallet_manager = _wallet_manager(tmp_wallet_dir)
    blockchain = DummyBlockchain()
    provider = BlockchainBalanceProvider(wallet_manager, blockchain)

    txid = provider.transfer(
        "alice",
        "bob",
        "USDT",
        Decimal("100.0"),
        context={"trade_id": "trade-123", "leg": "test_leg"},
    )

    assert txid is not None
    assert provider.verify_transfer(txid)
    assert blockchain.pending_transactions[0].metadata["asset"] == "USDT"

    alice_balance = wallet_manager.get_wallet("alice").get_total_balance("USDT")
    bob_balance = wallet_manager.get_wallet("bob").get_total_balance("USDT")
    assert alice_balance == Decimal("900.0")
    assert bob_balance == Decimal("100.0")


def test_blockchain_balance_provider_waits_for_confirmations(tmp_wallet_dir):
    wallet_manager = _wallet_manager(tmp_wallet_dir)
    blockchain = DummyBlockchain()
    provider = BlockchainBalanceProvider(
        wallet_manager,
        blockchain,
        confirmations_required=2,
    )

    txid = provider.transfer(
        "alice",
        "bob",
        "USDT",
        Decimal("50.0"),
        context={"trade_id": "trade-abc", "leg": "confirm_leg"},
    )
    assert txid

    # Move transaction from mempool to first block (only 1 confirmation)
    tx = blockchain.pending_transactions.pop()
    blockchain.chain.append({"transactions": [tx]})
    assert provider.verify_transfer(txid) is False

    # Append another block to satisfy confirmations
    blockchain.chain.append({"transactions": []})
    assert provider.verify_transfer(txid)
