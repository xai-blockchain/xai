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
from typing import TYPE_CHECKING, Set, Optional, Dict

if TYPE_CHECKING:
    from xai.core.blockchain import Blockchain, Transaction, Block
    from xai.core.node_consensus import ConsensusManager


class P2PNetworkManager:
    """
    Manages peer-to-peer networking for a blockchain node.

    Handles peer discovery, transaction/block broadcasting, and blockchain
    synchronization across the network.
    """

    def __init__(
        self,
        blockchain: Blockchain,
        consensus_manager: Optional["ConsensusManager"] = None,
        peers: Optional[Set[str]] = None,
        peer_api_key: str = "",
    ) -> None:
        """
        Initialize the P2P network manager.

        Args:
            blockchain: The blockchain instance to synchronize
        """
        self.blockchain = blockchain
        self.consensus_manager = consensus_manager
        self.peers: Set[str] = peers if peers is not None else set()
        self._peer_api_key = peer_api_key.strip()
        self._peer_headers = self._build_peer_headers()

    def add_peer(self, peer_url: str) -> None:
        """
        Add a peer node to the network.

        Args:
            peer_url: URL of the peer node to add
        """
        if peer_url not in self.peers:
            self.peers.add(peer_url)
            print(f"[P2P] Added peer: {peer_url}")

    def remove_peer(self, peer_url: str) -> None:
        """
        Remove a peer node from the network.

        Args:
            peer_url: URL of the peer node to remove
        """
        if peer_url in self.peers:
            self.peers.remove(peer_url)
            print(f"[P2P] Removed peer: {peer_url}")

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
                    timeout=2,
                    headers=self._peer_headers,
                )
            except Exception as e:
                print(f"[P2P] WARNING: Failed to broadcast transaction to {peer}: {e}")

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
                    timeout=2,
                    headers=self._peer_headers,
                )
            except Exception as e:
                print(f"[P2P] WARNING: Failed to broadcast block to {peer}: {e}")

    def sync_with_network(self) -> bool:
        """
        Synchronize blockchain with the network.

        Queries all peers for their blockchain and adopts the longest valid chain
        if it's longer than the current chain.

        Returns:
            True if blockchain was updated, False otherwise
        """
        best_candidate = None
        best_length = len(self.blockchain.chain)

        for peer in self.peers:
            try:
                response = requests.get(f"{peer}/blocks", timeout=5)
                if response.status_code != 200:
                    continue
                data = response.json()
                chain_length = data.get("total", 0)
                if chain_length <= best_length:
                    continue

                full_response = requests.get(
                    f"{peer}/blocks?limit={chain_length}", timeout=10
                )
                if full_response.status_code != 200:
                    continue
                blocks_payload = full_response.json().get("blocks", [])
                candidate_chain = self.blockchain.deserialize_chain(blocks_payload)

                if self.consensus_manager is not None:
                    is_valid, error = self.consensus_manager.validate_chain(candidate_chain)
                    if not is_valid:
                        print(f"[P2P] WARNING: Peer {peer} chain invalid: {error}")
                        continue

                best_candidate = candidate_chain
                best_length = chain_length

            except Exception as e:
                print(f"[P2P] WARNING: Error syncing with {peer}: {e}")

        if best_candidate and len(best_candidate) > len(self.blockchain.chain):
            if self.blockchain.replace_chain(best_candidate):
                print(
                    f"[P2P] Sync complete. Adopted chain length {len(best_candidate)} from peer network."
                )
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

    def _build_peer_headers(self) -> Optional[Dict[str, str]]:
        if not self._peer_api_key:
            return None
        return {"X-API-Key": self._peer_api_key}
