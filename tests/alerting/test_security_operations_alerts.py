import math
import re
from pathlib import Path

import pytest
import yaml


RULES_PATH = Path(__file__).resolve().parents[2] / "prometheus/alerts/security_operations.yml"
BLOCKCHAIN_RULES_PATH = Path(__file__).resolve().parents[2] / "prometheus/alerts/blockchain_alerts.yml"


def load_rules():
    data = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))
    rules = {}
    for group in data.get("groups", []):
        for rule in group.get("rules", []):
            rules[rule["alert"]] = rule
    return rules


def load_blockchain_rules():
    data = yaml.safe_load(BLOCKCHAIN_RULES_PATH.read_text(encoding="utf-8"))
    rules = {}
    for group in data.get("groups", []):
        for rule in group.get("rules", []):
            rules[rule["alert"]] = rule
    return rules


def evaluate_increase_expression(expr: str, series):
    pattern = re.compile(
        r"increase\((?P<metric>[a-zA-Z0-9_]+)(?:\{[^}]*\})?\[(?P<window>[0-9]+m)\]\)\s*>\s*(?P<threshold>[0-9.]+)"
    )
    match = pattern.match(expr.replace(" ", ""))
    if not match:
        raise AssertionError(f"Expression {expr} not supported")
    threshold = float(match.group("threshold"))
    delta = series[-1] - series[0]
    return delta > threshold


def evaluate_gauge_expression(expr: str, value: float):
    pattern = re.compile(r"(?P<metric>[a-zA-Z0-9_]+)\s*(?P<op>[<>])\s*(?P<threshold>[0-9.]+)")
    match = pattern.match(expr.strip())
    if not match:
        raise AssertionError(f"Expression {expr} not supported")
    threshold = float(match.group("threshold"))
    op = match.group("op")
    if op == ">":
        return value > threshold, threshold
    return value < threshold, threshold


def evaluate_histogram_expression(expr: str, buckets):
    pattern = re.compile(
        r"histogram_quantile\((?P<quant>[0-9.]+),\s*rate\((?P<metric>[a-zA-Z0-9_]+)_bucket\[.+?\]\)\)\s*(?P<op>[<>])\s*(?P<threshold>[0-9.]+)"
    )
    match = pattern.match(expr.replace(" ", ""))
    if not match:
        raise AssertionError(f"Expression {expr} not supported")
    quant = float(match.group("quant"))
    threshold = float(match.group("threshold"))
    op = match.group("op")
    value = _compute_histogram_quantile(buckets, quant)
    if op == ">":
        return value > threshold, threshold, value
    return value < threshold, threshold, value


def _compute_histogram_quantile(buckets, quantile):
    if not buckets:
        return 0.0
    def parse_boundary(boundary):
        if boundary == "+Inf":
            return float("inf")
        return float(boundary)

    sorted_buckets = sorted(buckets, key=lambda x: parse_boundary(x[0]))
    total = sorted_buckets[-1][1]
    if total <= 0:
        return 0.0
    target = quantile * total
    prev_count = 0.0
    prev_boundary = 0.0
    for boundary, count in sorted_buckets:
        current_boundary = parse_boundary(boundary)
        if target <= count:
            if math.isinf(current_boundary):
                return prev_boundary
            if count == prev_count:
                return current_boundary
            fraction = (target - prev_count) / (count - prev_count)
            return prev_boundary + (current_boundary - prev_boundary) * fraction
        prev_count = count
        prev_boundary = current_boundary
    return prev_boundary


def evaluate_ratio_expression(expr: str, numerator_series, denominator_series):
    pattern = re.compile(
        r"rate\((?P<num>[a-zA-Z0-9_]+)(?:\{[^}]*\})?\[(?P<num_window>[0-9]+m)\]\)\s*/\s*rate\((?P<den>[a-zA-Z0-9_]+)(?:\{[^}]*\})?\[(?P<den_window>[0-9]+m)\]\)\s*(?P<op>[<>])\s*(?P<threshold>[0-9.]+)"
    )
    match = pattern.match(expr.replace(" ", ""))
    if not match:
        raise AssertionError(f"Expression {expr} not supported")
    threshold = float(match.group("threshold"))
    op = match.group("op")
    ratio = _calculate_rate_ratio(numerator_series, denominator_series)
    if op == ">":
        return ratio > threshold, threshold, ratio
    return ratio < threshold, threshold, ratio


def _calculate_rate_ratio(numerator_series, denominator_series):
    if len(numerator_series) < 2 or len(denominator_series) < 2:
        return 0.0
    num_delta = numerator_series[-1] - numerator_series[0]
    den_delta = denominator_series[-1] - denominator_series[0]
    if den_delta <= 0:
        return 0.0
    return num_delta / den_delta


def evaluate_equality_expression(expr: str, value: float):
    pattern = re.compile(r"(?P<metric>[a-zA-Z0-9_]+)\s*==\s*(?P<target>[0-9.]+)")
    match = pattern.match(expr.strip())
    if not match:
        raise AssertionError(f"Expression {expr} not supported")
    target = float(match.group("target"))
    return value == target, target


def test_api_key_revocations_alert_triggers_on_increase():
    rules = load_rules()
    expr = rules["ApiKeyRevocations"]["expr"]
    assert evaluate_increase_expression(expr, [0, 1])
    assert not evaluate_increase_expression(expr, [5, 5])


def test_security_event_storm_alert_threshold():
    rules = load_rules()
    expr = rules["SecurityEventStorm"]["expr"]
    assert evaluate_increase_expression(expr, [0, 30])
    assert not evaluate_increase_expression(expr, [10, 30])  # delta 20 < 25


def test_withdrawal_rate_spike_threshold_is_15():
    rules = load_rules()
    expr = rules["WithdrawalRateSpike"]["expr"]
    triggered, threshold = evaluate_gauge_expression(expr, 16)
    assert threshold == 15
    assert triggered
    triggered, _ = evaluate_gauge_expression(expr, 14)
    assert not triggered


def test_time_lock_backlog_threshold_is_5():
    rules = load_rules()
    expr = rules["TimeLockBacklogGrowing"]["expr"]
    triggered, threshold = evaluate_gauge_expression(expr, 6)
    assert threshold == 5
    assert triggered
    triggered, _ = evaluate_gauge_expression(expr, 4)
    assert not triggered


def test_low_block_production_rate_threshold():
    rules = load_blockchain_rules()
    expr = rules["LowBlockProductionRate"]["expr"]
    triggered, threshold = evaluate_gauge_expression(expr, 0.4)
    assert threshold == 0.5
    assert triggered
    triggered, _ = evaluate_gauge_expression(expr, 0.6)
    assert not triggered


def test_high_cpu_usage_threshold():
    rules = load_blockchain_rules()
    expr = rules["HighCPUUsage"]["expr"]
    triggered, threshold = evaluate_gauge_expression(expr, 95)
    assert threshold == 90
    assert triggered
    triggered, _ = evaluate_gauge_expression(expr, 80)
    assert not triggered


def test_high_network_latency_histogram_alert():
    rules = load_blockchain_rules()
    expr = rules["HighNetworkLatency"]["expr"]
    buckets_high = [
        ("0.5", 10),
        ("1", 30),
        ("2", 80),
        ("3", 120),
        ("4", 140),
        ("5", 150),
        ("+Inf", 155),
    ]
    triggered, threshold, value = evaluate_histogram_expression(expr, buckets_high)
    assert threshold == 2
    assert triggered
    buckets_low = [
        ("0.5", 80),
        ("1", 150),
        ("1.5", 190),
        ("2", 210),
        ("3", 215),
        ("+Inf", 220),
    ]
    triggered, _, _ = evaluate_histogram_expression(expr, buckets_low)
    assert not triggered


def test_slow_api_responses_histogram_alert():
    rules = load_blockchain_rules()
    expr = rules["SlowAPIResponses"]["expr"]
    buckets_slow = [
        ("1", 30),
        ("2", 70),
        ("3", 110),
        ("5", 150),
        ("7", 170),
        ("10", 190),
        ("+Inf", 200),
    ]
    triggered, threshold, _ = evaluate_histogram_expression(expr, buckets_slow)
    assert threshold == 5
    assert triggered
    buckets_fast = [
        ("1", 80),
        ("2", 140),
        ("3", 190),
        ("4", 210),
        ("5", 230),
        ("+Inf", 240),
    ]
    triggered, _, _ = evaluate_histogram_expression(expr, buckets_fast)
    assert not triggered


def test_high_memory_usage_threshold():
    rules = load_blockchain_rules()
    expr = rules["HighMemoryUsage"]["expr"]
    triggered, threshold = evaluate_gauge_expression(expr, 95)
    assert threshold == 90
    assert triggered
    triggered, _ = evaluate_gauge_expression(expr, 80)
    assert not triggered


def test_critical_disk_usage_threshold():
    rules = load_blockchain_rules()
    expr = rules["CriticalDiskUsage"]["expr"]
    triggered, threshold = evaluate_gauge_expression(expr, 97)
    assert threshold == 95
    assert triggered
    triggered, _ = evaluate_gauge_expression(expr, 90)
    assert not triggered


def test_high_api_error_rate_threshold():
    rules = load_blockchain_rules()
    expr = rules["HighAPIErrorRate"]["expr"]
    triggered, threshold, ratio = evaluate_ratio_expression(expr, [0, 10], [0, 100])
    assert threshold == 0.05
    assert pytest.approx(ratio, rel=1e-2) == 0.1
    assert triggered
    triggered, _, _ = evaluate_ratio_expression(expr, [0, 2], [0, 200])
    assert not triggered


def test_chain_not_synced_alert():
    rules = load_blockchain_rules()
    expr = rules["ChainNotSynced"]["expr"]
    triggered, target = evaluate_equality_expression(expr, 0)
    assert target == 0
    assert triggered
    triggered, _ = evaluate_equality_expression(expr, 1)
    assert not triggered
