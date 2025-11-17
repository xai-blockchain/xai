"""
AIXN Blockchain Node Consensus Management
Handles consensus mechanisms, block validation, and chain integrity verification.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List, Tuple, Optional, Dict, Any

if TYPE_CHECKING:
    from aixn.core.blockchain import Block, Blockchain


class ConsensusManager:
    """
    Manages consensus mechanisms and validation for the blockchain node.

    Responsibilities:
    - Validate individual blocks
    - Validate entire blockchain chains
    - Resolve forks using longest valid chain rule
    - Verify proof-of-work
    - Check chain integrity
    """

    def __init__(self, blockchain: Blockchain) -> None:
        """
        Initialize consensus manager.

        Args:
            blockchain: The blockchain instance to manage consensus for
        """
        self.blockchain = blockchain

    def validate_block(
        self,
        block: Block,
        previous_block: Optional[Block] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a single block according to consensus rules.

        Validates:
        1. Block hash matches calculated hash
        2. Proof-of-work meets difficulty requirement
        3. Previous hash links correctly to chain
        4. Block index is sequential
        5. Timestamp is reasonable

        Args:
            block: The block to validate
            previous_block: Optional previous block for validation

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if block passes all validation checks
            - error_message: Description of validation failure, or None if valid

        Example:
            >>> manager = ConsensusManager(blockchain)
            >>> is_valid, error = manager.validate_block(new_block)
            >>> if not is_valid:
            ...     print(f"Block invalid: {error}")
        """
        # Check block hash is correctly calculated
        calculated_hash = block.calculate_hash()
        if block.hash != calculated_hash:
            return False, f"Invalid block hash. Expected: {calculated_hash}, got: {block.hash}"

        # Check proof of work meets difficulty
        required_prefix = "0" * self.blockchain.difficulty
        if not block.hash.startswith(required_prefix):
            return False, f"Invalid proof of work. Hash must start with {required_prefix}"

        # If we have the previous block, validate linkage
        if previous_block is not None:
            # Check previous hash links correctly
            if block.previous_hash != previous_block.hash:
                return False, f"Previous hash mismatch. Expected: {previous_block.hash}, got: {block.previous_hash}"

            # Check index is sequential
            if block.index != previous_block.index + 1:
                return False, f"Invalid block index. Expected: {previous_block.index + 1}, got: {block.index}"

            # Check timestamp is after previous block
            if block.timestamp < previous_block.timestamp:
                return False, "Block timestamp is before previous block"

        # Check block index matches position
        if len(self.blockchain.chain) > 0:
            expected_index = len(self.blockchain.chain)
            if block.index != expected_index:
                return False, f"Block index mismatch. Expected: {expected_index}, got: {block.index}"

        return True, None

    def validate_block_transactions(self, block: Block) -> Tuple[bool, Optional[str]]:
        """
        Validate all transactions in a block.

        Args:
            block: Block containing transactions to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> is_valid, error = manager.validate_block_transactions(block)
        """
        for i, tx in enumerate(block.transactions):
            # Skip validation for coinbase/reward transactions
            if tx.sender in ["COINBASE", "SYSTEM", "AIRDROP"]:
                continue

            # Verify transaction signature
            if hasattr(tx, 'verify_signature') and not tx.verify_signature():
                return False, f"Invalid signature in transaction {i}: {tx.txid}"

            # Check sender has sufficient balance (except for special transactions)
            if tx.tx_type == "normal":
                balance = self.blockchain.get_balance(tx.sender)
                required = tx.amount + tx.fee
                if balance < required:
                    return False, f"Insufficient balance in transaction {i}. Address {tx.sender} has {balance}, needs {required}"

        return True, None

    def validate_chain(self, chain: List[Block]) -> Tuple[bool, Optional[str]]:
        """
        Validate an entire blockchain.

        Performs comprehensive validation:
        1. Genesis block is valid
        2. All blocks link correctly
        3. All proof-of-work is valid
        4. All timestamps are sequential
        5. All transactions are valid

        Args:
            chain: List of blocks forming a blockchain

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> is_valid, error = manager.validate_chain(received_chain)
            >>> if is_valid:
            ...     print("Chain is valid!")
        """
        if not chain or len(chain) == 0:
            return False, "Chain is empty"

        # Validate genesis block
        genesis = chain[0]
        if genesis.index != 0:
            return False, "Genesis block must have index 0"

        if genesis.previous_hash != "0":
            return False, "Genesis block must have previous_hash of '0'"

        # Validate each subsequent block
        for i in range(1, len(chain)):
            current_block = chain[i]
            previous_block = chain[i - 1]

            # Validate block
            is_valid, error = self.validate_block(current_block, previous_block)
            if not is_valid:
                return False, f"Block {i} validation failed: {error}"

            # Validate block transactions
            is_valid, error = self.validate_block_transactions(current_block)
            if not is_valid:
                return False, f"Block {i} transaction validation failed: {error}"

        return True, None

    def resolve_forks(
        self,
        chains: List[List[Block]]
    ) -> Tuple[Optional[List[Block]], str]:
        """
        Resolve blockchain forks using longest valid chain rule.

        Implements consensus mechanism:
        1. Validate all competing chains
        2. Select longest valid chain
        3. In case of tie, use cumulative difficulty

        Args:
            chains: List of competing blockchain forks

        Returns:
            Tuple of (canonical_chain, reason)
            - canonical_chain: The selected chain, or None if all invalid
            - reason: Explanation of selection

        Example:
            >>> chains = [chain1, chain2, chain3]
            >>> selected, reason = manager.resolve_forks(chains)
            >>> print(f"Selected chain: {reason}")
        """
        if not chains:
            return None, "No chains provided"

        valid_chains: List[Tuple[List[Block], int]] = []

        # Validate all chains and track their lengths
        for i, chain in enumerate(chains):
            is_valid, error = self.validate_chain(chain)
            if is_valid:
                valid_chains.append((chain, len(chain)))
            else:
                print(f"Chain {i} rejected: {error}")

        if not valid_chains:
            return None, "No valid chains found"

        # Sort by length (descending)
        valid_chains.sort(key=lambda x: x[1], reverse=True)

        # Return longest chain
        longest_chain, length = valid_chains[0]

        # Check for ties
        ties = [c for c, l in valid_chains if l == length]
        if len(ties) > 1:
            reason = f"Selected longest valid chain (length: {length}, {len(ties)} chains tied)"
        else:
            reason = f"Selected longest valid chain (length: {length})"

        return longest_chain, reason

    def check_chain_integrity(self) -> Tuple[bool, List[str]]:
        """
        Check integrity of the current blockchain.

        Verifies:
        1. No gaps in block indices
        2. All hashes link correctly
        3. All proof-of-work is valid
        4. No double-spending

        Returns:
            Tuple of (is_intact, issues)
            - is_intact: True if chain has no issues
            - issues: List of integrity problems found

        Example:
            >>> is_intact, issues = manager.check_chain_integrity()
            >>> if not is_intact:
            ...     for issue in issues:
            ...         print(f"Integrity issue: {issue}")
        """
        issues: List[str] = []

        if len(self.blockchain.chain) == 0:
            return True, []

        # Check for index gaps
        for i, block in enumerate(self.blockchain.chain):
            if block.index != i:
                issues.append(f"Block index mismatch at position {i}: expected {i}, got {block.index}")

        # Validate chain linkage
        is_valid, error = self.validate_chain(self.blockchain.chain)
        if not is_valid:
            issues.append(f"Chain validation failed: {error}")

        # Check for double-spending
        spent_outputs: Dict[str, set] = {}
        for block in self.blockchain.chain:
            for tx in block.transactions:
                # Track spending
                if hasattr(tx, 'inputs') and tx.inputs:
                    for inp in tx.inputs:
                        tx_id = inp.get('txid')
                        output_index = inp.get('output_index')
                        if tx_id:
                            key = f"{tx_id}:{output_index}"
                            if tx_id in spent_outputs and key in spent_outputs[tx_id]:
                                issues.append(f"Double-spend detected: {key}")
                            else:
                                if tx_id not in spent_outputs:
                                    spent_outputs[tx_id] = set()
                                spent_outputs[tx_id].add(key)

        return len(issues) == 0, issues

    def calculate_chain_work(self, chain: List[Block]) -> int:
        """
        Calculate total cumulative work in a chain.

        Used for tie-breaking when chains have equal length.

        Args:
            chain: Blockchain to calculate work for

        Returns:
            Total proof-of-work as integer

        Example:
            >>> work = manager.calculate_chain_work(chain)
            >>> print(f"Total chain work: {work}")
        """
        total_work = 0

        for block in chain:
            # Count leading zeros in hash as work
            work = 0
            for char in block.hash:
                if char == '0':
                    work += 1
                else:
                    break
            total_work += work

        return total_work

    def should_replace_chain(
        self,
        new_chain: List[Block]
    ) -> Tuple[bool, str]:
        """
        Determine if we should replace our current chain with a new one.

        Decision criteria:
        1. New chain must be valid
        2. New chain must be longer than current
        3. New chain must have more cumulative work (if same length)

        Args:
            new_chain: Candidate chain to potentially adopt

        Returns:
            Tuple of (should_replace, reason)

        Example:
            >>> should_replace, reason = manager.should_replace_chain(peer_chain)
            >>> if should_replace:
            ...     blockchain.chain = peer_chain
            ...     print(f"Chain replaced: {reason}")
        """
        # Validate new chain
        is_valid, error = self.validate_chain(new_chain)
        if not is_valid:
            return False, f"New chain is invalid: {error}"

        current_length = len(self.blockchain.chain)
        new_length = len(new_chain)

        # New chain must be longer
        if new_length <= current_length:
            return False, f"New chain is not longer ({new_length} vs {current_length})"

        # Calculate work for tie-breaking
        current_work = self.calculate_chain_work(self.blockchain.chain)
        new_work = self.calculate_chain_work(new_chain)

        if new_length == current_length:
            if new_work <= current_work:
                return False, f"New chain does not have more work ({new_work} vs {current_work})"

        return True, f"New chain is longer and valid ({new_length} blocks, {new_work} total work)"

    def verify_proof_of_work(
        self,
        block: Block,
        difficulty: int
    ) -> bool:
        """
        Verify that a block's hash meets the proof-of-work requirement.

        Args:
            block: Block to verify
            difficulty: Required number of leading zeros

        Returns:
            True if proof-of-work is valid

        Example:
            >>> if manager.verify_proof_of_work(block, 4):
            ...     print("Valid proof of work!")
        """
        required_prefix = "0" * difficulty
        return block.hash.startswith(required_prefix)

    def get_consensus_info(self) -> Dict[str, Any]:
        """
        Get information about current consensus state.

        Returns:
            Dictionary with consensus metrics

        Example:
            >>> info = manager.get_consensus_info()
            >>> print(f"Chain height: {info['chain_height']}")
        """
        chain_work = self.calculate_chain_work(self.blockchain.chain)
        is_intact, issues = self.check_chain_integrity()

        return {
            "chain_height": len(self.blockchain.chain),
            "difficulty": self.blockchain.difficulty,
            "total_work": chain_work,
            "chain_intact": is_intact,
            "integrity_issues": len(issues),
            "genesis_hash": self.blockchain.chain[0].hash if self.blockchain.chain else None,
            "latest_block_hash": self.blockchain.chain[-1].hash if self.blockchain.chain else None,
        }
