"""
XAI Blockchain - Pre-mine Generation Script

Generates genesis block with complete pre-mine allocation:
- 11 founder wallets (5M XAI each total including vested portions)
- 1 dev wallet (10M XAI - vested)
- 1 marketing wallet (6M XAI - vested)
- 1 liquidity wallet (400K XAI - monthly vesting)
- 2,323 premium wallets (~1,352-1,602 XAI each, randomized)
- 5,320 bonus wallets (~400-463 XAI each, randomized for miners)
- 10,000 standard wallets (50 XAI each, 920 time capsule eligible)
- 25,000 micro wallets (10 XAI each)
- 1 time capsule reserve (414K XAI)

Total: 26,853,368 XAI across 37,336 wallets

RUN ONCE ONLY - generates genesis block and all pre-mine wallets
"""

import sys
import os
import json
import random  # Used for deterministic seed-based time capsule selection (line 288)
import secrets  # Used for cryptographically secure wallet amount randomization
from datetime import datetime, timezone

# Add core directory to path
from src.xai.core.wallet import Wallet
from src.xai.core.blockchain import Block, Transaction
from src.xai.core.wallet_encryption import WalletEncryption
from src.xai.audit_signer import AuditSigner
from src.xai.core.config import Config

# Timestamps
GENESIS_TIMESTAMP = 1704067200.0  # Jan 1, 2024 00:00:00 UTC
FOUNDER_VEST_START = 1765497600.0  # Dec 12, 2026
DEV_VEST_START = 1799049600.0  # Jan 4, 2028
MARKETING_VEST = 1830585600.0  # Jan 4, 2029
LIQUIDITY_VEST_START = GENESIS_TIMESTAMP  # Immediate monthly vesting

# Founder allocations (immediate amounts)
FOUNDER_IMMEDIATE_AMOUNTS = [
    137500,
    97600,
    112300,
    89400,
    103700,
    78900,
    94200,
    121000,
    68500,
    82300,
    14600,
]

# Pre-calculated ratios (same for vested)
FOUNDER_RATIOS = [amt / 1000000 for amt in FOUNDER_IMMEDIATE_AMOUNTS]


class PreMineGenerator:
    """Generate complete pre-mine allocation"""

    def __init__(self):
        self.all_wallets = []
        self.genesis_transactions = []
        self.wallet_password = None
        self.premium_total = 0
        self.bonus_total = 0
        self.standard_total = 0
        self.micro_total = 0
        self.reserve_total = 0

    def generate_founder_wallets(self):
        """Generate 11 founder wallets with immediate + vested"""
        print("Generating founder wallets...")

        founder_wallets = []

        for i in range(11):
            wallet = Wallet()

            immediate_amount = FOUNDER_IMMEDIATE_AMOUNTS[i]
            vested_amount = FOUNDER_RATIOS[i] * 5000000  # 5M vested, same ratio

            wallet_data = {
                "address": wallet.address,
                "private_key": wallet.private_key,
                "public_key": wallet.public_key,
                "category": "founder",
                "wallet_number": i + 1,
                "immediate_amount": immediate_amount,
                "vested_amount": vested_amount,
                "total_amount": immediate_amount + vested_amount,
                "vest_schedule": {
                    "lock_until": FOUNDER_VEST_START,
                    "releases": [
                        {"date": FOUNDER_VEST_START, "amount": vested_amount * 0.25},
                        {
                            "date": FOUNDER_VEST_START + 31536000,
                            "amount": vested_amount * 0.25,
                        },  # +1 year
                        {
                            "date": FOUNDER_VEST_START + 63072000,
                            "amount": vested_amount * 0.25,
                        },  # +2 years
                        {
                            "date": FOUNDER_VEST_START + 94608000,
                            "amount": vested_amount * 0.25,
                        },  # +3 years
                    ],
                },
            }

            founder_wallets.append(wallet_data)

            # Create COINBASE transaction for immediate
            tx_immediate = Transaction("COINBASE", wallet.address, immediate_amount)
            tx_immediate.txid = tx_immediate.calculate_hash()
            self.genesis_transactions.append(tx_immediate)

            # Create COINBASE transaction for vested (locked)
            tx_vested = Transaction("COINBASE", wallet.address, vested_amount)
            tx_vested.txid = tx_vested.calculate_hash()
            self.genesis_transactions.append(tx_vested)

            print(
                f"  Founder {i+1}: {immediate_amount:,.0f} immediate + {vested_amount:,.0f} vested = {wallet_data['total_amount']:,.0f} XAI"
            )

        self.all_wallets.extend(founder_wallets)
        return founder_wallets

    def generate_vested_wallets(self):
        """Generate dev, marketing, liquidity wallets"""
        print("\nGenerating vested wallets...")

        vested_wallets = []

        # Dev fund
        dev_wallet = Wallet()
        dev_data = {
            "address": dev_wallet.address,
            "private_key": dev_wallet.private_key,
            "public_key": dev_wallet.public_key,
            "category": "dev_fund",
            "amount": 10000000,
            "vest_schedule": {
                "lock_until": DEV_VEST_START,
                "releases": [
                    {"date": DEV_VEST_START, "amount": 2500000},
                    {"date": DEV_VEST_START + 31536000, "amount": 2500000},
                    {"date": DEV_VEST_START + 63072000, "amount": 2500000},
                    {"date": DEV_VEST_START + 94608000, "amount": 2500000},
                ],
            },
        }
        vested_wallets.append(dev_data)

        tx = Transaction("COINBASE", dev_wallet.address, 10000000)
        tx.txid = tx.calculate_hash()
        self.genesis_transactions.append(tx)
        print(f"  Dev Fund: 10,000,000 XAI (vested)")

        # Marketing fund
        marketing_wallet = Wallet()
        marketing_data = {
            "address": marketing_wallet.address,
            "private_key": marketing_wallet.private_key,
            "public_key": marketing_wallet.public_key,
            "category": "marketing",
            "amount": 6000000,
            "vest_schedule": {
                "lock_until": MARKETING_VEST,
                "releases": [{"date": MARKETING_VEST, "amount": 6000000}],  # Single release
            },
        }
        vested_wallets.append(marketing_data)

        tx = Transaction("COINBASE", marketing_wallet.address, 6000000)
        tx.txid = tx.calculate_hash()
        self.genesis_transactions.append(tx)
        print(f"  Marketing: 6,000,000 XAI (vested)")

        # Liquidity fund
        liquidity_wallet = Wallet()
        liquidity_data = {
            "address": liquidity_wallet.address,
            "private_key": liquidity_wallet.private_key,
            "public_key": liquidity_wallet.public_key,
            "category": "liquidity",
            "amount": 400000,
            "vest_schedule": {
                "lock_until": LIQUIDITY_VEST_START,
                "type": "monthly",
                "monthly_amount": 8333.33,
                "duration_months": 48,
            },
        }
        vested_wallets.append(liquidity_data)

        tx = Transaction("COINBASE", liquidity_wallet.address, 400000)
        tx.txid = tx.calculate_hash()
        self.genesis_transactions.append(tx)
        print(f"  Liquidity: 400,000 XAI (monthly vesting)")

        self.all_wallets.extend(vested_wallets)
        return vested_wallets

    def generate_premium_wallets(self):
        """Generate 2,323 premium wallets (~1,352-1,602 XAI each)"""
        print("\nGenerating premium wallets...")

        premium_wallets = []

        sr = secrets.SystemRandom()
        for i in range(2323):
            wallet = Wallet()
            # Use cryptographically secure random for amount distribution
            amount = sr.randint(1352, 1602)

            wallet_data = {
                "address": wallet.address,
                "private_key": wallet.private_key,
                "public_key": wallet.public_key,
                "category": "premium",
                "wallet_number": i + 1,
                "amount": amount,
                "claimed": False,
                "tier": "premium",
            }

            premium_wallets.append(wallet_data)
            self.premium_total += amount

            tx = Transaction("COINBASE", wallet.address, amount)
            tx.txid = tx.calculate_hash()
            self.genesis_transactions.append(tx)

            if (i + 1) % 500 == 0:
                print(f"  Generated {i + 1}/2,323 premium wallets...")

        print(f"  Total premium issuance: {self.premium_total:,} XAI")

        self.all_wallets.extend(premium_wallets)
        return premium_wallets

    def generate_bonus_wallets(self):
        """Generate 5,320 bonus wallets (~400-463 XAI each)"""
        print("\nGenerating bonus wallets for early miners...")

        bonus_wallets = []

        sr = secrets.SystemRandom()
        for i in range(5320):
            wallet = Wallet()
            # Use cryptographically secure random for amount distribution
            amount = sr.randint(400, 463)

            wallet_data = {
                "address": wallet.address,
                "private_key": wallet.private_key,
                "public_key": wallet.public_key,
                "category": "bonus",
                "wallet_number": i + 1,
                "amount": amount,
                "claimed": False,
                "tier": "bonus",
            }

            bonus_wallets.append(wallet_data)
            self.bonus_total += amount

            tx = Transaction("COINBASE", wallet.address, amount)
            tx.txid = tx.calculate_hash()
            self.genesis_transactions.append(tx)

            if (i + 1) % 1000 == 0:
                print(f"  Generated {i + 1}/5,320 bonus wallets...")

        print(f"  Total bonus issuance: {self.bonus_total:,} XAI")

        self.all_wallets.extend(bonus_wallets)
        return bonus_wallets

    def generate_standard_wallets(self):
        """Generate 10,000 standard wallets (50 XAI each, 920 time capsule eligible)"""
        print("\nGenerating standard wallets...")

        standard_wallets = []
        amount_per_wallet = 50

        # Randomly select 920 for time capsule eligibility using cryptographically secure random
        # but seeded for deterministic premine generation
        # Use hash-based selection for deterministic but unpredictable distribution
        import hashlib
        time_capsule_indices = set()
        for i in range(10000):
            # Deterministic but cryptographically unpredictable selection
            hash_val = hashlib.sha256(f"time_capsule_seed_42_{i}".encode()).digest()
            hash_int = int.from_bytes(hash_val[:4], 'big')
            # Select if hash mod 10380 < 1000 (produces ~933, truncated to 920)
            if hash_int % 10380 < 1000:
                time_capsule_indices.add(i)
        # Ensure exactly 920 by truncating to 920 (modulo produces slightly more)
        indices_list = sorted(time_capsule_indices)
        time_capsule_indices = set(indices_list[:920])

        for i in range(10000):
            wallet = Wallet()

            is_time_capsule = i in time_capsule_indices

            wallet_data = {
                "address": wallet.address,
                "private_key": wallet.private_key,
                "public_key": wallet.public_key,
                "category": "standard",
                "wallet_number": i + 1,
                "amount": amount_per_wallet,
                "claimed": False,
                "tier": "standard",
                "time_capsule_eligible": is_time_capsule,
                "time_capsule_bonus": 450 if is_time_capsule else 0,
            }

            standard_wallets.append(wallet_data)

            # Create COINBASE transaction
            tx = Transaction("COINBASE", wallet.address, amount_per_wallet)
            tx.txid = tx.calculate_hash()
            self.genesis_transactions.append(tx)
            self.standard_total += amount_per_wallet

            if (i + 1) % 2000 == 0:
                print(f"  Generated {i + 1}/10,000 standard wallets...")

        print(f"  Total: 10,000 × {amount_per_wallet} = {10000 * amount_per_wallet:,} XAI")
        print(f"  Time capsule eligible: 920 wallets")

        self.all_wallets.extend(standard_wallets)
        return standard_wallets

    def generate_micro_wallets(self):
        """Generate 25,000 micro wallets (10 XAI each)"""
        print("\nGenerating micro wallets...")

        micro_wallets = []
        amount_per_wallet = 10

        for i in range(25000):
            wallet = Wallet()

            wallet_data = {
                "address": wallet.address,
                "private_key": wallet.private_key,
                "public_key": wallet.public_key,
                "category": "micro",
                "wallet_number": i + 1,
                "amount": amount_per_wallet,
                "claimed": False,
                "tier": "micro",
            }

            micro_wallets.append(wallet_data)

            # Create COINBASE transaction
            tx = Transaction("COINBASE", wallet.address, amount_per_wallet)
            tx.txid = tx.calculate_hash()
            self.genesis_transactions.append(tx)
            self.micro_total += amount_per_wallet

            if (i + 1) % 5000 == 0:
                print(f"  Generated {i + 1}/25,000 micro wallets...")

        print(f"  Total: 25,000 × {amount_per_wallet} = {25000 * amount_per_wallet:,} XAI")

        self.all_wallets.extend(micro_wallets)
        return micro_wallets

    def generate_time_capsule_reserve(self):
        """Generate time capsule reserve wallet (414,000 XAI)"""
        print("\nGenerating time capsule reserve...")

        wallet = Wallet()

        reserve_data = {
            "address": wallet.address,
            "private_key": wallet.private_key,
            "public_key": wallet.public_key,
            "category": "time_capsule_reserve",
            "amount": 414000,
            "purpose": "Fund time capsule bonuses (920 × 450 XAI)",
        }

        self.reserve_total = reserve_data["amount"]
        self.all_wallets.append(reserve_data)

        # Create COINBASE transaction
        tx = Transaction("COINBASE", wallet.address, 414000)
        tx.txid = tx.calculate_hash()
        self.genesis_transactions.append(tx)

        print(f"  Reserve: 414,000 XAI")

        return reserve_data

    def mine_genesis_block(self):
        """Mine the genesis block with all transactions"""
        print("\nMining genesis block...")

        # Create genesis block
        genesis_block = Block(
            index=0, transactions=self.genesis_transactions, previous_hash="0", difficulty=4
        )

        # Set genesis timestamp
        genesis_block.timestamp = GENESIS_TIMESTAMP

        # Mine the block
        print("  Mining (this may take a moment)...")
        genesis_block.hash = genesis_block.mine_block()

        print(f"  Genesis block mined!")
        print(f"  Hash: {genesis_block.hash}")
        print(f"  Transactions: {len(self.genesis_transactions)}")

        return genesis_block

    def save_wallets(self, password: str):
        """Save all wallets to encrypted file"""
        print("\nSaving wallets...")

        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        self.wallet_password = password

        # Encrypt all wallets
        encrypted_wallets = []
        for wallet_data in self.all_wallets:
            if "private_key" in wallet_data:
                # Encrypt wallet
                encrypted = WalletEncryption.encrypt_wallet(wallet_data, password)
                encrypted_wallets.append(encrypted)

        # Save to file
        output_file = "premine_wallets_ENCRYPTED.json"
        if os.path.exists(output_file):
            raise RuntimeError(f"Encrypted wallet file already exists: {output_file}")
        with open(output_file, "w") as f:
            json.dump(
                {
                    "total_wallets": len(encrypted_wallets),
                    "encryption": "AES-256 with PBKDF2",
                    "note": "Password required to decrypt",
                    "wallets": encrypted_wallets,
                },
                f,
                indent=2,
            )

        print(f"  Saved {len(encrypted_wallets)} encrypted wallets to {output_file}")

        # Also save unencrypted summary (no private keys)
        summary = []
        for wallet_data in self.all_wallets:
            summary_data = {k: v for k, v in wallet_data.items() if k != "private_key"}
            address = summary_data.get("address", "")
            if not address.startswith(Config.ADDRESS_PREFIX):
                raise ValueError(
                    f"Generated wallet {address} does not match prefix {Config.ADDRESS_PREFIX}"
                )
            summary.append(summary_data)

        summary_file = "premine_wallets_SUMMARY.json"
        with open(summary_file, "w") as f:
            json.dump({"total_wallets": len(summary), "wallets": summary}, f, indent=2)

        print(f"  Saved wallet summary (no private keys) to {summary_file}")

        self._write_manifest(summary)

    def save_genesis_block(self, genesis_block):
        """Save genesis block to file"""
        print("\nSaving genesis block...")

        genesis_data = {
            "index": genesis_block.index,
            "timestamp": genesis_block.timestamp,
            "transactions": [tx.to_dict() for tx in genesis_block.transactions],
            "previous_hash": genesis_block.previous_hash,
            "merkle_root": genesis_block.merkle_root,
            "nonce": genesis_block.nonce,
            "hash": genesis_block.hash,
            "difficulty": genesis_block.difficulty,
            "total_premine": sum(tx.amount for tx in genesis_block.transactions),
            "total_transactions": len(genesis_block.transactions),
        }

        output_file = "genesis.json"
        with open(output_file, "w") as f:
            json.dump(genesis_data, f, indent=2)

        print(f"  Saved genesis block to {output_file}")
        print(f"  Total pre-mine: {genesis_data['total_premine']:,.0f} XAI")

    def _manifest_path(self):
        return os.path.join(os.getcwd(), "premine_manifest.json")

    def _write_manifest(self, summary):
        manifest_path = self._manifest_path()
        signer = AuditSigner(os.getcwd())
        manifest_payload = {
            "network": "testnet",
            "address_prefix": Config.ADDRESS_PREFIX,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_wallets": len(summary),
            "wallets": summary,
        }
        signature = signer.sign(json.dumps(manifest_payload, sort_keys=True))
        manifest_payload["signature"] = signature
        manifest_payload["public_key"] = signer.public_key()

        if os.path.exists(manifest_path):
            with open(manifest_path, "r") as f:
                existing = json.load(f)
            if existing.get("signature") == signature:
                print(f"  Manifest already exists and matches current run ({manifest_path})")
                return
            else:
                raise RuntimeError(
                    f"Manifest already exists with a different signature: {manifest_path}"
                )

        with open(manifest_path, "w") as f:
            json.dump(manifest_payload, f, indent=2)

        print(f"  Saved signed manifest to {manifest_path}")

    def verify_totals(self):
        """Verify all allocations are correct"""
        print("\nVerifying totals...")

        total_xai = sum(tx.amount for tx in self.genesis_transactions)

        # Calculate expected
        founder_total = (
            sum(FOUNDER_IMMEDIATE_AMOUNTS) + 5000000
        )  # immediate + 5M vested per founder
        dev_total = 10000000
        marketing_total = 6000000
        liquidity_total = 400000
        premium_total = self.premium_total
        bonus_total = self.bonus_total
        standard_total = self.standard_total
        micro_total = self.micro_total
        reserve_total = self.reserve_total or 414000

        expected_total = (
            founder_total
            + dev_total
            + marketing_total
            + liquidity_total
            + premium_total
            + bonus_total
            + standard_total
            + micro_total
            + reserve_total
        )

        print(f"  Founder: {founder_total:,} XAI")
        print(f"  Dev: {dev_total:,} XAI")
        print(f"  Marketing: {marketing_total:,} XAI")
        print(f"  Liquidity: {liquidity_total:,} XAI")
        print(f"  Premium: {premium_total:,} XAI")
        print(f"  Bonus: {bonus_total:,} XAI")
        print(f"  Standard: {standard_total:,} XAI")
        print(f"  Micro: {micro_total:,} XAI")
        print(f"  Reserve: {reserve_total:,} XAI")
        print(f"  ─────────────────────────")
        print(f"  Expected: {expected_total:,} XAI")
        print(f"  Actual: {total_xai:,} XAI")

        if abs(total_xai - expected_total) < 0.01:
            print(f"  ✓ Totals match!")
        else:
            print(f"  ✗ ERROR: Totals don't match!")
            raise ValueError(f"Total mismatch: expected {expected_total}, got {total_xai}")

    def generate_all(self, password: str):
        """Generate complete pre-mine"""
        print("=" * 60)
        print("XAI BLOCKCHAIN - PRE-MINE GENERATION")
        print("=" * 60)
        print(f"Genesis timestamp: {datetime.fromtimestamp(GENESIS_TIMESTAMP, tz=timezone.utc)}")
        print("=" * 60)

        # Generate all wallets
        self.generate_founder_wallets()
        self.generate_vested_wallets()
        self.generate_premium_wallets()
        self.generate_bonus_wallets()
        self.generate_standard_wallets()
        self.generate_micro_wallets()
        self.generate_time_capsule_reserve()

        # Verify
        self.verify_totals()

        # Mine genesis
        genesis_block = self.mine_genesis_block()

        # Save everything
        self.save_wallets(password)
        self.save_genesis_block(genesis_block)

        print("\n" + "=" * 60)
        print("PRE-MINE GENERATION COMPLETE")
        print("=" * 60)
        print(f"Total wallets: {len(self.all_wallets):,}")
        print(f"Total transactions: {len(self.genesis_transactions):,}")
        print(f"Total XAI: {sum(tx.amount for tx in self.genesis_transactions):,.0f}")
        print("=" * 60)
        print("\nFiles created:")
        print("  - genesis.json (genesis block)")
        print("  - premine_wallets_ENCRYPTED.json (all wallets, encrypted)")
        print("  - premine_wallets_SUMMARY.json (summary, no private keys)")
        print("\n⚠️  BACKUP THE ENCRYPTED WALLET FILE!")
        print("⚠️  STORE PASSWORD SECURELY!")
        print("=" * 60)


if __name__ == "__main__":
    import getpass

    print("\n⚠️  This script generates the XAI blockchain genesis block.")
    print("⚠️  Run ONCE only!")
    print()

    confirm = input("Generate pre-mine? (type 'YES' to confirm): ")
    if confirm != "YES":
        print("Cancelled.")
        sys.exit(0)

    print()
    password = getpass.getpass("Enter encryption password (min 8 chars): ")
    password_confirm = getpass.getpass("Confirm password: ")

    if password != password_confirm:
        print("Passwords don't match!")
        sys.exit(1)

    if len(password) < 8:
        print("Password must be at least 8 characters!")
        sys.exit(1)

    print()

    # Generate
    generator = PreMineGenerator()
    generator.generate_all(password)
