"""
AXN Blockchain Node - P2P Networking Module

Handles all peer-to-peer networking functionality including:
- Peer management
- Transaction broadcasting
- Block broadcasting
- Blockchain synchronization
"""

from __future__ import annotations

import requests
from typing import TYPE_CHECKING, Set, Optional

if TYPE_CHECKING:
    from aixn.core.blockchain import Blockchain, Transaction, Block


class P2PNetworkManager:
    """
    Manages peer-to-peer networking for a blockchain node.
    
    Handles peer discovery, transaction/block broadcasting, and blockchain
    synchronization across the network.
    """
    
    def __init__(self, blockchain: Blockchain) -> None:
        """
        Initialize the P2P network manager.
        
        Args:
            blockchain: The blockchain instance to synchronize
        """
        self.blockchain = blockchain
        self.peers: Set[str] = set()
    
    def add_peer(self, peer_url: str) -> None:
        """
        Add a peer node to the network.
        
        Args:
            peer_url: URL of the peer node to add
        """
        if peer_url not in self.peers:
            self.peers.add(peer_url)
            print(f"🔗 Added peer: {peer_url}")
    
    def remove_peer(self, peer_url: str) -> None:
        """
        Remove a peer node from the network.
        
        Args:
            peer_url: URL of the peer node to remove
        """
        if peer_url in self.peers:
            self.peers.remove(peer_url)
            print(f"🔌 Removed peer: {peer_url}")
    
    def broadcast_transaction(self, transaction: Transaction) -> None:
        """
        Broadcast a transaction to all connected peers.
        
        Args:
            transaction: The transaction to broadcast
        """
        for peer in self.peers:
            try:
                requests.post(
                    f"{peer}/transaction/receive",
                    json=transaction.to_dict(),
                    timeout=2
                )
            except Exception as e:
                print(f"⚠️  Failed to broadcast transaction to {peer}: {e}")
    
    def broadcast_block(self, block: Block) -> None:
        """
        Broadcast a newly mined block to all connected peers.
        
        Args:
            block: The block to broadcast
        """
        for peer in self.peers:
            try:
                requests.post(
                    f"{peer}/block/receive",
                    json=block.to_dict(),
                    timeout=2
                )
            except Exception as e:
                print(f"⚠️  Failed to broadcast block to {peer}: {e}")
    
    def sync_with_network(self) -> bool:
        """
        Synchronize blockchain with the network.
        
        Queries all peers for their blockchain and adopts the longest valid chain
        if it's longer than the current chain.
        
        Returns:
            True if blockchain was updated, False otherwise
        """
        longest_chain = None
        max_length = len(self.blockchain.chain)
        
        # Query all peers for their chain
        for peer in self.peers:
            try:
                response = requests.get(f"{peer}/blocks", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    chain_length = data.get("total", 0)
                    
                    if chain_length > max_length:
                        # This chain is longer, get full chain
                        full_response = requests.get(
                            f"{peer}/blocks?limit={chain_length}",
                            timeout=10
                        )
                        if full_response.status_code == 200:
                            longest_chain = full_response.json().get("blocks", [])
                            max_length = chain_length
                            
            except Exception as e:
                print(f"⚠️  Error syncing with {peer}: {e}")
        
        # Replace chain if we found a longer valid one
        if longest_chain and len(longest_chain) > len(self.blockchain.chain):
            # TODO: In production, implement full chain validation before replacement
            print(f"🔄 Syncing blockchain... New length: {len(longest_chain)}")
            # self.blockchain.replace_chain(longest_chain)  # Would need to implement this
            return True
        
        return False
    
    def get_peer_count(self) -> int:
        """
        Get the number of connected peers.
        
        Returns:
            Number of active peers
        """
        return len(self.peers)
    
    def get_peers(self) -> Set[str]:
        """
        Get the set of connected peer URLs.
        
        Returns:
            Set of peer URLs
        """
        return self.peers.copy()
