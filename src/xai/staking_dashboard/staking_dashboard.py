#!/usr/bin/env python3
"""
XAI Staking Dashboard

Web-based dashboard for staking operations on the XAI blockchain.
Provides UI for staking, unstaking, validator management, and rewards claiming.
"""

import logging
import os
import time
from datetime import datetime
from decimal import Decimal
from typing import Any

import requests
from flask import Flask, Response, jsonify, render_template_string, request

logger = logging.getLogger(__name__)

# Configuration
STAKING_PORT = int(os.getenv("STAKING_PORT", "8089"))
XAI_API_URL = os.getenv("XAI_API_URL", "http://localhost:8080")
REQUEST_TIMEOUT = 10

app = Flask(__name__)

# Token decimals (XAI uses 18 decimals like ETH)
DECIMALS = 18
PRECISION = 10 ** DECIMALS


def format_token_amount(wei_amount: int) -> str:
    """Format wei amount to human-readable token amount."""
    if wei_amount == 0:
        return "0"
    amount = Decimal(wei_amount) / Decimal(PRECISION)
    if amount >= 1_000_000:
        return f"{amount / 1_000_000:,.2f}M"
    elif amount >= 1_000:
        return f"{amount / 1_000:,.2f}K"
    else:
        return f"{amount:,.4f}"


def format_percentage(basis_points: int) -> str:
    """Format basis points to percentage string."""
    return f"{basis_points / 100:.2f}%"


def format_duration(seconds: int) -> str:
    """Format duration in human-readable format."""
    if seconds < 3600:
        return f"{seconds // 60}m"
    elif seconds < 86400:
        return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h"


def format_timestamp(timestamp: float) -> str:
    """Format Unix timestamp to readable date."""
    if timestamp == 0:
        return "N/A"
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")


def api_get(endpoint: str) -> dict[str, Any]:
    """Make GET request to XAI API."""
    try:
        url = f"{XAI_API_URL}{endpoint}"
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
        logger.warning(f"API GET {endpoint} returned {response.status_code}")
    except requests.RequestException as e:
        logger.error(f"API GET {endpoint} failed: {e}")
    return {}


def api_post(endpoint: str, data: dict) -> dict[str, Any]:
    """Make POST request to XAI API."""
    try:
        url = f"{XAI_API_URL}{endpoint}"
        response = requests.post(url, json=data, timeout=REQUEST_TIMEOUT)
        return {"status_code": response.status_code, "data": response.json()}
    except requests.RequestException as e:
        logger.error(f"API POST {endpoint} failed: {e}")
        return {"status_code": 500, "data": {"error": str(e)}}


# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XAI Staking Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }

        :root {
            --accent: #00d4aa;
            --accent-hover: #00f0c0;
            --accent-dim: rgba(0, 212, 170, 0.1);
            --bg-primary: #0a0a0a;
            --bg-secondary: #111111;
            --bg-card: #151515;
            --border: #222222;
            --text-primary: #e0e0e0;
            --text-secondary: #888888;
            --text-muted: #555555;
            --success: #00d4aa;
            --warning: #ffd000;
            --error: #ff4444;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
        }

        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }

        /* Header */
        header {
            text-align: center;
            padding: 40px 20px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 30px;
        }
        h1 {
            font-size: 2.5rem;
            color: var(--accent);
            margin-bottom: 8px;
        }
        .subtitle { color: var(--text-secondary); }

        /* Navigation */
        nav {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 25px;
            flex-wrap: wrap;
        }
        nav a {
            color: var(--text-secondary);
            text-decoration: none;
            padding: 10px 20px;
            border-radius: 8px;
            border: 1px solid var(--border);
            transition: all 0.2s;
        }
        nav a:hover, nav a.active {
            color: var(--accent);
            border-color: var(--accent);
            background: var(--accent-dim);
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            text-align: center;
        }
        .stat-label {
            font-size: 0.85rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        .stat-value {
            font-size: 1.8rem;
            font-weight: 600;
            color: var(--accent);
        }
        .stat-subtext {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 5px;
        }

        /* Cards */
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
        }
        .card h2 {
            color: var(--accent);
            font-size: 1.2rem;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border);
        }

        /* Forms */
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            color: var(--text-secondary);
            margin-bottom: 8px;
            font-size: 0.9rem;
        }
        .form-group input, .form-group select {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--bg-secondary);
            color: var(--text-primary);
            font-size: 1rem;
        }
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: var(--accent);
        }

        /* Buttons */
        .btn {
            display: inline-block;
            padding: 12px 24px;
            border-radius: 8px;
            border: none;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
        }
        .btn-primary {
            background: var(--accent);
            color: var(--bg-primary);
        }
        .btn-primary:hover {
            background: var(--accent-hover);
        }
        .btn-secondary {
            background: transparent;
            color: var(--accent);
            border: 1px solid var(--accent);
        }
        .btn-secondary:hover {
            background: var(--accent-dim);
        }
        .btn-danger {
            background: var(--error);
            color: white;
        }
        .btn-full { width: 100%; }

        /* Tables */
        .table-wrapper { overflow-x: auto; }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 14px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }
        th {
            color: var(--text-secondary);
            font-weight: 500;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        tr:hover { background: var(--accent-dim); }

        /* Status badges */
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        .badge-active { background: rgba(0, 212, 170, 0.2); color: var(--success); }
        .badge-inactive { background: rgba(136, 136, 136, 0.2); color: var(--text-secondary); }
        .badge-jailed { background: rgba(255, 68, 68, 0.2); color: var(--error); }
        .badge-unbonding { background: rgba(255, 208, 0, 0.2); color: var(--warning); }

        /* Progress bar */
        .progress-bar {
            height: 8px;
            background: var(--border);
            border-radius: 4px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: var(--accent);
            border-radius: 4px;
        }

        /* Two column layout */
        .two-col {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }

        /* Alerts */
        .alert {
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .alert-info { background: var(--accent-dim); border: 1px solid var(--accent); }
        .alert-warning { background: rgba(255, 208, 0, 0.1); border: 1px solid var(--warning); }
        .alert-error { background: rgba(255, 68, 68, 0.1); border: 1px solid var(--error); }

        /* Validator card */
        .validator-item {
            display: flex;
            align-items: center;
            padding: 16px;
            border: 1px solid var(--border);
            border-radius: 8px;
            margin-bottom: 12px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .validator-item:hover {
            border-color: var(--accent);
            background: var(--accent-dim);
        }
        .validator-item.selected {
            border-color: var(--accent);
            background: var(--accent-dim);
        }
        .validator-info { flex: 1; }
        .validator-name { font-weight: 600; margin-bottom: 4px; }
        .validator-address { font-size: 0.8rem; color: var(--text-muted); font-family: monospace; }
        .validator-stats { text-align: right; }
        .validator-stake { font-weight: 600; color: var(--accent); }
        .validator-commission { font-size: 0.85rem; color: var(--text-secondary); }

        /* Transaction history */
        .tx-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px;
            border-bottom: 1px solid var(--border);
        }
        .tx-item:last-child { border-bottom: none; }
        .tx-type { font-weight: 600; }
        .tx-details { font-size: 0.85rem; color: var(--text-secondary); }
        .tx-amount { font-weight: 600; }
        .tx-amount.positive { color: var(--success); }
        .tx-amount.negative { color: var(--error); }

        /* Footer */
        footer {
            text-align: center;
            padding: 30px;
            color: var(--text-muted);
            border-top: 1px solid var(--border);
            margin-top: 40px;
        }
        footer a { color: var(--accent); text-decoration: none; }

        /* Section visibility */
        .section { display: none; }
        .section.active { display: block; }

        /* Responsive */
        @media (max-width: 768px) {
            h1 { font-size: 1.8rem; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .two-col { grid-template-columns: 1fr; }
            nav a { padding: 8px 14px; font-size: 0.9rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>XAI Staking</h1>
            <p class="subtitle">Stake your XAI tokens to earn rewards and secure the network</p>
            <nav>
                <a href="#" class="active" data-section="overview">Overview</a>
                <a href="#" data-section="stake">Stake</a>
                <a href="#" data-section="unstake">Unstake</a>
                <a href="#" data-section="validators">Validators</a>
                <a href="#" data-section="rewards">Rewards</a>
                <a href="#" data-section="history">History</a>
            </nav>
        </header>

        <!-- Overview Section -->
        <section id="overview" class="section active">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Total Staked</div>
                    <div class="stat-value">{{ stats.total_staked_formatted }}</div>
                    <div class="stat-subtext">XAI</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Annual Yield (APY)</div>
                    <div class="stat-value">{{ stats.apy }}</div>
                    <div class="stat-subtext">Base reward rate</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Active Validators</div>
                    <div class="stat-value">{{ stats.active_validators }}</div>
                    <div class="stat-subtext">of {{ stats.total_validators }} total</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Your Stake</div>
                    <div class="stat-value">{{ user.total_staked_formatted }}</div>
                    <div class="stat-subtext">XAI</div>
                </div>
            </div>

            <div class="two-col">
                <div class="card">
                    <h2>Network Stats</h2>
                    <table>
                        <tr>
                            <td>Total Rewards Distributed</td>
                            <td style="text-align: right; color: var(--accent);">{{ stats.total_rewards_formatted }} XAI</td>
                        </tr>
                        <tr>
                            <td>Unbonding Period</td>
                            <td style="text-align: right;">{{ stats.unbonding_period_formatted }}</td>
                        </tr>
                        <tr>
                            <td>Minimum Delegation</td>
                            <td style="text-align: right;">100 XAI</td>
                        </tr>
                        <tr>
                            <td>Network Status</td>
                            <td style="text-align: right;"><span class="badge badge-active">Active</span></td>
                        </tr>
                    </table>
                </div>

                <div class="card">
                    <h2>Your Staking Summary</h2>
                    <table>
                        <tr>
                            <td>Staked Amount</td>
                            <td style="text-align: right; color: var(--accent);">{{ user.total_staked_formatted }} XAI</td>
                        </tr>
                        <tr>
                            <td>Pending Rewards</td>
                            <td style="text-align: right; color: var(--success);">{{ user.pending_rewards_formatted }} XAI</td>
                        </tr>
                        <tr>
                            <td>Unbonding Amount</td>
                            <td style="text-align: right; color: var(--warning);">{{ user.unbonding_formatted }} XAI</td>
                        </tr>
                        <tr>
                            <td>Validators Delegated</td>
                            <td style="text-align: right;">{{ user.delegations_count }}</td>
                        </tr>
                    </table>
                </div>
            </div>
        </section>

        <!-- Stake Section -->
        <section id="stake" class="section">
            <div class="two-col">
                <div class="card">
                    <h2>Stake XAI Tokens</h2>
                    <form id="stakeForm">
                        <div class="form-group">
                            <label for="stakeAmount">Amount to Stake (XAI)</label>
                            <input type="number" id="stakeAmount" name="amount" placeholder="Enter amount" min="100" step="0.0001" required>
                        </div>
                        <div class="form-group">
                            <label for="stakeValidator">Select Validator</label>
                            <select id="stakeValidator" name="validator" required>
                                <option value="">-- Select a validator --</option>
                                {% for v in validators %}
                                <option value="{{ v.address }}">{{ v.name }} ({{ v.commission_pct }} commission)</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="alert alert-info">
                            <strong>Note:</strong> Minimum stake is 100 XAI. Staked tokens will be locked and subject to the 21-day unbonding period when unstaking.
                        </div>
                        <button type="submit" class="btn btn-primary btn-full">Stake XAI</button>
                    </form>
                </div>

                <div class="card">
                    <h2>Top Validators</h2>
                    {% for v in validators[:5] %}
                    <div class="validator-item" onclick="selectValidator('{{ v.address }}')">
                        <div class="validator-info">
                            <div class="validator-name">{{ v.name }}</div>
                            <div class="validator-address">{{ v.address[:10] }}...{{ v.address[-8:] }}</div>
                        </div>
                        <div class="validator-stats">
                            <div class="validator-stake">{{ v.total_stake_formatted }} XAI</div>
                            <div class="validator-commission">{{ v.commission_pct }} commission</div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </section>

        <!-- Unstake Section -->
        <section id="unstake" class="section">
            <div class="two-col">
                <div class="card">
                    <h2>Unstake XAI Tokens</h2>
                    <form id="unstakeForm">
                        <div class="form-group">
                            <label for="unstakeValidator">Select Delegation</label>
                            <select id="unstakeValidator" name="validator" required>
                                <option value="">-- Select a delegation --</option>
                                {% for d in user.delegations %}
                                <option value="{{ d.validator }}">{{ d.validator_name }}: {{ d.amount_formatted }} XAI</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="unstakeAmount">Amount to Unstake (XAI)</label>
                            <input type="number" id="unstakeAmount" name="amount" placeholder="Enter amount" min="0" step="0.0001" required>
                        </div>
                        <div class="alert alert-warning">
                            <strong>Unbonding Period:</strong> {{ stats.unbonding_period_formatted }}. Your tokens will not be available until the unbonding period completes.
                        </div>
                        <button type="submit" class="btn btn-danger btn-full">Unstake XAI</button>
                    </form>
                </div>

                <div class="card">
                    <h2>Active Unbondings</h2>
                    {% if user.unbondings %}
                    {% for u in user.unbondings %}
                    <div class="tx-item">
                        <div>
                            <div class="tx-type">{{ u.validator_name }}</div>
                            <div class="tx-details">Completes: {{ u.completion_formatted }}</div>
                        </div>
                        <div class="tx-amount">{{ u.amount_formatted }} XAI</div>
                    </div>
                    {% endfor %}
                    {% else %}
                    <p style="color: var(--text-muted); text-align: center; padding: 40px;">No active unbondings</p>
                    {% endif %}
                </div>
            </div>
        </section>

        <!-- Validators Section -->
        <section id="validators" class="section">
            <div class="card">
                <h2>All Validators ({{ validators|length }})</h2>
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th>Validator</th>
                                <th>Status</th>
                                <th>Total Stake</th>
                                <th>Commission</th>
                                <th>Voting Power</th>
                                <th>Uptime</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for v in validators %}
                            <tr>
                                <td>
                                    <div class="validator-name">{{ v.name }}</div>
                                    <div style="font-size: 0.75rem; color: var(--text-muted); font-family: monospace;">{{ v.address[:16] }}...</div>
                                </td>
                                <td>
                                    <span class="badge badge-{{ v.status }}">{{ v.status }}</span>
                                </td>
                                <td>{{ v.total_stake_formatted }} XAI</td>
                                <td>{{ v.commission_pct }}</td>
                                <td>
                                    <div class="progress-bar" style="width: 100px;">
                                        <div class="progress-fill" style="width: {{ v.voting_power_pct }}%;"></div>
                                    </div>
                                    <span style="font-size: 0.75rem; color: var(--text-muted);">{{ v.voting_power_pct }}%</span>
                                </td>
                                <td>{{ v.uptime }}</td>
                                <td>
                                    {% if v.status == 'active' %}
                                    <a href="#stake" class="btn btn-secondary" style="padding: 6px 12px; font-size: 0.8rem;" onclick="selectValidator('{{ v.address }}'); showSection('stake');">Delegate</a>
                                    {% else %}
                                    <span style="color: var(--text-muted);">--</span>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- Rewards Section -->
        <section id="rewards" class="section">
            <div class="stats-grid" style="margin-bottom: 30px;">
                <div class="stat-card">
                    <div class="stat-label">Total Pending Rewards</div>
                    <div class="stat-value">{{ user.pending_rewards_formatted }}</div>
                    <div class="stat-subtext">XAI</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Estimated Daily</div>
                    <div class="stat-value">{{ user.estimated_daily }}</div>
                    <div class="stat-subtext">XAI / day</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Estimated Yearly</div>
                    <div class="stat-value">{{ user.estimated_yearly }}</div>
                    <div class="stat-subtext">XAI / year</div>
                </div>
            </div>

            <div class="two-col">
                <div class="card">
                    <h2>Pending Rewards by Validator</h2>
                    {% if user.rewards_by_validator %}
                    {% for r in user.rewards_by_validator %}
                    <div class="tx-item">
                        <div>
                            <div class="tx-type">{{ r.validator_name }}</div>
                            <div class="tx-details">{{ r.validator[:16] }}...</div>
                        </div>
                        <div class="tx-amount positive">{{ r.amount_formatted }} XAI</div>
                    </div>
                    {% endfor %}
                    {% else %}
                    <p style="color: var(--text-muted); text-align: center; padding: 40px;">No pending rewards</p>
                    {% endif %}
                </div>

                <div class="card">
                    <h2>Claim Rewards</h2>
                    <form id="claimForm">
                        <div class="form-group">
                            <label for="claimValidator">Select Validator (or All)</label>
                            <select id="claimValidator" name="validator">
                                <option value="all">Claim All Rewards</option>
                                {% for r in user.rewards_by_validator %}
                                <option value="{{ r.validator }}">{{ r.validator_name }}: {{ r.amount_formatted }} XAI</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="alert alert-info">
                            Claimed rewards will be sent to your wallet address.
                        </div>
                        <button type="submit" class="btn btn-primary btn-full">Claim Rewards</button>
                    </form>
                </div>
            </div>
        </section>

        <!-- History Section -->
        <section id="history" class="section">
            <div class="card">
                <h2>Staking Transaction History</h2>
                {% if history %}
                {% for tx in history %}
                <div class="tx-item">
                    <div>
                        <div class="tx-type">{{ tx.type }}</div>
                        <div class="tx-details">{{ tx.validator_name }} | {{ tx.timestamp_formatted }}</div>
                    </div>
                    <div class="tx-amount {{ tx.amount_class }}">{{ tx.amount_formatted }} XAI</div>
                </div>
                {% endfor %}
                {% else %}
                <p style="color: var(--text-muted); text-align: center; padding: 60px;">No staking transactions yet</p>
                {% endif %}
            </div>
        </section>

        <footer>
            <p>XAI Staking Dashboard | <a href="/api/staking/info">JSON API</a></p>
            <p style="margin-top: 8px; font-size: 0.85rem;">Last updated: {{ last_updated }}</p>
        </footer>
    </div>

    <script>
        // Section navigation
        document.querySelectorAll('nav a').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = e.target.dataset.section;
                showSection(section);
            });
        });

        function showSection(sectionId) {
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('nav a').forEach(a => a.classList.remove('active'));
            document.getElementById(sectionId).classList.add('active');
            document.querySelector(`nav a[data-section="${sectionId}"]`).classList.add('active');
        }

        function selectValidator(address) {
            document.getElementById('stakeValidator').value = address;
        }

        // Form submissions
        document.getElementById('stakeForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = {
                amount: parseFloat(formData.get('amount')) * 1e18,
                validator: formData.get('validator'),
                address: '{{ user.address }}'
            };

            try {
                const resp = await fetch('/api/staking/delegate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const result = await resp.json();
                if (result.success) {
                    alert('Stake successful! Transaction: ' + result.tx_hash);
                    location.reload();
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (err) {
                alert('Request failed: ' + err.message);
            }
        });

        document.getElementById('unstakeForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = {
                amount: parseFloat(formData.get('amount')) * 1e18,
                validator: formData.get('validator'),
                address: '{{ user.address }}'
            };

            try {
                const resp = await fetch('/api/staking/undelegate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const result = await resp.json();
                if (result.success) {
                    alert('Unstake initiated! Unbonding period: 21 days');
                    location.reload();
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (err) {
                alert('Request failed: ' + err.message);
            }
        });

        document.getElementById('claimForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const validator = formData.get('validator');
            const endpoint = validator === 'all' ? '/api/staking/claim-all' : '/api/staking/claim-rewards';
            const data = {
                validator: validator !== 'all' ? validator : undefined,
                address: '{{ user.address }}'
            };

            try {
                const resp = await fetch(endpoint, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const result = await resp.json();
                if (result.success) {
                    alert('Rewards claimed: ' + result.amount_formatted + ' XAI');
                    location.reload();
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (err) {
                alert('Request failed: ' + err.message);
            }
        });
    </script>
</body>
</html>
"""


def get_staking_stats() -> dict[str, Any]:
    """Fetch staking network statistics."""
    data = api_get("/api/staking/info")
    if not data:
        # Return default/mock data for display
        data = {
            "total_staked": 0,
            "total_validators": 0,
            "active_validators": 0,
            "total_rewards_distributed": 0,
            "reward_rate": 500,  # 5% APY
            "unbonding_period": 21 * 24 * 3600,
        }

    return {
        "total_staked": data.get("total_staked", 0),
        "total_staked_formatted": format_token_amount(data.get("total_staked", 0)),
        "total_validators": data.get("total_validators", 0),
        "active_validators": data.get("active_validators", 0),
        "total_rewards_distributed": data.get("total_rewards_distributed", 0),
        "total_rewards_formatted": format_token_amount(data.get("total_rewards_distributed", 0)),
        "apy": format_percentage(data.get("reward_rate", 500)),
        "unbonding_period": data.get("unbonding_period", 21 * 24 * 3600),
        "unbonding_period_formatted": format_duration(data.get("unbonding_period", 21 * 24 * 3600)),
    }


def get_validators() -> list[dict[str, Any]]:
    """Fetch list of validators."""
    data = api_get("/api/staking/validators")
    validators = data.get("validators", []) if data else []

    # Calculate total stake for voting power percentage
    total_stake = sum(v.get("total_stake", 0) for v in validators) or 1

    result = []
    for v in validators:
        total_v_stake = v.get("total_stake", 0)
        blocks_proposed = v.get("blocks_proposed", 0)
        blocks_missed = v.get("blocks_missed", 0)
        total_blocks = blocks_proposed + blocks_missed
        uptime = f"{(blocks_proposed / total_blocks * 100):.1f}%" if total_blocks > 0 else "100%"

        result.append({
            "address": v.get("address", ""),
            "name": v.get("name", "Unknown"),
            "status": v.get("status", "inactive"),
            "commission": v.get("commission", 0),
            "commission_pct": format_percentage(v.get("commission", 0)),
            "self_stake": v.get("self_stake", 0),
            "delegated_stake": v.get("delegated_stake", 0),
            "total_stake": total_v_stake,
            "total_stake_formatted": format_token_amount(total_v_stake),
            "voting_power_pct": round(total_v_stake / total_stake * 100, 2) if total_stake > 0 else 0,
            "uptime": uptime,
            "blocks_proposed": blocks_proposed,
            "blocks_missed": blocks_missed,
            "slashing_events": v.get("slashing_events", 0),
        })

    # Sort by total stake descending
    result.sort(key=lambda x: x["total_stake"], reverse=True)
    return result


def get_user_staking_info(address: str) -> dict[str, Any]:
    """Fetch user's staking information."""
    if not address:
        return {
            "address": "",
            "total_staked": 0,
            "total_staked_formatted": "0",
            "pending_rewards": 0,
            "pending_rewards_formatted": "0",
            "unbonding": 0,
            "unbonding_formatted": "0",
            "delegations": [],
            "delegations_count": 0,
            "unbondings": [],
            "rewards_by_validator": [],
            "estimated_daily": "0",
            "estimated_yearly": "0",
        }

    data = api_get(f"/api/staking/delegations/{address}")
    delegations_data = data.get("delegations", []) if data else []

    rewards_data = api_get(f"/api/staking/rewards/{address}")
    rewards_by_val = rewards_data.get("rewards_by_validator", {}) if rewards_data else {}

    # Process delegations
    delegations = []
    unbondings = []
    total_staked = 0
    total_unbonding = 0
    total_rewards = 0

    validators_data = get_validators()
    val_names = {v["address"]: v["name"] for v in validators_data}

    for d in delegations_data:
        val_addr = d.get("validator", "")
        amount = d.get("amount", 0)
        total_staked += amount

        delegations.append({
            "validator": val_addr,
            "validator_name": val_names.get(val_addr, "Unknown"),
            "amount": amount,
            "amount_formatted": format_token_amount(amount),
            "shares": d.get("shares", 0),
        })

        unbond_amount = d.get("unbonding_amount", 0)
        if unbond_amount > 0:
            total_unbonding += unbond_amount
            unbondings.append({
                "validator": val_addr,
                "validator_name": val_names.get(val_addr, "Unknown"),
                "amount": unbond_amount,
                "amount_formatted": format_token_amount(unbond_amount),
                "completion": d.get("unbonding_completion", 0),
                "completion_formatted": format_timestamp(d.get("unbonding_completion", 0)),
            })

    # Process rewards
    rewards_list = []
    for val_addr, reward_amount in rewards_by_val.items():
        total_rewards += reward_amount
        rewards_list.append({
            "validator": val_addr,
            "validator_name": val_names.get(val_addr, "Unknown"),
            "amount": reward_amount,
            "amount_formatted": format_token_amount(reward_amount),
        })

    # Estimate rewards (5% APY)
    apy_rate = 0.05
    estimated_yearly = int(total_staked * apy_rate)
    estimated_daily = estimated_yearly // 365

    return {
        "address": address,
        "total_staked": total_staked,
        "total_staked_formatted": format_token_amount(total_staked),
        "pending_rewards": total_rewards,
        "pending_rewards_formatted": format_token_amount(total_rewards),
        "unbonding": total_unbonding,
        "unbonding_formatted": format_token_amount(total_unbonding),
        "delegations": delegations,
        "delegations_count": len(delegations),
        "unbondings": unbondings,
        "rewards_by_validator": rewards_list,
        "estimated_daily": format_token_amount(estimated_daily),
        "estimated_yearly": format_token_amount(estimated_yearly),
    }


def get_staking_history(address: str) -> list[dict[str, Any]]:
    """Fetch user's staking transaction history."""
    if not address:
        return []

    data = api_get(f"/api/staking/history/{address}")
    history = data.get("history", []) if data else []

    validators_data = get_validators()
    val_names = {v["address"]: v["name"] for v in validators_data}

    result = []
    for tx in history:
        tx_type = tx.get("type", "unknown")
        amount = tx.get("amount", 0)

        result.append({
            "type": tx_type.replace("_", " ").title(),
            "validator": tx.get("validator", ""),
            "validator_name": val_names.get(tx.get("validator", ""), "Unknown"),
            "amount": amount,
            "amount_formatted": format_token_amount(amount),
            "amount_class": "positive" if tx_type in ["claim", "delegate"] else "negative",
            "timestamp": tx.get("timestamp", 0),
            "timestamp_formatted": format_timestamp(tx.get("timestamp", 0)),
            "tx_hash": tx.get("tx_hash", ""),
        })

    return result


# Routes
@app.route("/")
def index():
    """Render staking dashboard."""
    # Get user address from query param or session (simplified for demo)
    user_address = request.args.get("address", "")

    stats = get_staking_stats()
    validators = get_validators()
    user = get_user_staking_info(user_address)
    history = get_staking_history(user_address)

    return render_template_string(
        HTML_TEMPLATE,
        stats=stats,
        validators=validators,
        user=user,
        history=history,
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
    )


@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


# API Endpoints
@app.route("/api/staking/info")
def api_staking_info():
    """Get staking network information."""
    return jsonify(get_staking_stats())


@app.route("/api/staking/validators")
def api_validators():
    """Get list of validators."""
    return jsonify({"validators": get_validators()})


@app.route("/api/staking/delegations/<address>")
def api_delegations(address: str) -> Response:
    """Get user's delegations."""
    user_info = get_user_staking_info(address)
    return jsonify({
        "address": address,
        "delegations": user_info["delegations"],
        "total_staked": user_info["total_staked"],
    })


@app.route("/api/staking/rewards/<address>")
def api_rewards(address: str) -> Response:
    """Get user's pending rewards."""
    user_info = get_user_staking_info(address)
    return jsonify({
        "address": address,
        "total_rewards": user_info["pending_rewards"],
        "rewards_by_validator": {
            r["validator"]: r["amount"] for r in user_info["rewards_by_validator"]
        },
    })


@app.route("/api/staking/delegate", methods=["POST"])
def api_delegate():
    """Delegate stake to a validator."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Invalid request body"}), 400

    required = ["address", "validator", "amount"]
    for field in required:
        if field not in data:
            return jsonify({"success": False, "error": f"Missing field: {field}"}), 400

    # Forward to XAI API
    result = api_post("/api/staking/delegate", {
        "caller": data["address"],
        "validator": data["validator"],
        "amount": int(data["amount"]),
    })

    if result["status_code"] == 200:
        return jsonify({
            "success": True,
            "tx_hash": result["data"].get("tx_hash", ""),
            "message": "Delegation successful",
        })
    else:
        return jsonify({
            "success": False,
            "error": result["data"].get("error", "Delegation failed"),
        }), result["status_code"]


@app.route("/api/staking/undelegate", methods=["POST"])
def api_undelegate():
    """Undelegate stake from a validator."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Invalid request body"}), 400

    required = ["address", "validator", "amount"]
    for field in required:
        if field not in data:
            return jsonify({"success": False, "error": f"Missing field: {field}"}), 400

    # Forward to XAI API
    result = api_post("/api/staking/undelegate", {
        "caller": data["address"],
        "validator": data["validator"],
        "amount": int(data["amount"]),
    })

    if result["status_code"] == 200:
        return jsonify({
            "success": True,
            "tx_hash": result["data"].get("tx_hash", ""),
            "unbonding_completion": result["data"].get("unbonding_completion", 0),
            "message": "Undelegation initiated",
        })
    else:
        return jsonify({
            "success": False,
            "error": result["data"].get("error", "Undelegation failed"),
        }), result["status_code"]


@app.route("/api/staking/claim-rewards", methods=["POST"])
def api_claim_rewards():
    """Claim rewards from a specific validator."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Invalid request body"}), 400

    required = ["address", "validator"]
    for field in required:
        if field not in data:
            return jsonify({"success": False, "error": f"Missing field: {field}"}), 400

    # Forward to XAI API
    result = api_post("/api/staking/claim-rewards", {
        "caller": data["address"],
        "validator": data["validator"],
    })

    if result["status_code"] == 200:
        amount = result["data"].get("amount", 0)
        return jsonify({
            "success": True,
            "amount": amount,
            "amount_formatted": format_token_amount(amount),
            "tx_hash": result["data"].get("tx_hash", ""),
            "message": "Rewards claimed",
        })
    else:
        return jsonify({
            "success": False,
            "error": result["data"].get("error", "Claim failed"),
        }), result["status_code"]


@app.route("/api/staking/claim-all", methods=["POST"])
def api_claim_all():
    """Claim all pending rewards."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Invalid request body"}), 400

    if "address" not in data:
        return jsonify({"success": False, "error": "Missing field: address"}), 400

    # Forward to XAI API
    result = api_post("/api/staking/claim-all", {
        "caller": data["address"],
    })

    if result["status_code"] == 200:
        amount = result["data"].get("amount", 0)
        return jsonify({
            "success": True,
            "amount": amount,
            "amount_formatted": format_token_amount(amount),
            "tx_hash": result["data"].get("tx_hash", ""),
            "message": "All rewards claimed",
        })
    else:
        return jsonify({
            "success": False,
            "error": result["data"].get("error", "Claim failed"),
        }), result["status_code"]


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger.info(f"Starting XAI Staking Dashboard on port {STAKING_PORT}")
    logger.info(f"XAI API URL: {XAI_API_URL}")
    app.run(host="0.0.0.0", port=STAKING_PORT, debug=False)
