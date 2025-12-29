"""
QUIC transport adapter for P2P networking.
Uses aioquic for minimal handshake and frame send/receive.
"""
from __future__ import annotations

import asyncio
from functools import partial
from typing import TYPE_CHECKING, Any, Awaitable, Callable

if TYPE_CHECKING:
    from aioquic.asyncio import QuicConnectionProtocol
    from aioquic.quic.configuration import QuicConfiguration
    from aioquic.quic.events import StreamDataReceived

try:
    from aioquic.asyncio import QuicConnectionProtocol, connect, serve
    from aioquic.quic.configuration import QuicConfiguration
    from aioquic.quic.events import StreamDataReceived
    AIOQUIC_AVAILABLE = True
except ImportError:  # pragma: no cover
    # Soft dependency; QUIC remains disabled when not installed.
    AIOQUIC_AVAILABLE = False
    serve = None  # type: ignore[assignment]
    connect = None  # type: ignore[assignment]
    QuicConfiguration = None  # type: ignore[assignment,misc]
    StreamDataReceived = None  # type: ignore[assignment,misc]
    QuicConnectionProtocol = None  # type: ignore[assignment,misc]


class QuicDialTimeout(ConnectionError):
    """Raised when QUIC dial/send exceeds the configured timeout."""

    def __init__(self, timeout: float) -> None:
        super().__init__(f"QUIC send timed out after {timeout} seconds")
        self.timeout = timeout


class QuicTransportError(ConnectionError):
    """Raised when QUIC transport operations fail."""
    pass


class QUICServer:
    class _HandlerProtocol(QuicConnectionProtocol):  # type: ignore[misc]
        def __init__(self, *args: Any, handler: Callable[[bytes], Awaitable[None]], **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self._handler = handler

        def quic_event_received(self, event: Any) -> None:
            if StreamDataReceived is not None and isinstance(event, StreamDataReceived):
                result = self._handler(event.data)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)

    def __init__(self, host: str, port: int, configuration: Any, handler: Callable[[bytes], Awaitable[None]]) -> None:
        self.host = host
        self.port = port
        self.configuration = configuration
        self.handler = handler
        self._server: Any = None

    async def start(self) -> None:
        if serve is None:
            raise RuntimeError("aioquic not installed - QUIC transport unavailable")
        self._server = await serve(
            self.host,
            self.port,
            configuration=self.configuration,
            create_protocol=partial(self._HandlerProtocol, handler=self.handler),
        )

    async def close(self) -> None:
        if self._server:
            self._server.close()
            if hasattr(self._server, "wait_closed"):
                await self._server.wait_closed()


async def quic_client_send(host: str, port: int, data: bytes, configuration: Any) -> None:
    if connect is None:
        raise RuntimeError("aioquic not installed - QUIC transport unavailable")
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
    host: str, port: int, data: bytes, configuration: Any, timeout: float = 1.5
) -> None:
    try:
        await asyncio.wait_for(quic_client_send(host, port, data, configuration), timeout=timeout)
    except asyncio.TimeoutError as exc:
        raise QuicDialTimeout(timeout) from exc
    except (OSError, ConnectionError) as exc:
        raise QuicTransportError(f"QUIC network error: {exc}") from exc
    except (ValueError, TypeError) as exc:
        raise QuicTransportError(f"Invalid QUIC parameters: {exc}") from exc
    except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
        raise QuicTransportError(f"QUIC send failed: {exc}") from exc
