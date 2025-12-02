"""
QUIC transport adapter for P2P networking.
Uses aioquic for minimal handshake and frame send/receive.
"""
from __future__ import annotations

import asyncio
from functools import partial
from typing import Callable, Awaitable

try:
    from aioquic.asyncio import serve, connect, QuicConnectionProtocol
    from aioquic.quic.configuration import QuicConfiguration
    from aioquic.quic.events import StreamDataReceived
except ImportError:  # pragma: no cover
    # Soft dependency; QUIC remains disabled when not installed.
    serve = connect = QuicConfiguration = StreamDataReceived = QuicConnectionProtocol = None
    QuicDialTimeout = None  # type: ignore[misc]
else:
    class QuicDialTimeout(ConnectionError):
        """Raised when QUIC dial/send exceeds the configured timeout."""

        def __init__(self, timeout: float):
            super().__init__(f"QUIC send timed out after {timeout} seconds")
            self.timeout = timeout


class QUICServer:
    class _HandlerProtocol(QuicConnectionProtocol):
        def __init__(self, *args, handler: Callable[[bytes], Awaitable[None]], **kwargs):
            super().__init__(*args, **kwargs)
            self._handler = handler

        def quic_event_received(self, event):
            if isinstance(event, StreamDataReceived):
                result = self._handler(event.data)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)

    def __init__(self, host: str, port: int, configuration: QuicConfiguration, handler: Callable[[bytes], Awaitable[None]]):
        self.host = host
        self.port = port
        self.configuration = configuration
        self.handler = handler
        self._server = None

    async def start(self):
        self._server = await serve(
            self.host,
            self.port,
            configuration=self.configuration,
            create_protocol=partial(self._HandlerProtocol, handler=self.handler),
        )

    async def close(self):
        if self._server:
            self._server.close()
            if hasattr(self._server, "wait_closed"):
                await self._server.wait_closed()


async def quic_client_send(host: str, port: int, data: bytes, configuration: QuicConfiguration):
    async with connect(host, port, configuration=configuration) as client:
        stream_id = client._quic.get_next_available_stream_id()
        client._quic.send_stream_data(stream_id, data, end_stream=True)
        client.transmit()
        # Let the network loop progress briefly; aioquic handles retransmits internally.
        await asyncio.sleep(0.05)
        client.close()
        if hasattr(client, "wait_closed"):
            await client.wait_closed()


async def quic_client_send_with_timeout(
    host: str, port: int, data: bytes, configuration: QuicConfiguration, timeout: float = 1.5
):
    try:
        await asyncio.wait_for(quic_client_send(host, port, data, configuration), timeout=timeout)
    except asyncio.TimeoutError as exc:
        raise QuicDialTimeout(timeout) from exc  # type: ignore[misc]
    except Exception as exc:
        raise ConnectionError(f"QUIC send failed: {exc}") from exc
