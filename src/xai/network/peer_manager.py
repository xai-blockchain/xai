import time
from collections import defaultdict
from typing import List, Dict, Any


class PeerManager:
    def __init__(self, max_connections_per_ip: int = 5):
        if not isinstance(max_connections_per_ip, int) or max_connections_per_ip <= 0:
            raise ValueError("Max connections per IP must be a positive integer.")

        self.max_connections_per_ip = max_connections_per_ip
        self.trusted_peers: set[str] = set()  # Set of trusted IP addresses or node IDs
        self.banned_peers: set[str] = set()  # Set of banned IP addresses or node IDs

        # Stores connected peers: {peer_id: {"ip_address": str}}
        self.connected_peers: Dict[str, Dict[str, Any]] = {}
        # Tracks connections per IP: {ip_address: count}
        self.connections_by_ip: Dict[str, int] = defaultdict(int)
        self._peer_id_counter = 0
        print(f"PeerManager initialized. Max connections per IP: {self.max_connections_per_ip}.")

    def add_trusted_peer(self, peer_identifier: str):
        """Adds a peer to the trusted list."""
        self.trusted_peers.add(peer_identifier.lower())
        print(f"Added {peer_identifier} to trusted peers.")

    def remove_trusted_peer(self, peer_identifier: str):
        """Removes a peer from the trusted list."""
        self.trusted_peers.discard(peer_identifier.lower())
        print(f"Removed {peer_identifier} from trusted peers.")

    def ban_peer(self, peer_identifier: str):
        """Adds a peer to the banned list and disconnects if currently connected."""
        self.banned_peers.add(peer_identifier.lower())
        print(f"Banned {peer_identifier}.")

        # Disconnect any active connections from this banned peer
        peers_to_disconnect = [
            pid
            for pid, peer_info in self.connected_peers.items()
            if peer_info["ip_address"].lower() == peer_identifier.lower()
        ]
        for pid in peers_to_disconnect:
            self.disconnect_peer(pid)

    def unban_peer(self, peer_identifier: str):
        """Removes a peer from the banned list."""
        self.banned_peers.discard(peer_identifier.lower())
        print(f"Unbanned {peer_identifier}.")

    def can_connect(self, ip_address: str) -> bool:
        """
        Checks if a peer with the given IP address is allowed to connect.
        Considers banned list and connection limits.
        """
        ip_lower = ip_address.lower()

        if ip_lower in self.banned_peers:
            print(f"Connection from {ip_address} rejected: IP is banned.")
            return False

        if self.connections_by_ip[ip_lower] >= self.max_connections_per_ip:
            print(
                f"Connection from {ip_address} rejected: Exceeds max connections per IP ({self.max_connections_per_ip})."
            )
            return False

        print(f"Connection from {ip_address} allowed by policy.")
        return True

    def connect_peer(self, ip_address: str) -> str:
        """
        Simulates connecting a new peer if allowed by policy.
        Returns the peer_id if successful.
        """
        if not self.can_connect(ip_address):
            raise ValueError(
                f"Cannot connect to peer from {ip_address} due to policy restrictions."
            )

        self._peer_id_counter += 1
        peer_id = f"peer_{self._peer_id_counter}"

        self.connected_peers[peer_id] = {"ip_address": ip_address}
        self.connections_by_ip[ip_address] += 1
        print(
            f"Peer {peer_id} connected from {ip_address}. Total connections from {ip_address}: {self.connections_by_ip[ip_address]}"
        )
        return peer_id

    def disconnect_peer(self, peer_id: str):
        """Simulates disconnecting a peer."""
        peer = self.connected_peers.pop(peer_id, None)
        if peer:
            ip_address = peer["ip_address"]
            self.connections_by_ip[ip_address] -= 1
            if self.connections_by_ip[ip_address] == 0:
                del self.connections_by_ip[ip_address]
            print(f"Peer {peer_id} from {ip_address} disconnected.")
        else:
            print(f"Peer {peer_id} not found.")


# Example Usage (for testing purposes)
if __name__ == "__main__":
    manager = PeerManager(max_connections_per_ip=2)

    trusted_node_ip = "10.0.0.1"
    malicious_ip = "192.168.1.100"
    normal_ip_1 = "172.16.0.1"
    normal_ip_2 = "172.16.0.2"

    manager.add_trusted_peer(trusted_node_ip)
    manager.ban_peer(malicious_ip)

    print("\n--- Attempting Connections ---")
    # Trusted peer connection
    try:
        peer_trusted_1 = manager.connect_peer(trusted_node_ip)
        peer_trusted_2 = manager.connect_peer(trusted_node_ip)
        # peer_trusted_3 = manager.connect_peer(trusted_node_ip) # This would exceed max_connections_per_ip
    except ValueError as e:
        print(f"Error (expected): {e}")

    # Banned peer connection
    try:
        manager.connect_peer(malicious_ip)
    except ValueError as e:
        print(f"Error (expected): {e}")

    # Normal peer connections
    try:
        peer_normal_1 = manager.connect_peer(normal_ip_1)
        peer_normal_2 = manager.connect_peer(normal_ip_1)
        peer_normal_3 = manager.connect_peer(normal_ip_1)  # Should fail
    except ValueError as e:
        print(f"Error (expected): {e}")

    try:
        peer_normal_4 = manager.connect_peer(normal_ip_2)
    except ValueError as e:
        print(f"Error: {e}")

    print("\n--- Disconnecting and Re-evaluating ---")
    manager.disconnect_peer(peer_normal_1)
    try:
        peer_normal_5 = manager.connect_peer(normal_ip_1)  # Should now be allowed
    except ValueError as e:
        print(f"Error: {e}")

    print("\n--- Unbanning and Connecting ---")
    manager.unban_peer(malicious_ip)
    try:
        manager.connect_peer(malicious_ip)
    except ValueError as e:
        print(f"Error: {e}")
