#!/usr/bin/env python3
"""
Example: Create a Wallet

This example demonstrates how to create a new wallet using the XAI SDK.
"""

import sys
import os
import json
from pathlib import Path

# Add SDK to path
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk" / "python"))

from xai_sdk import XAIClient, WalletType


def main():
    """Create wallets and demonstrate wallet operations."""
    
    print("=" * 60)
    print("XAI Blockchain - Create Wallet Example")
    print("=" * 60)
    
    # Initialize client (connects to local node by default)
    client = XAIClient(
        base_url="http://localhost:5000"
    )
    
    try:
        # Create a standard wallet
        print("\n1. Creating standard wallet...")
        wallet = client.wallet.create()
        
        print(f"   Address: {wallet.address}")
        print(f"   Public Key: {wallet.public_key}")
        print(f"   Private Key: {wallet.private_key}")
        print(f"   Type: {wallet.wallet_type}")
        print(f"   Created: {wallet.created_at}")
        
        # Save wallet info to file
        wallet_data = {
            "address": wallet.address,
            "public_key": wallet.public_key,
            "private_key": wallet.private_key,
            "wallet_type": wallet.wallet_type.value,
            "created_at": wallet.created_at.isoformat(),
        }
        
        wallet_file = "wallet.json"
        with open(wallet_file, "w") as f:
            json.dump(wallet_data, f, indent=2)
        print(f"\n   Wallet saved to: {wallet_file}")
        
        # Get wallet information
        print("\n2. Retrieving wallet information...")
        retrieved = client.wallet.get(wallet.address)
        print(f"   Address: {retrieved.address}")
        print(f"   Nonce: {retrieved.nonce}")
        
        # Get wallet balance
        print("\n3. Retrieving wallet balance...")
        balance = client.wallet.get_balance(wallet.address)
        print(f"   Total Balance: {balance.balance}")
        print(f"   Available Balance: {balance.available_balance}")
        print(f"   Locked Balance: {balance.locked_balance}")
        print(f"   Nonce: {balance.nonce}")
        
        # Create an embedded wallet
        print("\n4. Creating embedded wallet...")
        embedded = client.wallet.create_embedded(
            app_id="my_app",
            user_id="user_123",
            metadata={"username": "trader_001"}
        )
        print(f"   Wallet ID: {embedded['wallet_id']}")
        print(f"   Address: {embedded['address']}")
        print(f"   Session Token: {embedded['session_token']}")
        
        # Create named wallet
        print("\n5. Creating named wallet...")
        named = client.wallet.create(name="Trading Wallet")
        print(f"   Address: {named.address}")
        print(f"   Type: {named.wallet_type}")
        
        print("\n" + "=" * 60)
        print("SUCCESS: Wallet creation examples completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        return 1
    finally:
        client.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
