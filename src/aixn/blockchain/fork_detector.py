from typing import Dict, Any, List


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
        print(
            f"ForkDetector initialized for node {self.node_id}. Initial chain head: {self.current_chain_head['height']} ({self.current_chain_head['hash'][:8]}...)"
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
        print(
            f"Node {self.node_id} updated chain head to: {self.current_chain_head['height']} ({self.current_chain_head['hash'][:8]}...)"
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
        print(
            f"Peer {peer_id} reported chain head: {peer_chain_head['height']} ({peer_chain_head['hash'][:8]}...)"
        )

    def check_for_forks(self, consensus_threshold: float = 0.51) -> bool:
        """
        Checks for potential forks by comparing the node's chain head with its peers.
        Triggers a conceptual alert if a significant discrepancy is found.
        consensus_threshold: Percentage of peers that must agree with the node's chain head.
        Returns True if a fork risk is detected, False otherwise.
        """
        if not self.peer_chain_heads:
            print("No peer chain heads reported. Cannot check for forks.")
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
            print(
                f"!!! FORK ALERT !!! Node {self.node_id} has {agreement_percentage:.2%} agreement with peers on chain head. "
                f"Expected at least {consensus_threshold:.2%}. Potential fork detected!"
            )
            # In a real system, this would trigger an actual alert and potentially a re-sync process.
            return True
        else:
            print(
                f"Node {self.node_id} is in consensus with {agreement_percentage:.2%} of peers. No fork detected."
            )
            return False


# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Initial chain state
    genesis_block = {"hash": "0xgenesis", "height": 0}
    block_1 = {"hash": "0xblock1", "height": 1}
    block_2_main = {"hash": "0xblock2_main", "height": 2}
    block_2_fork = {"hash": "0xblock2_fork", "height": 2}  # A different block at same height

    # Node A's perspective
    node_a_detector = ForkDetector("NodeA", block_2_main)

    # Peers' perspectives
    node_a_detector.report_peer_chain_head("Peer1", block_2_main)
    node_a_detector.report_peer_chain_head("Peer2", block_2_main)
    node_a_detector.report_peer_chain_head("Peer3", block_2_main)
    node_a_detector.report_peer_chain_head("Peer4", block_2_fork)  # This peer is on a fork
    node_a_detector.report_peer_chain_head("Peer5", block_2_fork)  # This peer is on a fork

    print("\n--- Initial Fork Check (Node A) ---")
    node_a_detector.check_for_forks(consensus_threshold=0.6)  # 3/5 = 60% agreement, should pass

    print("\n--- Simulating More Peers on Fork ---")
    node_a_detector.report_peer_chain_head("Peer6", block_2_fork)  # Now 3 peers on main, 3 on fork
    node_a_detector.report_peer_chain_head("Peer7", block_2_fork)  # Now 3 peers on main, 4 on fork

    print("\n--- Fork Check After More Peers on Fork ---")
    node_a_detector.check_for_forks(
        consensus_threshold=0.6
    )  # 3/7 = ~42% agreement, should trigger alert

    print("\n--- Node A updates to the longer chain (resolves fork) ---")
    block_3_main = {"hash": "0xblock3_main", "height": 3}
    node_a_detector.update_node_chain_head(block_3_main)
    node_a_detector.report_peer_chain_head("Peer1", block_3_main)
    node_a_detector.report_peer_chain_head("Peer2", block_3_main)
    node_a_detector.report_peer_chain_head("Peer3", block_3_main)
    # Peers 4,5,6,7 are still on block_2_fork, but now Node A is on a longer chain

    print("\n--- Fork Check After Node A Updates ---")
    node_a_detector.check_for_forks(
        consensus_threshold=0.6
    )  # 3/7 = ~42% agreement, still a risk, but Node A is on the longer chain
