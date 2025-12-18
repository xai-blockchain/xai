#!/usr/bin/env python3
"""
Example: Query Blockchain

This example demonstrates how to query blockchain data including
blocks, statistics, and sync status.
"""

import sys
import os
import json
from pathlib import Path

# Add SDK to path
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk" / "python"))

from xai_sdk import XAIClient, XAIError


def main():
    """Query blockchain and retrieve blockchain data."""
    
    print("=" * 60)
    print("XAI Blockchain - Query Blockchain Example")
    print("=" * 60)
    
    # Initialize client
    client = XAIClient(
        base_url="http://localhost:12001"
    )
    
    try:
        # Get node info
        print("\n1. Retrieving node information...")
        info = client.blockchain.get_node_info()
        print(f"   Status: {info.get('status', 'N/A')}")
        print(f"   Node: {info.get('node', 'N/A')}")
        print(f"   Version: {info.get('version', 'N/A')}")
        print(f"   Network: {info.get('network', 'N/A')}")
        
        # Get health status
        print("\n2. Checking node health...")
        health = client.blockchain.get_health()
        print(f"   Status: {health.get('status', 'N/A')}")
        print(f"   Uptime: {health.get('uptime_seconds', 0)} seconds")
        print(f"   Peers connected: {health.get('peers_connected', 0)}")
        print(f"   Sync status: {health.get('sync_status', 'N/A')}")
        
        # Get blockchain statistics
        print("\n3. Retrieving blockchain statistics...")
        stats = client.blockchain.get_stats()
        
        print(f"   Total blocks: {stats.total_blocks}")
        print(f"   Total transactions: {stats.total_transactions}")
        print(f"   Total accounts: {stats.total_accounts}")
        print(f"   Current difficulty: {stats.difficulty}")
        print(f"   Network hashrate: {stats.hashrate}")
        print(f"   Average block time: {stats.average_block_time} seconds")
        print(f"   Total supply: {stats.total_supply}")
        print(f"   Network: {stats.network}")
        
        # Get sync status
        print("\n4. Checking blockchain sync status...")
        sync_status = client.blockchain.get_sync_status()
        print(f"   Syncing: {sync_status.get('syncing', False)}")
        print(f"   Current block: {sync_status.get('current_block', 0)}")
        print(f"   Highest block: {sync_status.get('highest_block', 0)}")
        print(f"   Starting block: {sync_status.get('starting_block', 0)}")
        
        if not sync_status.get('syncing'):
            print("   Status: Fully synced")
        
        # Get latest blocks
        print("\n5. Retrieving latest blocks...")
        blocks_result = client.blockchain.list_blocks(limit=5)
        
        print(f"   Total blocks: {blocks_result['total']}")
        print(f"   Retrieved: {len(blocks_result['blocks'])}")
        
        if blocks_result['blocks']:
            print("\n   Latest blocks:")
            for i, block in enumerate(blocks_result['blocks'], 1):
                print(f"   {i}. Block #{block.number}")
                print(f"      Hash: {block.hash[:16]}...")
                print(f"      Miner: {block.miner[:16]}...")
                print(f"      Timestamp: {block.timestamp}")
                print(f"      Transactions: {block.transactions}")
                print(f"      Gas used: {block.gas_used}")
                print(f"      Difficulty: {block.difficulty}")
        
        # Get specific block details
        if blocks_result['blocks']:
            print("\n6. Retrieving specific block details...")
            latest_block = blocks_result['blocks'][0]
            
            block_detail = client.blockchain.get_block(latest_block.number)
            print(f"   Block number: {block_detail.number}")
            print(f"   Hash: {block_detail.hash}")
            print(f"   Parent hash: {block_detail.parent_hash}")
            print(f"   Timestamp: {block_detail.timestamp}")
            print(f"   Miner: {block_detail.miner}")
            print(f"   Difficulty: {block_detail.difficulty}")
            print(f"   Gas limit: {block_detail.gas_limit}")
            print(f"   Gas used: {block_detail.gas_used}")
            print(f"   Transactions: {block_detail.transactions}")
            print(f"   Transaction hashes: {len(block_detail.transaction_hashes)}")
            
            # Get block transactions
            print("\n7. Retrieving block transactions...")
            block_txs = client.blockchain.get_block_transactions(latest_block.number)
            print(f"   Found {len(block_txs)} transactions")
            
            if block_txs:
                print("   Transaction hashes:")
                for i, tx_hash in enumerate(block_txs[:5], 1):
                    print(f"   {i}. {tx_hash[:16]}...")
        
        # Prepare summary report
        print("\n8. Generating blockchain summary report...")
        
        summary = {
            "timestamp": str(stats.metadata.get('timestamp', 'N/A')),
            "node_info": {
                "status": info.get('status'),
                "version": info.get('version'),
                "network": info.get('network'),
            },
            "health": {
                "status": health.get('status'),
                "uptime_seconds": health.get('uptime_seconds'),
                "peers_connected": health.get('peers_connected'),
            },
            "blockchain_stats": {
                "total_blocks": stats.total_blocks,
                "total_transactions": stats.total_transactions,
                "total_accounts": stats.total_accounts,
                "difficulty": stats.difficulty,
                "hashrate": stats.hashrate,
                "average_block_time": stats.average_block_time,
                "total_supply": stats.total_supply,
            },
            "sync_status": {
                "syncing": sync_status.get('syncing'),
                "current_block": sync_status.get('current_block'),
                "highest_block": sync_status.get('highest_block'),
            },
        }
        
        # Save to file
        report_file = "blockchain_query.json"
        with open(report_file, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"   Saved to: {report_file}")
        
        print("\n" + "=" * 60)
        print("SUCCESS: Blockchain query examples completed!")
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
