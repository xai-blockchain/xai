"""
Mobile wallet bridge helpers.

Allows constrained devices to request unsigned transactions, display them
as QR/USB payloads, and later submit signed transactions for broadcasting.
"""

import base64
import json
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional

from blockchain import Transaction


class MobileWalletBridge:
    """Draft/commit flow for mobile wallets and air-gapped signers."""

    DEFAULT_EXPIRY_SECONDS = 15 * 60  # 15 minutes

    def __init__(self, blockchain, validator, fee_optimizer=None):
        self.blockchain = blockchain
        self.validator = validator
        self.fee_optimizer = fee_optimizer
        self._drafts: Dict[str, Dict[str, Any]] = {}
        self.expiry_seconds = self.DEFAULT_EXPIRY_SECONDS

    def create_draft(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create an unsigned transaction draft."""
        self._purge_expired()

        sender = payload.get('sender', '').strip()
        recipient = payload.get('recipient', '').strip()
        amount = payload.get('amount')
        priority = (payload.get('priority') or 'normal').lower()
        memo = payload.get('memo')
        metadata = payload.get('metadata') or {}
        client_id = payload.get('client_id')
        defer_congestion = payload.get('defer_until_congestion_below')

        if not sender or not recipient:
            raise ValueError("sender and recipient are required")

        try:
            self.validator.validate_address(sender, 'sender')
            self.validator.validate_address(recipient, 'recipient')
        except Exception as exc:
            raise ValueError(str(exc))

        try:
            amount = self.validator.validate_amount(float(amount), 'amount')
        except Exception as exc:
            raise ValueError(str(exc))

        if sender in self._active_drafts_for_sender(sender):
            # Only one outstanding draft per sender (matches nonce sequencing)
            raise ValueError("Existing draft pending for this sender. Commit or cancel it before creating another.")

        nonce = self.blockchain.nonce_tracker.get_next_nonce(sender)
        fee_quote = self._get_fee_quote(priority)
        timestamp = time.time()

        unsigned_tx = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'fee': fee_quote['recommended_fee'],
            'nonce': nonce,
            'priority': priority,
            'memo': memo,
            'metadata': metadata,
            'timestamp': timestamp,
        }

        draft_id = str(uuid.uuid4())
        qr_payload = base64.b64encode(json.dumps(unsigned_tx, sort_keys=True).encode()).decode()

        self._drafts[draft_id] = {
            'unsigned_tx': unsigned_tx,
            'created_at': timestamp,
            'client_id': client_id,
            'fee_quote': fee_quote,
            'defer_until_congestion_below': defer_congestion,
            'status': 'draft',
        }

        return {
            'draft_id': draft_id,
            'unsigned_transaction': unsigned_tx,
            'fee_quote': fee_quote,
            'qr_payload': qr_payload,
            'expires_at': timestamp + self.expiry_seconds,
            'defer_until_congestion_below': defer_congestion,
        }

    def get_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        self._purge_expired()
        draft = self._drafts.get(draft_id)
        if not draft:
            return None

        remaining = max(0, draft['created_at'] + self.expiry_seconds - time.time())
        return {
            'draft_id': draft_id,
            'unsigned_transaction': draft['unsigned_tx'],
            'fee_quote': draft['fee_quote'],
            'status': draft['status'],
            'expires_in': remaining,
        }

    def commit_draft(self, draft_id: str, signature: str, public_key: str) -> Transaction:
        self._purge_expired()
        draft = self._drafts.get(draft_id)
        if not draft:
            raise ValueError("Draft not found or expired")

        unsigned_tx = draft['unsigned_tx']
        tx = Transaction(
            sender=unsigned_tx['sender'],
            recipient=unsigned_tx['recipient'],
            amount=float(unsigned_tx['amount']),
            fee=float(unsigned_tx['fee']),
            nonce=unsigned_tx['nonce'],
            metadata=unsigned_tx.get('metadata') or {}
        )
        tx.timestamp = unsigned_tx['timestamp']
        tx.public_key = public_key
        tx.signature = signature
        tx.tx_type = 'mobile'

        if not tx.verify_signature():
            raise ValueError("Signature verification failed")

        tx.txid = tx.calculate_hash()

        if not self.blockchain.add_transaction(tx):
            raise ValueError("Failed to queue transaction—see node logs for details")

        draft['status'] = 'submitted'
        draft['submitted_txid'] = tx.txid
        # Keep the draft around briefly so status queries show completion.
        draft['created_at'] = time.time()

        return tx

    def _get_fee_quote(self, priority: str) -> Dict[str, Any]:
        pending = len(self.blockchain.pending_transactions)
        if self.fee_optimizer:
            try:
                return self.fee_optimizer.predict_optimal_fee(pending, priority=priority)
            except Exception:
                pass

        base_fee = Decimal('0.05')
        if priority == 'high':
            base_fee *= Decimal('1.5')
        elif priority == 'low':
            base_fee *= Decimal('0.75')

        congestion = min(pending / 100.0, 2.0)
        recommended_fee = float((base_fee * (1 + Decimal(str(congestion)))).quantize(Decimal('0.00000001')))

        return {
            'recommended_fee': recommended_fee,
            'conditions': {
                'priority': priority,
                'pending_transactions': pending,
                'congestion_factor': round(congestion, 2)
            },
            'confidence': 0.5
        }

    def _active_drafts_for_sender(self, sender: str) -> List[str]:
        return [
            draft_id for draft_id, draft in self._drafts.items()
            if draft['unsigned_tx']['sender'] == sender and draft['status'] == 'draft'
        ]

    def _purge_expired(self):
        if not self._drafts:
            return
        now = time.time()
        expired = [
            draft_id for draft_id, draft in self._drafts.items()
            if draft['status'] == 'draft' and (now - draft['created_at']) > self.expiry_seconds
        ]
        for draft_id in expired:
            self._drafts.pop(draft_id, None)
