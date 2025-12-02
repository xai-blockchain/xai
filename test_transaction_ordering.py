#!/usr/bin/env python3
"""
Test script to demonstrate transaction ordering rules for MEV prevention.

This script shows how the new transaction ordering validation prevents:
- MEV (Miner Extractable Value) attacks
- Front-running attacks
- Transaction reordering for profit
- Nonce sequencing bypass
"""

from xai.core.transaction import Transaction
from xai.core.advanced_consensus import TransactionOrdering
from xai.core.wallet import Wallet
import time


def demo_coinbase_ordering():
    """Demo: Coinbase must be first"""
    print("\n=== Demo 1: Coinbase Ordering ===")

    wallet = Wallet()

    # Create transactions
    coinbase = Transaction("COINBASE", wallet.address, 12.5)
    coinbase.txid = coinbase.calculate_hash()

    regular_tx = Transaction(wallet.address, "XAI" + "1" * 40, 5.0, 0.01, public_key=wallet.public_key)
    regular_tx.txid = regular_tx.calculate_hash()

    # Correct order: coinbase first
    correct = [coinbase, regular_tx]
    print(f"Correct order (coinbase first): {TransactionOrdering.validate_transaction_order(correct)}")

    # Wrong order: coinbase not first
    wrong = [regular_tx, coinbase]
    print(f"Wrong order (coinbase not first): {TransactionOrdering.validate_transaction_order(wrong)}")


def demo_duplicate_detection():
    """Demo: No duplicate transactions allowed"""
    print("\n=== Demo 2: Duplicate Detection ===")

    wallet = Wallet()

    coinbase = Transaction("COINBASE", wallet.address, 12.5)
    coinbase.txid = coinbase.calculate_hash()

    tx1 = Transaction(wallet.address, "XAI" + "1" * 40, 5.0, 0.01, public_key=wallet.public_key)
    tx1.txid = tx1.calculate_hash()

    # Duplicate transaction (same txid)
    tx2 = tx1  # Same object = same txid

    transactions = [coinbase, tx1, tx2]
    print(f"With duplicate transaction: {TransactionOrdering.validate_transaction_order(transactions)}")

    # No duplicates
    tx3 = Transaction(wallet.address, "XAI" + "2" * 40, 3.0, 0.01, public_key=wallet.public_key)
    tx3.txid = tx3.calculate_hash()

    transactions_no_dup = [coinbase, tx1, tx3]
    print(f"Without duplicates: {TransactionOrdering.validate_transaction_order(transactions_no_dup)}")


def demo_nonce_sequencing():
    """Demo: Same-sender transactions must be in nonce order"""
    print("\n=== Demo 3: Nonce Sequencing (MEV Prevention) ===")

    wallet = Wallet()

    coinbase = Transaction("COINBASE", wallet.address, 12.5)
    coinbase.txid = coinbase.calculate_hash()

    # Same sender, different nonces
    tx1 = Transaction(wallet.address, "XAI" + "1" * 40, 5.0, 0.01, public_key=wallet.public_key, nonce=1)
    tx1.txid = tx1.calculate_hash()

    tx2 = Transaction(wallet.address, "XAI" + "2" * 40, 3.0, 0.01, public_key=wallet.public_key, nonce=2)
    tx2.txid = tx2.calculate_hash()

    tx3 = Transaction(wallet.address, "XAI" + "3" * 40, 2.0, 0.01, public_key=wallet.public_key, nonce=3)
    tx3.txid = tx3.calculate_hash()

    # Correct nonce order: 1, 2, 3
    correct = [coinbase, tx1, tx2, tx3]
    print(f"Correct nonce order (1→2→3): {TransactionOrdering.validate_transaction_order(correct)}")

    # Wrong nonce order: 1, 3, 2 (skips nonce 2, then goes back)
    wrong = [coinbase, tx1, tx3, tx2]
    print(f"Wrong nonce order (1→3→2): {TransactionOrdering.validate_transaction_order(wrong)}")


def demo_fee_ordering_same_sender():
    """Demo: Same sender without nonces must be fee-ordered"""
    print("\n=== Demo 4: Fee Ordering for Same Sender (No Nonces) ===")

    wallet = Wallet()

    coinbase = Transaction("COINBASE", wallet.address, 12.5)
    coinbase.txid = coinbase.calculate_hash()

    # Same sender, no nonces, different fees
    tx_high_fee = Transaction(wallet.address, "XAI" + "1" * 40, 5.0, 0.5, public_key=wallet.public_key)
    tx_high_fee.txid = tx_high_fee.calculate_hash()

    tx_low_fee = Transaction(wallet.address, "XAI" + "2" * 40, 3.0, 0.1, public_key=wallet.public_key)
    tx_low_fee.txid = tx_low_fee.calculate_hash()

    # Correct: higher fee first
    correct = [coinbase, tx_high_fee, tx_low_fee]
    print(f"Correct fee order (0.5→0.1): {TransactionOrdering.validate_transaction_order(correct)}")

    # Wrong: lower fee first
    wrong = [coinbase, tx_low_fee, tx_high_fee]
    print(f"Wrong fee order (0.1→0.5): {TransactionOrdering.validate_transaction_order(wrong)}")


def demo_automatic_ordering():
    """Demo: Automatic transaction ordering with nonces"""
    print("\n=== Demo 5: Automatic Transaction Ordering ===")

    wallet1 = Wallet()
    wallet2 = Wallet()

    # Create mixed transactions
    coinbase = Transaction("COINBASE", wallet1.address, 12.5)
    coinbase.txid = coinbase.calculate_hash()

    # Wallet 1 transactions with nonces
    w1_tx1 = Transaction(wallet1.address, "XAI" + "1" * 40, 5.0, 0.1, public_key=wallet1.public_key, nonce=1)
    w1_tx1.txid = w1_tx1.calculate_hash()

    w1_tx2 = Transaction(wallet1.address, "XAI" + "2" * 40, 3.0, 0.5, public_key=wallet1.public_key, nonce=2)
    w1_tx2.txid = w1_tx2.calculate_hash()

    # Wallet 2 transaction
    w2_tx = Transaction(wallet2.address, "XAI" + "3" * 40, 10.0, 1.0, public_key=wallet2.public_key, nonce=1)
    w2_tx.txid = w2_tx.calculate_hash()

    # Unordered list
    unordered = [w1_tx2, w2_tx, coinbase, w1_tx1]  # Random order

    # Order automatically
    ordered = TransactionOrdering.order_transactions(unordered)

    print("Original order:")
    for i, tx in enumerate(unordered):
        print(f"  {i}: sender={tx.sender[:8] if tx.sender != 'COINBASE' else 'COINBASE':8s}, fee={tx.fee:.1f}, nonce={tx.nonce}")

    print("\nOrdered (for block inclusion):")
    for i, tx in enumerate(ordered):
        print(f"  {i}: sender={tx.sender[:8] if tx.sender != 'COINBASE' else 'COINBASE':8s}, fee={tx.fee:.1f}, nonce={tx.nonce}")

    print(f"\nValidation result: {TransactionOrdering.validate_transaction_order(ordered)}")


if __name__ == "__main__":
    print("=" * 70)
    print("Transaction Ordering Rules - MEV Prevention Demonstration")
    print("=" * 70)

    demo_coinbase_ordering()
    demo_duplicate_detection()
    demo_nonce_sequencing()
    demo_fee_ordering_same_sender()
    demo_automatic_ordering()

    print("\n" + "=" * 70)
    print("All demonstrations complete!")
    print("=" * 70)
