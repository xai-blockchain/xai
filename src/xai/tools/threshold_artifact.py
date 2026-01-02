from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from collections.abc import Mapping


def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def _coerce_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

@dataclass
class ThresholdTopUser:
    user: str
    count: int
    total_volume: float

@dataclass
class ThresholdAnalysis:
    events_analyzed: int
    unique_users: int
    total_volume: float
    max_rate_per_minute: int
    p95_rate_per_minute: float
    current_backlog: int
    top_users: list[ThresholdTopUser]

@dataclass
class ThresholdInputs:
    percentile: float
    headroom: float
    backlog_headroom: float
    window_seconds: int
    events_log: str
    locks_file: str

@dataclass
class ThresholdRecommendations:
    rate_per_minute: int | None
    time_lock_backlog: int | None

@dataclass
class ThresholdCurrent:
    rate_per_minute: int | None
    time_lock_backlog: int | None

@dataclass
class ThresholdDetails:
    generated_at: str
    analysis: ThresholdAnalysis
    recommendations: ThresholdRecommendations
    inputs: ThresholdInputs
    current_thresholds: ThresholdCurrent
    alert_required: bool

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ThresholdDetails":
        analysis = payload.get("analysis", {})
        rec = payload.get("recommendations", {})
        current = payload.get("current_thresholds", {})
        inputs = payload.get("inputs", {})
        top_users = [
            ThresholdTopUser(
                user=str(entry.get("user", "unknown")),
                count=int(entry.get("count", 0)),
                total_volume=_coerce_float(entry.get("total_volume")),
            )
            for entry in analysis.get("top_users", [])[:5]
        ]
        details = cls(
            generated_at=str(payload.get("generated_at") or datetime.now(timezone.utc).isoformat()),
            analysis=ThresholdAnalysis(
                events_analyzed=int(analysis.get("events_analyzed", 0)),
                unique_users=int(analysis.get("unique_users", 0)),
                total_volume=_coerce_float(analysis.get("total_volume")),
                max_rate_per_minute=int(analysis.get("max_rate_per_minute", 0)),
                p95_rate_per_minute=_coerce_float(analysis.get("p95_rate_per_minute")),
                current_backlog=int(analysis.get("current_backlog", 0)),
                top_users=top_users,
            ),
            recommendations=ThresholdRecommendations(
                rate_per_minute=_coerce_int(rec.get("rate_per_minute")),
                time_lock_backlog=_coerce_int(rec.get("time_lock_backlog")),
            ),
            inputs=ThresholdInputs(
                percentile=float(inputs.get("percentile", 0.95)),
                headroom=float(inputs.get("headroom", 0.0)),
                backlog_headroom=float(inputs.get("backlog_headroom", 0.0)),
                window_seconds=int(inputs.get("window_seconds", 60)),
                events_log=str(inputs.get("events_log", "")),
                locks_file=str(inputs.get("locks_file", "")),
            ),
            current_thresholds=ThresholdCurrent(
                rate_per_minute=_coerce_int(current.get("rate_per_minute")),
                time_lock_backlog=_coerce_int(current.get("time_lock_backlog")),
            ),
            alert_required=bool(payload.get("alert_required", False)),
        )
        return details

    @classmethod
    def from_path(cls, path: Path) -> "ThresholdDetails":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "analysis": {
                "events_analyzed": self.analysis.events_analyzed,
                "unique_users": self.analysis.unique_users,
                "total_volume": self.analysis.total_volume,
                "max_rate_per_minute": self.analysis.max_rate_per_minute,
                "p95_rate_per_minute": self.analysis.p95_rate_per_minute,
                "current_backlog": self.analysis.current_backlog,
                "top_users": [asdict(user) for user in self.analysis.top_users],
            },
            "recommendations": asdict(self.recommendations),
            "inputs": asdict(self.inputs),
            "current_thresholds": asdict(self.current_thresholds),
            "alert_required": self.alert_required,
        }

    def to_markdown(self, *, environment: str, commit: str | None = None) -> str:
        lines = [
            f"**Environment**: {environment}",
            f"**Generated**: {self.generated_at}",
        ]
        if commit:
            lines.append(f"**Commit**: `{commit}`")
        lines.extend(
            [
                "",
                f"- Recommended rate threshold: {self.recommendations.rate_per_minute}",
                f"- Recommended backlog threshold: {self.recommendations.time_lock_backlog}",
                f"- Current rate threshold: {self.current_thresholds.rate_per_minute}",
                f"- Current backlog threshold: {self.current_thresholds.time_lock_backlog}",
                f"- Alert required: {'yes' if self.alert_required else 'no'}",
                "",
                f"Events analyzed: {self.analysis.events_analyzed}, "
                f"unique users: {self.analysis.unique_users}, "
                f"max rate/min: {self.analysis.max_rate_per_minute}, "
                f"p95 rate/min: {self.analysis.p95_rate_per_minute:.2f}",
                f"Current backlog: {self.analysis.current_backlog}",
                "",
                "Top users:",
            ]
        )
        if not self.analysis.top_users:
            lines.append("  - None recorded")
        else:
            for entry in self.analysis.top_users:
                lines.append(
                    f"  - {entry.user}: {entry.count} withdrawals, {entry.total_volume:.2f} total"
                )
        return "\n".join(lines)

    def to_history_entry(self, *, environment: str, commit: str | None = None) -> "ThresholdHistoryEntry":
        return ThresholdHistoryEntry(
            generated_at=self.generated_at,
            environment=environment,
            commit=commit,
            recommended_rate=self.recommendations.rate_per_minute,
            recommended_backlog=self.recommendations.time_lock_backlog,
            current_rate_threshold=self.current_thresholds.rate_per_minute,
            current_backlog_threshold=self.current_thresholds.time_lock_backlog,
            alert_required=self.alert_required,
            events_analyzed=self.analysis.events_analyzed,
            unique_users=self.analysis.unique_users,
            total_volume=self.analysis.total_volume,
            max_rate_per_minute=self.analysis.max_rate_per_minute,
            p95_rate_per_minute=self.analysis.p95_rate_per_minute,
            current_backlog=self.analysis.current_backlog,
        )

@dataclass
class ThresholdHistoryEntry:
    generated_at: str
    environment: str
    commit: str | None
    recommended_rate: int | None
    recommended_backlog: int | None
    current_rate_threshold: int | None
    current_backlog_threshold: int | None
    alert_required: bool
    events_analyzed: int
    unique_users: int
    total_volume: float
    max_rate_per_minute: int
    p95_rate_per_minute: float
    current_backlog: int

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

def append_history_entry(history_path: Path, entry: ThresholdHistoryEntry) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(entry.to_json())
        handle.write("\n")

def load_history(history_path: Path) -> list[ThresholdHistoryEntry]:
    if not history_path.exists():
        return []
    entries: list[ThresholdHistoryEntry] = []
    with history_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            entries.append(
                ThresholdHistoryEntry(
                    generated_at=str(payload.get("generated_at")),
                    environment=str(payload.get("environment", "")),
                    commit=payload.get("commit"),
                    recommended_rate=_coerce_int(payload.get("recommended_rate")),
                    recommended_backlog=_coerce_int(payload.get("recommended_backlog")),
                    current_rate_threshold=_coerce_int(payload.get("current_rate_threshold")),
                    current_backlog_threshold=_coerce_int(payload.get("current_backlog_threshold")),
                    alert_required=bool(payload.get("alert_required", False)),
                    events_analyzed=int(payload.get("events_analyzed", 0)),
                    unique_users=int(payload.get("unique_users", 0)),
                    total_volume=_coerce_float(payload.get("total_volume")),
                    max_rate_per_minute=int(payload.get("max_rate_per_minute", 0)),
                    p95_rate_per_minute=_coerce_float(payload.get("p95_rate_per_minute")),
                    current_backlog=int(payload.get("current_backlog", 0)),
                )
            )
    return entries

def prune_history(history_path: Path, max_entries: int) -> None:
    if max_entries <= 0 or not history_path.exists():
        return
    with history_path.open("r", encoding="utf-8") as handle:
        lines = [line for line in handle.readlines() if line.strip()]
    if len(lines) <= max_entries:
        return
    trimmed = lines[-max_entries:]
    with history_path.open("w", encoding="utf-8") as handle:
        handle.writelines(trimmed)
