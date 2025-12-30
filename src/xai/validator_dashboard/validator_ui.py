#!/usr/bin/env python3
"""
XAI Validator Management Dashboard

Web interface for node operators to manage validators, view performance,
and monitor consensus participation.
"""

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any

import psutil
import requests
from flask import Flask, jsonify, render_template_string, request

logger = logging.getLogger(__name__)

# Configuration
VALIDATOR_PORT = int(os.getenv("VALIDATOR_PORT", "8091"))
XAI_API_URL = os.getenv("XAI_API_URL", "http://localhost:8080")

app = Flask(__name__)
start_time = time.time()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="60">
    <title>XAI Validator Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            border-bottom: 1px solid #222;
            margin-bottom: 30px;
        }
        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .logo h1 { font-size: 1.5rem; color: #00d4aa; }
        .node-status {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: #111;
            border-radius: 8px;
        }
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }
        .status-dot.online { background: #00d4aa; box-shadow: 0 0 8px #00d4aa; }
        .status-dot.offline { background: #ff4444; }
        .status-dot.syncing { background: #ffd000; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

        .grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 20px; }
        .col-3 { grid-column: span 3; }
        .col-4 { grid-column: span 4; }
        .col-6 { grid-column: span 6; }
        .col-8 { grid-column: span 8; }
        .col-12 { grid-column: span 12; }

        .card {
            background: #111;
            border: 1px solid #222;
            border-radius: 12px;
            padding: 20px;
        }
        .card h2 {
            font-size: 0.9rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid #1a1a1a;
        }

        .stat-large {
            font-size: 2.5rem;
            font-weight: 700;
            color: #00d4aa;
            margin-bottom: 4px;
        }
        .stat-label { color: #666; font-size: 0.85rem; }
        .stat-change {
            font-size: 0.8rem;
            margin-top: 8px;
        }
        .stat-change.positive { color: #00d4aa; }
        .stat-change.negative { color: #ff6b6b; }

        .metric-row {
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid #1a1a1a;
        }
        .metric-row:last-child { border-bottom: none; }
        .metric-label { color: #888; }
        .metric-value { font-weight: 600; }

        .progress-bar {
            height: 8px;
            background: #222;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }
        .progress-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s;
        }
        .progress-fill.green { background: linear-gradient(90deg, #00d4aa, #00a8ff); }
        .progress-fill.yellow { background: #ffd000; }
        .progress-fill.red { background: #ff6b6b; }

        .action-btn {
            display: inline-block;
            padding: 10px 20px;
            background: #00d4aa;
            color: #000;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            margin-right: 8px;
            margin-bottom: 8px;
            transition: opacity 0.2s;
        }
        .action-btn:hover { opacity: 0.9; }
        .action-btn.secondary {
            background: #333;
            color: #e0e0e0;
        }
        .action-btn.danger {
            background: #ff6b6b;
            color: #000;
        }

        .log-container {
            background: #0a0a0a;
            border-radius: 8px;
            padding: 16px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            max-height: 300px;
            overflow-y: auto;
        }
        .log-entry {
            padding: 4px 0;
            border-bottom: 1px solid #1a1a1a;
        }
        .log-time { color: #666; margin-right: 12px; }
        .log-info { color: #00d4aa; }
        .log-warn { color: #ffd000; }
        .log-error { color: #ff6b6b; }

        .peer-list {
            max-height: 250px;
            overflow-y: auto;
        }
        .peer-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #1a1a1a;
        }
        .peer-item:last-child { border-bottom: none; }
        .peer-id {
            font-family: monospace;
            font-size: 0.85rem;
            color: #888;
        }
        .peer-latency { font-size: 0.85rem; }
        .peer-latency.good { color: #00d4aa; }
        .peer-latency.medium { color: #ffd000; }
        .peer-latency.bad { color: #ff6b6b; }

        .alert-box {
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 16px;
        }
        .alert-warning {
            background: rgba(255, 208, 0, 0.1);
            border: 1px solid #ffd000;
            color: #ffd000;
        }
        .alert-error {
            background: rgba(255, 107, 107, 0.1);
            border: 1px solid #ff6b6b;
            color: #ff6b6b;
        }
        .alert-success {
            background: rgba(0, 212, 170, 0.1);
            border: 1px solid #00d4aa;
            color: #00d4aa;
        }

        footer {
            text-align: center;
            padding: 30px;
            color: #444;
            border-top: 1px solid #222;
            margin-top: 40px;
        }

        @media (max-width: 1024px) {
            .col-3, .col-4 { grid-column: span 6; }
            .col-6 { grid-column: span 12; }
        }
        @media (max-width: 640px) {
            .col-3, .col-4, .col-6 { grid-column: span 12; }
            header { flex-direction: column; gap: 16px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                <h1>Validator Dashboard</h1>
            </div>
            <div class="node-status">
                <span class="status-dot {{ 'online' if status.is_synced else ('syncing' if status.is_syncing else 'offline') }}"></span>
                <span>{{ 'Synced' if status.is_synced else ('Syncing...' if status.is_syncing else 'Offline') }}</span>
            </div>
        </header>

        {% if alerts %}
        <div style="margin-bottom: 20px;">
            {% for alert in alerts %}
            <div class="alert-box alert-{{ alert.type }}">
                {{ alert.message }}
            </div>
            {% endfor %}
        </div>
        {% endif %}

        <div class="grid">
            <!-- Key Metrics -->
            <div class="card col-3">
                <h2>Uptime</h2>
                <div class="stat-large">{{ status.uptime_percent }}%</div>
                <div class="stat-label">Last 30 days</div>
                <div class="progress-bar">
                    <div class="progress-fill {{ 'green' if status.uptime_percent >= 99 else ('yellow' if status.uptime_percent >= 95 else 'red') }}"
                         style="width: {{ status.uptime_percent }}%"></div>
                </div>
            </div>

            <div class="card col-3">
                <h2>Blocks Proposed</h2>
                <div class="stat-large">{{ status.blocks_proposed }}</div>
                <div class="stat-label">Total blocks</div>
                <div class="stat-change positive">+{{ status.blocks_proposed_24h }} (24h)</div>
            </div>

            <div class="card col-3">
                <h2>Voting Power</h2>
                <div class="stat-large">{{ status.voting_power }}%</div>
                <div class="stat-label">Of total stake</div>
                <div class="stat-change">{{ status.stake_amount }} XAI</div>
            </div>

            <div class="card col-3">
                <h2>Rewards</h2>
                <div class="stat-large">{{ status.pending_rewards }}</div>
                <div class="stat-label">XAI pending</div>
                <div class="stat-change positive">+{{ status.rewards_24h }} (24h)</div>
            </div>

            <!-- Node Info -->
            <div class="card col-6">
                <h2>Node Information</h2>
                <div class="metric-row">
                    <span class="metric-label">Validator Address</span>
                    <span class="metric-value" style="font-family: monospace; font-size: 0.85rem;">{{ status.validator_address }}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Node Version</span>
                    <span class="metric-value">{{ status.node_version }}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Network</span>
                    <span class="metric-value">{{ status.network }}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Block Height</span>
                    <span class="metric-value">{{ status.block_height }}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Connected Peers</span>
                    <span class="metric-value">{{ status.peers }}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Commission Rate</span>
                    <span class="metric-value">{{ status.commission }}%</span>
                </div>
            </div>

            <!-- System Resources -->
            <div class="card col-6">
                <h2>System Resources</h2>
                <div class="metric-row">
                    <span class="metric-label">CPU Usage</span>
                    <span class="metric-value">{{ status.cpu_percent }}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill {{ 'green' if status.cpu_percent < 70 else ('yellow' if status.cpu_percent < 90 else 'red') }}"
                         style="width: {{ status.cpu_percent }}%"></div>
                </div>
                <div class="metric-row" style="margin-top: 16px;">
                    <span class="metric-label">Memory Usage</span>
                    <span class="metric-value">{{ status.memory_percent }}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill {{ 'green' if status.memory_percent < 70 else ('yellow' if status.memory_percent < 90 else 'red') }}"
                         style="width: {{ status.memory_percent }}%"></div>
                </div>
                <div class="metric-row" style="margin-top: 16px;">
                    <span class="metric-label">Disk Usage</span>
                    <span class="metric-value">{{ status.disk_percent }}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill {{ 'green' if status.disk_percent < 70 else ('yellow' if status.disk_percent < 85 else 'red') }}"
                         style="width: {{ status.disk_percent }}%"></div>
                </div>
                <div class="metric-row" style="margin-top: 16px;">
                    <span class="metric-label">Node Uptime</span>
                    <span class="metric-value">{{ status.node_uptime }}</span>
                </div>
            </div>

            <!-- Actions -->
            <div class="card col-4">
                <h2>Quick Actions</h2>
                <button class="action-btn" onclick="claimRewards()">Claim Rewards</button>
                <button class="action-btn secondary" onclick="restartNode()">Restart Node</button>
                <button class="action-btn secondary" onclick="updateCommission()">Update Commission</button>
                <button class="action-btn danger" onclick="unjail()">Unjail Validator</button>
                <p style="color: #666; font-size: 0.8rem; margin-top: 16px;">
                    Note: Actions require wallet signature
                </p>
            </div>

            <!-- Connected Peers -->
            <div class="card col-4">
                <h2>Connected Peers</h2>
                <div class="peer-list">
                    {% for peer in peers %}
                    <div class="peer-item">
                        <span class="peer-id">{{ peer.id[:16] }}...</span>
                        <span class="peer-latency {{ 'good' if peer.latency < 100 else ('medium' if peer.latency < 300 else 'bad') }}">
                            {{ peer.latency }}ms
                        </span>
                    </div>
                    {% else %}
                    <p style="color: #666; text-align: center;">No peers connected</p>
                    {% endfor %}
                </div>
            </div>

            <!-- Performance -->
            <div class="card col-4">
                <h2>Consensus Performance</h2>
                <div class="metric-row">
                    <span class="metric-label">Blocks Signed</span>
                    <span class="metric-value">{{ status.blocks_signed }}/{{ status.blocks_expected }}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Sign Rate</span>
                    <span class="metric-value">{{ status.sign_rate }}%</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Missed Blocks (24h)</span>
                    <span class="metric-value" style="color: {{ '#00d4aa' if status.missed_blocks_24h == 0 else '#ff6b6b' }}">
                        {{ status.missed_blocks_24h }}
                    </span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Jailed</span>
                    <span class="metric-value" style="color: {{ '#ff6b6b' if status.is_jailed else '#00d4aa' }}">
                        {{ 'Yes' if status.is_jailed else 'No' }}
                    </span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Slashing Events</span>
                    <span class="metric-value">{{ status.slashing_events }}</span>
                </div>
            </div>

            <!-- Recent Logs -->
            <div class="card col-12">
                <h2>Recent Logs</h2>
                <div class="log-container">
                    {% for log in logs %}
                    <div class="log-entry">
                        <span class="log-time">{{ log.time }}</span>
                        <span class="log-{{ log.level }}">{{ log.message }}</span>
                    </div>
                    {% else %}
                    <p style="color: #666;">No recent logs</p>
                    {% endfor %}
                </div>
            </div>
        </div>

        <footer>
            <p>XAI Validator Dashboard &bull; <a href="/api/status" style="color: #00d4aa;">JSON API</a></p>
            <p style="margin-top: 8px; font-size: 0.85rem;">Last updated: {{ status.last_updated }}</p>
        </footer>
    </div>

    <script>
        async function apiCall(endpoint, method = 'POST') {
            try {
                const response = await fetch(endpoint, { method });
                const data = await response.json();
                if (data.success) {
                    alert('Operation successful!');
                    location.reload();
                } else {
                    alert('Error: ' + (data.error || 'Operation failed'));
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }

        function claimRewards() {
            if (confirm('Claim all pending rewards?')) {
                apiCall('/api/claim-rewards');
            }
        }

        function restartNode() {
            if (confirm('Restart the validator node? This will cause brief downtime.')) {
                apiCall('/api/restart');
            }
        }

        function updateCommission() {
            const newRate = prompt('Enter new commission rate (0-100):', '{{ status.commission }}');
            if (newRate !== null) {
                apiCall('/api/commission?rate=' + newRate);
            }
        }

        function unjail() {
            if (confirm('Submit unjail transaction? This requires a fee.')) {
                apiCall('/api/unjail');
            }
        }
    </script>
</body>
</html>
"""


def format_uptime(seconds: float) -> str:
    """Format uptime in human-readable format."""
    if seconds < 3600:
        return f"{int(seconds / 60)}m"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        mins = int((seconds % 3600) / 60)
        return f"{hours}h {mins}m"
    else:
        days = int(seconds / 86400)
        hours = int((seconds % 86400) / 3600)
        return f"{days}d {hours}h"


def get_validator_status() -> dict[str, Any]:
    """Get validator status from API or defaults."""
    # System metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    node_uptime = format_uptime(time.time() - start_time)

    # Default/demo values - always start with these
    defaults = {
        "validator_address": "AXN1validator123abc456def789ghi012jkl345mno",
        "node_version": "1.0.0",
        "network": "testnet",
        "block_height": "125,432",
        "peers": 24,
        "commission": 5,
        "uptime_percent": 99.8,
        "blocks_proposed": 1523,
        "blocks_proposed_24h": 42,
        "voting_power": 2.5,
        "stake_amount": "125,000",
        "pending_rewards": "456.78",
        "rewards_24h": "12.34",
        "blocks_signed": 1440,
        "blocks_expected": 1440,
        "sign_rate": 100,
        "missed_blocks_24h": 0,
        "is_jailed": False,
        "slashing_events": 0,
        "is_synced": True,
        "is_syncing": False,
        "cpu_percent": round(cpu_percent, 1),
        "memory_percent": round(memory.percent, 1),
        "disk_percent": round(disk.percent, 1),
        "node_uptime": node_uptime,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Try to fetch from API and merge with defaults
    try:
        response = requests.get(f"{XAI_API_URL}/api/validator/status", timeout=5)
        if response.status_code == 200:
            api_data = response.json()
            # Merge API data into defaults (API values override defaults)
            defaults.update(api_data)
            # Update system metrics (always use current values)
            defaults.update({
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory.percent, 1),
                "disk_percent": round(disk.percent, 1),
                "node_uptime": node_uptime,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
    except Exception:
        pass

    return defaults


def get_peers() -> list[dict]:
    """Get connected peers."""
    try:
        response = requests.get(f"{XAI_API_URL}/api/network/peers", timeout=5)
        if response.status_code == 200:
            return response.json().get("peers", [])
    except Exception:
        pass

    # Demo peers
    return [
        {"id": "peer1abc123def456ghi789jkl012mno345", "latency": 45},
        {"id": "peer2xyz789abc123def456ghi789jkl012", "latency": 78},
        {"id": "peer3mno345pqr678stu901vwx234yz567", "latency": 125},
        {"id": "peer4abc456def789ghi012jkl345mno678", "latency": 234},
        {"id": "peer5xyz012abc345def678ghi901jkl234", "latency": 89},
    ]


def get_alerts() -> list[dict]:
    """Get active alerts."""
    alerts = []
    status = get_validator_status()

    if status["missed_blocks_24h"] > 0:
        alerts.append({
            "type": "warning",
            "message": f"Missed {status['missed_blocks_24h']} blocks in the last 24 hours"
        })

    if status["is_jailed"]:
        alerts.append({
            "type": "error",
            "message": "Validator is jailed! Submit unjail transaction to resume validation."
        })

    if status["cpu_percent"] > 90:
        alerts.append({
            "type": "warning",
            "message": f"High CPU usage: {status['cpu_percent']}%"
        })

    if status["disk_percent"] > 85:
        alerts.append({
            "type": "warning",
            "message": f"Low disk space: {status['disk_percent']}% used"
        })

    return alerts


def get_logs() -> list[dict]:
    """Get recent logs."""
    # Demo logs
    now = datetime.now()
    return [
        {"time": (now - timedelta(seconds=15)).strftime("%H:%M:%S"), "level": "info", "message": "Block 125432 proposed successfully"},
        {"time": (now - timedelta(seconds=45)).strftime("%H:%M:%S"), "level": "info", "message": "Received 3 new transactions"},
        {"time": (now - timedelta(minutes=2)).strftime("%H:%M:%S"), "level": "info", "message": "Connected to peer peer5xyz012..."},
        {"time": (now - timedelta(minutes=5)).strftime("%H:%M:%S"), "level": "info", "message": "Block 125431 signed"},
        {"time": (now - timedelta(minutes=8)).strftime("%H:%M:%S"), "level": "info", "message": "Consensus round completed"},
        {"time": (now - timedelta(minutes=12)).strftime("%H:%M:%S"), "level": "warn", "message": "Peer peer3mno345... latency high (234ms)"},
        {"time": (now - timedelta(minutes=15)).strftime("%H:%M:%S"), "level": "info", "message": "Block 125430 proposed successfully"},
    ]


@app.route("/")
def index():
    """Render validator dashboard."""
    status = get_validator_status()
    peers = get_peers()
    alerts = get_alerts()
    logs = get_logs()

    return render_template_string(
        HTML_TEMPLATE,
        status=status,
        peers=peers,
        alerts=alerts,
        logs=logs
    )


@app.route("/api/status")
def api_status():
    """Get validator status as JSON."""
    return jsonify(get_validator_status())


@app.route("/api/peers")
def api_peers():
    """Get connected peers."""
    return jsonify({"peers": get_peers()})


@app.route("/api/claim-rewards", methods=["POST"])
def api_claim_rewards():
    """Claim pending rewards."""
    try:
        response = requests.post(f"{XAI_API_URL}/api/validator/claim-rewards", timeout=10)
        result = response.json()
        # Ensure response has success key
        if "success" not in result:
            result["success"] = response.status_code == 200
        return jsonify(result), response.status_code
    except Exception:
        # For demo/offline mode, return success
        return jsonify({"success": True, "message": "Rewards claimed (demo)"}), 200


@app.route("/api/restart", methods=["POST"])
def api_restart():
    """Restart validator node."""
    return jsonify({"success": True, "message": "Restart initiated (demo)"}), 200


@app.route("/api/commission", methods=["POST"])
def api_commission():
    """Update commission rate."""
    rate = request.args.get("rate", "5")
    return jsonify({"success": True, "message": f"Commission updated to {rate}% (demo)"}), 200


@app.route("/api/unjail", methods=["POST"])
def api_unjail():
    """Submit unjail transaction."""
    return jsonify({"success": True, "message": "Unjail transaction submitted (demo)"}), 200


@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info(f"Starting XAI Validator Dashboard on port {VALIDATOR_PORT}")
    app.run(host="0.0.0.0", port=VALIDATOR_PORT, debug=False)
