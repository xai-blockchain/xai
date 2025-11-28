"""Fully featured wallet trade manager implementation."""

from __future__ import annotations

import json
import os
import time
import uuid
import secrets
import threading
import hmac
import hashlib
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Tuple, Optional, List

from xai.core.trading import SwapOrderType, TradeMatchStatus
from xai.core.nonce_tracker import NonceTracker


DATA_DIR_DEFAULT = os.path.join(os.path.dirname(__file__), "..", "data", "wallet_trades")
STATE_FILE = "state.json"
AUDIT_SECRET_FILE = "audit_secret"
MAX_HISTORY = 500
MATCH_STATUS_OPEN = "open"


def _ensure_directory(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _now() -> float:
    return time.time()


@dataclass
class WalletTradeOrder:
    """Represents a wallet-level peer trade order."""

    order_id: str
    maker_address: str
    token_offered: str
    amount_offered: float
    token_requested: str
    amount_requested: float
    price: float
    order_type: SwapOrderType
    status: str = MATCH_STATUS_OPEN
    remaining_offered: float = field(default=0.0)
    remaining_requested: float = field(default=0.0)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def __post_init__(self) -> None:
        if self.remaining_offered == 0:
            self.remaining_offered = self.amount_offered
        if self.remaining_requested == 0:
            self.remaining_requested = self.amount_requested

    @property
    def exchange_rate(self) -> float:
        if self.amount_offered == 0:
            return 0.0
        return self.amount_requested / self.amount_offered

    def fill(self, offered_delta: float, requested_delta: float) -> None:
        self.remaining_offered = max(self.remaining_offered - offered_delta, 0.0)
        self.remaining_requested = max(self.remaining_requested - requested_delta, 0.0)
        self.updated_at = _now()
        if self.remaining_offered <= 1e-9 or self.remaining_requested <= 1e-9:
            self.status = "filled"
        else:
            self.status = "partial"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "maker_address": self.maker_address,
            "token_offered": self.token_offered,
            "amount_offered": self.amount_offered,
            "token_requested": self.token_requested,
            "amount_requested": self.amount_requested,
            "price": self.price,
            "order_type": self.order_type.value,
            "status": self.status,
            "remaining_offered": self.remaining_offered,
            "remaining_requested": self.remaining_requested,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WalletTradeOrder":
        return cls(
            order_id=data["order_id"],
            maker_address=data["maker_address"],
            token_offered=data["token_offered"],
            amount_offered=data["amount_offered"],
            token_requested=data["token_requested"],
            amount_requested=data["amount_requested"],
            price=data["price"],
            order_type=SwapOrderType(data["order_type"]),
            status=data.get("status", MATCH_STATUS_OPEN),
            remaining_offered=data.get("remaining_offered", data["amount_offered"]),
            remaining_requested=data.get("remaining_requested", data["amount_requested"]),
            created_at=data.get("created_at", _now()),
            updated_at=data.get("updated_at", _now()),
        )


@dataclass
class WalletTradeMatch:
    """Represents a matched trade awaiting settlement."""

    match_id: str
    maker_order_id: str
    taker_order_id: str
    maker_amount: float
    taker_amount: float
    maker_token: str
    taker_token: str
    secret: str
    status: TradeMatchStatus = TradeMatchStatus.MATCHED
    created_at: float = field(default_factory=_now)
    settled_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "maker_order_id": self.maker_order_id,
            "taker_order_id": self.taker_order_id,
            "maker_amount": self.maker_amount,
            "taker_amount": self.taker_amount,
            "maker_token": self.maker_token,
            "taker_token": self.taker_token,
            "secret": self.secret,
            "status": self.status.value,
            "created_at": self.created_at,
            "settled_at": self.settled_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WalletTradeMatch":
        return cls(
            match_id=data["match_id"],
            maker_order_id=data["maker_order_id"],
            taker_order_id=data["taker_order_id"],
            maker_amount=data["maker_amount"],
            taker_amount=data["taker_amount"],
            maker_token=data["maker_token"],
            taker_token=data["taker_token"],
            secret=data["secret"],
            status=TradeMatchStatus(data.get("status", TradeMatchStatus.MATCHED.value)),
            created_at=data.get("created_at", _now()),
            settled_at=data.get("settled_at"),
        )


class AuditSigner:
    """Provides deterministic signing for gossip batches."""

    def __init__(self, secret: Optional[str] = None):
        self._secret = secret or secrets.token_hex(32)
        self._public = hashlib.sha256(self._secret.encode()).hexdigest()

    def public_key(self) -> str:
        return self._public

    def sign(self, payload: Dict[str, Any]) -> str:
        message = json.dumps(payload, sort_keys=True).encode()
        digest = hmac.new(self._secret.encode(), message, hashlib.sha256).hexdigest()
        return digest

    def serialize(self) -> str:
        return self._secret

    @classmethod
    def from_file(cls, path: str) -> "AuditSigner":
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                secret = handle.read().strip()
                if secret:
                    return cls(secret)
        signer = cls()
        _ensure_directory(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(signer.serialize())
        return signer


class WalletTradeManager:
    """Stateful trade manager used by wallet APIs."""

    def __init__(
        self,
        exchange_wallet_manager: Optional[Any] = None,
        data_dir: Optional[str] = None,
        nonce_tracker: Optional[NonceTracker] = None,
    ) -> None:
        self.data_dir = _ensure_directory(data_dir or DATA_DIR_DEFAULT)
        self.state_file = os.path.join(self.data_dir, STATE_FILE)
        self.audit_signer = AuditSigner.from_file(os.path.join(self.data_dir, AUDIT_SECRET_FILE))
        self.exchange_wallet_manager = exchange_wallet_manager
        self.nonce_tracker = nonce_tracker or NonceTracker()
        self.orders: Dict[str, WalletTradeOrder] = {}
        self.matches: Dict[str, WalletTradeMatch] = {}
        self.event_log: List[Dict[str, Any]] = []
        self.handshakes: Dict[str, Dict[str, Any]] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.RLock()
        self._load_state()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _load_state(self) -> None:
        if not os.path.exists(self.state_file):
            return
        try:
            with open(self.state_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            self.orders = {
                item["order_id"]: WalletTradeOrder.from_dict(item)
                for item in data.get("orders", [])
            }
            self.matches = {
                item["match_id"]: WalletTradeMatch.from_dict(item)
                for item in data.get("matches", [])
            }
            self.event_log = data.get("events", [])[-MAX_HISTORY:]
            self.handshakes = data.get("handshakes", {})
            self.sessions = data.get("sessions", {})
        except (json.JSONDecodeError, OSError):
            self.orders = {}
            self.matches = {}
            self.event_log = []
            self.handshakes = {}
            self.sessions = {}

    def _save_state(self) -> None:
        data = {
            "orders": [order.to_dict() for order in self.orders.values()],
            "matches": [match.to_dict() for match in self.matches.values()],
            "events": self.event_log[-MAX_HISTORY:],
            "handshakes": self.handshakes,
            "sessions": self.sessions,
        }
        with open(self.state_file, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)

    # ------------------------------------------------------------------
    # Session / handshake lifecycle
    # ------------------------------------------------------------------
    def begin_walletconnect_handshake(self, wallet_address: str) -> Dict[str, Any]:
        with self.lock:
            handshake_id = str(uuid.uuid4())
            uri_key = secrets.token_hex(16)
            record = {
                "wallet_address": wallet_address,
                "handshake_id": handshake_id,
                "uri": f"wc:{handshake_id}@1?bridge=https://bridge.xai.io&key={uri_key}",
                "created_at": _now(),
            }
            self.handshakes[handshake_id] = record
            self._save_state()
            return {"success": True, **record}

    def complete_walletconnect_handshake(
        self, handshake_id: str, wallet_address: str, client_public: str
    ) -> Dict[str, Any]:
        with self.lock:
            record = self.handshakes.get(handshake_id)
            if not record or record["wallet_address"] != wallet_address:
                return {"success": False, "error": "invalid_handshake"}

            session_token = secrets.token_urlsafe(32)
            session = {
                "session_token": session_token,
                "wallet_address": wallet_address,
                "client_public": client_public,
                "created_at": _now(),
                "expires_at": _now() + 3600,
            }
            self.sessions[session_token] = session
            self.handshakes.pop(handshake_id, None)
            self._save_state()
            return {"success": True, **session}

    def register_session(self, wallet_address: str) -> Dict[str, Any]:
        with self.lock:
            session_token = secrets.token_urlsafe(24)
            session = {
                "session_token": session_token,
                "wallet_address": wallet_address,
                "created_at": _now(),
                "expires_at": _now() + 900,
            }
            self.sessions[session_token] = session
            self._save_state()
            return session

    # ------------------------------------------------------------------
    # Order workflow
    # ------------------------------------------------------------------
    def attach_exchange_manager(self, manager: Any) -> None:
        with self.lock:
            self.exchange_wallet_manager = manager

    def place_order(
        self,
        maker_address: str,
        token_offered: str,
        amount_offered: float,
        token_requested: str,
        amount_requested: float,
        price: float,
        order_type: SwapOrderType,
    ) -> Tuple[WalletTradeOrder, List[WalletTradeMatch]]:
        order = WalletTradeOrder(
            order_id=str(uuid.uuid4()),
            maker_address=maker_address,
            token_offered=token_offered,
            amount_offered=float(amount_offered),
            token_requested=token_requested,
            amount_requested=float(amount_requested),
            price=float(price),
            order_type=order_type,
        )
        matches: List[WalletTradeMatch] = []
        with self.lock:
            self.orders[order.order_id] = order
            matches = self._match_order(order)
            self._save_state()
        return order, matches

    def _match_order(self, taker_order: WalletTradeOrder) -> List[WalletTradeMatch]:
        matched: List[WalletTradeMatch] = []
        for candidate in self.orders.values():
            if candidate.order_id == taker_order.order_id:
                continue
            if candidate.status != MATCH_STATUS_OPEN:
                continue
            if not self._orders_compatible(candidate, taker_order):
                continue

            maker_token_amount = min(
                candidate.remaining_offered, taker_order.remaining_requested
            )
            if maker_token_amount <= 0:
                continue

            quote_needed = maker_token_amount * candidate.exchange_rate
            if taker_order.remaining_offered < quote_needed:
                scale = taker_order.remaining_offered / quote_needed
                maker_token_amount *= scale
                quote_needed = maker_token_amount * candidate.exchange_rate

            if maker_token_amount <= 0 or quote_needed <= 0:
                continue

            candidate.fill(maker_token_amount, quote_needed)
            taker_order.fill(quote_needed, maker_token_amount)

            match = WalletTradeMatch(
                match_id=str(uuid.uuid4()),
                maker_order_id=candidate.order_id,
                taker_order_id=taker_order.order_id,
                maker_amount=maker_token_amount,
                taker_amount=quote_needed,
                maker_token=candidate.token_offered,
                taker_token=taker_order.token_offered,
                secret=secrets.token_hex(32),
            )
            self.matches[match.match_id] = match
            matched.append(match)
            self._record_event(
                "match_created",
                {
                    "match_id": match.match_id,
                    "maker_order_id": candidate.order_id,
                    "taker_order_id": taker_order.order_id,
                },
            )

            if taker_order.status == "filled":
                break
        return matched

    def _orders_compatible(self, maker: WalletTradeOrder, taker: WalletTradeOrder) -> bool:
        if maker.token_offered != taker.token_requested:
            return False
        if maker.token_requested != taker.token_offered:
            return False
        maker_rate = maker.exchange_rate
        taker_rate = taker.exchange_rate
        if maker_rate == 0 or taker_rate == 0:
            return False
        tolerance = 0.0001
        reciprocal = 1 / taker_rate
        return abs(maker_rate - reciprocal) <= tolerance

    def get_order(self, order_id: str) -> Optional[WalletTradeOrder]:
        return self.orders.get(order_id)

    def get_match(self, match_id: str) -> Optional[WalletTradeMatch]:
        return self.matches.get(match_id)

    def list_orders(self) -> List[WalletTradeOrder]:
        return sorted(self.orders.values(), key=lambda o: o.created_at, reverse=True)

    def list_matches(self) -> List[WalletTradeMatch]:
        return sorted(self.matches.values(), key=lambda m: m.created_at, reverse=True)

    def settle_match(self, match_id: str, secret: str) -> Dict[str, Any]:
        with self.lock:
            match = self.matches.get(match_id)
            if not match:
                return {"success": False, "error": "match_not_found"}
            if match.status != TradeMatchStatus.MATCHED:
                return {"success": False, "error": "match_not_settleable"}
            if match.secret != secret:
                return {"success": False, "error": "invalid_secret"}
            if not self.exchange_wallet_manager:
                return {"success": False, "error": "exchange_manager_unavailable"}

            maker_order = self.orders.get(match.maker_order_id)
            taker_order = self.orders.get(match.taker_order_id)
            maker_address = maker_order.maker_address if maker_order else None
            taker_address = taker_order.maker_address if taker_order else None
            if not maker_address or not taker_address:
                return {"success": False, "error": "order_not_found"}

            # Execute simulated escrow release
            self.exchange_wallet_manager.withdraw(
                maker_address, match.maker_token, match.maker_amount
            )
            self.exchange_wallet_manager.deposit(
                taker_address, match.maker_token, match.maker_amount, deposit_type="trade"
            )
            self.exchange_wallet_manager.withdraw(
                taker_address, match.taker_token, match.taker_amount
            )
            self.exchange_wallet_manager.deposit(
                maker_address, match.taker_token, match.taker_amount, deposit_type="trade"
            )

            match.status = TradeMatchStatus.SETTLED
            match.settled_at = _now()
            self._record_event(
                "match_settled",
                {
                    "match_id": match.match_id,
                    "maker_order_id": match.maker_order_id,
                    "taker_order_id": match.taker_order_id,
                },
            )
            self._save_state()
            return {"success": True, "match": match.to_dict()}

    # ------------------------------------------------------------------
    # Gossip & diagnostics
    # ------------------------------------------------------------------
    def ingest_gossip(self, event: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            normalized = {
                "received_at": _now(),
                "event": event,
            }
            self.event_log.append(normalized)
            self.event_log = self.event_log[-MAX_HISTORY:]
            self._save_state()
        return {"success": True, "message": "event_ingested"}

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "orders": [order.to_dict() for order in self.list_orders()],
                "matches": [match.to_dict() for match in self.list_matches()],
                "active_sessions": len(self.sessions),
                "pending_handshakes": len(self.handshakes),
            }

    def signed_event_batch(self, limit: int) -> List[Dict[str, Any]]:
        with self.lock:
            events = self.event_log[-limit:]
            batches = []
            for entry in events:
                payload = entry["event"]
                batches.append(
                    {
                        "event": payload,
                        "signature": self.audit_signer.sign(payload),
                        "public_key": self.audit_signer.public_key(),
                    }
                )
            return batches

    def _record_event(self, event_type: str, details: Dict[str, Any]) -> None:
        entry = {"type": event_type, "details": details, "timestamp": _now()}
        self.event_log.append({"event": entry, "received_at": _now()})
        self.event_log = self.event_log[-MAX_HISTORY:]

    # ------------------------------------------------------------------
    # Atomic Swap Coordination (Multi-party)
    # ------------------------------------------------------------------
    def initiate_atomic_swap(
        self,
        participants: List[Dict[str, Any]],
        timeout_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Initiate a multi-party atomic swap with state synchronization.

        Args:
            participants: List of participant dictionaries with
                         {address, token, amount, public_key}
            timeout_seconds: Swap timeout duration

        Returns:
            Atomic swap coordination data
        """
        if len(participants) < 2:
            return {"success": False, "error": "At least 2 participants required"}

        with self.lock:
            swap_id = str(uuid.uuid4())
            swap_secret = secrets.token_hex(32)
            swap_hash = hashlib.sha256(swap_secret.encode()).hexdigest()

            # Initialize swap state
            swap_state = {
                "swap_id": swap_id,
                "participants": participants,
                "swap_hash": swap_hash,
                "status": "initiated",
                "created_at": _now(),
                "expires_at": _now() + timeout_seconds,
                "timeout_seconds": timeout_seconds,
                "participant_states": {
                    p["address"]: {
                        "status": "pending",
                        "committed": False,
                        "revealed": False,
                        "hash_lock_created": False,
                        "timeout_set": False
                    }
                    for p in participants
                },
                "coordination_log": []
            }

            # Store in sessions for coordination
            self.sessions[f"atomic_swap_{swap_id}"] = swap_state

            self._record_event("atomic_swap_initiated", {
                "swap_id": swap_id,
                "participant_count": len(participants),
                "expires_at": swap_state["expires_at"]
            })

            self._save_state()

            return {
                "success": True,
                "swap_id": swap_id,
                "swap_hash": swap_hash,
                "expires_at": swap_state["expires_at"],
                "participants": participants,
                "message": "Atomic swap initiated. Participants must commit within timeout."
            }

    def commit_to_swap(
        self,
        swap_id: str,
        participant_address: str,
        hash_lock: str,
        signature: str
    ) -> Dict[str, Any]:
        """
        Participant commits to atomic swap by creating hash lock.

        Args:
            swap_id: Swap identifier
            participant_address: Committing participant
            hash_lock: Hash lock for this participant's funds
            signature: Signature proving commitment

        Returns:
            Commitment status
        """
        with self.lock:
            swap_key = f"atomic_swap_{swap_id}"
            swap_state = self.sessions.get(swap_key)

            if not swap_state:
                return {"success": False, "error": "swap_not_found"}

            if swap_state["status"] not in ["initiated", "committing"]:
                return {"success": False, "error": f"swap_not_committable, status: {swap_state['status']}"}

            if _now() > swap_state["expires_at"]:
                return self._timeout_swap(swap_id, "commitment_timeout")

            if participant_address not in swap_state["participant_states"]:
                return {"success": False, "error": "participant_not_found"}

            p_state = swap_state["participant_states"][participant_address]

            if p_state["committed"]:
                return {"success": False, "error": "already_committed"}

            # Record commitment
            p_state["committed"] = True
            p_state["hash_lock"] = hash_lock
            p_state["commit_signature"] = signature
            p_state["hash_lock_created"] = True
            p_state["committed_at"] = _now()

            swap_state["coordination_log"].append({
                "event": "commitment",
                "participant": participant_address,
                "timestamp": _now()
            })

            # Check if all committed
            all_committed = all(
                s["committed"] for s in swap_state["participant_states"].values()
            )

            if all_committed:
                swap_state["status"] = "committed"
                swap_state["all_committed_at"] = _now()

            swap_state["status"] = "committing" if not all_committed else "committed"

            self._record_event("swap_commitment", {
                "swap_id": swap_id,
                "participant": participant_address,
                "all_committed": all_committed
            })

            self._save_state()

            return {
                "success": True,
                "swap_id": swap_id,
                "participant": participant_address,
                "all_committed": all_committed,
                "committed_count": sum(1 for s in swap_state["participant_states"].values() if s["committed"]),
                "total_participants": len(swap_state["participants"])
            }

    def reveal_swap_secret(
        self,
        swap_id: str,
        participant_address: str,
        secret: str
    ) -> Dict[str, Any]:
        """
        Reveal secret to complete atomic swap.

        Args:
            swap_id: Swap identifier
            participant_address: Revealing participant
            secret: The swap secret

        Returns:
            Reveal status
        """
        with self.lock:
            swap_key = f"atomic_swap_{swap_id}"
            swap_state = self.sessions.get(swap_key)

            if not swap_state:
                return {"success": False, "error": "swap_not_found"}

            if swap_state["status"] != "committed":
                return {"success": False, "error": f"swap_not_ready_for_reveal, status: {swap_state['status']}"}

            # Verify secret matches hash
            secret_hash = hashlib.sha256(secret.encode()).hexdigest()
            if secret_hash != swap_state["swap_hash"]:
                return {"success": False, "error": "invalid_secret"}

            if participant_address not in swap_state["participant_states"]:
                return {"success": False, "error": "participant_not_found"}

            p_state = swap_state["participant_states"][participant_address]

            if p_state["revealed"]:
                return {"success": False, "error": "already_revealed"}

            # Record reveal
            p_state["revealed"] = True
            p_state["revealed_at"] = _now()
            p_state["status"] = "completed"

            swap_state["coordination_log"].append({
                "event": "secret_revealed",
                "participant": participant_address,
                "timestamp": _now()
            })

            # Check if all revealed
            all_revealed = all(
                s["revealed"] for s in swap_state["participant_states"].values()
            )

            if all_revealed:
                swap_state["status"] = "completed"
                swap_state["completed_at"] = _now()
                swap_state["swap_secret"] = secret  # Store for audit

            self._record_event("swap_secret_revealed", {
                "swap_id": swap_id,
                "participant": participant_address,
                "all_revealed": all_revealed
            })

            self._save_state()

            return {
                "success": True,
                "swap_id": swap_id,
                "participant": participant_address,
                "all_revealed": all_revealed,
                "swap_completed": all_revealed,
                "revealed_count": sum(1 for s in swap_state["participant_states"].values() if s["revealed"])
            }

    def rollback_swap(
        self,
        swap_id: str,
        reason: str,
        initiator_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rollback atomic swap on failure.

        Args:
            swap_id: Swap identifier
            reason: Reason for rollback
            initiator_address: Who initiated rollback

        Returns:
            Rollback status
        """
        with self.lock:
            swap_key = f"atomic_swap_{swap_id}"
            swap_state = self.sessions.get(swap_key)

            if not swap_state:
                return {"success": False, "error": "swap_not_found"}

            if swap_state["status"] == "completed":
                return {"success": False, "error": "cannot_rollback_completed_swap"}

            if swap_state["status"] == "rolled_back":
                return {"success": False, "error": "already_rolled_back"}

            # Execute rollback
            swap_state["status"] = "rolled_back"
            swap_state["rollback_reason"] = reason
            swap_state["rollback_initiator"] = initiator_address
            swap_state["rolled_back_at"] = _now()

            # Mark all participants as rolled back
            for p_address, p_state in swap_state["participant_states"].items():
                if p_state["committed"] and not p_state["revealed"]:
                    p_state["status"] = "rolled_back"
                    p_state["funds_returned"] = True

            swap_state["coordination_log"].append({
                "event": "rollback",
                "reason": reason,
                "initiator": initiator_address,
                "timestamp": _now()
            })

            self._record_event("swap_rolled_back", {
                "swap_id": swap_id,
                "reason": reason,
                "initiator": initiator_address
            })

            self._save_state()

            return {
                "success": True,
                "swap_id": swap_id,
                "status": "rolled_back",
                "reason": reason,
                "participants_refunded": len(swap_state["participants"])
            }

    def _timeout_swap(self, swap_id: str, reason: str) -> Dict[str, Any]:
        """Internal method to handle swap timeout."""
        return self.rollback_swap(swap_id, f"timeout: {reason}", initiator_address="system")

    def get_swap_status(self, swap_id: str) -> Dict[str, Any]:
        """Get current status of atomic swap."""
        with self.lock:
            swap_key = f"atomic_swap_{swap_id}"
            swap_state = self.sessions.get(swap_key)

            if not swap_state:
                return {"success": False, "error": "swap_not_found"}

            return {
                "success": True,
                "swap_id": swap_id,
                "status": swap_state["status"],
                "created_at": swap_state["created_at"],
                "expires_at": swap_state["expires_at"],
                "time_remaining": max(0, swap_state["expires_at"] - _now()),
                "participants": swap_state["participants"],
                "participant_states": swap_state["participant_states"],
                "coordination_log": swap_state["coordination_log"]
            }

