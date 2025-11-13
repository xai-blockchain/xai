"""
Account abstraction helpers and embedded wallet management.
"""

import json
import os
import hashlib
import secrets
from pathlib import Path
from typing import Dict, Optional

from aixn.core.wallet import WalletManager
from aixn.config_manager import Config


class EmbeddedWalletRecord:
    def __init__(self, alias: str, contact: str, wallet_name: str, address: str, secret_hash: str):
        self.alias = alias
        self.contact = contact
        self.wallet_name = wallet_name
        self.address = address
        self.secret_hash = secret_hash

    def to_dict(self) -> Dict[str, str]:
        return {
            'alias': self.alias,
            'contact': self.contact,
            'wallet_name': self.wallet_name,
            'address': self.address,
            'secret_hash': self.secret_hash
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "EmbeddedWalletRecord":
        return cls(
            alias=data['alias'],
            contact=data['contact'],
            wallet_name=data['wallet_name'],
            address=data['address'],
            secret_hash=data['secret_hash']
        )


class AccountAbstractionManager:
    """Manage embedded wallets that map to social/email identities."""

    def __init__(self, wallet_manager: WalletManager, storage_path: Optional[str] = None):
        self.wallet_manager = wallet_manager
        self.storage_path = storage_path or Config.EMBEDDED_WALLET_DIR
        os.makedirs(self.storage_path, exist_ok=True)
        self.records_file = os.path.join(self.storage_path, "embedded_wallets.json")
        self.records: Dict[str, EmbeddedWalletRecord] = {}
        self.sessions: Dict[str, str] = {}
        self._load()

    def _hash_secret(self, secret: str) -> str:
        salted = f"{secret}{Config.EMBEDDED_WALLET_SALT}"
        return hashlib.sha256(salted.encode()).hexdigest()

    def _wallet_filename(self, alias: str) -> str:
        safe_alias = alias.replace(" ", "_")
        return os.path.join(self.storage_path, f"{safe_alias}.wallet")

    def _load(self):
        if os.path.exists(self.records_file):
            with open(self.records_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for entry in data:
                    record = EmbeddedWalletRecord.from_dict(entry)
                    self.records[record.alias] = record

    def _save(self):
        with open(self.records_file, 'w', encoding='utf-8') as f:
            json.dump([rec.to_dict() for rec in self.records.values()], f, indent=2)

    def create_embedded_wallet(self, alias: str, contact: str, secret: str) -> EmbeddedWalletRecord:
        if alias in self.records:
            raise ValueError("Alias already exists")

        wallet_name = f"embedded_{alias}"
        password = secret or Config.WALLET_PASSWORD or secrets.token_hex(16)
        wallet = self.wallet_manager.create_wallet(wallet_name, password=password)
        record = EmbeddedWalletRecord(
            alias=alias,
            contact=contact,
            wallet_name=wallet_name,
            address=wallet.address,
            secret_hash=self._hash_secret(secret)
        )
        self.records[alias] = record
        self.sessions[alias] = secrets.token_hex(16)
        self._save()
        return record

    def authenticate(self, alias: str, secret: str) -> Optional[str]:
        record = self.records.get(alias)
        if not record:
            return None
        if record.secret_hash != self._hash_secret(secret):
            return None
        token = secrets.token_hex(16)
        self.sessions[alias] = token
        return token

    def get_session_token(self, alias: str) -> Optional[str]:
        return self.sessions.get(alias)

    def get_session(self, alias: str) -> Optional[str]:
        return self.sessions.get(alias)

    def get_record(self, alias: str) -> Optional[EmbeddedWalletRecord]:
        return self.records.get(alias)
