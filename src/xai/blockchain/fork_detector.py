import logging
from typing import Dict, Any, List

logger = logging.getLogger("xai.blockchain.fork_detector")


class ForkDetector:
    def __init__(self, node_id: str, initial_chain_head: Dict[str, Any]):
        if not node_id:
            raise ValueError("Node ID cannot be empty.")
        if (
            not isinstance(initial_chain_head, dict)
            or "hash" not in initial_chain_head
            or "height" not in initial_chain_head
        ):
            raise ValueError("Initial chain head must be a dictionary with 'hash' and 'height'.")

        self.node_id = node_id
        self.current_chain_head = initial_chain_head  # {"hash": "...", "height": int}
        # Stores peer chain heads: {peer_id: {"hash": "...", "height": int}}
        self.peer_chain_heads: Dict[str, Dict[str, Any]] = {}
        logger.info(
            "ForkDetector initialized for node %s at height %s (%s)",
            self.node_id,
            self.current_chain_head["height"],
            self.current_chain_head["hash"],
        )

    def update_node_chain_head(self, new_chain_head: Dict[str, Any]):
        """Updates the node's own view of the current chain head."""
        if (
            not isinstance(new_chain_head, dict)
            or "hash" not in new_chain_head
            or "height" not in new_chain_head
        ):
            raise ValueError("New chain head must be a dictionary with 'hash' and 'height'.")
        self.current_chain_head = new_chain_head
        logger.info(
            "Node %s updated chain head to height %s (%s)",
            self.node_id,
            self.current_chain_head["height"],
            self.current_chain_head["hash"],
        )

    def report_peer_chain_head(self, peer_id: str, peer_chain_head: Dict[str, Any]):
        """A peer reports its current chain head."""
        if not peer_id:
            raise ValueError("Peer ID cannot be empty.")
        if (
            not isinstance(peer_chain_head, dict)
            or "hash" not in peer_chain_head
            or "height" not in peer_chain_head
        ):
            raise ValueError("Peer chain head must be a dictionary with 'hash' and 'height'.")
        self.peer_chain_heads[peer_id] = peer_chain_head
        logger.debug(
            "Peer %s reported chain head height %s (%s)",
            peer_id,
            peer_chain_head["height"],
            peer_chain_head["hash"],
        )

    def check_for_forks(self, consensus_threshold: float = 0.51) -> bool:
        """
        Checks for potential forks by comparing the node's chain head with its peers.
        Triggers a conceptual alert if a significant discrepancy is found.
        consensus_threshold: Percentage of peers that must agree with the node's chain head.
        Returns True if a fork risk is detected, False otherwise.
        """
        if not self.peer_chain_heads:
            logger.warning("No peer chain heads reported. Cannot check for forks.")
            return False

        # Count how many peers agree with the node's current chain head
        agreeing_peers = 0
        for peer_id, peer_head in self.peer_chain_heads.items():
            if (
                peer_head["hash"] == self.current_chain_head["hash"]
                and peer_head["height"] == self.current_chain_head["height"]
            ):
                agreeing_peers += 1

        total_peers = len(self.peer_chain_heads)
        agreement_percentage = agreeing_peers / total_peers if total_peers > 0 else 0.0

        if agreement_percentage < consensus_threshold:
            logger.error(
                "Fork alert: node %s has %.2f%% agreement (threshold %.2f%%)",
                self.node_id,
                agreement_percentage * 100,
                consensus_threshold * 100,
            )
            # In a real system, this would trigger an actual alert and potentially a re-sync process.
            return True
        else:
            logger.info(
                "Node %s has %.2f%% agreement with peers (no fork)",
                self.node_id,
                agreement_percentage * 100,
            )
            return False
