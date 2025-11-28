from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
import json
import math
from collections import Counter, defaultdict


@dataclass
class WithdrawalAnalysis:
    total_events: int
    total_volume: float
    unique_users: int
    top_users: List[Tuple[str, int, float]]
    sliding_rates: List[int]
    p95_rate: float
    max_rate: int


def load_events(path: Path) -> List[Dict[str, float]]:
    """Load withdrawal events from a JSONL file."""
    if not path.exists():
        return []
    events: List[Dict[str, float]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def load_time_lock_snapshot(path: Path) -> int:
    """Return the number of pending time-locked withdrawals."""
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8") as handle:
            entries = json.load(handle)
    except json.JSONDecodeError:
        return 0
    return sum(1 for entry in entries if entry.get("status", "pending") == "pending")


def _sliding_window_rates(timestamps: List[float], window_seconds: int = 60) -> List[int]:
    if not timestamps:
        return []
    timestamps = sorted(timestamps)
    rates: List[int] = []
    start = 0
    for end, ts in enumerate(timestamps):
        while timestamps[start] < ts - window_seconds:
            start += 1
        rates.append(end - start + 1)
    return rates


def _percentile(sorted_values: List[float], percentile: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    percentile = max(0.0, min(percentile, 1.0))
    k = (len(sorted_values) - 1) * percentile
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_values[int(k)])
    return float(sorted_values[f] * (c - k) + sorted_values[c] * (k - f))


def analyze_events(events: Iterable[Dict[str, float]], window_seconds: int = 60) -> WithdrawalAnalysis:
    events_list = list(events)
    if not events_list:
        return WithdrawalAnalysis(0, 0.0, 0, [], [], 0.0, 0)

    timestamps = [float(evt.get("timestamp", 0.0)) for evt in events_list]
    sliding_rates = _sliding_window_rates(timestamps, window_seconds)
    sorted_rates = sorted(sliding_rates)
    p95_rate = _percentile(sorted_rates, 0.95)
    max_rate = sorted_rates[-1] if sorted_rates else 0

    total_volume = sum(float(evt.get("amount", 0.0)) for evt in events_list)
    user_counts: Counter[str] = Counter()
    user_volume: defaultdict[str, float] = defaultdict(float)

    for evt in events_list:
        user = str(evt.get("user", "unknown"))
        user_counts[user] += 1
        user_volume[user] += float(evt.get("amount", 0.0))

    top_users = [
        (user, user_counts[user], user_volume[user])
        for user in user_counts.most_common(5)
    ]

    return WithdrawalAnalysis(
        total_events=len(events_list),
        total_volume=total_volume,
        unique_users=len(user_counts),
        top_users=top_users,
        sliding_rates=sliding_rates,
        p95_rate=p95_rate,
        max_rate=max_rate,
    )


def recommend_rate_threshold(
    analysis: WithdrawalAnalysis,
    percentile: float = 0.95,
    headroom: float = 0.25,
    floor: int = 5,
) -> int:
    """Recommend a withdrawal rate threshold based on historical data."""
    if not analysis.sliding_rates:
        return floor
    sorted_rates = sorted(analysis.sliding_rates)
    pct_value = _percentile(sorted_rates, percentile)
    baseline = max(pct_value, analysis.max_rate, floor)
    return max(floor, int(math.ceil(baseline * (1 + headroom))))


def recommend_backlog_threshold(
    current_backlog: int,
    headroom: float = 0.5,
    floor: int = 3,
) -> int:
    """Recommend time-lock backlog threshold with configurable headroom."""
    baseline = max(current_backlog, floor)
    return max(floor, int(math.ceil(baseline * (1 + headroom))))
