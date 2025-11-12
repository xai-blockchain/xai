"""
Multi-Signature Cold Wallet System (Phase 2)
Requires multiple approvals for cold wallet withdrawals
"""

import json
import os
import time
import hashlib
from decimal import Decimal
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum


class ProposalStatus(Enum):
    """Status of a withdrawal proposal"""
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    EXECUTED = 'executed'
    EXPIRED = 'expired'


@dataclass
class Signer:
    """Represents a person authorized to sign cold wallet transactions"""
    id: str
    name: str
    email: str
    public_key: str  # For cryptographic signature verification
    role: str  # e.g., "CEO", "CFO", "CTO", "Security Officer"
    active: bool = True


@dataclass
class WithdrawalProposal:
    """Represents a proposed cold wallet withdrawal"""
    id: str
    currency: str
    amount: Decimal
    from_address: str  # Cold wallet address
    to_address: str    # Destination (hot wallet or external)
    reason: str
    proposed_by: str   # Signer ID
    proposed_at: float
    required_signatures: int
    signatures: List[str] = field(default_factory=list)  # List of signer IDs who approved
    status: ProposalStatus = ProposalStatus.PENDING
    expires_at: float = 0  # Timestamp when proposal expires
    executed_at: Optional[float] = None
    tx_hash: Optional[str] = None
    notes: List[Dict] = field(default_factory=list)

    def is_expired(self) -> bool:
        """Check if proposal has expired"""
        return time.time() > self.expires_at

    def has_enough_signatures(self) -> bool:
        """Check if proposal has enough signatures"""
        return len(self.signatures) >= self.required_signatures

    def can_execute(self) -> bool:
        """Check if proposal can be executed"""
        return (
            self.status == ProposalStatus.PENDING and
            not self.is_expired() and
            self.has_enough_signatures()
        )

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'currency': self.currency,
            'amount': float(self.amount),
            'from_address': self.from_address,
            'to_address': self.to_address,
            'reason': self.reason,
            'proposed_by': self.proposed_by,
            'proposed_at': self.proposed_at,
            'required_signatures': self.required_signatures,
            'signatures': self.signatures,
            'signature_count': len(self.signatures),
            'status': self.status.value,
            'expires_at': self.expires_at,
            'time_remaining': max(0, self.expires_at - time.time()) if not self.is_expired() else 0,
            'executed_at': self.executed_at,
            'tx_hash': self.tx_hash,
            'notes': self.notes,
            'can_execute': self.can_execute()
        }


class MultiSigColdWallet:
    """
    Multi-signature cold wallet management system

    Security Model:
    - 2-of-3 for small withdrawals (< $10K)
    - 3-of-5 for large withdrawals (>= $10K)
    - All proposals expire after 48 hours
    - Proposals require reason/justification
    - Full audit trail of all approvals
    """

    def __init__(self, data_dir: str = 'multisig_data'):
        self.data_dir = data_dir
        self.signers: Dict[str, Signer] = {}
        self.proposals: Dict[str, WithdrawalProposal] = {}

        # Multi-sig configuration
        self.small_withdrawal_threshold = 10000  # $10K USD equivalent
        self.small_withdrawal_signatures = 2  # 2-of-N
        self.large_withdrawal_signatures = 3  # 3-of-N

        # Proposal expiration (48 hours)
        self.proposal_expiry_seconds = 48 * 3600

        self.load_data()

    def add_signer(self, name: str, email: str, public_key: str, role: str) -> Signer:
        """Add a new authorized signer"""

        signer_id = hashlib.sha256(f"{name}{email}{time.time()}".encode()).hexdigest()[:16]

        signer = Signer(
            id=signer_id,
            name=name,
            email=email,
            public_key=public_key,
            role=role,
            active=True
        )

        self.signers[signer_id] = signer
        self.save_data()

        return signer

    def deactivate_signer(self, signer_id: str) -> bool:
        """Deactivate a signer (doesn't delete, just makes inactive)"""

        if signer_id in self.signers:
            self.signers[signer_id].active = False
            self.save_data()
            return True

        return False

    def get_active_signers(self) -> List[Signer]:
        """Get list of active signers"""
        return [s for s in self.signers.values() if s.active]

    def create_proposal(
        self,
        currency: str,
        amount: float,
        from_address: str,
        to_address: str,
        reason: str,
        proposed_by_id: str,
        usd_value: float = None
    ) -> WithdrawalProposal:
        """Create a new withdrawal proposal"""

        # Verify proposer is an active signer
        if proposed_by_id not in self.signers or not self.signers[proposed_by_id].active:
            raise ValueError("Proposer is not an active signer")

        # Determine required signatures based on USD value
        if usd_value is None:
            usd_value = amount  # Assume 1:1 if not provided

        if usd_value >= self.small_withdrawal_threshold:
            required_sigs = self.large_withdrawal_signatures
        else:
            required_sigs = self.small_withdrawal_signatures

        # Verify we have enough signers
        active_signers = len(self.get_active_signers())
        if active_signers < required_sigs:
            raise ValueError(f"Not enough active signers ({active_signers}) for required signatures ({required_sigs})")

        # Create proposal
        proposal_id = hashlib.sha256(f"{currency}{amount}{time.time()}".encode()).hexdigest()[:16]

        proposal = WithdrawalProposal(
            id=proposal_id,
            currency=currency,
            amount=Decimal(str(amount)),
            from_address=from_address,
            to_address=to_address,
            reason=reason,
            proposed_by=proposed_by_id,
            proposed_at=time.time(),
            required_signatures=required_sigs,
            expires_at=time.time() + self.proposal_expiry_seconds
        )

        # Proposer automatically signs their own proposal
        proposal.signatures.append(proposed_by_id)

        self.proposals[proposal_id] = proposal
        self.save_data()

        return proposal

    def sign_proposal(self, proposal_id: str, signer_id: str, notes: str = "") -> bool:
        """Sign/approve a withdrawal proposal"""

        if proposal_id not in self.proposals:
            raise ValueError("Proposal not found")

        if signer_id not in self.signers or not self.signers[signer_id].active:
            raise ValueError("Signer is not active")

        proposal = self.proposals[proposal_id]

        # Check if already expired
        if proposal.is_expired():
            proposal.status = ProposalStatus.EXPIRED
            self.save_data()
            raise ValueError("Proposal has expired")

        # Check if already signed
        if signer_id in proposal.signatures:
            raise ValueError("Signer has already approved this proposal")

        # Check if proposal is still pending
        if proposal.status != ProposalStatus.PENDING:
            raise ValueError(f"Proposal is {proposal.status.value}, cannot sign")

        # Add signature
        proposal.signatures.append(signer_id)

        # Add note
        if notes:
            proposal.notes.append({
                'signer_id': signer_id,
                'signer_name': self.signers[signer_id].name,
                'action': 'approved',
                'notes': notes,
                'timestamp': time.time()
            })

        # Check if we now have enough signatures
        if proposal.has_enough_signatures():
            proposal.status = ProposalStatus.APPROVED

        self.save_data()

        return True

    def reject_proposal(self, proposal_id: str, signer_id: str, reason: str) -> bool:
        """Reject a withdrawal proposal"""

        if proposal_id not in self.proposals:
            raise ValueError("Proposal not found")

        if signer_id not in self.signers or not self.signers[signer_id].active:
            raise ValueError("Signer is not active")

        proposal = self.proposals[proposal_id]

        if proposal.status != ProposalStatus.PENDING:
            raise ValueError(f"Proposal is {proposal.status.value}, cannot reject")

        # Mark as rejected
        proposal.status = ProposalStatus.REJECTED

        # Add rejection note
        proposal.notes.append({
            'signer_id': signer_id,
            'signer_name': self.signers[signer_id].name,
            'action': 'rejected',
            'notes': reason,
            'timestamp': time.time()
        })

        self.save_data()

        return True

    def execute_proposal(self, proposal_id: str, tx_hash: str) -> bool:
        """Mark proposal as executed (called after blockchain transaction completes)"""

        if proposal_id not in self.proposals:
            raise ValueError("Proposal not found")

        proposal = self.proposals[proposal_id]

        if not proposal.can_execute():
            raise ValueError("Proposal cannot be executed (not enough signatures or expired)")

        # Mark as executed
        proposal.status = ProposalStatus.EXECUTED
        proposal.executed_at = time.time()
        proposal.tx_hash = tx_hash

        self.save_data()

        return True

    def get_pending_proposals(self) -> List[WithdrawalProposal]:
        """Get all pending proposals"""
        proposals = []

        for proposal in self.proposals.values():
            if proposal.status == ProposalStatus.PENDING:
                # Check if expired
                if proposal.is_expired():
                    proposal.status = ProposalStatus.EXPIRED
                    self.save_data()
                else:
                    proposals.append(proposal)

        return proposals

    def get_executable_proposals(self) -> List[WithdrawalProposal]:
        """Get proposals that are ready to execute"""
        return [p for p in self.proposals.values() if p.can_execute()]

    def get_proposal_history(self, limit: int = 50) -> List[WithdrawalProposal]:
        """Get recent proposal history"""
        all_proposals = sorted(
            self.proposals.values(),
            key=lambda p: p.proposed_at,
            reverse=True
        )

        return all_proposals[:limit]

    def get_stats(self) -> dict:
        """Get multi-sig system statistics"""
        proposals = list(self.proposals.values())

        return {
            'total_signers': len(self.signers),
            'active_signers': len(self.get_active_signers()),
            'total_proposals': len(proposals),
            'pending_proposals': len([p for p in proposals if p.status == ProposalStatus.PENDING]),
            'approved_proposals': len([p for p in proposals if p.status == ProposalStatus.APPROVED]),
            'executed_proposals': len([p for p in proposals if p.status == ProposalStatus.EXECUTED]),
            'rejected_proposals': len([p for p in proposals if p.status == ProposalStatus.REJECTED]),
            'expired_proposals': len([p for p in proposals if p.status == ProposalStatus.EXPIRED]),
            'small_withdrawal_threshold': self.small_withdrawal_threshold,
            'small_withdrawal_signatures': self.small_withdrawal_signatures,
            'large_withdrawal_signatures': self.large_withdrawal_signatures,
            'proposal_expiry_hours': self.proposal_expiry_seconds / 3600
        }

    def save_data(self):
        """Save signers and proposals to disk"""
        os.makedirs(self.data_dir, exist_ok=True)

        # Save signers
        signers_file = os.path.join(self.data_dir, 'signers.json')
        signers_data = {
            sid: {
                'id': s.id,
                'name': s.name,
                'email': s.email,
                'public_key': s.public_key,
                'role': s.role,
                'active': s.active
            }
            for sid, s in self.signers.items()
        }

        with open(signers_file, 'w') as f:
            json.dump(signers_data, f, indent=2)

        # Save proposals
        proposals_file = os.path.join(self.data_dir, 'proposals.json')
        proposals_data = {
            pid: {
                'id': p.id,
                'currency': p.currency,
                'amount': float(p.amount),
                'from_address': p.from_address,
                'to_address': p.to_address,
                'reason': p.reason,
                'proposed_by': p.proposed_by,
                'proposed_at': p.proposed_at,
                'required_signatures': p.required_signatures,
                'signatures': p.signatures,
                'status': p.status.value,
                'expires_at': p.expires_at,
                'executed_at': p.executed_at,
                'tx_hash': p.tx_hash,
                'notes': p.notes
            }
            for pid, p in self.proposals.items()
        }

        with open(proposals_file, 'w') as f:
            json.dump(proposals_data, f, indent=2)

    def load_data(self):
        """Load signers and proposals from disk"""

        # Load signers
        signers_file = os.path.join(self.data_dir, 'signers.json')
        if os.path.exists(signers_file):
            with open(signers_file, 'r') as f:
                signers_data = json.load(f)

            for sid, data in signers_data.items():
                self.signers[sid] = Signer(**data)

        # Load proposals
        proposals_file = os.path.join(self.data_dir, 'proposals.json')
        if os.path.exists(proposals_file):
            with open(proposals_file, 'r') as f:
                proposals_data = json.load(f)

            for pid, data in proposals_data.items():
                data['amount'] = Decimal(str(data['amount']))
                data['status'] = ProposalStatus(data['status'])
                self.proposals[pid] = WithdrawalProposal(**data)


if __name__ == '__main__':
    import sys
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("Multi-Signature Cold Wallet System")
    print("=" * 80)
    print()

    ms = MultiSigColdWallet()

    # Add test signers
    print("Adding signers...")
    ceo = ms.add_signer("Alice Johnson", "alice@aixn.com", "pubkey_alice_123", "CEO")
    cfo = ms.add_signer("Bob Smith", "bob@aixn.com", "pubkey_bob_456", "CFO")
    cto = ms.add_signer("Carol Wang", "carol@aixn.com", "pubkey_carol_789", "CTO")

    print(f"  CEO: {ceo.name} ({ceo.id})")
    print(f"  CFO: {cfo.name} ({cfo.id})")
    print(f"  CTO: {cto.name} ({cto.id})")
    print()

    # Create a small withdrawal proposal
    print("Creating small withdrawal proposal (< $10K)...")
    proposal1 = ms.create_proposal(
        currency='BTC',
        amount=0.05,
        from_address='bc1q_cold_wallet_123',
        to_address='bc1q_hot_wallet_456',
        reason='Refill hot wallet for daily operations',
        proposed_by_id=ceo.id,
        usd_value=2500
    )

    print(f"  Proposal ID: {proposal1.id}")
    print(f"  Required signatures: {proposal1.required_signatures}")
    print(f"  Current signatures: {len(proposal1.signatures)}")
    print()

    # Second signer approves
    print("CFO approving proposal...")
    ms.sign_proposal(proposal1.id, cfo.id, "Approved - standard hot wallet refill")
    proposal1 = ms.proposals[proposal1.id]

    print(f"  Current signatures: {len(proposal1.signatures)}/{proposal1.required_signatures}")
    print(f"  Status: {proposal1.status.value}")
    print(f"  Can execute: {proposal1.can_execute()}")
    print()

    # Get stats
    print("=" * 80)
    print("System Statistics:")
    print("-" * 80)

    stats = ms.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print()
    print("Multi-sig system test complete!")
