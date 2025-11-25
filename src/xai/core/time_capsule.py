"""
XAI Blockchain - Time Capsule System

Allows users to create time-locked capsules that release funds on a future date.
Time capsule locks are represented by on-chain `time_capsule_lock` transactions,
and the unlock is handled automatically via `time_capsule_claim` transactions.
"""

import time
import os
import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from xai.core.config import Config
from xai.core.crypto_utils import deterministic_keypair_from_seed


class TimeCapsuleType:
    """Types of time capsules"""

    XAI_ONLY = "xai_only"
    CROSS_CHAIN = "cross_chain"


class TimeCapsule:
    """Represents a time-locked capsule"""

    def __init__(
        self,
        capsule_id: str,
        creator: str,
        beneficiary: str,
        unlock_time: int,
        capsule_type: str,
        amount: float = 0,
        coin_type: str = "XAI",
        message: str = "",
        htlc_details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.capsule_id = capsule_id
        self.creator = creator
        self.beneficiary = beneficiary
        self.unlock_time = unlock_time
        self.capsule_type = capsule_type
        self.amount = amount
        self.coin_type = coin_type
        self.message = message
        self.htlc_details = htlc_details or {}
        self.metadata = metadata or {}
        self.created_time = int(time.time())
        self.claimed = False
        self.claimed_time: Optional[int] = None

    def is_unlocked(self) -> bool:
        return int(time.time()) >= self.unlock_time

    def time_remaining(self) -> int:
        return self.unlock_time - int(time.time())

    def days_remaining(self) -> float:
        return self.time_remaining() / 86400

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capsule_id": self.capsule_id,
            "creator": self.creator,
            "beneficiary": self.beneficiary,
            "unlock_time": self.unlock_time,
            "unlock_date": datetime.fromtimestamp(self.unlock_time).isoformat(),
            "capsule_type": self.capsule_type,
            "amount": self.amount,
            "coin_type": self.coin_type,
            "message": self.message,
            "htlc_details": self.htlc_details,
            "metadata": self.metadata,
            "created_time": self.created_time,
            "claimed": self.claimed,
            "claimed_time": self.claimed_time,
            "is_unlocked": self.is_unlocked(),
            "time_remaining_seconds": max(0, self.time_remaining()),
            "days_remaining": max(0, self.days_remaining()),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimeCapsule":
        capsule = cls(
            capsule_id=data["capsule_id"],
            creator=data["creator"],
            beneficiary=data["beneficiary"],
            unlock_time=int(data["unlock_time"]),
            capsule_type=data.get("capsule_type", TimeCapsuleType.XAI_ONLY),
            amount=float(data.get("amount", 0)),
            coin_type=data.get("coin_type", "XAI"),
            message=data.get("message", ""),
            htlc_details=data.get("htlc_details", {}),
            metadata=data.get("metadata", {}),
        )
        capsule.created_time = int(data.get("created_time", capsule.created_time))
        capsule.claimed = data.get("claimed", False)
        capsule.claimed_time = data.get("claimed_time")
        return capsule


class TimeCapsuleManager:
    """Manages time capsules and the deterministic addresses used to hold them"""

    STORAGE_FILENAME = "time_capsules.json"

    def __init__(self, blockchain, storage_file: Optional[str] = None):
        self.blockchain = blockchain
        data_dir = Path(storage_file if storage_file else Config.DATA_DIR)
        self.storage_path = data_dir / self.STORAGE_FILENAME
        self.log_path = data_dir / "time_capsule_events.log"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.capsules: Dict[str, TimeCapsule] = {}
        self.user_capsules: Dict[str, List[str]] = {}
        self._load_capsules()

    def _load_capsules(self):
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            for capsule_data in payload.get("capsules", []):
                capsule = TimeCapsule.from_dict(capsule_data)
                self.capsules[capsule.capsule_id] = capsule
            self.user_capsules = payload.get("users", {})
        except Exception:
            self.capsules = {}
            self.user_capsules = {}

    def _save_capsules(self):
        data = {
            "capsules": [capsule.to_dict() for capsule in self.capsules.values()],
            "users": self.user_capsules,
        }
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _log_event(self, event_type: str, payload: Dict[str, Any]):
        entry = {"event": event_type, "timestamp": int(time.time()), "payload": payload}
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    @staticmethod
    def _capsule_seed(capsule_id: str) -> bytes:
        master = Config.TIME_CAPSULE_MASTER_KEY.encode()
        return hashlib.sha256(master + capsule_id.encode()).digest()

    def _capsule_keypair(self, capsule_id: str):
        seed = self._capsule_seed(capsule_id)
        return deterministic_keypair_from_seed(seed)

    def capsule_address(self, capsule_id: str) -> str:
        _, public_hex = self._capsule_keypair(capsule_id)
        hashed = hashlib.sha256(public_hex.encode()).hexdigest()
        return f"XAI{hashed[:40]}"

    def _record_user_capsule(self, address: str, capsule_id: str):
        if address not in self.user_capsules:
            self.user_capsules[address] = []
        if capsule_id not in self.user_capsules[address]:
            self.user_capsules[address].append(capsule_id)

    def register_lock_transaction(
        self, tx: "Transaction", block_height: int, block_timestamp: float
    ):
        capsule_id = tx.metadata.get("capsule_id")
        if not capsule_id:
            return
        beneficiary = tx.metadata.get("beneficiary", tx.sender)
        unlock_time = int(tx.metadata.get("unlock_time") or 0)
        allow_past_unlock = bool(tx.metadata.get("allow_past_unlock"))
        if unlock_time <= 0:
            return
        if unlock_time < int(time.time()) and not allow_past_unlock:
            return
        message = tx.metadata.get("message", "")
        capsule_type = tx.metadata.get("capsule_type", TimeCapsuleType.XAI_ONLY)
        coin_type = tx.metadata.get("coin_type", "XAI")
        htlc_hash = tx.metadata.get("htlc_hash")

        if capsule_id in self.capsules:
            capsule = self.capsules[capsule_id]
        else:
            capsule = TimeCapsule(
                capsule_id=capsule_id,
                creator=tx.sender,
                beneficiary=beneficiary,
                unlock_time=unlock_time,
                capsule_type=capsule_type,
                amount=tx.amount,
                coin_type=coin_type,
                message=message,
                htlc_details={"hash": htlc_hash} if htlc_hash else {},
            )
        capsule.metadata.update(
            {
                "status": "locked",
                "lock_txid": tx.txid,
                "capsule_address": tx.recipient,
                "block_height": block_height,
                "created_at": block_timestamp,
                "claim_txid": None,
            }
        )
        self.capsules[capsule_id] = capsule
        self._record_user_capsule(tx.sender, capsule_id)
        self._record_user_capsule(beneficiary, capsule_id)
        self._save_capsules()
        self._log_event(
            "time_capsule_buried",
            {
                "capsule_id": capsule_id,
                "amount": capsule.amount,
                "unlock_time": capsule.unlock_time,
                "creator": capsule.creator,
                "beneficiary": capsule.beneficiary,
                "txid": tx.txid,
            },
        )

    def get_unlockable_capsules(self, current_time: Optional[float] = None) -> List[TimeCapsule]:
        if current_time is None:
            current_time = time.time()
        return [
            capsule
            for capsule in self.capsules.values()
            if capsule.metadata.get("status") == "locked" and capsule.unlock_time <= current_time
        ]

    def build_claim_transaction(self, capsule: TimeCapsule) -> Optional["Transaction"]:
        if capsule.metadata.get("status") != "locked":
            return None
        capsule_address = self.capsule_address(capsule.capsule_id)
        from xai.core.blockchain import Transaction

        claim_tx = Transaction(
            sender=capsule_address,
            recipient=capsule.beneficiary,
            amount=capsule.amount,
            fee=0.0,
            tx_type="time_capsule_claim",
            metadata={"capsule_id": capsule.capsule_id},
        )
        private_key_hex, _ = self._capsule_keypair(capsule.capsule_id)
        claim_tx.sign_transaction(private_key_hex)
        capsule.metadata["status"] = "claim_pending"
        capsule.metadata["claim_txid"] = claim_tx.txid
        capsule.metadata["claim_requested_at"] = time.time()
        self._save_capsules()
        return claim_tx

    def register_claim_transaction(self, tx: "Transaction", block_timestamp: float):
        capsule_id = tx.metadata.get("capsule_id")
        capsule = self.capsules.get(capsule_id)
        if not capsule:
            return
        capsule.metadata["status"] = "claimed"
        capsule.metadata["claim_txid"] = tx.txid
        capsule.metadata["claimed_at"] = block_timestamp
        capsule.claimed = True
        capsule.claimed_time = int(block_timestamp)
        self._save_capsules()
        self._log_event(
            "time_capsule_opened",
            {
                "capsule_id": capsule_id,
                "txid": tx.txid,
                "amount": capsule.amount,
                "coin_type": capsule.coin_type,
                "beneficiary": capsule.beneficiary,
            },
        )

    def _value_snapshot(self, capsule: TimeCapsule) -> Dict[str, Any]:
        address = capsule.metadata.get("capsule_address") or self.capsule_address(
            capsule.capsule_id
        )
        utxos = self.blockchain.utxo_set.get(address, [])
        current_total = sum(u["amount"] for u in utxos if not u["spent"])
        delta = round(current_total - capsule.amount, 8)
        previous = capsule.metadata.get("last_announced_value", capsule.amount)
        delta_since_last = round(current_total - previous, 8)
        if delta_since_last > 0:
            message = f"Time Capsule value whispered up by {delta_since_last:.2f} XAI since the last check-in—still safe and secure."
            capsule.metadata["last_announced_value"] = current_total
            self._save_capsules()
        else:
            message = f"Time Capsule safe & secure at {round(current_total, 8):.2f} XAI; value talk resumes when it grows."
        return {
            "capsule_address": address,
            "current_value": round(current_total, 8),
            "net_change": delta_since_last,
            "value_change_note": message,
        }

    def _burial_windows(self) -> List[Dict[str, datetime]]:
        year = datetime.utcnow().year
        return [
            {"start": datetime(year, 3, 10), "end": datetime(year, 3, 30)},
            {"start": datetime(year, 11, 10), "end": datetime(year, 11, 30)},
        ]

    def _in_burial_window(self) -> bool:
        now = datetime.utcnow()
        for window in self._burial_windows():
            if window["start"] <= now <= window["end"]:
                return True
        return False

    def _next_burial_window(self) -> datetime:
        now = datetime.utcnow()
        for window in self._burial_windows():
            if now <= window["end"]:
                return window["start"]
        next_year_start = datetime(now.year + 1, 3, 10)
        return next_year_start

    def create_xai_capsule(
        self, creator: str, beneficiary: str, amount: float, unlock_time: int, message: str = ""
    ) -> Dict[str, Any]:
        if amount <= 0:
            return {"success": False, "error": "Amount must be positive"}
        if unlock_time <= int(time.time()):
            return {"success": False, "error": "Unlock time must be in the future"}
        balance = self.blockchain.get_balance(creator)
        if balance < amount:
            return {
                "success": False,
                "error": f"Insufficient balance. Have: {balance}, Need: {amount}",
            }
        if not self._in_burial_window():
            next_window = self._next_burial_window()
            return {
                "success": False,
                "error": "Time Capsules may only be buried twice per year.",
                "next_open_window": next_window.strftime("%Y-%m-%d"),
            }
        capsule_id = self._generate_capsule_id(creator, unlock_time)
        capsule_address = self.capsule_address(capsule_id)
        return {
            "success": True,
            "capsule_id": capsule_id,
            "capsule_address": capsule_address,
            "unlock_time": unlock_time,
            "message": "Construct a signed time_capsule_lock transaction using this capsule_id and send it from your wallet.",
        }

    def create_cross_chain_capsule(
        self,
        creator: str,
        beneficiary: str,
        coin_type: str,
        amount: float,
        unlock_time: int,
        htlc_hash: str,
        origin_chain_tx: str,
        message: str = "",
    ) -> Dict[str, Any]:
        if unlock_time <= int(time.time()):
            return {"success": False, "error": "Unlock time must be in the future"}
        supported = ["BTC", "ETH", "LTC", "DOGE", "XMR", "BCH", "ZEC", "DASH"]
        if coin_type not in supported:
            return {"success": False, "error": f"Unsupported coin. Supported: {supported}"}
        if not self._in_burial_window():
            next_window = self._next_burial_window()
            return {
                "success": False,
                "error": "Time Capsules may only be buried twice per year.",
                "next_open_window": next_window.strftime("%Y-%m-%d"),
            }
        capsule_id = self._generate_capsule_id(creator, unlock_time)
        capsule_address = self.capsule_address(capsule_id)
        return {
            "success": True,
            "capsule_id": capsule_id,
            "capsule_address": capsule_address,
            "unlock_time": unlock_time,
            "next_steps": [
                f"1. Lock {amount} {coin_type} in an HTLC contract referencing the hash {htlc_hash}",
                f"2. Record the origin transaction: {origin_chain_tx}",
                "3. When unlock_time passes, claim the HTLC using the preimage you control",
            ],
        }

    def claim_capsule(
        self, capsule_id: str, claimer: str, htlc_preimage: Optional[str] = None
    ) -> Dict[str, Any]:
        capsule = self.capsules.get(capsule_id)
        if not capsule:
            return {"success": False, "error": "Capsule not found"}
        if not capsule.is_unlocked():
            return {
                "success": False,
                "error": f"Capsule locked for {capsule.days_remaining():.1f} more days",
            }
        if capsule.claimed:
            return {"success": False, "error": "Capsule already claimed"}
        if claimer != capsule.beneficiary:
            return {"success": False, "error": f"Only {capsule.beneficiary} can claim this capsule"}
        if capsule.capsule_type == TimeCapsuleType.CROSS_CHAIN:
            if not htlc_preimage:
                return {"success": False, "error": "HTLC preimage required"}
            expected = capsule.metadata.get("htlc_hash")
            if expected and hashlib.sha256(htlc_preimage.encode()).hexdigest() != expected:
                return {"success": False, "error": "Preimage hash mismatch"}
            return {
                "success": True,
                "message": "Time Capsule opened—bring this preimage to the origin chain.",
                "htlc_preimage": htlc_preimage,
                "htlc_hash": expected,
            }
        capsule.claimed = True
        capsule.claimed_time = int(time.time())
        self._save_capsules()
        return {
            "success": True,
            "message": "Time Capsule ready to be unearthed via the automated claim transaction",
        }

    def get_user_capsules(self, address: str) -> List[Dict[str, Any]]:
        if address not in self.user_capsules:
            return []
        capsules = []
        for cid in self.user_capsules[address]:
            if cid not in self.capsules:
                continue
            data = self.capsules[cid].to_dict()
            snapshot = self._value_snapshot(self.capsules[cid])
            data.update(snapshot)
            capsules.append(data)
        capsules.sort(key=lambda c: c["unlock_time"])
        return capsules

    def get_capsule(self, capsule_id: str) -> Optional[Dict[str, Any]]:
        capsule = self.capsules.get(capsule_id)
        if not capsule:
            return None
        result = capsule.to_dict()
        result["metadata"] = capsule.metadata
        result.update(self._value_snapshot(capsule))
        return result

    def get_statistics(self) -> Dict[str, Any]:
        total = len(self.capsules)
        claimed = sum(1 for c in self.capsules.values() if c.claimed)
        unlocked = sum(1 for c in self.capsules.values() if c.is_unlocked() and not c.claimed)
        locked = total - claimed - unlocked
        total_locked_value = sum(c.amount for c in self.capsules.values() if not c.claimed)
        total_claimed_value = sum(c.amount for c in self.capsules.values() if c.claimed)
        return {
            "total_capsules": total,
            "claimed": claimed,
            "unlocked_unclaimed": unlocked,
            "still_locked": locked,
            "total_locked_value": total_locked_value,
            "total_claimed_value": total_claimed_value,
            "unique_users": len(self.user_capsules),
        }

    def _generate_capsule_id(self, creator: str, unlock_time: int) -> str:
        payload = f"{creator}{unlock_time}{int(time.time())}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


def get_time_capsule_manager(blockchain, storage_file: Optional[str] = None) -> TimeCapsuleManager:
    return TimeCapsuleManager(blockchain, storage_file)
