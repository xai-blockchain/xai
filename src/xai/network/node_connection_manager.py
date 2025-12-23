from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

from xai.core.p2p_security import P2PSecurityConfig, P2PSecurityManager


class NodeConnectionManager:
    def __init__(
        self,
        max_inbound_connections: int = 100,
        max_outbound_connections: int = 50,
        security_manager: P2PSecurityManager | None = None,
    ):
        if not isinstance(max_inbound_connections, int) or max_inbound_connections <= 0:
            raise ValueError("Max inbound connections must be a positive integer.")
        if not isinstance(max_outbound_connections, int) or max_outbound_connections <= 0:
            raise ValueError("Max outbound connections must be a positive integer.")

        self.max_inbound_connections = max_inbound_connections
        self.max_outbound_connections = max_outbound_connections

        self.current_inbound_connections = 0
        self.current_outbound_connections = 0

        # Stores active connections: {connection_id: {"type": "inbound"|"outbound", "peer_info": Any}}
        self.active_connections: dict[str, dict[str, Any]] = {}
        self._connection_id_counter = 0
        self.security_manager = security_manager or P2PSecurityManager()

        print(
            f"NodeConnectionManager initialized. Max inbound: {self.max_inbound_connections}, "
            f"Max outbound: {self.max_outbound_connections}, Security enabled."
        )

    def _generate_connection_id(self) -> str:
        self._connection_id_counter += 1
        return f"conn_{self._connection_id_counter}"

    async def handle_inbound_connection(self, peer_info: Any) -> str:
        """
        Handles an incoming connection request, enforcing max inbound limits.
        Returns connection_id if successful.
        """
        # Simulate async security check (could involve async I/O)
        await asyncio.sleep(0)
        can_accept, reason = self.security_manager.can_accept_peer(
            peer_url=str(peer_info.get("url", peer_info)), ip_address=peer_info.get("ip")
        )
        if not can_accept:
            raise ValueError(f"Inbound connection rejected: {reason}")

        if self.current_inbound_connections >= self.max_inbound_connections:
            raise ValueError(
                f"Inbound connection rejected: Max inbound connections ({self.max_inbound_connections}) reached."
            )

        conn_id = self._generate_connection_id()
        self.active_connections[conn_id] = {"type": "inbound", "peer_info": peer_info}
        self.current_inbound_connections += 1
        self.security_manager.track_peer_connection(
            peer_url=str(peer_info.get("url", peer_info)),
            ip_address=peer_info.get("ip", "unknown"),
        )

        print(
            f"Inbound connection {conn_id} established. Inbound: {self.current_inbound_connections}/{self.max_inbound_connections}"
        )
        return conn_id

    async def establish_outbound_connection(self, peer_info: Any) -> str:
        """
        Establishes an outgoing connection, enforcing max outbound limits.
        Returns connection_id if successful.
        """
        # Simulate async connection establishment
        await asyncio.sleep(0)
        if self.current_outbound_connections >= self.max_outbound_connections:
            raise ValueError(
                f"Outbound connection rejected: Max outbound connections ({self.max_outbound_connections}) reached."
            )

        conn_id = self._generate_connection_id()
        self.active_connections[conn_id] = {"type": "outbound", "peer_info": peer_info}
        self.current_outbound_connections += 1
        self.security_manager.track_peer_connection(
            peer_url=str(peer_info.get("url", peer_info)),
            ip_address=peer_info.get("ip", "unknown"),
        )

        print(
            f"Outbound connection {conn_id} established. Outbound: {self.current_outbound_connections}/{self.max_outbound_connections}"
        )
        return conn_id

    def disconnect_connection(self, connection_id: str):
        """
        Disconnects an active connection and updates counts.
        """
        connection = self.active_connections.pop(connection_id, None)
        if connection:
            if connection["type"] == "inbound":
                self.current_inbound_connections -= 1
                print(
                    f"Inbound connection {connection_id} disconnected. Current inbound: {self.current_inbound_connections}/{self.max_inbound_connections}"
                )
            elif connection["type"] == "outbound":
                self.current_outbound_connections -= 1
                print(
                    f"Outbound connection {connection_id} disconnected. Current outbound: {self.current_outbound_connections}/{self.max_outbound_connections}"
                )
        else:
            print(f"Connection {connection_id} not found.")

    async def validate_peer_message(self, peer_url: str, message_data: bytes, message: dict[str, Any]) -> bool:
        """
        Validate message using the configured security manager.
        """
        # Simulate async validation (message verification could be async)
        await asyncio.sleep(0)
        valid, reason = self.security_manager.validate_message(peer_url, message_data, message)
        if not valid:
            print(f"Peer {peer_url} message rejected: {reason}")
            self.security_manager.report_bad_behavior(peer_url, severity="minor")
            return False
        self.security_manager.report_good_behavior(peer_url)
        return True

    def get_connection_counts(self) -> dict[str, int]:
        """Returns the current inbound and outbound connection counts."""
        return {
            "inbound": self.current_inbound_connections,
            "outbound": self.current_outbound_connections,
            "total": len(self.active_connections),
        }

# Example Usage (for testing purposes)
async def main():
    manager = NodeConnectionManager(max_inbound_connections=3, max_outbound_connections=2)

    print("\n--- Handling Inbound Connections ---")
    in_conn_1 = await manager.handle_inbound_connection("peer_A_info")
    in_conn_2 = await manager.handle_inbound_connection("peer_B_info")
    in_conn_3 = await manager.handle_inbound_connection("peer_C_info")
    try:
        await manager.handle_inbound_connection("peer_D_info")  # Should fail
    except ValueError as e:
        logger.warning(
            "ValueError in get_connection_counts",
            extra={
                "error_type": "ValueError",
                "error": str(e),
                "function": "get_connection_counts"
            }
        )
        print(f"Error (expected): {e}")
    print(f"Current connections: {manager.get_connection_counts()}")

    print("\n--- Establishing Outbound Connections ---")
    out_conn_1 = await manager.establish_outbound_connection("peer_X_info")
    out_conn_2 = await manager.establish_outbound_connection("peer_Y_info")
    try:
        await manager.establish_outbound_connection("peer_Z_info")  # Should fail
    except ValueError as e:
        logger.warning(
            "ValueError in get_connection_counts",
            extra={
                "error_type": "ValueError",
                "error": str(e),
                "function": "get_connection_counts"
            }
        )
        print(f"Error (expected): {e}")
    print(f"Current connections: {manager.get_connection_counts()}")

    print("\n--- Disconnecting Connections ---")
    manager.disconnect_connection(in_conn_1)
    manager.disconnect_connection(out_conn_1)
    print(f"Current connections: {manager.get_connection_counts()}")

    print("\n--- Re-establishing after Disconnect ---")
    in_conn_4 = await manager.handle_inbound_connection("peer_D_info")  # Should now be allowed
    print(f"Current connections: {manager.get_connection_counts()}")

if __name__ == "__main__":
    asyncio.run(main())
