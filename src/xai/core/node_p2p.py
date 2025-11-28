"""
AXN Blockchain Node - P2P Networking Module

Handles all peer-to-peer networking functionality including:
- Peer management
- Transaction broadcasting
- Block broadcasting
- Blockchain synchronization
"""

from __future__ import annotations

import asyncio
import os
import threading
from urllib.parse import urlparse
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed
import json
from typing import TYPE_CHECKING, Set, Optional, Dict, Any, Union

import requests
from xai.network.peer_manager import PeerManager
from xai.core.block_header import BlockHeader
from xai.core.p2p_security import MessageRateLimiter, BandwidthLimiter
from xai.core.config import Config

if TYPE_CHECKING:
    from xai.core.blockchain import Blockchain, Transaction, Block
    from xai.core.node_consensus import ConsensusManager


class P2PNetworkManager:
    """
    Manages peer-to-peer networking for a blockchain node using WebSockets.
    """

    def __init__(
        self,
        blockchain: Blockchain,
        peer_manager: Optional[PeerManager] = None,
        consensus_manager: Optional["ConsensusManager"] = None,
        host: str = "0.0.0.0",
        port: int = 8765,
        max_connections: int = 50,
        max_bandwidth_in: int = 1024 * 1024, # 1 MB/s
        max_bandwidth_out: int = 1024 * 1024, # 1 MB/s
    ) -> None:
        self.blockchain = blockchain
        data_dir = getattr(getattr(self.blockchain, "storage", None), "data_dir", "data")
        if peer_manager is None:
            peer_manager = PeerManager(
                max_connections_per_ip=max_connections,
                nonce_ttl_seconds=getattr(Config, "PEER_NONCE_TTL_SECONDS", 300),
                require_client_cert=bool(getattr(Config, "PEER_REQUIRE_CLIENT_CERT", False)),
                trusted_cert_fps_file=getattr(Config, "TRUSTED_PEER_CERT_FPS_FILE", ""),
                trusted_peer_pubkeys_file=getattr(Config, "TRUSTED_PEER_PUBKEYS_FILE", ""),
                ca_bundle_path=getattr(Config, "P2P_CA_BUNDLE", None) if hasattr(Config, "P2P_CA_BUNDLE") else None,
                cert_dir=os.path.join(data_dir, "certs"),
                key_dir=os.path.join(data_dir, "keys"),
            )
        if not isinstance(peer_manager, PeerManager):
            raise TypeError("peer_manager must be an instance of PeerManager to enforce P2P security.")

        self.peer_manager = peer_manager
        self.consensus_manager = consensus_manager
        self.host = host
        self.port = port
        self.server: Optional[websockets.WebSocketServer] = None
        self.connections: Dict[str, WebSocketServerProtocol] = {}
        self.websocket_peer_ids: Dict[WebSocketServerProtocol, str] = {}
        self.http_peers: Set[str] = set()
        self.peers = self.http_peers  # Alias used by legacy callers/tests
        self._peer_lock = threading.RLock()
        self.max_connections = max_connections
        max_msg_rate = getattr(Config, "P2P_MAX_MESSAGE_RATE", 100)
        security_log_rate = getattr(Config, "P2P_SECURITY_LOG_RATE", 20)
        max_bandwidth_in = getattr(Config, "P2P_MAX_BANDWIDTH_IN", max_bandwidth_in)
        max_bandwidth_out = getattr(Config, "P2P_MAX_BANDWIDTH_OUT", max_bandwidth_out)
        self.rate_limiter = MessageRateLimiter(max_rate=max_msg_rate)
        self.security_log_limiter = MessageRateLimiter(max_rate=security_log_rate)
        self.bandwidth_limiter_in = BandwidthLimiter(max_bandwidth_in, max_bandwidth_in // 10)
        self.bandwidth_limiter_out = BandwidthLimiter(max_bandwidth_out, max_bandwidth_out // 10)
        self.received_chains = []

    @staticmethod
    def _normalize_peer_uri(peer_uri: str) -> str:
        parsed = urlparse(peer_uri if "://" in peer_uri else f"http://{peer_uri}")
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid peer URI: {peer_uri}")
        return f"{parsed.scheme}://{parsed.netloc}"

    def add_peer(self, peer_uri: str) -> bool:
        """Register a peer URI for HTTP/WebSocket communication."""
        normalized = self._normalize_peer_uri(peer_uri)
        host = urlparse(normalized).hostname
        with self._peer_lock:
            if normalized in self.http_peers:
                return False
            self.http_peers.add(normalized)
        if host:
            try:
                if self.peer_manager.can_connect(host):
                    self.peer_manager.connect_peer(host)
            except Exception:
                # Do not fail peer registration on connection policy errors; reputation will handle at runtime.
                pass
        return True

    def remove_peer(self, peer_uri: str) -> None:
        """Remove a peer URI and disconnect matching active peers."""
        normalized = self._normalize_peer_uri(peer_uri)
        host = urlparse(normalized).hostname
        with self._peer_lock:
            self.http_peers.discard(normalized)
        if host:
            peers_to_disconnect = [
                pid for pid, info in self.peer_manager.connected_peers.items()
                if info.get("ip_address") == host
            ]
            for pid in peers_to_disconnect:
                try:
                    self.peer_manager.disconnect_peer(pid)
                except Exception:
                    pass

    def get_peer_count(self) -> int:
        """Return count of known peers (HTTP/WebSocket)."""
        with self._peer_lock:
            return len(self.http_peers)

    def get_peers(self) -> Set[str]:
        with self._peer_lock:
            return set(self.http_peers)

    async def start(self) -> None:
        """Starts the P2P network manager."""
        ssl_context = self.peer_manager.encryption.create_ssl_context(
            is_server=True,
            require_client_cert=self.peer_manager.require_client_cert,
            ca_bundle=self.peer_manager.ca_bundle_path,
        )
        self.server = await websockets.serve(
            self._handler, self.host, self.port, ssl=ssl_context
        )
        print(f"P2P server started on {self.host}:{self.port}")
        asyncio.create_task(self._connect_to_peers())
        asyncio.create_task(self._health_check())

    async def stop(self) -> None:
        """Stops the P2P network manager."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        for conn in self.connections.values():
            await conn.close()
        self.connections.clear()
        print("P2P server stopped.")

    async def _handler(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """Handles incoming WebSocket connections."""
        remote_ip = websocket.remote_address[0]
        if not self.peer_manager.can_connect(remote_ip):
            await websocket.close()
            return

        ssl_object = websocket.transport.get_extra_info("ssl_object")
        fingerprint = self.peer_manager.encryption.fingerprint_from_ssl_object(ssl_object) if ssl_object else None
        if self.peer_manager.require_client_cert and not fingerprint:
            self._log_security_event(remote_ip, "missing_client_certificate")
            await websocket.close()
            return
        if not self.peer_manager.is_cert_allowed(fingerprint):
            self._log_security_event(remote_ip, "untrusted_client_certificate")
            await websocket.close()
            return

        if len(self.connections) >= self.max_connections:
            print("Max connections reached. Rejecting new connection.")
            await websocket.close()
            return
        
        peer_id = self.peer_manager.connect_peer(remote_ip)
        self.connections[peer_id] = websocket
        self.websocket_peer_ids[websocket] = peer_id
        print(f"Peer connected: {websocket.remote_address}")

        try:
            async for message in websocket:
                await self._handle_message(websocket, message)
        except ConnectionClosed:
            pass
        finally:
            if peer_id in self.connections:
                conn = self.connections.pop(peer_id, None)
                if conn:
                    self.websocket_peer_ids.pop(conn, None)
                self.peer_manager.disconnect_peer(peer_id)
            print(f"Peer disconnected: {websocket.remote_address}")

    async def _connect_to_peers(self) -> None:
        """Connects to the initial set of peers with backoff/retry."""
        peers_to_connect = self.peer_manager.discovery.get_random_peers()
        for peer_uri in peers_to_connect:
            asyncio.create_task(self._connect_with_retry(peer_uri))

    async def _connect_with_retry(self, peer_uri: str, max_retries: int = 5, initial_delay: int = 5) -> None:
        """Tries to connect to a peer with exponential backoff."""
        delay = initial_delay
        for attempt in range(max_retries):
            try:
                ssl_context = self.peer_manager.encryption.create_ssl_context(
                    ca_bundle=self.peer_manager.ca_bundle_path
                )
                websocket = await websockets.connect(peer_uri, ssl=ssl_context)
                ssl_object = websocket.transport.get_extra_info("ssl_object")
                fingerprint = self.peer_manager.encryption.fingerprint_from_ssl_object(ssl_object) if ssl_object else None
                if not self.peer_manager.is_cert_allowed(fingerprint):
                    self._log_security_event(peer_uri, "untrusted_cert_fingerprint")
                    await websocket.close()
                    self.peer_manager.reputation.record_invalid_block(peer_uri)  # Generic penalty
                    return
                peer_id = self.peer_manager.connect_peer(websocket.remote_address[0])
                self.connections[peer_id] = websocket
                self.websocket_peer_ids[websocket] = peer_id
                print(f"Connected to peer: {peer_uri}")
                return
            except Exception as e:
                print(f"Failed to connect to peer {peer_uri} on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    print(f"Giving up on peer {peer_uri} after {max_retries} failed attempts.")
                    self.peer_manager.reputation.record_disconnect(peer_uri)

    async def _health_check(self) -> None:
        """Periodically checks the health of connected peers."""
        while True:
            await asyncio.sleep(60)
            try:
                self.peer_manager.refresh_trust_stores()
            except Exception as exc:
                self._log_security_event("self", f"trust_store_refresh_failed:{exc}")
            print(f"Health check: {self.get_peer_count()} peers connected.")

    def _log_security_event(self, peer_id: str, message: str) -> None:
        """Log security-related events with lightweight rate limiting to avoid log flooding."""
        if self.security_log_limiter.is_rate_limited(peer_id):
            return
        print(f"[SECURITY] {peer_id}: {message}")
        try:
            from xai.core.monitoring import MetricsCollector
            MetricsCollector.instance().record_security_event(
                event_type=f"p2p.{message}",
                severity="WARNING",
                payload={"peer": peer_id},
            )
        except Exception:
            pass
        
    async def _handle_message(self, websocket: WebSocketServerProtocol, message: Union[str, bytes]) -> None:
        """Handles incoming messages from peers."""
        peer_id = self.websocket_peer_ids.get(websocket, str(websocket.remote_address))
        raw_bytes = message if isinstance(message, (bytes, bytearray)) else message.encode("utf-8")
        
        message_size = len(raw_bytes)
        if not self.bandwidth_limiter_in.consume(peer_id, message_size):
            print(f"Peer {peer_id} is exceeding incoming bandwidth. Disconnecting.")
            await websocket.close()
            if peer_id in self.connections:
                conn = self.connections.pop(peer_id, None)
                if conn:
                    self.websocket_peer_ids.pop(conn, None)
                self.peer_manager.disconnect_peer(peer_id)
            return

        if self.rate_limiter.is_rate_limited(peer_id):
            print(f"Peer {peer_id} is rate-limited. Ignoring message.")
            self._log_security_event(peer_id, "rate_limited")
            return

        try:
            # Verify message signature
            verified_message = self.peer_manager.encryption.verify_signed_message(raw_bytes)
            if not verified_message:
                self._log_security_event(peer_id, "invalid_or_stale_signature")
                try:
                    from xai.core.monitoring import MetricsCollector
                    MetricsCollector.instance().record_security_event(
                        event_type="p2p.invalid_signature",
                        severity="WARNING",
                        payload={"peer": peer_id},
                    )
                except Exception:
                    pass
                self.peer_manager.reputation.record_invalid_transaction(peer_id) # Generic penalty
                return
            
            sender_id = verified_message.get("sender") or peer_id
            nonce = verified_message.get("nonce")
            timestamp = verified_message.get("timestamp")

            if not self.peer_manager.is_sender_allowed(sender_id):
                self._log_security_event(sender_id, "untrusted_sender")
                self.peer_manager.reputation.record_invalid_transaction(peer_id)
                return

            if nonce:
                if self.peer_manager.is_nonce_replay(sender_id, nonce, timestamp):
                    self._log_security_event(sender_id, "replay_detected")
                    self.peer_manager.reputation.record_invalid_transaction(sender_id)
                    return
                self.peer_manager.record_nonce(sender_id, nonce, timestamp)

            data = verified_message.get("payload")

            message_type = data.get("type")
            payload = data.get("payload")

            if message_type == "transaction":
                tx = self.blockchain._transaction_from_dict(payload)
                if self.blockchain.add_transaction(tx):
                    self.peer_manager.reputation.record_valid_transaction(peer_id)
                else:
                    self.peer_manager.reputation.record_invalid_transaction(peer_id)
            elif message_type == "block":
                block = self.blockchain.deserialize_block(payload)
                if self.blockchain.add_block(block):
                    self.peer_manager.reputation.record_valid_block(peer_id)
                else:
                    self.peer_manager.reputation.record_invalid_block(peer_id)
            elif message_type == "get_chain":
                await self._send_signed_message(
                    websocket,
                    peer_id,
                    {"type": "chain", "payload": self.blockchain.to_dict()},
                )
            elif message_type == "chain":
                self.received_chains.append(payload)
            elif message_type == "get_peers":
                peers = list(self.peer_manager.connected_peers.keys())
                await self._send_signed_message(
                    websocket,
                    peer_id,
                    {"type": "peers", "payload": peers},
                )
            elif message_type == "peers":
                self.peer_manager.discovery.exchange_peers(payload)
            elif message_type == "ping":
                await self._send_signed_message(websocket, peer_id, {"type": "pong"})
            elif message_type == "pong":
                # Latency can be calculated here
                pass
            else:
                print(f"Unknown message type: {message_type}")
        except json.JSONDecodeError:
            print("Invalid JSON received from peer.")
            self.peer_manager.reputation.record_invalid_transaction(peer_id)
        except Exception as e:
            print(f"Error handling message: {e}")
            self.peer_manager.reputation.record_invalid_transaction(peer_id)

    async def _send_signed_message(
        self,
        websocket: WebSocketServerProtocol,
        peer_id: str,
        message: Dict[str, Any],
    ) -> None:
        """Sign and send a message to a single peer with bandwidth enforcement."""
        try:
            signed_message = self.peer_manager.encryption.create_signed_message(message)
        except Exception as exc:
            print(f"Failed to sign message for {peer_id}: {exc}")
            return

        message_size = len(signed_message)
        if not self.bandwidth_limiter_out.consume(peer_id, message_size):
            print(f"Peer {peer_id} is exceeding outgoing bandwidth. Disconnecting.")
            await websocket.close()
            if peer_id in self.connections:
                conn = self.connections.pop(peer_id, None)
                if conn:
                    self.websocket_peer_ids.pop(conn, None)
                self.peer_manager.disconnect_peer(peer_id)
            return

        try:
            await websocket.send(signed_message.decode("utf-8"))
        except Exception as exc:
            print(f"Error sending signed message to {peer_id}: {exc}")
            if peer_id in self.connections:
                conn = self.connections.pop(peer_id, None)
                if conn:
                    self.websocket_peer_ids.pop(conn, None)
                self.peer_manager.disconnect_peer(peer_id)
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcasts a message to all connected peers."""
        if not self.connections:
            return

        try:
            signed_message = self.peer_manager.encryption.create_signed_message(message)
        except Exception as exc:
            print(f"Failed to sign broadcast message: {exc}")
            return

        message_size = len(signed_message)
        message_str = signed_message.decode("utf-8")
        
        for peer_id, conn in list(self.connections.items()):
            if not self.bandwidth_limiter_out.consume(peer_id, message_size):
                print(f"Peer {peer_id} is exceeding outgoing bandwidth. Disconnecting.")
                await conn.close()
                del self.connections[peer_id]
                self.websocket_peer_ids.pop(conn, None)
                self.peer_manager.disconnect_peer(peer_id)
                continue
            try:
                await conn.send(message_str)
            except Exception as exc:
                print(f"Error broadcasting to {peer_id}: {exc}")
                await conn.close()
                del self.connections[peer_id]
                self.websocket_peer_ids.pop(conn, None)
                self.peer_manager.disconnect_peer(peer_id)

    def _http_peers_snapshot(self) -> list[str]:
        with self._peer_lock:
            return list(self.http_peers)

    def _dispatch_async(self, coro: Any) -> None:
        """Run or schedule an asyncio coroutine even when no loop is running."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            asyncio.run(coro)

    def broadcast_transaction(self, transaction: "Transaction") -> None:
        """Broadcast a transaction to all connected peers."""
        message = {
            "type": "transaction",
            "payload": transaction.to_dict(),
        }
        payload = transaction.to_dict()
        for peer_uri in self._http_peers_snapshot():
            endpoint = f"{peer_uri.rstrip('/')}/transaction"
            try:
                response = requests.post(endpoint, json=payload, timeout=5)
                if response.status_code >= 400:
                    self.peer_manager.reputation.record_invalid_transaction(peer_uri)
                else:
                    self.peer_manager.reputation.record_valid_transaction(peer_uri)
            except Exception:
                self.peer_manager.reputation.record_invalid_transaction(peer_uri)
        self._dispatch_async(self.broadcast(message))

    def broadcast_block(self, block: "Block") -> None:
        """Broadcast a newly mined block to all connected peers."""
        message = {
            "type": "block",
            "payload": block.to_dict(),
        }
        for peer_uri in self._http_peers_snapshot():
            endpoint = f"{peer_uri.rstrip('/')}/block/receive"
            try:
                requests.post(endpoint, json=message["payload"], timeout=5)
            except Exception:
                pass
        self._dispatch_async(self.broadcast(message))

    def _http_sync(self) -> bool:
        """HTTP-based synchronization for manually registered peers."""
        for peer_uri in self._http_peers_snapshot():
            try:
                base_endpoint = f"{peer_uri.rstrip('/')}/blocks"
                response = requests.get(base_endpoint, timeout=5)
                if response.status_code != 200:
                    continue
                data = response.json()
                remote_blocks = data.get("blocks") or []
                remote_total = data.get("total", len(remote_blocks))
                if remote_total > len(self.blockchain.chain):
                    # Fetch full chain snapshot if remote height is greater
                    response_full = requests.get(
                        base_endpoint, params={"limit": remote_total, "offset": 0}, timeout=5
                    )
                    if response_full.status_code != 200:
                        continue
                    remote_blocks = response_full.json().get("blocks") or []
                    if not isinstance(remote_blocks, list):
                        continue
                    new_chain_headers: list[BlockHeader] = []
                    valid_chain = True
                    for block_data in remote_blocks:
                        header_dict = None
                        txs = []
                        if isinstance(block_data, dict):
                            header_dict = block_data.get("header") or block_data
                            txs = block_data.get("transactions", [])
                        if not header_dict:
                            valid_chain = False
                            break
                        if txs is None:
                            txs = []
                        if not isinstance(txs, list):
                            valid_chain = False
                            break
                        try:
                            header = BlockHeader(
                                index=header_dict["index"],
                                previous_hash=header_dict["previous_hash"],
                                timestamp=header_dict["timestamp"],
                                merkle_root=header_dict["merkle_root"],
                                nonce=header_dict["nonce"],
                                difficulty=header_dict["difficulty"],
                                miner_pubkey=header_dict.get("miner_pubkey"),
                                signature=header_dict.get("signature"),
                            )
                            # Preserve advertised hash if present for downstream integrity checks
                            if "hash" in header_dict:
                                header.hash = header_dict["hash"]
                            new_chain_headers.append(header)
                        except Exception:
                            valid_chain = False
                            break
                    if valid_chain and self.blockchain.replace_chain(new_chain_headers):
                        return True
            except Exception:
                continue
        return False

    async def _ws_sync(self) -> bool:
        """WebSocket-based synchronization using connected peers."""
        self.received_chains = []
        await self.broadcast({"type": "get_chain"})
        await asyncio.sleep(5)  # Wait for 5 seconds to receive chains from peers

        if not self.received_chains:
            return False

        longest_chain = None
        max_length = len(self.blockchain.chain)

        for chain_data in self.received_chains:
            chain = self.blockchain.from_dict(chain_data)
            if len(chain.chain) > max_length and self.blockchain.is_chain_valid(chain.chain):
                max_length = len(chain.chain)
                longest_chain = chain

        if longest_chain:
            self.blockchain.chain = longest_chain.chain
            self.blockchain.pending_transactions = longest_chain.pending_transactions
            return True
        return False

    def sync_with_network(self) -> bool:
        """Synchronize blockchain with peers (HTTP first, then WebSocket)."""
        if self._http_sync():
            return True
        try:
            return asyncio.run(self._ws_sync())
        except RuntimeError:
            # Already inside an event loop; schedule and return False to avoid blocking
            self._dispatch_async(self._ws_sync())
            return False
