from typing import List, Dict, Any, Optional
import hashlib
import logging
import threading
import time

logger = logging.getLogger(__name__)


class MultiSigTreasury:
    def __init__(self, owners: List[str], threshold: int, require_signatures: bool = True):
        """
        Initialize M-of-N multisig treasury with signature collection.

        Args:
            owners: List of owner addresses
            threshold: M in M-of-N (number of approvals required)
            require_signatures: Whether to require cryptographic signatures
        """
        if not owners:
            raise ValueError("Owners list cannot be empty.")
        if not isinstance(threshold, int) or not (1 <= threshold <= len(owners)):
            raise ValueError(
                f"Threshold must be an integer between 1 and the number of owners ({len(owners)})."
            )

        self.owners = sorted([owner.lower() for owner in owners])
        self.threshold = threshold
        self.require_signatures = require_signatures
        self.balance = 0.0  # Conceptual balance

        # Stores pending transactions with signature data
        self.pending_transactions: Dict[str, Dict[str, Any]] = {}
        self._transaction_id_counter = 0

        # Track executed transactions for fund tracking
        self.executed_transactions: List[Dict[str, Any]] = []

        # Fund tracking by category
        self.fund_allocations: Dict[str, float] = {
            "development": 0.0,
            "marketing": 0.0,
            "operations": 0.0,
            "reserve": 0.0,
            "other": 0.0
        }

        self._lock = threading.RLock()

        logger.info(
            f"MultiSigTreasury initialized. Owners: {len(self.owners)}, "
            f"Threshold: {self.threshold}-of-{len(self.owners)}, "
            f"Signatures required: {require_signatures}"
        )

    def deposit(self, amount: float, category: str = "reserve"):
        """
        Deposit funds into the treasury with category tracking.

        Args:
            amount: Amount to deposit
            category: Fund category (development, marketing, operations, reserve, other)
        """
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Deposit amount must be a positive number.")

        if category not in self.fund_allocations:
            category = "other"

        with self._lock:
            self.balance += amount
            self.fund_allocations[category] += amount
            logger.info(
                f"Deposited {amount:.2f} to {category}. "
                f"New balance: {self.balance:.2f}, {category}: {self.fund_allocations[category]:.2f}"
            )

    def get_balance(self) -> float:
        """Returns the current treasury balance."""
        return self.balance

    def get_fund_breakdown(self) -> Dict[str, float]:
        """Get detailed fund allocation breakdown."""
        with self._lock:
            return {
                "total": self.balance,
                **self.fund_allocations,
                "allocated": sum(self.fund_allocations.values())
            }

    def _generate_tx_hash(self, tx_id: str, recipient: str, amount: float, nonce: int) -> str:
        """Generate transaction hash for signature verification."""
        data = f"{tx_id}:{recipient}:{amount}:{nonce}".encode()
        return hashlib.sha256(data).hexdigest()

    def submit_transaction(self, proposer: str, recipient: str, amount: float,
                          description: str = "", category: str = "other") -> str:
        """
        Submit a new transaction for M-of-N approval.

        Args:
            proposer: Address of proposer (must be owner)
            recipient: Recipient address
            amount: Amount to transfer
            description: Transaction description
            category: Fund category

        Returns:
            Transaction ID
        """
        if proposer.lower() not in self.owners:
            raise ValueError(f"Proposer {proposer} is not an authorized owner.")
        if not recipient:
            raise ValueError("Recipient cannot be empty.")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Transaction amount must be a positive number.")

        with self._lock:
            if amount > self.balance:
                raise ValueError(
                    f"Insufficient treasury balance ({self.balance:.2f}) for transaction amount ({amount:.2f})."
                )

            self._transaction_id_counter += 1
            tx_id = f"tx_{self._transaction_id_counter}"
            nonce = int(time.time() * 1000)

            tx_hash = self._generate_tx_hash(tx_id, recipient, amount, nonce)

            self.pending_transactions[tx_id] = {
                "proposer": proposer.lower(),
                "recipient": recipient.lower(),
                "amount": amount,
                "description": description,
                "category": category,
                "approvals": set(),
                "signatures": {},  # {owner: signature}
                "executed": False,
                "created_at": int(time.time()),
                "nonce": nonce,
                "tx_hash": tx_hash
            }

            logger.info(
                f"Transaction {tx_id} submitted by {proposer}: "
                f"{amount:.2f} to {recipient} ({category}). Hash: {tx_hash[:16]}..."
            )

            return tx_id

    def approve_transaction(self, approver: str, tx_id: str, signature: Optional[str] = None):
        """
        Approve a pending transaction with signature collection.

        Args:
            approver: Address of approver (must be owner)
            tx_id: Transaction ID to approve
            signature: Optional cryptographic signature
        """
        if approver.lower() not in self.owners:
            raise ValueError(f"Approver {approver} is not an authorized owner.")

        with self._lock:
            transaction = self.pending_transactions.get(tx_id)
            if not transaction:
                raise ValueError(f"Transaction {tx_id} not found.")
            if transaction["executed"]:
                raise ValueError(f"Transaction {tx_id} has already been executed.")

            if approver.lower() in transaction["approvals"]:
                logger.debug(f"Approver {approver} has already approved transaction {tx_id}")
                return

            # Verify signature if required
            if self.require_signatures:
                if not signature:
                    raise ValueError("Signature required for approval")
                # In production, verify signature against tx_hash
                # For now, store signature
                transaction["signatures"][approver.lower()] = signature

            transaction["approvals"].add(approver.lower())

            logger.info(
                f"Transaction {tx_id} approved by {approver}. "
                f"Approvals: {len(transaction['approvals'])}/{self.threshold}"
            )

            # Auto-execute if threshold met
            if len(transaction["approvals"]) >= self.threshold:
                logger.info(f"Transaction {tx_id} reached threshold, ready for execution")

    def get_transaction_status(self, tx_id: str) -> Dict[str, Any]:
        """Get detailed status of a transaction."""
        with self._lock:
            transaction = self.pending_transactions.get(tx_id)
            if not transaction:
                # Check executed transactions
                for exec_tx in self.executed_transactions:
                    if exec_tx["tx_id"] == tx_id:
                        return {
                            "tx_id": tx_id,
                            "status": "executed",
                            "executed_at": exec_tx.get("executed_at"),
                            **exec_tx
                        }
                raise ValueError(f"Transaction {tx_id} not found")

            return {
                "tx_id": tx_id,
                "status": "pending" if not transaction["executed"] else "executed",
                "proposer": transaction["proposer"],
                "recipient": transaction["recipient"],
                "amount": transaction["amount"],
                "description": transaction.get("description", ""),
                "category": transaction.get("category", "other"),
                "approvals": list(transaction["approvals"]),
                "approval_count": len(transaction["approvals"]),
                "threshold": self.threshold,
                "ready_to_execute": len(transaction["approvals"]) >= self.threshold,
                "created_at": transaction.get("created_at"),
                "tx_hash": transaction.get("tx_hash")
            }

    def execute_transaction(self, executor: str, tx_id: str):
        """
        Execute a transaction when M-of-N threshold is met.

        Args:
            executor: Address executing (must be owner)
            tx_id: Transaction ID to execute
        """
        if executor.lower() not in self.owners:
            raise ValueError(f"Executor {executor} is not an authorized owner.")

        with self._lock:
            transaction = self.pending_transactions.get(tx_id)
            if not transaction:
                raise ValueError(f"Transaction {tx_id} not found.")
            if transaction["executed"]:
                raise ValueError(f"Transaction {tx_id} has already been executed.")

            if len(transaction["approvals"]) < self.threshold:
                raise ValueError(
                    f"Transaction {tx_id} does not have enough approvals. "
                    f"Required: {self.threshold}, Current: {len(transaction['approvals'])}"
                )

            if transaction["amount"] > self.balance:
                raise ValueError(
                    f"Insufficient treasury balance ({self.balance:.2f}) for "
                    f"transaction amount ({transaction['amount']:.2f}). Cannot execute."
                )

            # Verify signatures if required
            if self.require_signatures and len(transaction["signatures"]) < self.threshold:
                raise ValueError(
                    f"Insufficient signatures. Required: {self.threshold}, "
                    f"Current: {len(transaction['signatures'])}"
                )

            # Execute transaction
            self.balance -= transaction["amount"]
            category = transaction.get("category", "other")
            if category in self.fund_allocations:
                self.fund_allocations[category] -= min(transaction["amount"], self.fund_allocations[category])

            transaction["executed"] = True
            transaction["executed_at"] = int(time.time())
            transaction["executor"] = executor.lower()

            # Move to executed transactions
            exec_record = {
                "tx_id": tx_id,
                **transaction
            }
            self.executed_transactions.append(exec_record)

            # Remove from pending
            del self.pending_transactions[tx_id]

            logger.info(
                f"Transaction {tx_id} executed by {executor}. "
                f"Amount {transaction['amount']:.2f} sent to {transaction['recipient']}. "
                f"New balance: {self.balance:.2f}"
            )

    def get_pending_transactions(self) -> List[Dict[str, Any]]:
        """Get all pending transactions."""
        with self._lock:
            return [
                {
                    "tx_id": tx_id,
                    "approvals": len(tx["approvals"]),
                    "threshold": self.threshold,
                    "amount": tx["amount"],
                    "recipient": tx["recipient"],
                    "ready": len(tx["approvals"]) >= self.threshold
                }
                for tx_id, tx in self.pending_transactions.items()
            ]

    def get_executed_transactions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recently executed transactions."""
        with self._lock:
            return self.executed_transactions[-limit:]


# Example Usage (for testing purposes)
if __name__ == "__main__":
    owners_list = ["Alice", "Bob", "Charlie", "David", "Eve"]
    treasury = MultiSigTreasury(owners_list, threshold=3)  # 3-of-5 multi-sig

    treasury.deposit(1000.0)

    print("\n--- Scenario 1: Successful Transaction ---")
    tx1_id = treasury.submit_transaction("Alice", "0xDevFund", 200.0)
    treasury.approve_transaction("Bob", tx1_id)
    treasury.approve_transaction("Charlie", tx1_id)
    treasury.execute_transaction("David", tx1_id)

    print("\n--- Scenario 2: Insufficient Approvals ---")
    tx2_id = treasury.submit_transaction("Bob", "0xMarketing", 300.0)
    treasury.approve_transaction("Alice", tx2_id)
    try:
        treasury.execute_transaction("Eve", tx2_id)  # Should fail
    except ValueError as e:
        logger.warning(
            "ValueError in get_executed_transactions",
            error_type="ValueError",
            error=str(e),
            function="get_executed_transactions",
        )
        print(f"Error (expected): {e}")

    print("\n--- Scenario 3: Duplicate Approval ---")
    treasury.approve_transaction("Alice", tx2_id)  # Alice already approved, should print message
    treasury.approve_transaction("David", tx2_id)  # Now 3 approvals
    treasury.execute_transaction("Charlie", tx2_id)

    print("\n--- Scenario 4: Insufficient Balance (after previous transactions) ---")
    try:
        tx3_id = treasury.submit_transaction(
            "Eve", "0xGrant", 600.0
        )  # Balance is 1000 - 200 - 300 = 500
    except ValueError as e:
        logger.warning(
            "ValueError in get_executed_transactions",
            error_type="ValueError",
            error=str(e),
            function="get_executed_transactions",
        )
        print(f"Error (expected): {e}")

    print(f"\nFinal Treasury Balance: {treasury.get_balance():.2f}")
