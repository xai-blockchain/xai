from pathlib import Path

import pytest

from xai.core.crypto_deposit_manager import CryptoDepositManager


class DummyExchangeWalletManager:
    """Deterministic stub for exchange wallet interactions."""

    def __init__(self):
        self.deposits = []

    def deposit(self, user_address, currency, amount, deposit_type="manual", tx_hash=None):
        tx_id = f"deposit_tx_{len(self.deposits) + 1}"
        record = {
            "user_address": user_address,
            "currency": currency,
            "amount": amount,
            "deposit_type": deposit_type,
            "tx_hash": tx_hash,
            "tx_id": tx_id,
        }
        self.deposits.append(record)
        return {"success": True, "transaction": {"id": tx_id}, "new_balance": amount}


def create_manager(tmp_path: Path):
    wallet = DummyExchangeWalletManager()
    manager = CryptoDepositManager(wallet, data_dir=str(tmp_path))
    return manager, wallet


def test_generate_deposit_address_persists(tmp_path):
    manager, _ = create_manager(tmp_path)
    result = manager.generate_deposit_address("user1", "btc")
    assert result["success"] is True
    assert result["currency"] == "BTC"
    addresses = manager.get_user_deposit_addresses("user1")
    assert len(addresses) == 1
    assert addresses[0]["required_confirmations"] == 6

    # Reload manager to ensure persistence
    reloaded = CryptoDepositManager(DummyExchangeWalletManager(), data_dir=str(tmp_path))
    reloaded_addresses = reloaded.get_user_deposit_addresses("user1")
    assert reloaded_addresses == addresses


def test_record_and_confirm_deposit_creates_wallet_credit(tmp_path):
    manager, wallet = create_manager(tmp_path)
    addr = manager.generate_deposit_address("user-wallet", "btc")["deposit_address"]
    tx_hash = "abcd" * 16
    amount = 0.75

    pending = manager.record_blockchain_deposit(
        user_address="user-wallet",
        currency="btc",
        amount=amount,
        tx_hash=tx_hash,
        deposit_address=addr,
        confirmations=2,
        metadata={"source": "watcher"},
    )
    assert pending["success"] is True
    assert pending["status"] == "pending"
    assert len(manager.get_pending_deposits("user-wallet")) == 1

    update = manager.update_confirmations(tx_hash, 6)
    assert update["status"] == "credited"
    assert not manager.get_pending_deposits("user-wallet")
    history = manager.get_deposit_history("user-wallet")
    assert len(history) == 1
    assert history[0]["status"] == "credited"
    assert wallet.deposits[-1]["amount"] == amount
    assert wallet.deposits[-1]["deposit_type"] == "crypto"

    stats = manager.get_stats()
    assert stats["confirmed_deposits"] == 1
    assert pytest.approx(stats["confirmed_volume"]) == amount
    assert stats["credited_deposits"] == 1


def test_rejects_unknown_deposit_address(tmp_path):
    manager, _ = create_manager(tmp_path)
    manager.generate_deposit_address("user-two", "eth")
    result = manager.record_blockchain_deposit(
        user_address="user-two",
        currency="eth",
        amount=1.25,
        tx_hash="ff" * 32,
        deposit_address="nonexistent-address",
        confirmations=0,
    )
    assert result["success"] is False
    assert result["error"] == "UNKNOWN_DEPOSIT_ADDRESS"


def test_update_unknown_deposit(tmp_path):
    manager, _ = create_manager(tmp_path)
    response = manager.update_confirmations("doesnotexist", 4)
    assert response["success"] is False
    assert response["error"] == "UNKNOWN_DEPOSIT"
