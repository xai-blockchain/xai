"""Lightweight state helpers for the EVM-compatible executor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:  # pragma: no cover - runtime imports deferred
    from xai.core.blockchain import Blockchain, Block


@dataclass
class AccountState:
    address: str
    nonce: int
    balance: int
    code: bytes = b""
    storage_root: Optional[str] = None


@dataclass
class EVMState:
    """
    Adapter that mediates between the blockchain storage engine and VM access patterns.

    The class intentionally keeps the API narrow so we can swap implementations when
    snapshotting or sharded state backends land later.
    """

    blockchain: "Blockchain"
    block: "Block"
    caches: Dict[str, AccountState] = field(default_factory=dict)

    def get_account(self, address: str) -> AccountState:
        if address in self.caches:
            return self.caches[address]
        account = self._load_account(address)
        self.caches[address] = account
        return account

    def set_account(self, account: AccountState) -> None:
        self.caches[account.address] = account

    def commit(self) -> None:
        for account in self.caches.values():
            self._persist_account(account)
        self.caches.clear()

    def rollback(self) -> None:
        self.caches.clear()

    def _load_account(self, address: str) -> AccountState:
        # Placeholder implementation until the VM wiring lands.
        balance = self.blockchain.get_balance(address)
        nonce = self.blockchain.nonce_tracker.get_nonce(address)
        return AccountState(address=address, balance=int(balance), nonce=nonce)

    def _persist_account(self, account: AccountState) -> None:
        # Persistence is deferred to the blockchain layer.  Implementations should
        # update UTXO/account databases in tandem to keep both ledgers consistent.
        pass
