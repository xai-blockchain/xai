#!/usr/bin/env python3
"""
Example: Check Balance

This example demonstrates how to check wallet balances and retrieve
transaction history.
"""

import sys
import os
import json
from pathlib import Path

# Add SDK to path
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk" / "python"))

from xai_sdk import XAIClient, WalletError, ValidationError


def main():
    """Check wallet balance and transaction history."""
    
    print("=" * 60)
    print("XAI Blockchain - Check Balance Example")
    print("=" * 60)
    
    # Initialize client
    client = XAIClient(
        base_url="http://localhost:5000"
    )
    
    try:
        # Create a wallet to check balance
        print("\n1. Creating wallet...")
        wallet = client.wallet.create()
        print(f"   Address: {wallet.address}")
        
        # Get wallet details
        print("\n2. Retrieving wallet details...")
        wallet_info = client.wallet.get(wallet.address)
        print(f"   Public Key: {wallet_info.public_key}")
        print(f"   Created: {wallet_info.created_at}")
        print(f"   Nonce: {wallet_info.nonce}")
        print(f"   Type: {wallet_info.wallet_type}")
        
        # Get balance
        print("\n3. Checking wallet balance...")
        balance = client.wallet.get_balance(wallet.address)
        
        print(f"   Address: {balance.address}")
        print(f"   Total Balance: {balance.balance} wei")
        print(f"   Available Balance: {balance.available_balance} wei")
        print(f"   Locked Balance: {balance.locked_balance} wei")
        print(f"   Nonce: {balance.nonce}")
        
        # Convert to human-readable format
        balance_eth = float(balance.balance) / 1e18
        print(f"\n   Total Balance (XAI): {balance_eth:.6f}")
        
        # Get transaction history
        print("\n4. Retrieving transaction history...")
        history = client.wallet.get_transactions(
            address=wallet.address,
            limit=10,
            offset=0
        )
        
        print(f"   Total transactions: {history['total']}")
        print(f"   Retrieved: {len(history['transactions'])}")
        print(f"   Limit: {history['limit']}")
        print(f"   Offset: {history['offset']}")
        
        if history['transactions']:
            print("\n   Recent transactions:")
            for i, tx in enumerate(history['transactions'], 1):
                print(f"   {i}. {tx.get('hash', 'N/A')[:16]}...")
                print(f"      From: {tx.get('from', 'N/A')[:16]}...")
                print(f"      To: {tx.get('to', 'N/A')[:16]}...")
                print(f"      Amount: {tx.get('amount', 'N/A')}")
                print(f"      Status: {tx.get('status', 'N/A')}")
        else:
            print("   No transactions found")
        
        # Format balance information
        print("\n5. Balance Summary:")
        balance_info = {
            "address": balance.address,
            "balance_wei": balance.balance,
            "balance_xai": balance_eth,
            "locked_balance_wei": balance.locked_balance,
            "available_balance_wei": balance.available_balance,
            "nonce": balance.nonce,
            "transaction_count": history['total'],
        }
        
        # Save to file
        balance_file = "balance_check.json"
        with open(balance_file, "w") as f:
            json.dump(balance_info, f, indent=2)
        print(f"   Saved to: {balance_file}")
        
        # Show balance in different formats
        print("\n6. Balance Formats:")
        print(f"   Wei: {balance.balance}")
        print(f"   Satoshi (if 10**8): {float(balance.balance) / 1e8:.8f}")
        print(f"   XAI (if 10**18): {balance_eth:.18f}")
        
        print("\n" + "=" * 60)
        print("SUCCESS: Balance check examples completed!")
        print("=" * 60)
        
    except ValidationError as e:
        print(f"\nERROR: Validation error: {e}")
        return 1
    except WalletError as e:
        print(f"\nERROR: Wallet error: {e}")
        return 1
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        return 1
    finally:
        client.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
