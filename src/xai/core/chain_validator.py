"""
XAI Blockchain - Chain Validation System

Comprehensive blockchain validation performed on startup to ensure:
- Chain integrity (hashes, proof-of-work)
- Transaction validity (signatures, balances)
- UTXO consistency
- Supply cap compliance
- Merkle root validation
- Genesis block verification

This validator detects corruption and provides detailed diagnostics.
"""

import hashlib
import json
import time
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from xai.core.crypto_utils import verify_signature_hex


@dataclass
class ValidationIssue:
    """Represents a validation issue found during chain validation"""

    severity: str  # 'critical', 'error', 'warning'
    block_index: Optional[int]
    issue_type: str
    description: str
    details: Dict = field(default_factory=dict)


@dataclass
class ValidationReport:
    """Complete validation report"""

    success: bool
    total_blocks: int
    total_transactions: int
    validation_time: float
    issues: List[ValidationIssue] = field(default_factory=list)
    utxo_count: int = 0
    total_supply: float = 0.0
    genesis_valid: bool = False
    chain_integrity: bool = False
    signatures_valid: bool = False
    pow_valid: bool = False
    balances_consistent: bool = False
    supply_cap_valid: bool = False
    merkle_roots_valid: bool = False

    def add_issue(
        self,
        severity: str,
        block_index: Optional[int],
        issue_type: str,
        description: str,
        details: Dict = None,
    ):
        """Add a validation issue"""
        issue = ValidationIssue(
            severity=severity,
            block_index=block_index,
            issue_type=issue_type,
            description=description,
            details=details or {},
        )
        self.issues.append(issue)

    def get_critical_issues(self) -> List[ValidationIssue]:
        """Get all critical issues"""
        return [i for i in self.issues if i.severity == "critical"]

    def get_error_issues(self) -> List[ValidationIssue]:
        """Get all error issues"""
        return [i for i in self.issues if i.severity == "error"]

    def get_warning_issues(self) -> List[ValidationIssue]:
        """Get all warning issues"""
        return [i for i in self.issues if i.severity == "warning"]

    def to_dict(self) -> dict:
        """Convert report to dictionary"""
        return {
            "success": self.success,
            "total_blocks": self.total_blocks,
            "total_transactions": self.total_transactions,
            "validation_time": self.validation_time,
            "utxo_count": self.utxo_count,
            "total_supply": self.total_supply,
            "validations": {
                "genesis_valid": self.genesis_valid,
                "chain_integrity": self.chain_integrity,
                "signatures_valid": self.signatures_valid,
                "pow_valid": self.pow_valid,
                "balances_consistent": self.balances_consistent,
                "supply_cap_valid": self.supply_cap_valid,
                "merkle_roots_valid": self.merkle_roots_valid,
            },
            "issues": {
                "critical": len(self.get_critical_issues()),
                "errors": len(self.get_error_issues()),
                "warnings": len(self.get_warning_issues()),
                "total": len(self.issues),
            },
            "issue_details": [
                {
                    "severity": i.severity,
                    "block": i.block_index,
                    "type": i.issue_type,
                    "description": i.description,
                    "details": i.details,
                }
                for i in self.issues
            ],
        }


class ChainValidator:
    """
    Comprehensive blockchain validator

    Validates entire blockchain on startup to ensure:
    1. Genesis block integrity
    2. Sequential block validation (hashes, PoW)
    3. Transaction signature validation
    4. UTXO consistency
    5. Balance consistency
    6. Supply cap compliance
    7. Merkle root validation
    """

    def __init__(self, max_supply: float = 121000000.0, verbose: bool = True):
        """
        Initialize chain validator

        Args:
            max_supply: Maximum supply cap (default: 121M XAI)
            verbose: Print detailed progress during validation
        """
        self.max_supply = max_supply
        self.verbose = verbose
        self.report = None

    def _ensure_report(self):
        """Ensure the validation report exists for helper use."""
        if self.report is None:
            self.report = ValidationReport(
                success=False, total_blocks=0, total_transactions=0, validation_time=0.0
            )

    def validate_chain(
        self, blockchain_data: dict, expected_genesis_hash: Optional[str] = None
    ) -> ValidationReport:
        """
        Validate entire blockchain

        Args:
            blockchain_data: Blockchain dictionary with 'chain' and other data
            expected_genesis_hash: Expected hash of genesis block (optional)

        Returns:
            ValidationReport: Comprehensive validation report
        """
        start_time = time.time()

        # Initialize report
        chain = blockchain_data.get("chain", [])
        self.report = ValidationReport(
            success=False, total_blocks=len(chain), total_transactions=0, validation_time=0.0
        )

        if self.verbose:
            print(f"\n{'='*70}")
            print(f"XAI BLOCKCHAIN VALIDATION")
            print(f"{'='*70}")
            print(f"Total blocks to validate: {len(chain)}")
            print(f"Starting validation at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*70}\n")

        # Validate chain exists
        if not chain or len(chain) == 0:
            self.report.add_issue(
                "critical", None, "empty_chain", "Blockchain is empty - no blocks found"
            )
            self.report.validation_time = time.time() - start_time
            return self.report

        # Step 1: Validate genesis block
        if self.verbose:
            print("[1/7] Validating genesis block...")
        self.report.genesis_valid = self._validate_genesis_block(chain[0], expected_genesis_hash)

        # Step 2: Validate chain integrity (hashes, previous_hash links)
        if self.verbose:
            print("[2/7] Validating chain integrity (block hashes)...")
        self.report.chain_integrity = self._validate_chain_integrity(chain)

        # Step 3: Validate proof-of-work for all blocks
        if self.verbose:
            print("[3/7] Validating proof-of-work...")
        self.report.pow_valid = self._validate_proof_of_work(chain)

        # Step 4: Validate all transaction signatures
        if self.verbose:
            print("[4/7] Validating transaction signatures...")
        self.report.signatures_valid = self._validate_transaction_signatures(chain)

        # Step 5: Rebuild UTXO set and validate balances
        if self.verbose:
            print("[5/7] Rebuilding UTXO set and validating balances...")
        utxo_set, total_supply = self._rebuild_utxo_set(chain)
        self.report.utxo_count = len(utxo_set)
        self.report.total_supply = total_supply
        self.report.balances_consistent = self._validate_balance_consistency(chain, utxo_set)

        # Step 6: Validate supply cap
        if self.verbose:
            print(f"[6/7] Validating supply cap ({self.max_supply:,.0f} XAI)...")
        self.report.supply_cap_valid = self._validate_supply_cap(total_supply)

        # Step 7: Validate merkle roots
        if self.verbose:
            print("[7/7] Validating merkle roots...")
        self.report.merkle_roots_valid = self._validate_merkle_roots(chain)

        # Count total transactions
        self.report.total_transactions = sum(len(block.get("transactions", [])) for block in chain)

        # Determine overall success
        self.report.success = (
            self.report.genesis_valid
            and self.report.chain_integrity
            and self.report.pow_valid
            and self.report.signatures_valid
            and self.report.balances_consistent
            and self.report.supply_cap_valid
            and self.report.merkle_roots_valid
            and len(self.report.get_critical_issues()) == 0
        )

        # Record validation time
        self.report.validation_time = time.time() - start_time

        # Print summary
        if self.verbose:
            self._print_validation_summary()

        return self.report

    def _validate_genesis_block(
        self, genesis_block: dict, expected_hash: Optional[str] = None
    ) -> bool:
        """
        Validate genesis block

        Args:
            genesis_block: Genesis block data
            expected_hash: Expected genesis hash (optional)

        Returns:
            bool: True if valid
        """
        self._ensure_report()
        valid = True

        # Check block index
        if genesis_block.get("index") != 0:
            self.report.add_issue(
                "critical",
                0,
                "genesis_index",
                f"Genesis block has invalid index: {genesis_block.get('index')}",
            )
            valid = False

        # Check previous hash
        if genesis_block.get("previous_hash") != "0":
            self.report.add_issue(
                "critical",
                0,
                "genesis_previous_hash",
                f"Genesis block has invalid previous_hash: {genesis_block.get('previous_hash')}",
            )
            valid = False

        # Check expected hash if provided
        if expected_hash and genesis_block.get("hash") != expected_hash:
            self.report.add_issue(
                "critical",
                0,
                "genesis_hash_mismatch",
                f"Genesis hash mismatch. Expected: {expected_hash}, Got: {genesis_block.get('hash')}",
            )
            valid = False

        # Validate hash calculation
        calculated_hash = self._calculate_block_hash(genesis_block)
        if genesis_block.get("hash") != calculated_hash:
            self.report.add_issue(
                "critical",
                0,
                "genesis_hash_invalid",
                f"Genesis block hash is incorrect",
                {"expected": calculated_hash, "actual": genesis_block.get("hash")},
            )
            valid = False

        if self.verbose and valid:
            print(f"  ✓ Genesis block valid (hash: {genesis_block.get('hash', '')[:16]}...)")

        return valid

    def _validate_chain_integrity(self, chain: List[dict]) -> bool:
        """
        Validate chain integrity (hash links)

        Args:
            chain: List of blocks

        Returns:
            bool: True if valid
        """
        valid = True

        for i in range(1, len(chain)):
            current_block = chain[i]
            previous_block = chain[i - 1]

            # Check block index sequence
            if current_block.get("index") != i:
                self.report.add_issue(
                    "critical",
                    i,
                    "block_index",
                    f"Block has invalid index: {current_block.get('index')}, expected: {i}",
                )
                valid = False

            # Check previous_hash link
            if current_block.get("previous_hash") != previous_block.get("hash"):
                self.report.add_issue(
                    "critical",
                    i,
                    "previous_hash",
                    f"Block previous_hash doesn't match previous block hash",
                    {
                        "expected": previous_block.get("hash"),
                        "actual": current_block.get("previous_hash"),
                    },
                )
                valid = False

            # Validate hash calculation
            calculated_hash = self._calculate_block_hash(current_block)
            if current_block.get("hash") != calculated_hash:
                self.report.add_issue(
                    "critical",
                    i,
                    "block_hash",
                    f"Block hash is incorrect",
                    {"expected": calculated_hash, "actual": current_block.get("hash")},
                )
                valid = False

            # Progress indicator
            if self.verbose and i % 1000 == 0:
                print(f"  Validated {i}/{len(chain)} blocks...")

        if self.verbose and valid:
            print(f"  ✓ Chain integrity verified ({len(chain)} blocks)")

        return valid

    def _validate_proof_of_work(self, chain: List[dict]) -> bool:
        """
        Validate proof-of-work for all blocks

        Args:
            chain: List of blocks

        Returns:
            bool: True if valid
        """
        valid = True

        for i, block in enumerate(chain):
            difficulty = block.get("difficulty", 4)
            block_hash = block.get("hash", "")
            target = "0" * difficulty

            if not block_hash.startswith(target):
                self.report.add_issue(
                    "critical",
                    i,
                    "proof_of_work",
                    f"Block doesn't meet difficulty requirement",
                    {"difficulty": difficulty, "hash": block_hash, "required_prefix": target},
                )
                valid = False

            # Progress indicator
            if self.verbose and i % 1000 == 0 and i > 0:
                print(f"  Validated PoW for {i}/{len(chain)} blocks...")

        if self.verbose and valid:
            print(f"  ✓ Proof-of-work verified for all blocks")

        return valid

    def _validate_transaction_signatures(self, chain: List[dict]) -> bool:
        """
        Validate all transaction signatures

        Args:
            chain: List of blocks

        Returns:
            bool: True if valid
        """
        valid = True
        tx_count = 0

        for i, block in enumerate(chain):
            transactions = block.get("transactions", [])

            for tx in transactions:
                tx_count += 1

                # Skip coinbase transactions (no signature required)
                if tx.get("sender") == "COINBASE":
                    continue

                # Validate signature exists
                if not tx.get("signature"):
                    self.report.add_issue(
                        "error",
                        i,
                        "missing_signature",
                        f"Transaction {tx.get('txid', 'unknown')[:16]}... missing signature",
                    )
                    valid = False
                    continue

                # Validate public key exists
                if not tx.get("public_key"):
                    self.report.add_issue(
                        "error",
                        i,
                        "missing_public_key",
                        f"Transaction {tx.get('txid', 'unknown')[:16]}... missing public key",
                    )
                    valid = False
                    continue

                # Verify signature
                if not self._verify_transaction_signature(tx):
                    self.report.add_issue(
                        "critical",
                        i,
                        "invalid_signature",
                        f"Transaction {tx.get('txid', 'unknown')[:16]}... has invalid signature",
                        {"sender": tx.get("sender"), "txid": tx.get("txid")},
                    )
                    valid = False

            # Progress indicator
            if self.verbose and i % 1000 == 0 and i > 0:
                print(
                    f"  Validated signatures for {tx_count} transactions in {i}/{len(chain)} blocks..."
                )

        if self.verbose and valid:
            print(f"  ✓ All {tx_count} transaction signatures verified")

        return valid

    def _rebuild_utxo_set(self, chain: List[dict]) -> Tuple[Dict[str, List[dict]], float]:
        """
        Rebuild UTXO set from chain

        Args:
            chain: List of blocks

        Returns:
            tuple: (utxo_set, total_supply)
        """
        utxo_set = {}
        total_supply = 0.0

        for i, block in enumerate(chain):
            transactions = block.get("transactions", [])

            for tx in transactions:
                recipient = tx.get("recipient")
                amount = tx.get("amount", 0.0)
                sender = tx.get("sender")
                fee = tx.get("fee", 0.0)

                # Add new UTXO
                if recipient not in utxo_set:
                    utxo_set[recipient] = []

                utxo_set[recipient].append(
                    {"txid": tx.get("txid"), "amount": amount, "spent": False, "block": i}
                )

                total_supply += amount

                # Mark sender's UTXOs as spent
                if sender != "COINBASE" and sender in utxo_set:
                    spent_amount = amount + fee
                    remaining = spent_amount

                    for utxo in utxo_set[sender]:
                        if not utxo["spent"] and remaining > 0:
                            if utxo["amount"] <= remaining:
                                utxo["spent"] = True
                                total_supply -= utxo["amount"]
                                remaining -= utxo["amount"]
                            else:
                                # Partial spend
                                utxo["amount"] -= remaining
                                total_supply -= remaining
                                remaining = 0

            # Progress indicator
            if self.verbose and i % 1000 == 0 and i > 0:
                print(
                    f"  Rebuilt UTXO set for {i}/{len(chain)} blocks (supply: {total_supply:,.2f} XAI)..."
                )

        if self.verbose:
            print(
                f"  ✓ UTXO set rebuilt: {len(utxo_set)} addresses, {total_supply:,.2f} XAI total supply"
            )

        return utxo_set, total_supply

    def _validate_balance_consistency(
        self, chain: List[dict], utxo_set: Dict[str, List[dict]]
    ) -> bool:
        """
        Validate balance consistency (no double spends)

        Args:
            chain: List of blocks
            utxo_set: Rebuilt UTXO set

        Returns:
            bool: True if valid
        """
        valid = True

        # Check for negative balances
        for address, utxos in utxo_set.items():
            balance = sum(utxo["amount"] for utxo in utxos if not utxo["spent"])

            if balance < 0:
                self.report.add_issue(
                    "critical",
                    None,
                    "negative_balance",
                    f"Address has negative balance: {address}",
                    {"balance": balance},
                )
                valid = False

        if self.verbose and valid:
            print(f"  ✓ Balance consistency verified (no negative balances)")

        return valid

    def _validate_supply_cap(self, total_supply: float) -> bool:
        """
        Validate supply doesn't exceed cap

        Args:
            total_supply: Current total supply

        Returns:
            bool: True if valid
        """
        self._ensure_report()
        valid = True

        if total_supply > self.max_supply:
            self.report.add_issue(
                "critical",
                None,
                "supply_cap_exceeded",
                f"Total supply exceeds cap",
                {
                    "total_supply": total_supply,
                    "max_supply": self.max_supply,
                    "excess": total_supply - self.max_supply,
                },
            )
            valid = False

        if self.verbose:
            if valid:
                print(
                    f"  ✓ Supply cap verified: {total_supply:,.2f} / {self.max_supply:,.0f} XAI ({(total_supply/self.max_supply)*100:.2f}%)"
                )
            else:
                print(f"  ✗ Supply cap EXCEEDED: {total_supply:,.2f} / {self.max_supply:,.0f} XAI")

        return valid

    def _validate_merkle_roots(self, chain: List[dict]) -> bool:
        """
        Validate merkle roots for all blocks

        Args:
            chain: List of blocks

        Returns:
            bool: True if valid
        """
        valid = True

        for i, block in enumerate(chain):
            transactions = block.get("transactions", [])
            stored_merkle_root = block.get("merkle_root")

            # Calculate expected merkle root
            calculated_merkle_root = self._calculate_merkle_root(transactions)

            if stored_merkle_root != calculated_merkle_root:
                self.report.add_issue(
                    "error",
                    i,
                    "merkle_root",
                    f"Block merkle root mismatch",
                    {"expected": calculated_merkle_root, "actual": stored_merkle_root},
                )
                valid = False

            # Progress indicator
            if self.verbose and i % 1000 == 0 and i > 0:
                print(f"  Validated merkle roots for {i}/{len(chain)} blocks...")

        if self.verbose and valid:
            print(f"  ✓ All merkle roots verified")

        return valid

    def _calculate_block_hash(self, block: dict) -> str:
        """
        Calculate block hash

        Args:
            block: Block dictionary

        Returns:
            str: Block hash
        """
        block_data = {
            "index": block.get("index"),
            "timestamp": block.get("timestamp"),
            "transactions": block.get("transactions", []),
            "previous_hash": block.get("previous_hash"),
            "merkle_root": block.get("merkle_root"),
            "nonce": block.get("nonce"),
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def _calculate_merkle_root(self, transactions: List[dict]) -> str:
        """
        Calculate merkle root for transactions

        Args:
            transactions: List of transaction dictionaries

        Returns:
            str: Merkle root hash
        """
        if not transactions:
            return hashlib.sha256(b"").hexdigest()

        tx_hashes = [tx.get("txid", "") for tx in transactions]

        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 != 0:
                tx_hashes.append(tx_hashes[-1])

            new_hashes = []
            for i in range(0, len(tx_hashes), 2):
                combined = tx_hashes[i] + tx_hashes[i + 1]
                new_hash = hashlib.sha256(combined.encode()).hexdigest()
                new_hashes.append(new_hash)

            tx_hashes = new_hashes

        return tx_hashes[0]

    def _verify_transaction_signature(self, tx: dict) -> bool:
        """
        Verify transaction signature

        Args:
            tx: Transaction dictionary

        Returns:
            bool: True if signature is valid
        """
        try:
            public_key = tx.get("public_key")
            signature = tx.get("signature")
            sender = tx.get("sender")

            if not public_key or not signature:
                return False

            # Verify address matches public key
            pub_hash = hashlib.sha256(public_key.encode()).hexdigest()
            expected_address = f"XAI{pub_hash[:40]}"

            if expected_address != sender:
                return False

            # Calculate transaction hash
            tx_hash = self._calculate_transaction_hash(tx)

            # Verify signature
            return verify_signature_hex(public_key, tx_hash.encode(), signature)

        except Exception as e:
            return False

    def _calculate_transaction_hash(self, tx: dict) -> str:
        """
        Calculate transaction hash (TXID)

        Args:
            tx: Transaction dictionary

        Returns:
            str: Transaction hash
        """
        tx_data = {
            "sender": tx.get("sender"),
            "recipient": tx.get("recipient"),
            "amount": tx.get("amount"),
            "fee": tx.get("fee"),
            "timestamp": tx.get("timestamp"),
            "nonce": tx.get("nonce"),
        }
        tx_string = json.dumps(tx_data, sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()

    def _print_validation_summary(self):
        """Print validation summary"""
        print(f"\n{'='*70}")
        print(f"VALIDATION SUMMARY")
        print(f"{'='*70}")
        print(f"Status: {'✓ PASSED' if self.report.success else '✗ FAILED'}")
        print(f"Validation Time: {self.report.validation_time:.2f} seconds")
        print(f"Total Blocks: {self.report.total_blocks:,}")
        print(f"Total Transactions: {self.report.total_transactions:,}")
        print(f"Total Supply: {self.report.total_supply:,.2f} XAI")
        print(f"UTXO Addresses: {self.report.utxo_count:,}")
        print(f"\nValidation Checks:")
        print(f"  Genesis Block:        {'✓' if self.report.genesis_valid else '✗'}")
        print(f"  Chain Integrity:      {'✓' if self.report.chain_integrity else '✗'}")
        print(f"  Proof-of-Work:        {'✓' if self.report.pow_valid else '✗'}")
        print(f"  Transaction Signatures: {'✓' if self.report.signatures_valid else '✗'}")
        print(f"  Balance Consistency:  {'✓' if self.report.balances_consistent else '✗'}")
        print(f"  Supply Cap:           {'✓' if self.report.supply_cap_valid else '✗'}")
        print(f"  Merkle Roots:         {'✓' if self.report.merkle_roots_valid else '✗'}")

        # Print issues
        critical = self.report.get_critical_issues()
        errors = self.report.get_error_issues()
        warnings = self.report.get_warning_issues()

        if critical or errors or warnings:
            print(f"\nIssues Found:")
            print(f"  Critical: {len(critical)}")
            print(f"  Errors:   {len(errors)}")
            print(f"  Warnings: {len(warnings)}")

            # Print first few critical issues
            if critical:
                print(f"\nCritical Issues:")
                for issue in critical[:5]:
                    block_str = (
                        f"Block {issue.block_index}" if issue.block_index is not None else "Chain"
                    )
                    print(f"  - [{block_str}] {issue.description}")
                if len(critical) > 5:
                    print(f"  ... and {len(critical) - 5} more")

            # Print first few errors
            if errors:
                print(f"\nErrors:")
                for issue in errors[:5]:
                    block_str = (
                        f"Block {issue.block_index}" if issue.block_index is not None else "Chain"
                    )
                    print(f"  - [{block_str}] {issue.description}")
                if len(errors) > 5:
                    print(f"  ... and {len(errors) - 5} more")

        print(f"{'='*70}\n")


def validate_blockchain_on_startup(
    blockchain_data: dict,
    max_supply: float = 121000000.0,
    expected_genesis_hash: Optional[str] = None,
    verbose: bool = True,
) -> Tuple[bool, ValidationReport]:
    """
    Validate blockchain on startup

    This is the main entry point for chain validation.
    Should be called after loading blockchain from disk.

    Args:
        blockchain_data: Blockchain dictionary
        max_supply: Maximum supply cap
        expected_genesis_hash: Expected genesis hash (optional)
        verbose: Print detailed progress

    Returns:
        tuple: (success: bool, report: ValidationReport)
    """
    validator = ChainValidator(max_supply=max_supply, verbose=verbose)
    report = validator.validate_chain(blockchain_data, expected_genesis_hash)

    return report.success, report


# Example usage and testing
if __name__ == "__main__":
    import sys
    import os

    from xai.core.blockchain_persistence import BlockchainStorage

    print("XAI Chain Validator - Test Mode\n")

    # Try to load blockchain from disk
    storage = BlockchainStorage()
    success, blockchain_data, message = storage.load_from_disk()

    if success:
        print(f"Loaded blockchain: {message}\n")

        # Validate the chain
        is_valid, report = validate_blockchain_on_startup(
            blockchain_data, max_supply=121000000.0, verbose=True
        )

        # Save report to file
        report_file = os.path.join(storage.data_dir, "validation_report.json")
        with open(report_file, "w") as f:
            json.dump(report.to_dict(), f, indent=2)

        print(f"\nValidation report saved to: {report_file}")

        # Exit with appropriate code
        sys.exit(0 if is_valid else 1)
    else:
        print(f"Failed to load blockchain: {message}")
        sys.exit(1)
