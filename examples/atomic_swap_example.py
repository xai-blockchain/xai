#!/usr/bin/env python3
"""
Example: Atomic Swap / Peer-to-Peer Trading

This example demonstrates how to execute peer-to-peer trading
and atomic swap operations on the XAI blockchain.
"""

import sys
import os
import json
import uuid
from pathlib import Path

# Add SDK to path
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk" / "python"))

from xai_sdk import XAIClient, XAIError


def main():
    """Demonstrate peer-to-peer trading and atomic swaps."""
    
    print("=" * 60)
    print("XAI Blockchain - Atomic Swap / P2P Trading Example")
    print("=" * 60)
    
    # Initialize client
    client = XAIClient(
        base_url="http://localhost:12001"
    )
    
    try:
        # Create two trader wallets
        print("\n1. Creating trader wallets...")
        trader_a = client.wallet.create(name="Trader A")
        trader_b = client.wallet.create(name="Trader B")
        
        print(f"   Trader A: {trader_a.address}")
        print(f"   Trader B: {trader_b.address}")
        
        # Check initial balances
        print("\n2. Checking initial balances...")
        balance_a = client.wallet.get_balance(trader_a.address)
        balance_b = client.wallet.get_balance(trader_b.address)
        
        print(f"   Trader A: {float(balance_a.balance) / 1e18:.6f} XAI")
        print(f"   Trader B: {float(balance_b.balance) / 1e18:.6f} XAI")
        
        # Register trading session
        print("\n3. Registering trading session...")
        peer_id_a = str(uuid.uuid4())
        peer_id_b = str(uuid.uuid4())
        
        session_a = client.trading.register_session(
            wallet_address=trader_a.address,
            peer_id=peer_id_a
        )
        
        session_b = client.trading.register_session(
            wallet_address=trader_b.address,
            peer_id=peer_id_b
        )
        
        print(f"   Trader A session: {session_a['session_id']}")
        print(f"   Trader B session: {session_b['session_id']}")
        print(f"   Expires at: {session_a['expires_at']}")
        
        # Define trade parameters
        amount_a = "500000000000000000"  # 0.5 XAI
        amount_b = "300000000000000000"  # 0.3 XAI
        
        print("\n4. Creating trade order...")
        print(f"   Trader A offers: {float(amount_a) / 1e18:.6f} XAI")
        print(f"   Trader B offers: {float(amount_b) / 1e18:.6f} XAI")
        
        # Create trade order from Trader A
        order_a = client.trading.create_order(
            from_address=trader_a.address,
            to_address=trader_b.address,
            from_amount=amount_a,
            to_amount=amount_b,
            timeout=3600  # 1 hour
        )
        
        print(f"   Order ID: {order_a.id}")
        print(f"   Status: {order_a.status}")
        print(f"   Created: {order_a.created_at}")
        print(f"   Expires: {order_a.expires_at}")
        
        # List all orders
        print("\n5. Listing trade orders...")
        orders = client.trading.list_orders()
        print(f"   Total orders: {len(orders)}")
        
        for order in orders[:5]:  # Show first 5 orders
            print(f"\n   Order {order.id}:")
            print(f"      From: {order.from_address[:16]}...")
            print(f"      To: {order.to_address[:16]}...")
            print(f"      From amount: {float(order.from_amount) / 1e18:.6f}")
            print(f"      To amount: {float(order.to_amount) / 1e18:.6f}")
            print(f"      Status: {order.status}")
        
        # Get order status
        print(f"\n6. Checking order status...")
        order_status = client.trading.get_order_status(order_a.id)
        print(f"   Order ID: {order_status.get('order_id', order_a.id)}")
        print(f"   Status: {order_status.get('status', 'unknown')}")
        
        # Execute settlement transactions
        print("\n7. Executing settlement transactions...")
        
        # Trader A sends to Trader B
        print("   Trader A -> Trader B")
        tx_settlement_a = client.transaction.send(
            from_address=trader_a.address,
            to_address=trader_b.address,
            amount=amount_a
        )
        print(f"   Transaction: {tx_settlement_a.hash[:16]}...")
        print(f"   Status: {tx_settlement_a.status}")
        
        # Trader B sends to Trader A
        print("\n   Trader B -> Trader A")
        tx_settlement_b = client.transaction.send(
            from_address=trader_b.address,
            to_address=trader_a.address,
            amount=amount_b
        )
        print(f"   Transaction: {tx_settlement_b.hash[:16]}...")
        print(f"   Status: {tx_settlement_b.status}")
        
        # Verify final balances (after transactions)
        print("\n8. Verifying final balances...")
        final_balance_a = client.wallet.get_balance(trader_a.address)
        final_balance_b = client.wallet.get_balance(trader_b.address)
        
        print(f"   Trader A: {float(final_balance_a.balance) / 1e18:.6f} XAI")
        print(f"   Trader B: {float(final_balance_b.balance) / 1e18:.6f} XAI")
        
        # Calculate changes
        change_a = int(final_balance_a.balance) - int(balance_a.balance)
        change_b = int(final_balance_b.balance) - int(balance_b.balance)
        
        print(f"\n   Trader A change: {float(change_a) / 1e18:.6f} XAI")
        print(f"   Trader B change: {float(change_b) / 1e18:.6f} XAI")
        
        # Save trade data
        print("\n9. Saving trade data...")
        
        trade_record = {
            "trade_id": str(uuid.uuid4()),
            "timestamp": order_a.created_at.isoformat(),
            "participants": {
                "trader_a": {
                    "address": trader_a.address,
                    "initial_balance": balance_a.balance,
                    "final_balance": final_balance_a.balance,
                    "sent_amount": amount_a,
                    "received_amount": amount_b,
                },
                "trader_b": {
                    "address": trader_b.address,
                    "initial_balance": balance_b.balance,
                    "final_balance": final_balance_b.balance,
                    "sent_amount": amount_b,
                    "received_amount": amount_a,
                },
            },
            "transactions": {
                "settlement_a": {
                    "hash": tx_settlement_a.hash,
                    "from": tx_settlement_a.from_address,
                    "to": tx_settlement_a.to_address,
                    "amount": tx_settlement_a.amount,
                    "status": tx_settlement_a.status.value,
                },
                "settlement_b": {
                    "hash": tx_settlement_b.hash,
                    "from": tx_settlement_b.from_address,
                    "to": tx_settlement_b.to_address,
                    "amount": tx_settlement_b.amount,
                    "status": tx_settlement_b.status.value,
                },
            },
            "order": {
                "id": order_a.id,
                "status": order_a.status,
                "created_at": order_a.created_at.isoformat(),
                "expires_at": order_a.expires_at.isoformat() if order_a.expires_at else None,
            },
        }
        
        trade_file = "atomic_swap_record.json"
        with open(trade_file, "w") as f:
            json.dump(trade_record, f, indent=2)
        print(f"   Trade record saved to: {trade_file}")
        
        print("\n" + "=" * 60)
        print("SUCCESS: Atomic swap / P2P trading examples completed!")
        print("=" * 60)
        
    except XAIError as e:
        print(f"\nERROR: {e.message}")
        return 1
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        return 1
    finally:
        client.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
