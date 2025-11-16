from typing import Dict, Any, List, Set


class PartitionDetector:
    def __init__(self, node_id: str, known_peers: List[str]):
        if not node_id:
            raise ValueError("Node ID cannot be empty.")
        if not isinstance(known_peers, list):
            raise ValueError("Known peers must be a list.")
        if node_id in known_peers:
            raise ValueError("Node ID cannot be in known_peers list.")

        self.node_id = node_id
        self.known_peers: Set[str] = set(known_peers)
        # Stores reachability info: {reporting_peer_id: {reachable_peer_id_1, reachable_peer_id_2, ...}}
        self.peer_reachability: Dict[str, Set[str]] = {
            self.node_id: set()
        }  # Initialize own reachability
        for peer in known_peers:
            self.peer_reachability[peer] = set()  # Initialize other peers' reachability

        print(
            f"PartitionDetector initialized for node {self.node_id}. Known peers: {self.known_peers}."
        )

    def update_own_reachability(self, reachable_peers: List[str]):
        """Updates the node's own view of which peers it can reach."""
        if not isinstance(reachable_peers, list):
            raise ValueError("Reachable peers must be a list.")
        self.peer_reachability[self.node_id] = set(reachable_peers).intersection(self.known_peers)
        print(
            f"Node {self.node_id} updated its reachability: {self.peer_reachability[self.node_id]}"
        )

    def report_peer_reachability(self, reporting_peer_id: str, reachable_peers: List[str]):
        """A peer reports which other peers it can reach."""
        if reporting_peer_id not in self.known_peers and reporting_peer_id != self.node_id:
            print(f"Warning: Reporting peer {reporting_peer_id} is not a known peer.")
            return
        if not isinstance(reachable_peers, list):
            raise ValueError("Reachable peers must be a list.")

        # Only store reachability for known peers
        self.peer_reachability[reporting_peer_id] = set(reachable_peers).intersection(
            self.known_peers.union({self.node_id})
        )
        print(
            f"Peer {reporting_peer_id} reported reachability: {self.peer_reachability[reporting_peer_id]}"
        )

    def _get_all_nodes(self) -> Set[str]:
        """Returns a set of all nodes in the network (self + known_peers)."""
        return self.known_peers.union({self.node_id})

    def detect_partitions(self) -> bool:
        """
        Detects network partitions by conceptually analyzing peer reachability.
        Returns True if a partition is detected, False otherwise.
        """
        all_nodes = self._get_all_nodes()
        if len(all_nodes) <= 1:
            print("Not enough nodes to detect a partition.")
            return False

        # Build a conceptual connectivity graph
        # For simplicity, we'll use a basic DFS/BFS to find connected components
        # A more robust solution would use a proper graph library.

        # Start DFS/BFS from our own node
        visited = set()
        queue = [self.node_id]
        visited.add(self.node_id)

        while queue:
            current_node = queue.pop(0)
            # Consider direct connections from current_node
            direct_connections = self.peer_reachability.get(current_node, set())

            # Also consider connections where current_node is reported as reachable by others
            # This is a simplification; a true graph would be built from all reported edges.
            for reporter, reachable_set in self.peer_reachability.items():
                if current_node in reachable_set:
                    direct_connections.add(reporter)

            for neighbor in direct_connections:
                if neighbor in all_nodes and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        # If not all nodes are visited, then there's a partition
        if len(visited) < len(all_nodes):
            unreachable_nodes = all_nodes - visited
            print(
                f"!!! NETWORK PARTITION DETECTED !!! Node {self.node_id} can reach {len(visited)} nodes, "
                f"but {len(unreachable_nodes)} nodes are unreachable: {unreachable_nodes}."
            )
            # In a real system, this would trigger an actual alert.
            return True
        else:
            print(f"Node {self.node_id} sees a fully connected network. No partition detected.")
            return False


# Example Usage (for testing purposes)
if __name__ == "__main__":
    node_a = "NodeA"
    node_b = "NodeB"
    node_c = "NodeC"
    node_d = "NodeD"
    node_e = "NodeE"

    all_known_peers = [node_b, node_c, node_d, node_e]

    detector_a = PartitionDetector(node_a, all_known_peers)

    print("\n--- Scenario 1: Fully Connected Network ---")
    detector_a.update_own_reachability([node_b, node_c, node_d, node_e])
    detector_a.report_peer_reachability(node_b, [node_a, node_c, node_d, node_e])
    detector_a.report_peer_reachability(node_c, [node_a, node_b, node_d, node_e])
    detector_a.report_peer_reachability(node_d, [node_a, node_b, node_c, node_e])
    detector_a.report_peer_reachability(node_e, [node_a, node_b, node_c, node_d])
    detector_a.detect_partitions()

    print("\n--- Scenario 2: Network Partition (A,B,C vs D,E) ---")
    detector_a_partition = PartitionDetector(node_a, all_known_peers)
    detector_a_partition.update_own_reachability([node_b, node_c])  # A can only reach B, C
    detector_a_partition.report_peer_reachability(node_b, [node_a, node_c])
    detector_a_partition.report_peer_reachability(node_c, [node_a, node_b])
    detector_a_partition.report_peer_reachability(node_d, [node_e])  # D can only reach E
    detector_a_partition.report_peer_reachability(node_e, [node_d])
    detector_a_partition.detect_partitions()

    print("\n--- Scenario 3: Partial Partition (A,B,C connected, D,E isolated) ---")
    detector_a_partial = PartitionDetector(node_a, all_known_peers)
    detector_a_partial.update_own_reachability([node_b, node_c])
    detector_a_partial.report_peer_reachability(node_b, [node_a, node_c])
    detector_a_partial.report_peer_reachability(node_c, [node_a, node_b])
    detector_a_partial.report_peer_reachability(node_d, [])  # D is isolated
    detector_a_partial.report_peer_reachability(node_e, [])  # E is isolated
    detector_a_partial.detect_partitions()
