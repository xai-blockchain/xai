"""
Unit tests for wallet generation, signing, persistence, and manager helpers.
"""

import json
import os
from pathlib import Path

import pytest

from xai.core.wallet import Wallet, WalletManager


class StubHardwareWallet:
    """Stub hardware wallet to drive hardware branch."""

    def __init__(self):
        self._address = "HWADDR"

    def get_address(self):
        return self._address

    def sign_transaction(self, data: bytes) -> bytes:
        return b"hw_signature"


def test_wallet_generation_and_sign_verify():
    """Generated wallet signs/verifies messages correctly."""
    wallet = Wallet()
    msg = "hello"
    sig = wallet.sign_message(msg)
    assert wallet.verify_signature(msg, sig, wallet.public_key) is True


def test_wallet_save_and_load_with_password(tmp_path):
    """Wallet persists to disk with password and loads round-trip."""
    wallet = Wallet()
    path = tmp_path / "w.wallet"
    wallet.save_to_file(str(path), password="secret")

    loaded = Wallet.load_from_file(str(path), password="secret")
    assert loaded.address == wallet.address
    assert loaded.private_key == wallet.private_key


def test_wallet_manager_create_and_list(tmp_path):
    """WalletManager creates, lists, and loads wallets."""
    mgr = WalletManager(data_dir=str(tmp_path))
    mgr.create_wallet("alice", password="pw")
    mgr.create_wallet("bob", password="pw")

    names = sorted(mgr.list_wallets())
    assert names == ["alice", "bob"]
    loaded = mgr.load_wallet("alice", password="pw")
    assert loaded.address == mgr.get_wallet("alice").address


def test_hardware_wallet_path(monkeypatch):
    """When hardware wallet is present, Wallet uses it for address/signing."""
    monkeypatch.setattr("xai.core.wallet.HARDWARE_WALLET_ENABLED", True)
    monkeypatch.setattr("xai.core.wallet.get_default_hardware_wallet", lambda: StubHardwareWallet())

    wallet = Wallet()
    assert wallet.address == "HWADDR"
    assert wallet.sign_message("msg") == "68775f7369676e6174757265"  # hex of "hw_signature"
