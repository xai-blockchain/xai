"""
XAI Trading Primitives

Defines the lightweight order format used by wallet-to-wallet swaps,
signature verification helpers, and status tracking that's persisted on-chain.
"""

import hashlib
import json
import time
import hmac
import logging
import os
import secrets
import base64
import ecdsa
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
from secrets import token_bytes
from collections import defaultdict
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

from audit_signer import AuditSigner
from config import Config


class OrderStatus(Enum):
    """Lifecycle states for an on-chain trade order"""
    PENDING = "pending"
    MATCHED = "matched"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"


class SwapOrderType(Enum):
    BUY = "buy"
    SELL = "sell"


class SwapOrderStatus(Enum):
    """States used by the GUI/orderbook for UI"""
    PENDING = "pending"
    MATCHED = "matched"
    CANCELLED = "cancelled"


WALLETCONNECT_HANDSHAKE_TTL = 300
HKDF_INFO = b"walletconnect-trade"


@dataclass
class WalletConnectHandshake:
    handshake_id: str
    wallet_address: str
    server_private: ec.EllipticCurvePrivateKey
    created_at: float

    def is_expired(self) -> bool:
        return time.time() - self.created_at > WALLETCONNECT_HANDSHAKE_TTL

    def public_bytes(self) -> bytes:
        return self.server_private.public_key().public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )


@dataclass
class TradeOrder:
    """Lightweight wallet order with signature and lifecycle details"""

    maker_address: str
    maker_public_key: str
    token_offered: str
    amount_offered: float
    token_requested: str
    amount_requested: float
    price: float
    expiry: float
    nonce: int
    order_type: SwapOrderType = SwapOrderType.SELL
    order_type: SwapOrderType
    fee: float = 0.0
    order_id: Optional[str] = None
    signature: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    matched_order_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.order_id:
            self.order_id = self._generate_order_id()

        self.token_offered = self.token_offered.upper()
        self.token_requested = self.token_requested.upper()

        if isinstance(self.order_type, str):
            self.order_type = SwapOrderType(self.order_type)

    def _generate_order_id(self) -> str:
        payload = f"{self.maker_address}{self.token_offered}{self.token_requested}{self.nonce}{time.time()}"
        return hashlib.sha256(payload.encode()).hexdigest()[:20]

    def payload(self) -> Dict[str, Any]:
        return {
            'maker_address': self.maker_address,
            'maker_public_key': self.maker_public_key,
            'token_offered': self.token_offered,
            'amount_offered': round(self.amount_offered, 8),
            'token_requested': self.token_requested,
            'amount_requested': round(self.amount_requested, 8),
            'price': round(self.price, 8),
            'expiry': self.expiry,
            'nonce': self.nonce,
            'fee': round(self.fee, 8),
            'order_type': self.order_type.value
        }

    def calculate_hash(self) -> str:
        payload_str = json.dumps(self.payload(), sort_keys=True)
        return hashlib.sha256(payload_str.encode()).hexdigest()

    def sign(self, private_key: str):
        sk = ecdsa.SigningKey.from_string(bytes.fromhex(private_key), curve=ecdsa.SECP256k1)
        digest = self.calculate_hash().encode()
        self.signature = sk.sign(digest).hex()

    def verify_signature(self) -> bool:
        if not self.signature or not self.maker_public_key:
            return False

        try:
            vk = ecdsa.VerifyingKey.from_string(
                bytes.fromhex(self.maker_public_key),
                curve=ecdsa.SECP256k1
            )
            message = self.calculate_hash().encode()
            vk.verify(bytes.fromhex(self.signature), message)
            pub_hash = hashlib.sha256(self.maker_public_key.encode()).hexdigest()
            expected_address = f"XAI{pub_hash[:40]}"
            return expected_address == self.maker_address
        except Exception:
            return False

    def is_expired(self) -> bool:
        return time.time() >= self.expiry

    def to_dict(self) -> Dict[str, Any]:
        return {
            'order_id': self.order_id,
            'maker_address': self.maker_address,
            'maker_public_key': self.maker_public_key,
            'token_offered': self.token_offered,
            'amount_offered': self.amount_offered,
            'token_requested': self.token_requested,
            'amount_requested': self.amount_requested,
            'price': self.price,
            'expiry': self.expiry,
            'nonce': self.nonce,
            'fee': self.fee,
            'signature': self.signature,
            'status': self.status.value,
            'matched_order_id': self.matched_order_id,
            'order_type': self.order_type.value,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeOrder':
        status_val = data.get('status', OrderStatus.PENDING.value)
        status = OrderStatus(status_val)
        order_type_value = data.get('order_type', SwapOrderType.SELL.value)
        return cls(
            maker_address=data['maker_address'],
            maker_public_key=data['maker_public_key'],
            token_offered=data['token_offered'],
            amount_offered=float(data['amount_offered']),
            token_requested=data['token_requested'],
            amount_requested=float(data['amount_requested']),
            price=float(data['price']),
            expiry=float(data['expiry']),
            nonce=int(data['nonce']),
            fee=float(data.get('fee', 0.0)),
            order_id=data.get('order_id'),
            signature=data.get('signature'),
            status=status,
            matched_order_id=data.get('matched_order_id'),
            metadata=data.get('metadata', {}),
            order_type=SwapOrderType(order_type_value)
        )


class TradeMatchStatus(Enum):
    MATCHED = "matched"
    SETTLED = "settled"
    REFUNDED = "refunded"
    EXPIRED = "expired"


@dataclass
class TradeMatch:
    match_id: str
    maker_order_id: str
    taker_order_id: str
    secret_hash: str
    created_at: float
    expires_at: float
    status: TradeMatchStatus = TradeMatchStatus.MATCHED
    metadata: Dict[str, Any] = field(default_factory=dict)
    secret: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'match_id': self.match_id,
            'maker_order_id': self.maker_order_id,
            'taker_order_id': self.taker_order_id,
            'secret_hash': self.secret_hash,
            'created_at': self.created_at,
            'expires_at': self.expires_at,
            'status': self.status.value,
            'metadata': self.metadata,
            'secret': self.secret
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeMatch':
        status_val = data.get('status', TradeMatchStatus.MATCHED.value)
        status = TradeMatchStatus(status_val)
        return cls(
            match_id=data['match_id'],
            maker_order_id=data['maker_order_id'],
            taker_order_id=data['taker_order_id'],
            secret_hash=data['secret_hash'],
            created_at=float(data['created_at']),
            expires_at=float(data['expires_at']),
            status=status,
            metadata=data.get('metadata', {}),
            secret=data.get('secret')
        )


class TradeManager:
    """Manages wallet-to-wallet trade orders and matches"""

    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.orders: Dict[str, TradeOrder] = {}
        self.orderbook: List[TradeOrder] = []
        self.matches: Dict[str, TradeMatch] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.nonces: Dict[str, float] = defaultdict(int)
        self.event_log: List[Dict[str, Any]] = []
        self.trade_dir = os.path.join(Config.DATA_DIR, 'wallet_trades')
        os.makedirs(self.trade_dir, exist_ok=True)
        self._load_snapshot()
        self._load_event_log()
        self.wc_handshakes: Dict[str, WalletConnectHandshake] = {}
        self.audit_signer = AuditSigner(self.trade_dir)

    def _cleanup_handshakes(self):
        now = time.time()
        expired = [hid for hid, handshake in self.wc_handshakes.items() if handshake.is_expired()]
        for hid in expired:
            logger.info(f"Expiring WalletConnect handshake {hid}")
            del self.wc_handshakes[hid]

    def begin_walletconnect_handshake(self, wallet_address: str) -> Dict[str, Any]:
        self._cleanup_handshakes()
        handshake_id = secrets.token_hex(16)
        private_key = ec.generate_private_key(ec.SECP256R1())
        handshake = WalletConnectHandshake(
            handshake_id=handshake_id,
            wallet_address=wallet_address,
            server_private=private_key,
            created_at=time.time()
        )
        self.wc_handshakes[handshake_id] = handshake
        server_public = base64.b64encode(handshake.public_bytes()).decode()
        logger.info(f"Started WalletConnect handshake {handshake_id} for {wallet_address}")
        return {
            'success': True,
            'handshake_id': handshake_id,
            'server_public': server_public,
            'curve': 'P-256'
        }

    def complete_walletconnect_handshake(self, handshake_id: str, wallet_address: str, client_public_b64: str) -> Optional[Dict[str, Any]]:
        handshake = self.wc_handshakes.get(handshake_id)
        if not handshake or handshake.wallet_address != wallet_address or handshake.is_expired():
            return None
        client_bytes = base64.b64decode(client_public_b64)
        client_public = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), client_bytes)
        secret = self._derive_shared_secret(handshake.server_private, client_public, handshake_id)
        session = self.register_session(wallet_address, secret.hex())
        del self.wc_handshakes[handshake_id]
        self._log_event('walletconnect_handshake', {'wallet_address': wallet_address, 'session_token': session['session_token']})
        return session

    def _derive_shared_secret(self, server_private: ec.EllipticCurvePrivateKey, client_public: ec.EllipticCurvePublicKey, handshake_id: str) -> bytes:
        shared = server_private.exchange(ec.ECDH(), client_public)
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=handshake_id.encode(),
            info=HKDF_INFO,
            backend=default_backend()
        )
        return hkdf.derive(shared)

    def register_session(self, wallet_address: str, secret: Optional[str] = None) -> Dict[str, str]:
        """Create a trading session for a wallet address"""
        token = secrets.token_hex(16)
        session_secret = secret or secrets.token_hex(32)
        self.sessions[token] = {
            'address': wallet_address,
            'secret': session_secret,
            'created_at': time.time()
        }
        logger.info(f"Trade session {token} registered for {wallet_address}")
        return {'session_token': token, 'session_secret': session_secret}

    def place_order(
        self,
        order: TradeOrder,
        session_token: Optional[str] = None,
        signature: Optional[str] = None,
        skip_validation: bool = False,
    ) -> Tuple[bool, str, Optional[TradeMatch]]:
        """Validate, store, and attempt to match a new trade order"""
        if order.order_id in self.orders:
            return False, "Order already exists", None

        if order.is_expired():
            return False, "Order expired", None

        if not skip_validation:
            if not session_token or not signature:
                return False, "Missing session information", None

            session = self.sessions.get(session_token)
            if not session or session['address'] != order.maker_address:
                return False, "Invalid session token", None

            expected = hmac.new(
                session['secret'].encode(),
                order.calculate_hash().encode(),
                hashlib.sha256
            ).hexdigest()
            if signature != expected:
                return False, "Signature mismatch", None

            if order.nonce <= self.nonces.get(order.maker_address, 0):
                return False, "Nonce replay detected", None

            self.nonces[order.maker_address] = order.nonce
        else:
            self.nonces[order.maker_address] = max(
                self.nonces.get(order.maker_address, 0), order.nonce
            )

        self.orders[order.order_id] = order
        self.orderbook.append(order)
        self._log_event('order_created', order.to_dict())
        self._save_snapshot()

        match = self._find_matching_order(order)
        if match:
            self._log_event('order_matched', {
                'order_id': order.order_id,
                'match_id': match.match_id
            })
            self._save_snapshot()
            return True, "Order matched", match

        return True, "Order pending", None

    def _find_matching_order(self, order: TradeOrder) -> Optional[TradeMatch]:
        """Try to match the new order with an existing opposite order"""
        for candidate in list(self.orderbook):
            if candidate.order_id == order.order_id:
                continue
            if candidate.status != OrderStatus.PENDING:
                continue

            if order.order_type == candidate.order_type:
                continue

            if candidate.token_offered != order.token_requested:
                continue
            if candidate.token_requested != order.token_offered:
                continue

            amount_match = abs(candidate.amount_offered - order.amount_requested) < 0.01
            price_match = abs(candidate.price - order.price) < 0.001

            if amount_match and price_match:
                order.status = OrderStatus.MATCHED
                candidate.status = OrderStatus.MATCHED
                self.orderbook = [o for o in self.orderbook if o.order_id not in {order.order_id, candidate.order_id}]

                match_id = hashlib.sha256(f"{order.order_id}-{candidate.order_id}-{time.time()}".encode()).hexdigest()[:20]
                secret_bytes = token_bytes(32)
                secret_hash = hashlib.sha256(secret_bytes).hexdigest()
                expires_at = time.time() + Config.TRADE_ORDER_EXPIRY
                fee = (order.amount_offered + candidate.amount_offered) * Config.TRADE_FEE_PERCENT

                match = TradeMatch(
                    match_id=match_id,
                    maker_order_id=order.order_id,
                    taker_order_id=candidate.order_id,
                    secret_hash=secret_hash,
                    created_at=time.time(),
                    expires_at=expires_at,
                    metadata={
                        'price': order.price,
                        'fee': fee,
                        'secret_hex': secret_bytes.hex()
                    }
                )
                self.matches[match_id] = match
                return match

        return None

    def reveal_secret(self, match_id: str, secret: str) -> Tuple[bool, str]:
        """Reveal secret for a matched swap to queue its settlement"""
        match = self.matches.get(match_id)
        if not match:
            return False, "Match not found"

        if match.status != TradeMatchStatus.MATCHED:
            return False, "Match already settled"

        computed = hashlib.sha256(bytes.fromhex(secret)).hexdigest()
        if computed != match.secret_hash:
            return False, "Secret mismatch"

        match.secret = secret
        match.metadata['revealed_at'] = time.time()
        self.blockchain.enqueue_trade_settlement(match)
        self._log_event('secret_revealed', {'match_id': match_id})
        self._save_snapshot()
        return True, "Secret accepted"

    def ingest_gossip(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process gossip events from peer nodes"""
        event_type = event.get('type')
        if event_type == 'order':
            payload = event.get('order')
            if not payload:
                return {'success': False, 'error': 'Order payload missing'}

            order = TradeOrder.from_dict(payload)
            success, message, match = self.place_order(order, skip_validation=True)
            return {'success': success, 'message': message, 'match': match.to_dict() if match else None}

        if event_type == 'match':
            match_payload = event.get('match')
            if not match_payload:
                return {'success': False, 'error': 'Match payload missing'}

            match_id = match_payload.get('match_id')
            if match_id and match_id not in self.matches:
                self.matches[match_id] = TradeMatch.from_dict(match_payload)
                self._log_event('match_relayed', match_payload)
                return {'success': True, 'message': 'Match registered'}

        return {'success': False, 'error': 'Unsupported event type'}

    def _log_event(self, event_type: str, payload: Dict[str, Any]):
        entry = {
            'type': event_type,
            'timestamp': time.time(),
            'payload': payload
        }
        self.event_log.append(entry)
        logger.info(json.dumps(entry))
        self._append_event_log(entry)

    def get_order(self, order_id: str) -> Optional[TradeOrder]:
        return self.orders.get(order_id)

    def get_match(self, match_id: str) -> Optional[TradeMatch]:
        return self.matches.get(match_id)

    def list_orders(self, status: Optional[OrderStatus] = None) -> List[TradeOrder]:
        return [
            order for order in self.orders.values()
            if status is None or order.status == status
        ]

    def list_matches(self) -> List[TradeMatch]:
        return list(self.matches.values())

    def snapshot(self) -> Dict[str, Any]:
        """Return a snapshot of current orders/matches for syncing peers"""
        pending = [order.to_dict() for order in self.orders.values() if order.status == OrderStatus.PENDING]
        active_matches = [match.to_dict() for match in self.matches.values() if match.status == TradeMatchStatus.MATCHED]
        return {'orders': pending, 'matches': active_matches}

    def _snapshot_path(self) -> str:
        return os.path.join(self.trade_dir, 'orderbook_snapshot.json')

    def _gossip_log_path(self) -> str:
        return os.path.join(self.trade_dir, 'gossip.log')

    def _save_snapshot(self):
        with open(self._snapshot_path(), 'w') as f:
            json.dump(self.snapshot(), f, indent=2)

    def _load_snapshot(self):
        path = self._snapshot_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            for order in data.get('orders', []):
                self.orders[order['order_id']] = TradeOrder.from_dict(order)
            for match in data.get('matches', []):
                self.matches[match['match_id']] = TradeMatch.from_dict(match)
        except Exception as exc:
            logger.warning(f"Failed to load trade snapshot: {exc}")

    def _append_event_log(self, event: Dict[str, Any]):
        entry = {**event, 'timestamp': time.time()}
        self.event_log.append(entry)
        try:
            with open(self._gossip_log_path(), 'a') as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as exc:
            logger.warning(f"Unable to append trade log: {exc}")

    def recent_events(self, limit: int = 25) -> List[Dict[str, Any]]:
        return self.event_log[-limit:]

    def signed_event_batch(self, limit: int = 25) -> List[Dict[str, str]]:
        events = self.recent_events(limit)
        signed = []
        for event in events:
            signed.append(self.audit_payload(event))
        return signed

    def audit_payload(self, event: Dict[str, Any]) -> Dict[str, str]:
        payload = json.dumps(event, sort_keys=True)
        signature = self.audit_signer.sign(payload)
        return {'payload': payload, 'signature': signature, 'public_key': self.audit_signer.public_key()}

    def _load_event_log(self):
        path = self._gossip_log_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, 'r') as f:
                for line in f:
                    self.event_log.append(json.loads(line.strip()))
        except Exception as exc:
            logger.warning(f"Unable to load trade log: {exc}")
