from __future__ import annotations

class PacketFilter:
    def __init__(self, default_allowed_ports: list[int] = None):
        self.allowed_ports: set[int] = (
            set(default_allowed_ports) if default_allowed_ports else set()
        )
        self.blocked_ips: set[str] = set()
        print(
            f"PacketFilter initialized. Allowed ports: {self.allowed_ports}, Blocked IPs: {self.blocked_ips}."
        )

    def add_allowed_port(self, port: int):
        """Adds a port to the list of allowed destination ports."""
        if not isinstance(port, int) or not (0 <= port <= 65535):
            raise ValueError("Port must be an integer between 0 and 65535.")
        self.allowed_ports.add(port)
        print(f"Port {port} added to allowed ports.")

    def remove_allowed_port(self, port: int):
        """Removes a port from the list of allowed destination ports."""
        self.allowed_ports.discard(port)
        print(f"Port {port} removed from allowed ports.")

    def add_blocked_ip(self, ip_address: str):
        """Adds an IP address to the list of blocked source IPs."""
        # Basic IP validation (can be enhanced with regex for full validation)
        if not isinstance(ip_address, str) or not ip_address:
            raise ValueError("IP address must be a non-empty string.")
        self.blocked_ips.add(ip_address)
        print(f"IP {ip_address} added to blocked IPs.")

    def remove_blocked_ip(self, ip_address: str):
        """Removes an IP address from the list of blocked source IPs."""
        self.blocked_ips.discard(ip_address)
        print(f"IP {ip_address} removed from blocked IPs.")

    def filter_packet(self, source_ip: str, destination_port: int) -> bool:
        """
        Simulates filtering an incoming packet.
        Returns True if the packet is allowed, False if blocked.
        """
        if source_ip in self.blocked_ips:
            print(
                f"Packet from {source_ip} to port {destination_port} BLOCKED: Source IP is blocked."
            )
            return False

        if destination_port not in self.allowed_ports:
            print(
                f"Packet from {source_ip} to port {destination_port} BLOCKED: Destination port is not allowed."
            )
            return False

        print(f"Packet from {source_ip} to port {destination_port} ALLOWED.")
        return True

# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Initialize with common blockchain ports
    filter = PacketFilter(default_allowed_ports=[80, 443, 8080, 30303])

    # Add some blocked IPs
    filter.add_blocked_ip("192.168.1.100")
    filter.add_blocked_ip("10.0.0.5")

    print("\n--- Testing Packet Filtering ---")
    # Allowed packet
    filter.filter_packet("1.2.3.4", 80)
    filter.filter_packet("5.6.7.8", 30303)

    # Blocked IP
    filter.filter_packet("192.168.1.100", 80)
    filter.filter_packet("10.0.0.5", 30303)

    # Blocked Port
    filter.filter_packet("1.2.3.4", 22)  # SSH port, not allowed by default
    filter.filter_packet("9.9.9.9", 12345)

    # Add a new allowed port
    filter.add_allowed_port(22)
    filter.filter_packet("1.2.3.4", 22)  # Now allowed

    # Remove a blocked IP
    filter.remove_blocked_ip("192.168.1.100")
    filter.filter_packet("192.168.1.100", 80)  # Now allowed
