"""
Initialize Multi-Signature Cold Wallet System
Sets up authorized signers for cold wallet withdrawals
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.multisig_cold_wallet import MultiSigColdWallet
import hashlib


def generate_public_key(name: str) -> str:
    """Generate a demo public key for a signer"""
    return hashlib.sha256(f"PUBKEY_{name}".encode()).hexdigest()


def main():
    print("=" * 80)
    print("AIXN Exchange - Multi-Signature Cold Wallet Initialization")
    print("=" * 80)
    print()

    multisig = MultiSigColdWallet()

    # Define initial signers
    # In production, these would be actual team members with real keys
    initial_signers = [
        {
            "name": "Chief Executive Officer",
            "email": "ceo@aixnexchange.com",
            "role": "CEO",
        },
        {
            "name": "Chief Financial Officer",
            "email": "cfo@aixnexchange.com",
            "role": "CFO",
        },
        {
            "name": "Chief Technology Officer",
            "email": "cto@aixnexchange.com",
            "role": "CTO",
        },
        {
            "name": "Head of Security",
            "email": "security@aixnexchange.com",
            "role": "Security Lead",
        },
        {
            "name": "Chief Operating Officer",
            "email": "coo@aixnexchange.com",
            "role": "COO",
        },
    ]

    print("Adding authorized signers...\n")

    for signer_data in initial_signers:
        public_key = generate_public_key(signer_data["name"])

        signer = multisig.add_signer(
            name=signer_data["name"],
            email=signer_data["email"],
            public_key=public_key,
            role=signer_data["role"]
        )

        print(f"✓ Added {signer_data['role']}: {signer_data['name']}")
        print(f"  ID: {signer.id}")
        print(f"  Email: {signer_data['email']}")
        print(f"  Public Key: {public_key[:16]}...")
        print()

    print("=" * 80)
    print("MULTI-SIG CONFIGURATION")
    print("=" * 80)
    print()
    print(f"Total Authorized Signers: {len(multisig.signers)}")
    print()
    print("Signature Requirements:")
    print(f"  Small Withdrawals (<$10,000): {multisig.small_withdrawal_signatures} signatures required")
    print(f"  Large Withdrawals (≥$10,000): {multisig.large_withdrawal_signatures} signatures required")
    print(f"  Proposal Expiry: {multisig.proposal_expiry_seconds / 3600:.0f} hours")
    print()

    print("=" * 80)
    print("AUTHORIZED SIGNERS")
    print("=" * 80)
    print()

    for signer_id, signer in multisig.signers.items():
        status = "ACTIVE" if signer.active else "INACTIVE"
        print(f"{signer.role:<20} {signer.name:<30} [{status}]")
        print(f"  ID: {signer.id}")
        print(f"  Email: {signer.email}")
        print()

    print("=" * 80)
    print("WORKFLOW EXAMPLE")
    print("=" * 80)
    print()
    print("To create a cold wallet withdrawal proposal:")
    print()
    print("  from core.multisig_cold_wallet import MultiSigColdWallet")
    print("  multisig = MultiSigColdWallet()")
    print()
    print("  # Create proposal")
    print("  proposal = multisig.create_proposal(")
    print("      currency='BTC',")
    print("      amount=0.5,")
    print("      from_address='bc1q...',")
    print("      to_address='bc1q...',")
    print("      reason='Exchange operational refill',")
    print("      proposed_by_id='signer_001',")
    print("      usd_value=25000  # Determines signature requirement")
    print("  )")
    print()
    print("  # Other signers approve")
    print("  multisig.sign_proposal(proposal.id, 'signer_002', 'Approved')")
    print("  multisig.sign_proposal(proposal.id, 'signer_003', 'Approved')")
    print()
    print("  # Execute when approved")
    print("  if proposal.status == ProposalStatus.APPROVED:")
    print("      multisig.execute_withdrawal(proposal.id)")
    print()

    print("=" * 80)
    print("SECURITY NOTES")
    print("=" * 80)
    print()
    print("⚠ IMPORTANT:")
    print("  1. In production, use real cryptographic keys (not demo keys)")
    print("  2. Store private keys in hardware security modules (HSMs)")
    print("  3. Never store private keys on the exchange server")
    print("  4. Implement key rotation policies")
    print("  5. Use air-gapped signing devices for high-value withdrawals")
    print("  6. Maintain detailed audit logs of all proposals and signatures")
    print()

    print("Initialization complete!")
    print()


if __name__ == "__main__":
    main()
