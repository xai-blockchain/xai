"""
Background monitor that ingests blockchain deposit events and credits exchange wallets.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import requests
from requests import RequestException

logger = logging.getLogger(__name__)

@dataclass
class DepositEvent:
    """Represents a blockchain deposit detection emitted by a source adapter."""

    tx_hash: str
    user_address: str
    deposit_address: str
    currency: str
    amount: float
    confirmations: int = 0
    required_confirmations: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized_currency(self) -> str:
        return self.currency.upper()

class BaseDepositSource(ABC):
    """Interface for deposit sources."""

    @abstractmethod
    def poll(self) -> list[DepositEvent]:
        """Return a list of new or updated deposit events."""

class FileDepositSource(BaseDepositSource):
    """
    Development-friendly deposit source that reads events from a JSON file.

    The file should contain an array of dicts with:
        - tx_hash
        - user_address
        - deposit_address
        - currency
        - amount
        - confirmations (optional)
        - required_confirmations (optional)
        - metadata (optional)
    """

    def __init__(
        self,
        path: str,
        *,
        min_confirmations: int = 0,
        max_events_per_poll: int = 500,
    ) -> None:
        self.path = os.path.abspath(path)
        self.min_confirmations = max(0, int(min_confirmations))
        self.max_events = max(1, int(max_events_per_poll))
        self._lock = threading.Lock()
        self._seen_confirmations: dict[str, int] = {}

    def poll(self) -> list[DepositEvent]:
        events: list[DepositEvent] = []
        if not os.path.exists(self.path):
            return events

        with self._lock:
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
            except (OSError, json.JSONDecodeError) as exc:
                logger.error(
                    "Failed to read deposit source file %s: %s",
                    self.path,
                    exc,
                    extra={"event": "deposit.file_source_error", "path": self.path},
                )
                return events

            if not isinstance(payload, list):
                logger.warning(
                    "Deposit source file malformed (expected list)",
                    extra={"event": "deposit.file_source_invalid_format", "path": self.path},
                )
                return events

            for entry in payload:
                if len(events) >= self.max_events:
                    break
                event = self._parse_entry(entry)
                if not event:
                    continue
                previous = self._seen_confirmations.get(event.tx_hash, -1)
                if event.confirmations <= previous:
                    continue
                self._seen_confirmations[event.tx_hash] = event.confirmations
                events.append(event)
        return events

    def _parse_entry(self, entry: dict[str, Any]) -> DepositEvent | None:
        if not isinstance(entry, dict):
            return None
        tx_hash = str(entry.get("tx_hash") or entry.get("txid") or "").strip()
        user_address = str(entry.get("user_address") or "").strip()
        deposit_address = str(entry.get("deposit_address") or "").strip()
        currency = str(entry.get("currency") or "").strip()
        amount = entry.get("amount")
        if not tx_hash or not user_address or not deposit_address or not currency:
            return None
        try:
            amount_float = float(amount)
        except (TypeError, ValueError):
            return None
        confirmations = int(entry.get("confirmations") or 0)
        confirmations = max(confirmations, self.min_confirmations)
        required = entry.get("required_confirmations")
        if required is not None:
            try:
                required = max(int(required), confirmations, self.min_confirmations)
            except (TypeError, ValueError):
                required = None
        metadata = entry.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        return DepositEvent(
            tx_hash=tx_hash,
            user_address=user_address,
            deposit_address=deposit_address,
            currency=currency,
            amount=amount_float,
            confirmations=confirmations,
            required_confirmations=required,
            metadata=metadata,
        )

class InMemoryDepositSource(BaseDepositSource):
    """Test utility that replays a predefined sequence of events."""

    def __init__(self, events: Iterable[DepositEvent] | None = None) -> None:
        self._events = list(events or [])
        self._lock = threading.Lock()

    def add_event(self, event: DepositEvent) -> None:
        with self._lock:
            self._events.append(event)

    def poll(self) -> list[DepositEvent]:
        with self._lock:
            events = list(self._events)
            self._events.clear()
            return events

def _extract_path(obj: Any, path: str | None, default: Any = None) -> Any:
    """Safely navigate dotted/indexed paths through dict/list structures."""
    if not path:
        return obj
    current = obj
    for segment in path.split("."):
        if isinstance(current, dict):
            if segment not in current:
                return default
            current = current[segment]
        elif isinstance(current, (list, tuple)):
            try:
                idx = int(segment)
            except ValueError:
                return default
            if idx < 0 or idx >= len(current):
                return default
            current = current[idx]
        else:
            return default
    return current

class ExplorerDepositSource(BaseDepositSource):
    """
    Polls HTTP explorer APIs for transactions hitting registered deposit addresses.

    Each poll iterates through known addresses (with configurable limits), calls
    the configured endpoint, extracts transaction metadata using dotted paths,
    and emits DepositEvent entries once confirmations exceed thresholds.
    """

    def __init__(
        self,
        deposit_manager,
        currency: str,
        endpoint_template: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        min_confirmations: int = 0,
        timeout: float = 6.0,
        amount_path: str = "amount",
        confirmations_path: str = "confirmations",
        txid_path: str = "txid",
        metadata_paths: dict[str, str] | None = None,
        records_path: str | None = None,
        amount_divisor: float = 1.0,
        max_addresses_per_cycle: int = 25,
    ) -> None:
        self.deposit_manager = deposit_manager
        self.currency = currency.upper()
        self.endpoint_template = endpoint_template
        self.method = (method or "GET").upper()
        self.headers = headers or {}
        self.params = params or {}
        self.min_confirmations = max(0, int(min_confirmations))
        self.timeout = max(1.0, float(timeout))
        self.amount_path = amount_path
        self.confirmations_path = confirmations_path
        self.txid_path = txid_path
        self.metadata_paths = metadata_paths or {}
        self.records_path = records_path
        self.amount_divisor = amount_divisor if amount_divisor not in (0, None) else 1.0
        self.max_addresses = max(1, int(max_addresses_per_cycle))
        self._seen_confirmations: dict[str, int] = {}

    def poll(self) -> list[DepositEvent]:
        addresses = self.deposit_manager.list_addresses_by_currency(self.currency)
        if not addresses:
            return []
        events: list[DepositEvent] = []
        for entry in addresses[: self.max_addresses]:
            deposit_address = entry.get("deposit_address")
            user_address = entry.get("user_address")
            if not deposit_address or not user_address:
                continue
            url = self.endpoint_template.format(address=deposit_address)
            try:
                resp = requests.request(
                    self.method,
                    url,
                    headers=self.headers,
                    params=self.params,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                payload = resp.json()
            except RequestException as exc:
                logger.warning(
                    "Explorer deposit request failed",
                    extra={
                        "event": "deposit.explorer_source_error",
                        "currency": self.currency,
                        "address": deposit_address,
                        "error": str(exc),
                    },
                )
                continue
            except ValueError as exc:
                logger.warning(
                    "Explorer deposit returned invalid JSON",
                    extra={
                        "event": "deposit.explorer_source_bad_json",
                        "currency": self.currency,
                        "address": deposit_address,
                        "error": str(exc),
                    },
                )
                continue

            records = payload
            if self.records_path:
                records = _extract_path(payload, self.records_path, default=[])
            if not isinstance(records, list):
                logger.debug(
                    "Explorer deposit response missing list records",
                    extra={
                        "event": "deposit.explorer_source_not_list",
                        "currency": self.currency,
                        "address": deposit_address,
                    },
                )
                continue

            for record in records:
                event = self._record_to_event(record, user_address, deposit_address)
                if not event:
                    continue
                previous = self._seen_confirmations.get(event.tx_hash, -1)
                if event.confirmations <= previous:
                    continue
                self._seen_confirmations[event.tx_hash] = event.confirmations
                events.append(event)
        return events

    def _record_to_event(
        self, record: Any, user_address: str, deposit_address: str
    ) -> DepositEvent | None:
        tx_hash = _extract_path(record, self.txid_path)
        if not tx_hash:
            return None
        amount_raw = _extract_path(record, self.amount_path)
        confirmations = _extract_path(record, self.confirmations_path, default=0)
        try:
            confirmations_int = max(0, int(confirmations))
        except (TypeError, ValueError):
            confirmations_int = 0
        if confirmations_int < self.min_confirmations:
            return None
        try:
            amount_value = float(amount_raw)
        except (TypeError, ValueError):
            return None
        amount = amount_value / self.amount_divisor
        metadata = {}
        for key, path in self.metadata_paths.items():
            metadata[key] = _extract_path(record, path)
        return DepositEvent(
            tx_hash=str(tx_hash),
            user_address=user_address,
            deposit_address=deposit_address,
            currency=self.currency,
            amount=amount,
            confirmations=confirmations_int,
            metadata=metadata,
        )

class CryptoDepositMonitor:
    """Coordinates deposit sources and feeds the crypto deposit manager."""

    def __init__(
        self,
        deposit_manager,
        *,
        poll_interval: int = 30,
        jitter_seconds: int = 5,
        metrics_collector: Any | None = None,
    ) -> None:
        self.deposit_manager = deposit_manager
        self.poll_interval = max(5, int(poll_interval))
        self.jitter_seconds = max(0, int(jitter_seconds))
        self.metrics_collector = metrics_collector
        self.sources: dict[str, BaseDepositSource] = {}
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._stats_lock = threading.Lock()
        self._stats: dict[str, Any] = {
            "processed": 0,
            "credited": 0,
            "pending": 0,
            "errors": 0,
            "last_run": None,
        }

    def register_source(self, currency: str, source: BaseDepositSource) -> None:
        normalized = currency.upper()
        self.sources[normalized] = source
        logger.info(
            "Registered crypto deposit source",
            extra={"event": "deposit.monitor_source_registered", "currency": normalized},
        )

    def start(self) -> bool:
        if not self.sources:
            logger.warning(
                "Crypto deposit monitor start skipped (no sources)",
                extra={"event": "deposit.monitor_no_sources"},
            )
            return False
        if self._thread and self._thread.is_alive():
            return True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, name="crypto-deposit-monitor", daemon=True
        )
        self._thread.start()
        logger.info(
            "Crypto deposit monitor started",
            extra={
                "event": "deposit.monitor_started",
                "interval": self.poll_interval,
                "sources": list(self.sources.keys()),
            },
        )
        return True

    def stop(self) -> None:
        if not self._thread:
            return
        self._stop_event.set()
        self._thread.join(timeout=5)
        logger.info("Crypto deposit monitor stopped", extra={"event": "deposit.monitor_stopped"})
        self._thread = None

    def run_once(self) -> None:
        """Process every source exactly once (useful for tests)."""
        self._process_sources()

    def get_stats(self) -> dict[str, Any]:
        with self._stats_lock:
            return dict(self._stats)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            start = time.time()
            try:
                self._process_sources()
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
                logger.error(
                    "Crypto deposit monitor iteration failed: %s",
                    exc,
                    extra={"event": "deposit.monitor_iteration_failed"},
                )
            elapsed = time.time() - start
            sleep_for = max(1.0, self.poll_interval - elapsed)
            if self.jitter_seconds:
                # Use cryptographically secure random for jitter
                import secrets
                sleep_for += secrets.randbelow(int(self.jitter_seconds * 1000)) / 1000.0
            if self._stop_event.wait(sleep_for):
                break

    def _process_sources(self) -> None:
        processed = credited = pending = errors = 0
        for currency, source in list(self.sources.items()):
            try:
                events = source.poll()
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:  # pragma: no cover - defensive logging
                errors += 1
                logger.error(
                    "Deposit source poll failed (%s): %s",
                    currency,
                    exc,
                    extra={"event": "deposit.source_poll_failed", "currency": currency},
                )
                continue
            for event in events:
                try:
                    status = self._handle_event(event)
                except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:  # pragma: no cover - defensive logging
                    errors += 1
                    logger.exception(
                        "Failed to process deposit event",
                        extra={
                            "event": "deposit.monitor_event_failed",
                            "currency": event.normalized_currency(),
                            "tx_hash": event.tx_hash,
                        },
                    )
                    continue
                processed += 1
                if status == "credited":
                    credited += 1
                else:
                    pending += 1
        snapshot = {
            "processed": processed,
            "credited": credited,
            "pending": pending,
            "errors": errors,
            "last_run": time.time(),
        }
        with self._stats_lock:
            self._stats = snapshot
        if self.metrics_collector:
            try:
                self.metrics_collector.record_crypto_deposit_stats(snapshot)
            except (RuntimeError, ValueError, AttributeError, KeyError) as e:  # pragma: no cover - optional metrics hook
                logger.debug(
                    "Metrics recorder for crypto deposits raised an exception",
                    extra={"error_type": type(e).__name__, "error": str(e)},
                    exc_info=True
                )

    def _handle_event(self, event: DepositEvent) -> str:
        metadata = event.metadata or {}
        response = self.deposit_manager.record_blockchain_deposit(
            user_address=event.user_address,
            currency=event.currency,
            amount=event.amount,
            tx_hash=event.tx_hash,
            deposit_address=event.deposit_address,
            confirmations=event.confirmations,
            metadata=metadata,
        )
        status = response.get("status", "pending")
        if status != "credited" and event.confirmations:
            self.deposit_manager.update_confirmations(event.tx_hash, event.confirmations)
        logger.info(
            "Processed crypto deposit event",
            extra={
                "event": "deposit.monitor_event",
                "tx_hash": event.tx_hash,
                "currency": event.normalized_currency(),
                "status": status,
                "amount": event.amount,
                "confirmations": event.confirmations,
                "user_address": event.user_address[:12] + "...",
            },
        )
        return status

def create_deposit_source(
    currency: str,
    config: dict[str, Any],
    deposit_manager,
) -> BaseDepositSource:
    """
    Construct a deposit source instance from configuration data.
    """
    if config is None:
        raise ValueError("Deposit source configuration missing")

    source_type = str(config.get("type") or "file").lower()

    if source_type == "file":
        path = (config.get("path") or config.get("file") or "").strip()
        if not path:
            raise ValueError("File deposit source requires 'path'")
        min_conf = int(config.get("min_confirmations", 0) or 0)
        max_events = int(config.get("max_events_per_poll", 500) or 500)
        return FileDepositSource(
            path=path,
            min_confirmations=min_conf,
            max_events_per_poll=max_events,
        )

    if source_type == "explorer":
        endpoint = (config.get("endpoint") or config.get("url") or "").strip()
        if not endpoint:
            raise ValueError("Explorer deposit source requires 'endpoint'")
        if deposit_manager is None:
            raise ValueError("Explorer deposit source requires a deposit manager")

        return ExplorerDepositSource(
            deposit_manager=deposit_manager,
            currency=currency,
            endpoint_template=endpoint,
            method=config.get("method", "GET"),
            headers=config.get("headers"),
            params=config.get("params"),
            min_confirmations=config.get("min_confirmations", 0),
            timeout=config.get("timeout", 6.0),
            amount_path=config.get("amount_path", "amount"),
            confirmations_path=config.get("confirmations_path", "confirmations"),
            txid_path=config.get("txid_path", "txid"),
            metadata_paths=config.get("metadata_paths"),
            records_path=config.get("records_path"),
            amount_divisor=config.get("amount_divisor", 1.0),
            max_addresses_per_cycle=config.get("max_addresses_per_cycle", 25),
        )

    raise ValueError(f"Unsupported deposit source type '{source_type}'")
