import time
from collections import defaultdict
from typing import List, Dict, Any

class EclipseProtector:
    def __init__(self, max_connections_per_ip: int = 3, min_diverse_peers: int = 5):
        if not isinstance(max_connections_per_ip, int) or max_connections_per_ip <= 0:
            raise ValueError("Max connections per IP must be a positive integer.")
        if not isinstance(min_diverse_peers, int) or min_diverse_peers <= 0:
            raise ValueError("Min diverse peers must be a positive integer.")

        self.max_connections_per_ip = max_connections_per_ip
        self.min_diverse_peers = min_diverse_peers
        
        # Stores connected peers: {peer_id: {"ip_address": str, "connection_time": float}}
        self.connected_peers: Dict[str, Dict[str, Any]] = {}
        # Tracks connections per IP: {ip_address: count}
        self.connections_by_ip: Dict[str, int] = defaultdict(int)
        self._peer_id_counter = 0
        print(f"EclipseProtector initialized. Max connections per IP: {self.max_connections_per_ip}, Min diverse peers: {self.min_diverse_peers}.")

    def connect_peer(self, ip_address: str) -> str:
        """
        Simulates connecting a new peer, enforcing connection limits per IP.
        Returns the peer_id if successful.
        """
        if self.connections_by_ip[ip_address] >= self.max_connections_per_ip:
            raise ValueError(f"Connection from IP {ip_address} rejected: Exceeds max connections per IP ({self.max_connections_per_ip}).")
        
        self._peer_id_counter += 1
        peer_id = f"peer_{self._peer_id_counter}"
        
        self.connected_peers[peer_id] = {"ip_address": ip_address, "connection_time": time.time()}
        self.connections_by_ip[ip_address] += 1
        print(f"Peer {peer_id} connected from {ip_address}. Total connections from {ip_address}: {self.connections_by_ip[ip_address]}")
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

    def check_for_eclipse_risk(self) -> bool:
        """
        Checks for potential Eclipse attack risk based on peer diversity.
        Returns True if at risk, False otherwise.
        """
        unique_ips = len(self.connections_by_ip)
        total_connections = len(self.connected_peers)

        if total_connections == 0:
            print("No peers connected. High Eclipse risk.")
            return True

        if unique_ips < self.min_diverse_peers:
            print(f"!!! ECLIPSE RISK ALERT !!! Only {unique_ips} unique IPs connected, less than minimum diverse peers ({self.min_diverse_peers}).")
            return True
        
        # Further checks could involve geographical diversity, ASN diversity, etc.
        print(f"Network diversity check passed. {unique_ips} unique IPs connected.")
        return False

# Example Usage (for testing purposes)
if __name__ == "__main__":
    protector = EclipseProtector(max_connections_per_ip=2, min_diverse_peers=3)

    print("\n--- Connecting Diverse Peers ---")
    peer1 = protector.connect_peer("1.1.1.1")
    peer2 = protector.connect_peer("2.2.2.2")
    peer3 = protector.connect_peer("3.3.3.3")
    protector.check_for_eclipse_risk()

    print("\n--- Attacker tries to monopolize connections ---")
    attacker_ip = "4.4.4.4"
    try:
        protector.connect_peer(attacker_ip)
        protector.connect_peer(attacker_ip)
        protector.connect_peer(attacker_ip) # Should fail
    except ValueError as e:
        print(f"Error (expected): {e}")
    protector.check_for_eclipse_risk()

    print("\n--- Disconnecting a diverse peer, increasing risk ---")
    protector.disconnect_peer(peer1)
    protector.check_for_eclipse_risk()

    print("\n--- Connecting another diverse peer, reducing risk ---")
    peer4 = protector.connect_peer("5.5.5.5")
    protector.check_for_eclipse_risk()
