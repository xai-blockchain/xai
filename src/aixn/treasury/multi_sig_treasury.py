from typing import List, Dict, Any


class MultiSigTreasury:
    def __init__(self, owners: List[str], threshold: int):
        if not owners:
            raise ValueError("Owners list cannot be empty.")
        if not isinstance(threshold, int) or not (1 <= threshold <= len(owners)):
            raise ValueError(
                f"Threshold must be an integer between 1 and the number of owners ({len(owners)})."
            )

        self.owners = sorted([owner.lower() for owner in owners])
        self.threshold = threshold
        self.balance = 0.0  # Conceptual balance

        # Stores pending transactions: {tx_id: {"proposer": str, "recipient": str, "amount": float, "approvals": set, "executed": bool}}
        self.pending_transactions: Dict[str, Dict[str, Any]] = {}
        self._transaction_id_counter = 0
        print(
            f"MultiSigTreasury initialized with owners: {self.owners} and threshold: {self.threshold}-of-{len(self.owners)}."
        )

    def deposit(self, amount: float):
        """Simulates depositing funds into the treasury."""
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Deposit amount must be a positive number.")
        self.balance += amount
        print(f"Deposited {amount:.2f}. New treasury balance: {self.balance:.2f}")

    def get_balance(self) -> float:
        """Returns the current treasury balance."""
        return self.balance

    def submit_transaction(self, proposer: str, recipient: str, amount: float) -> str:
        """
        Submits a new transaction for approval.
        Only owners can propose transactions.
        """
        if proposer.lower() not in self.owners:
            raise ValueError(f"Proposer {proposer} is not an authorized owner.")
        if not recipient:
            raise ValueError("Recipient cannot be empty.")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Transaction amount must be a positive number.")
        if amount > self.balance:
            raise ValueError(
                f"Insufficient treasury balance ({self.balance:.2f}) for transaction amount ({amount:.2f})."
            )

        self._transaction_id_counter += 1
        tx_id = f"tx_{self._transaction_id_counter}"

        self.pending_transactions[tx_id] = {
            "proposer": proposer.lower(),
            "recipient": recipient.lower(),
            "amount": amount,
            "approvals": set(),
            "executed": False,
        }
        print(f"Transaction {tx_id} submitted by {proposer} for {amount:.2f} to {recipient}.")
        return tx_id

    def approve_transaction(self, approver: str, tx_id: str):
        """
        An owner approves a pending transaction.
        """
        if approver.lower() not in self.owners:
            raise ValueError(f"Approver {approver} is not an authorized owner.")

        transaction = self.pending_transactions.get(tx_id)
        if not transaction:
            raise ValueError(f"Transaction {tx_id} not found.")
        if transaction["executed"]:
            raise ValueError(f"Transaction {tx_id} has already been executed.")
        if approver.lower() in transaction["approvals"]:
            print(f"Approver {approver} has already approved transaction {tx_id}.")
            return

        transaction["approvals"].add(approver.lower())
        print(
            f"Approver {approver} approved transaction {tx_id}. Current approvals: {len(transaction['approvals'])}/{self.threshold}"
        )

    def execute_transaction(self, executor: str, tx_id: str):
        """
        Executes a transaction if the approval threshold is met.
        Any owner can attempt to execute.
        """
        if executor.lower() not in self.owners:
            raise ValueError(f"Executor {executor} is not an authorized owner.")

        transaction = self.pending_transactions.get(tx_id)
        if not transaction:
            raise ValueError(f"Transaction {tx_id} not found.")
        if transaction["executed"]:
            raise ValueError(f"Transaction {tx_id} has already been executed.")

        if len(transaction["approvals"]) < self.threshold:
            raise ValueError(
                f"Transaction {tx_id} does not have enough approvals. Required: {self.threshold}, Current: {len(transaction['approvals'])}"
            )

        if transaction["amount"] > self.balance:
            raise ValueError(
                f"Insufficient treasury balance ({self.balance:.2f}) for transaction amount ({transaction['amount']:.2f}). Cannot execute."
            )

        self.balance -= transaction["amount"]
        transaction["executed"] = True
        print(
            f"Transaction {tx_id} executed by {executor}. Amount {transaction['amount']:.2f} sent to {transaction['recipient']}. New treasury balance: {self.balance:.2f}"
        )


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
        print(f"Error (expected): {e}")

    print(f"\nFinal Treasury Balance: {treasury.get_balance():.2f}")
