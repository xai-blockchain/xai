#!/usr/bin/env python3
"""
Example: Send Transaction

This example demonstrates how to send a transaction on the XAI blockchain.
"""

import sys
import os
import json
import time
from pathlib import Path

# Add SDK to path
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk" / "python"))

from xai_sdk import XAIClient, TransactionError, ValidationError


def main():
    """Send transactions and demonstrate transaction operations."""
    
    print("=" * 60)
    print("XAI Blockchain - Send Transaction Example")
    print("=" * 60)
    
    # Initialize client
    client = XAIClient(
        base_url="http://localhost:12001"
    )
    
    try:
        # Create two wallets for transaction
        print("\n1. Creating sender and receiver wallets...")
        sender = client.wallet.create()
        receiver = client.wallet.create()
        
        print(f"   Sender: {sender.address}")
        print(f"   Receiver: {receiver.address}")
        
        # Check initial balances
        print("\n2. Checking initial balances...")
        sender_balance = client.wallet.get_balance(sender.address)
        receiver_balance = client.wallet.get_balance(receiver.address)
        
        print(f"   Sender balance: {sender_balance.balance}")
        print(f"   Receiver balance: {receiver_balance.balance}")
        
        # Estimate transaction fee
        print("\n3. Estimating transaction fee...")
        amount = "1000000000000000000"  # 1 XAI in wei
        
        fee_estimate = client.transaction.estimate_fee(
            from_address=sender.address,
            to_address=receiver.address,
            amount=amount
        )
        print(f"   Gas limit: {fee_estimate['gas_limit']}")
        print(f"   Gas price: {fee_estimate['gas_price']}")
        print(f"   Estimated fee: {fee_estimate['estimated_fee']}")
        
        # Send transaction
        print("\n4. Sending transaction...")
        tx = client.transaction.send(
            from_address=sender.address,
            to_address=receiver.address,
            amount=amount,
            gas_limit=fee_estimate.get('gas_limit', '21000'),
            gas_price=fee_estimate.get('gas_price', '1000000000')
        )
        
        print(f"   Transaction hash: {tx.hash}")
        print(f"   Status: {tx.status}")
        print(f"   Fee: {tx.fee}")
        print(f"   Timestamp: {tx.timestamp}")
        
        # Get transaction details
        print("\n5. Retrieving transaction details...")
        tx_detail = client.transaction.get(tx.hash)
        print(f"   From: {tx_detail.from_address}")
        print(f"   To: {tx_detail.to_address}")
        print(f"   Amount: {tx_detail.amount}")
        print(f"   Status: {tx_detail.status}")
        print(f"   Block number: {tx_detail.block_number}")
        print(f"   Confirmations: {tx_detail.confirmations}")
        
        # Check transaction status
        print("\n6. Checking transaction status...")
        status = client.transaction.get_status(tx.hash)
        print(f"   Status: {status['status']}")
        print(f"   Confirmations: {status['confirmations']}")
        
        # Wait for confirmation (with timeout)
        print("\n7. Waiting for transaction confirmation...")
        print("   This may take a moment...")
        
        try:
            confirmed_tx = client.transaction.wait_for_confirmation(
                tx_hash=tx.hash,
                confirmations=1,
                timeout=300,  # 5 minutes
                poll_interval=5
            )
            print(f"   Transaction confirmed!")
            print(f"   Confirmations: {confirmed_tx.confirmations}")
            print(f"   Block number: {confirmed_tx.block_number}")
        except TransactionError as e:
            print(f"   Transaction confirmation failed: {e}")
        
        # Check final balances
        print("\n8. Checking final balances...")
        sender_final = client.wallet.get_balance(sender.address)
        receiver_final = client.wallet.get_balance(receiver.address)
        
        print(f"   Sender: {sender_final.balance} (change: {int(sender_final.balance) - int(sender_balance.balance)})")
        print(f"   Receiver: {receiver_final.balance} (change: {int(receiver_final.balance) - int(receiver_balance.balance)})")
        
        # Save transaction info
        tx_data = {
            "hash": tx.hash,
            "from": tx.from_address,
            "to": tx.to_address,
            "amount": tx.amount,
            "fee": tx.fee,
            "status": tx.status.value,
            "timestamp": tx.timestamp.isoformat(),
        }
        
        tx_file = "transaction.json"
        with open(tx_file, "w") as f:
            json.dump(tx_data, f, indent=2)
        print(f"\n   Transaction saved to: {tx_file}")
        
        print("\n" + "=" * 60)
        print("SUCCESS: Transaction examples completed!")
        print("=" * 60)
        
    except ValidationError as e:
        print(f"\nERROR: Validation error: {e}")
        return 1
    except TransactionError as e:
        print(f"\nERROR: Transaction error: {e}")
        return 1
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        return 1
    finally:
        client.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
