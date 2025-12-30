#!/usr/bin/env python3
"""
XAI Block Reward Estimator

A mining profitability calculator for the XAI blockchain.
Estimates block rewards, mining income, and halving schedules.
"""

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any

import requests
from flask import Flask, jsonify, render_template_string, request

logger = logging.getLogger(__name__)

# Configuration
ESTIMATOR_PORT = int(os.getenv("ESTIMATOR_PORT", "8088"))
XAI_API_URL = os.getenv("XAI_API_URL", "http://localhost:8080")

# XAI Economics
INITIAL_BLOCK_REWARD = 50.0  # XAI per block
HALVING_INTERVAL = 210000  # blocks
TARGET_BLOCK_TIME = 60  # seconds (1 minute)
MAX_SUPPLY = 21_000_000  # Maximum supply

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XAI Block Reward Estimator</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
            color: #e0e0e0;
            min-height: 100vh;
        }
        .container { max-width: 900px; margin: 0 auto; padding: 20px; }
        header {
            text-align: center;
            padding: 40px 0;
        }
        h1 {
            font-size: 2.2rem;
            background: linear-gradient(90deg, #00d4aa, #00a8ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        .subtitle { color: #888; margin-bottom: 30px; }

        .card {
            background: rgba(17, 17, 17, 0.9);
            border: 1px solid #222;
            border-radius: 16px;
            padding: 28px;
            margin-bottom: 24px;
        }
        .card h2 {
            font-size: 1.1rem;
            color: #00d4aa;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #222;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        .stat {
            background: #0a0a0a;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }
        .stat-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #00d4aa;
            margin-bottom: 8px;
        }
        .stat-label { color: #888; font-size: 0.9rem; }

        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            color: #888;
            margin-bottom: 8px;
            font-size: 0.9rem;
        }
        input, select {
            width: 100%;
            padding: 12px 16px;
            background: #0a0a0a;
            border: 1px solid #333;
            border-radius: 8px;
            color: #e0e0e0;
            font-size: 1rem;
        }
        input:focus, select:focus {
            outline: none;
            border-color: #00d4aa;
        }
        .input-group {
            display: flex;
            gap: 12px;
        }
        .input-group > div { flex: 1; }

        button {
            background: linear-gradient(90deg, #00d4aa, #00a8ff);
            color: #000;
            border: none;
            padding: 14px 28px;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0, 212, 170, 0.3);
        }

        .results {
            display: none;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #222;
        }
        .results.show { display: block; }
        .result-row {
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid #1a1a1a;
        }
        .result-row:last-child { border-bottom: none; }
        .result-label { color: #888; }
        .result-value { font-weight: 600; color: #00d4aa; }

        .halving-timeline {
            margin-top: 20px;
        }
        .halving-event {
            display: flex;
            align-items: center;
            padding: 16px 0;
            border-bottom: 1px solid #1a1a1a;
        }
        .halving-event:last-child { border-bottom: none; }
        .halving-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 16px;
        }
        .halving-dot.past { background: #333; }
        .halving-dot.current { background: #00d4aa; box-shadow: 0 0 10px #00d4aa; }
        .halving-dot.future { background: #444; }
        .halving-info { flex: 1; }
        .halving-title { font-weight: 600; margin-bottom: 4px; }
        .halving-details { color: #666; font-size: 0.9rem; }
        .halving-reward { color: #00d4aa; font-weight: 600; }

        footer {
            text-align: center;
            padding: 30px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Block Reward Estimator</h1>
            <p class="subtitle">Calculate your XAI mining profitability</p>
        </header>

        <div class="card">
            <h2>Current Network Stats</h2>
            <div class="stats-grid">
                <div class="stat">
                    <div class="stat-value">{{ stats.block_height }}</div>
                    <div class="stat-label">Block Height</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{{ stats.current_reward }} XAI</div>
                    <div class="stat-label">Block Reward</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{{ stats.blocks_to_halving }}</div>
                    <div class="stat-label">Blocks to Halving</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{{ stats.days_to_halving }}d</div>
                    <div class="stat-label">Days to Halving</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Mining Calculator</h2>
            <form id="calcForm">
                <div class="input-group">
                    <div class="form-group">
                        <label>Your Hashrate</label>
                        <input type="number" id="hashrate" value="1000" min="1" step="1">
                    </div>
                    <div class="form-group">
                        <label>Unit</label>
                        <select id="hashrateUnit">
                            <option value="1">H/s</option>
                            <option value="1000" selected>KH/s</option>
                            <option value="1000000">MH/s</option>
                            <option value="1000000000">GH/s</option>
                        </select>
                    </div>
                </div>
                <div class="input-group">
                    <div class="form-group">
                        <label>Network Hashrate (MH/s)</label>
                        <input type="number" id="networkHashrate" value="{{ stats.network_hashrate }}" min="1">
                    </div>
                    <div class="form-group">
                        <label>Electricity Cost ($/kWh)</label>
                        <input type="number" id="electricityCost" value="0.10" min="0" step="0.01">
                    </div>
                </div>
                <div class="form-group">
                    <label>Power Consumption (Watts)</label>
                    <input type="number" id="powerConsumption" value="500" min="0">
                </div>
                <button type="submit">Calculate Earnings</button>
            </form>

            <div class="results" id="results">
                <div class="result-row">
                    <span class="result-label">Daily Blocks (Est.)</span>
                    <span class="result-value" id="dailyBlocks">--</span>
                </div>
                <div class="result-row">
                    <span class="result-label">Daily XAI</span>
                    <span class="result-value" id="dailyXai">--</span>
                </div>
                <div class="result-row">
                    <span class="result-label">Weekly XAI</span>
                    <span class="result-value" id="weeklyXai">--</span>
                </div>
                <div class="result-row">
                    <span class="result-label">Monthly XAI</span>
                    <span class="result-value" id="monthlyXai">--</span>
                </div>
                <div class="result-row">
                    <span class="result-label">Daily Power Cost</span>
                    <span class="result-value" id="dailyPowerCost">--</span>
                </div>
                <div class="result-row">
                    <span class="result-label">Hash Share</span>
                    <span class="result-value" id="hashShare">--</span>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Halving Schedule</h2>
            <div class="halving-timeline">
                {% for event in halvings %}
                <div class="halving-event">
                    <span class="halving-dot {{ event.status }}"></span>
                    <div class="halving-info">
                        <div class="halving-title">{{ event.name }}</div>
                        <div class="halving-details">Block {{ event.block }} &bull; {{ event.date }}</div>
                    </div>
                    <div class="halving-reward">{{ event.reward }} XAI</div>
                </div>
                {% endfor %}
            </div>
        </div>

        <footer>
            <p>XAI Block Reward Estimator &bull; <a href="/api/stats" style="color: #00d4aa;">JSON API</a></p>
        </footer>
    </div>

    <script>
        document.getElementById('calcForm').addEventListener('submit', function(e) {
            e.preventDefault();

            const hashrate = parseFloat(document.getElementById('hashrate').value);
            const unit = parseFloat(document.getElementById('hashrateUnit').value);
            const networkHashrate = parseFloat(document.getElementById('networkHashrate').value) * 1000000;
            const electricityCost = parseFloat(document.getElementById('electricityCost').value);
            const powerConsumption = parseFloat(document.getElementById('powerConsumption').value);

            const userHashrate = hashrate * unit;
            const hashShare = userHashrate / networkHashrate;
            const blockReward = {{ stats.current_reward }};
            const blocksPerDay = 86400 / {{ stats.block_time }};

            const dailyBlocks = blocksPerDay * hashShare;
            const dailyXai = dailyBlocks * blockReward;
            const weeklyXai = dailyXai * 7;
            const monthlyXai = dailyXai * 30;
            const dailyPowerCost = (powerConsumption / 1000) * 24 * electricityCost;

            document.getElementById('dailyBlocks').textContent = dailyBlocks.toFixed(4);
            document.getElementById('dailyXai').textContent = dailyXai.toFixed(4) + ' XAI';
            document.getElementById('weeklyXai').textContent = weeklyXai.toFixed(4) + ' XAI';
            document.getElementById('monthlyXai').textContent = monthlyXai.toFixed(4) + ' XAI';
            document.getElementById('dailyPowerCost').textContent = '$' + dailyPowerCost.toFixed(2);
            document.getElementById('hashShare').textContent = (hashShare * 100).toFixed(6) + '%';

            document.getElementById('results').classList.add('show');
        });
    </script>
</body>
</html>
"""


def calculate_block_reward(block_height: int) -> float:
    """Calculate block reward at given height."""
    halvings = block_height // HALVING_INTERVAL
    reward = INITIAL_BLOCK_REWARD / (2 ** halvings)
    return max(reward, 0.00000001)


def get_halving_schedule(current_height: int) -> list[dict]:
    """Generate halving schedule."""
    halvings = []
    for i in range(10):  # First 10 halvings
        halving_block = i * HALVING_INTERVAL
        reward = INITIAL_BLOCK_REWARD / (2 ** i)

        if halving_block < current_height:
            status = "past"
        elif halving_block <= current_height + HALVING_INTERVAL:
            status = "current"
        else:
            status = "future"

        # Estimate date
        blocks_from_now = halving_block - current_height
        seconds_from_now = blocks_from_now * TARGET_BLOCK_TIME
        est_date = datetime.now() + timedelta(seconds=seconds_from_now)

        if halving_block == 0:
            name = "Genesis"
            date_str = "Network Launch"
        else:
            name = f"Halving #{i}"
            if status == "past":
                date_str = "Completed"
            else:
                date_str = est_date.strftime("%b %Y")

        halvings.append({
            "name": name,
            "block": f"{halving_block:,}",
            "reward": f"{reward:.4f}",
            "date": date_str,
            "status": status,
        })

    return halvings


def get_network_stats() -> dict[str, Any]:
    """Get current network statistics."""
    # Try to fetch from API
    block_height = 0
    network_hashrate = 100  # Default MH/s

    try:
        response = requests.get(f"{XAI_API_URL}/api/v1/info", timeout=5)
        if response.status_code == 200:
            data = response.json()
            block_height = data.get("height", data.get("block_height", 0))
            network_hashrate = data.get("hashrate", 100)
    except Exception:
        pass

    current_reward = calculate_block_reward(block_height)
    next_halving_block = ((block_height // HALVING_INTERVAL) + 1) * HALVING_INTERVAL
    blocks_to_halving = next_halving_block - block_height
    days_to_halving = (blocks_to_halving * TARGET_BLOCK_TIME) // 86400

    return {
        "block_height": f"{block_height:,}",
        "current_reward": f"{current_reward:.4f}",
        "blocks_to_halving": f"{blocks_to_halving:,}",
        "days_to_halving": int(days_to_halving),
        "network_hashrate": network_hashrate,
        "block_time": TARGET_BLOCK_TIME,
        "halving_interval": HALVING_INTERVAL,
        "max_supply": MAX_SUPPLY,
    }


@app.route("/")
def index():
    """Render estimator page."""
    stats = get_network_stats()
    block_height = int(stats["block_height"].replace(",", ""))
    halvings = get_halving_schedule(block_height)
    return render_template_string(HTML_TEMPLATE, stats=stats, halvings=halvings)


@app.route("/api/stats")
def api_stats():
    """Return network stats as JSON."""
    return jsonify(get_network_stats())


@app.route("/api/reward/<int:block_height>")
def api_reward(block_height: int):
    """Get reward for specific block height."""
    return jsonify({
        "block_height": block_height,
        "reward": calculate_block_reward(block_height),
    })


@app.route("/api/halving-schedule")
def api_halving_schedule():
    """Return halving schedule as JSON."""
    stats = get_network_stats()
    block_height = int(stats["block_height"].replace(",", ""))
    return jsonify(get_halving_schedule(block_height))


@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    """Calculate mining profitability."""
    data = request.get_json()

    hashrate = float(data.get("hashrate", 1000000))  # H/s
    network_hashrate = float(data.get("network_hashrate", 100000000))  # H/s
    electricity_cost = float(data.get("electricity_cost", 0.10))  # $/kWh
    power_consumption = float(data.get("power_consumption", 500))  # Watts

    stats = get_network_stats()
    block_reward = float(stats["current_reward"])

    hash_share = hashrate / network_hashrate
    blocks_per_day = 86400 / TARGET_BLOCK_TIME
    daily_blocks = blocks_per_day * hash_share
    daily_xai = daily_blocks * block_reward
    daily_power_cost = (power_consumption / 1000) * 24 * electricity_cost

    return jsonify({
        "daily_blocks": round(daily_blocks, 6),
        "daily_xai": round(daily_xai, 6),
        "weekly_xai": round(daily_xai * 7, 6),
        "monthly_xai": round(daily_xai * 30, 6),
        "yearly_xai": round(daily_xai * 365, 6),
        "daily_power_cost": round(daily_power_cost, 2),
        "hash_share_percent": round(hash_share * 100, 8),
    })


@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info(f"Starting XAI Block Reward Estimator on port {ESTIMATOR_PORT}")
    app.run(host="0.0.0.0", port=ESTIMATOR_PORT, debug=False)
