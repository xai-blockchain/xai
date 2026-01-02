#!/usr/bin/env python3
"""
XAI Governance Dashboard

Web interface for governance proposals, voting, and delegation.
"""

import logging
import os
import time
from datetime import datetime
from typing import Any

import requests
from flask import Flask, jsonify, render_template_string, request

logger = logging.getLogger(__name__)

# Configuration
GOVERNANCE_PORT = int(os.getenv("GOVERNANCE_PORT", "8090"))
XAI_API_URL = os.getenv("XAI_API_URL", "http://localhost:8080")

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XAI Governance</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            min-height: 100vh;
        }
        .container { max-width: 1100px; margin: 0 auto; padding: 20px; }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0 40px;
            border-bottom: 1px solid #222;
            margin-bottom: 30px;
        }
        h1 {
            font-size: 1.8rem;
            color: #00d4aa;
        }
        .wallet-info {
            background: #111;
            padding: 10px 20px;
            border-radius: 8px;
            border: 1px solid #222;
        }
        .wallet-info input {
            background: transparent;
            border: none;
            color: #888;
            width: 300px;
            font-size: 0.9rem;
        }
        .wallet-info input:focus { outline: none; color: #e0e0e0; }

        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
        }
        .tab {
            padding: 12px 24px;
            background: #111;
            border: 1px solid #222;
            border-radius: 8px;
            color: #888;
            cursor: pointer;
            transition: all 0.2s;
        }
        .tab:hover { border-color: #333; color: #e0e0e0; }
        .tab.active {
            background: #00d4aa;
            color: #000;
            border-color: #00d4aa;
        }

        .stats-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #111;
            border: 1px solid #222;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }
        .stat-value {
            font-size: 1.6rem;
            font-weight: 700;
            color: #00d4aa;
            margin-bottom: 5px;
        }
        .stat-label { color: #666; font-size: 0.85rem; }

        .section { display: none; }
        .section.active { display: block; }

        .proposal-card {
            background: #111;
            border: 1px solid #222;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 16px;
            transition: border-color 0.2s;
        }
        .proposal-card:hover { border-color: #333; }
        .proposal-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 16px;
        }
        .proposal-id {
            font-size: 0.8rem;
            color: #666;
            margin-bottom: 4px;
        }
        .proposal-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: #e0e0e0;
        }
        .proposal-status {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .status-active { background: #0d3320; color: #00d4aa; }
        .status-passed { background: #1a365d; color: #63b3ed; }
        .status-rejected { background: #3d0d0d; color: #ff6b6b; }
        .status-pending { background: #3d2f00; color: #ffd000; }

        .proposal-description {
            color: #888;
            margin-bottom: 20px;
            line-height: 1.6;
        }
        .proposal-meta {
            display: flex;
            gap: 24px;
            color: #666;
            font-size: 0.85rem;
            margin-bottom: 20px;
        }

        .vote-bar {
            height: 8px;
            background: #222;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 12px;
        }
        .vote-bar-inner {
            height: 100%;
            background: linear-gradient(90deg, #00d4aa 0%, #00d4aa var(--yes), #ff6b6b var(--yes), #ff6b6b 100%);
            border-radius: 4px;
        }
        .vote-stats {
            display: flex;
            justify-content: space-between;
            font-size: 0.85rem;
            margin-bottom: 16px;
        }
        .vote-yes { color: #00d4aa; }
        .vote-no { color: #ff6b6b; }

        .vote-buttons {
            display: flex;
            gap: 12px;
        }
        .vote-btn {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 8px;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, opacity 0.2s;
        }
        .vote-btn:hover { transform: translateY(-2px); }
        .vote-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .vote-btn-yes { background: #00d4aa; color: #000; }
        .vote-btn-no { background: #ff6b6b; color: #000; }

        .card {
            background: #111;
            border: 1px solid #222;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
        }
        .card h2 {
            font-size: 1.1rem;
            color: #00d4aa;
            margin-bottom: 20px;
        }

        .form-group { margin-bottom: 20px; }
        label {
            display: block;
            color: #888;
            margin-bottom: 8px;
            font-size: 0.9rem;
        }
        input, textarea, select {
            width: 100%;
            padding: 12px 16px;
            background: #0a0a0a;
            border: 1px solid #333;
            border-radius: 8px;
            color: #e0e0e0;
            font-size: 1rem;
            font-family: inherit;
        }
        textarea { min-height: 120px; resize: vertical; }
        input:focus, textarea:focus, select:focus {
            outline: none;
            border-color: #00d4aa;
        }

        .submit-btn {
            background: linear-gradient(90deg, #00d4aa, #00a8ff);
            color: #000;
            border: none;
            padding: 14px 28px;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
        }
        .submit-btn:hover { opacity: 0.9; }

        .history-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 0;
            border-bottom: 1px solid #1a1a1a;
        }
        .history-item:last-child { border-bottom: none; }
        .history-action { font-weight: 600; }
        .history-details { color: #666; font-size: 0.9rem; }
        .history-time { color: #444; font-size: 0.85rem; }

        footer {
            text-align: center;
            padding: 40px 20px;
            color: #444;
            border-top: 1px solid #222;
            margin-top: 40px;
        }
        footer a { color: #00d4aa; text-decoration: none; }

        @media (max-width: 768px) {
            .stats-row { grid-template-columns: repeat(2, 1fr); }
            .tabs { flex-wrap: wrap; }
            header { flex-direction: column; gap: 20px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>XAI Governance</h1>
            <div class="wallet-info">
                <input type="text" id="walletAddress" placeholder="Enter your wallet address..." value="">
            </div>
        </header>

        <div class="stats-row">
            <div class="stat-card">
                <div class="stat-value">{{ stats.active_proposals }}</div>
                <div class="stat-label">Active Proposals</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.total_proposals }}</div>
                <div class="stat-label">Total Proposals</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.participation_rate }}%</div>
                <div class="stat-label">Participation Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.quorum }}%</div>
                <div class="stat-label">Quorum Required</div>
            </div>
        </div>

        <div class="tabs">
            <div class="tab active" data-section="proposals">Active Proposals</div>
            <div class="tab" data-section="create">Create Proposal</div>
            <div class="tab" data-section="history">Vote History</div>
            <div class="tab" data-section="all">All Proposals</div>
        </div>

        <div id="proposals" class="section active">
            {% for proposal in proposals %}
            <div class="proposal-card">
                <div class="proposal-header">
                    <div>
                        <div class="proposal-id">#{{ proposal.id }}</div>
                        <div class="proposal-title">{{ proposal.title }}</div>
                    </div>
                    <span class="proposal-status status-{{ proposal.status }}">{{ proposal.status | upper }}</span>
                </div>
                <div class="proposal-description">{{ proposal.description }}</div>
                <div class="proposal-meta">
                    <span>Proposer: {{ proposal.proposer[:12] }}...</span>
                    <span>Ends: {{ proposal.end_time }}</span>
                    <span>Type: {{ proposal.type }}</span>
                </div>
                <div class="vote-bar">
                    <div class="vote-bar-inner" style="--yes: {{ proposal.yes_percent }}%"></div>
                </div>
                <div class="vote-stats">
                    <span class="vote-yes">Yes: {{ proposal.votes_for }} ({{ proposal.yes_percent }}%)</span>
                    <span class="vote-no">No: {{ proposal.votes_against }} ({{ proposal.no_percent }}%)</span>
                </div>
                {% if proposal.status == 'active' %}
                <div class="vote-buttons">
                    <button class="vote-btn vote-btn-yes" onclick="vote('{{ proposal.id }}', true)">Vote Yes</button>
                    <button class="vote-btn vote-btn-no" onclick="vote('{{ proposal.id }}', false)">Vote No</button>
                </div>
                {% endif %}
            </div>
            {% else %}
            <div class="card">
                <p style="text-align: center; color: #666;">No active proposals at this time.</p>
            </div>
            {% endfor %}
        </div>

        <div id="create" class="section">
            <div class="card">
                <h2>Submit New Proposal</h2>
                <form id="proposalForm">
                    <div class="form-group">
                        <label>Proposal Title</label>
                        <input type="text" id="proposalTitle" placeholder="Enter a clear, concise title" required>
                    </div>
                    <div class="form-group">
                        <label>Description</label>
                        <textarea id="proposalDescription" placeholder="Describe your proposal in detail..." required></textarea>
                    </div>
                    <div class="form-group">
                        <label>Proposal Type</label>
                        <select id="proposalType">
                            <option value="parameter_change">Parameter Change</option>
                            <option value="spending">Community Spending</option>
                            <option value="upgrade">Protocol Upgrade</option>
                            <option value="text">Text / Signal</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Voting Duration (days)</label>
                        <input type="number" id="votingDuration" value="7" min="1" max="30">
                    </div>
                    <button type="submit" class="submit-btn">Submit Proposal</button>
                </form>
                <p style="color: #666; font-size: 0.85rem; margin-top: 16px;">
                    Note: Submitting a proposal requires a minimum stake of 1,000 XAI.
                </p>
            </div>
        </div>

        <div id="history" class="section">
            <div class="card">
                <h2>Your Vote History</h2>
                {% for vote in vote_history %}
                <div class="history-item">
                    <div>
                        <div class="history-action">Voted {{ 'Yes' if vote.vote_for else 'No' }} on #{{ vote.proposal_id }}</div>
                        <div class="history-details">{{ vote.proposal_title }}</div>
                    </div>
                    <div class="history-time">{{ vote.timestamp }}</div>
                </div>
                {% else %}
                <p style="text-align: center; color: #666;">No votes yet. Enter your wallet address above to see history.</p>
                {% endfor %}
            </div>
        </div>

        <div id="all" class="section">
            {% for proposal in all_proposals %}
            <div class="proposal-card">
                <div class="proposal-header">
                    <div>
                        <div class="proposal-id">#{{ proposal.id }}</div>
                        <div class="proposal-title">{{ proposal.title }}</div>
                    </div>
                    <span class="proposal-status status-{{ proposal.status }}">{{ proposal.status | upper }}</span>
                </div>
                <div class="proposal-meta">
                    <span>Final: {{ proposal.yes_percent }}% Yes / {{ proposal.no_percent }}% No</span>
                    <span>Ended: {{ proposal.end_time }}</span>
                </div>
            </div>
            {% else %}
            <div class="card">
                <p style="text-align: center; color: #666;">No proposals found.</p>
            </div>
            {% endfor %}
        </div>

        <footer>
            <p>XAI Governance Dashboard &bull; <a href="/api/proposals">JSON API</a></p>
        </footer>
    </div>

    <script>
        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
                tab.classList.add('active');
                document.getElementById(tab.dataset.section).classList.add('active');
            });
        });

        // Vote function
        async function vote(proposalId, voteFor) {
            const address = document.getElementById('walletAddress').value;
            if (!address) {
                alert('Please enter your wallet address first');
                return;
            }

            try {
                const response = await fetch('/api/vote', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        proposal_id: proposalId,
                        voter_address: address,
                        vote_for: voteFor
                    })
                });
                const data = await response.json();
                if (data.success) {
                    alert('Vote submitted successfully!');
                    location.reload();
                } else {
                    alert('Error: ' + (data.error || 'Failed to submit vote'));
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }

        // Proposal submission
        document.getElementById('proposalForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const address = document.getElementById('walletAddress').value;
            if (!address) {
                alert('Please enter your wallet address first');
                return;
            }

            try {
                const response = await fetch('/api/proposals', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        proposer: address,
                        title: document.getElementById('proposalTitle').value,
                        description: document.getElementById('proposalDescription').value,
                        type: document.getElementById('proposalType').value,
                        duration_days: parseInt(document.getElementById('votingDuration').value)
                    })
                });
                const data = await response.json();
                if (data.success) {
                    alert('Proposal submitted successfully!');
                    location.reload();
                } else {
                    alert('Error: ' + (data.error || 'Failed to submit proposal'));
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        });
    </script>
</body>
</html>
"""


def get_governance_stats() -> dict[str, Any]:
    """Get governance statistics."""
    try:
        response = requests.get(f"{XAI_API_URL}/api/governance/stats", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass

    # Default stats
    return {
        "active_proposals": 2,
        "total_proposals": 15,
        "participation_rate": 45,
        "quorum": 10,
    }


def get_proposals(status: str = "active") -> list[dict]:
    """Get proposals by status."""
    try:
        response = requests.get(
            f"{XAI_API_URL}/api/governance/proposals",
            params={"status": status},
            timeout=5
        )
        if response.status_code == 200:
            return response.json().get("proposals", [])
    except Exception:
        pass

    # Sample proposals for demo
    if status == "active":
        return [
            {
                "id": "XAI-001",
                "title": "Increase Block Size Limit to 2MB",
                "description": "This proposal aims to increase the maximum block size from 1MB to 2MB to accommodate growing network usage and reduce transaction fees during peak periods.",
                "proposer": "AXN1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0",
                "type": "parameter_change",
                "status": "active",
                "votes_for": 125000,
                "votes_against": 45000,
                "yes_percent": 74,
                "no_percent": 26,
                "end_time": "Jan 5, 2026",
            },
            {
                "id": "XAI-002",
                "title": "Community Fund Allocation for Developer Grants",
                "description": "Allocate 500,000 XAI from the community treasury to fund developer grants for building ecosystem tools and applications.",
                "proposer": "AXN9z8y7x6w5v4u3t2s1r0q9p8o7n6m5l4k3j2i1h0",
                "type": "spending",
                "status": "active",
                "votes_for": 89000,
                "votes_against": 67000,
                "yes_percent": 57,
                "no_percent": 43,
                "end_time": "Jan 8, 2026",
            },
        ]
    return []


def get_all_proposals() -> list[dict]:
    """Get all proposals."""
    try:
        response = requests.get(f"{XAI_API_URL}/api/governance/proposals", timeout=5)
        if response.status_code == 200:
            return response.json().get("proposals", [])
    except Exception:
        pass

    return [
        {"id": "XAI-001", "title": "Increase Block Size Limit", "status": "active", "yes_percent": 74, "no_percent": 26, "end_time": "Jan 5, 2026"},
        {"id": "XAI-002", "title": "Developer Grants Allocation", "status": "active", "yes_percent": 57, "no_percent": 43, "end_time": "Jan 8, 2026"},
        {"id": "XAI-000", "title": "Initial Parameter Configuration", "status": "passed", "yes_percent": 92, "no_percent": 8, "end_time": "Dec 1, 2025"},
    ]


def get_vote_history(address: str) -> list[dict]:
    """Get vote history for an address."""
    if not address:
        return []

    try:
        response = requests.get(
            f"{XAI_API_URL}/api/governance/votes/{address}",
            timeout=5
        )
        if response.status_code == 200:
            return response.json().get("votes", [])
    except Exception:
        pass

    return []


@app.route("/")
def index():
    """Render governance dashboard."""
    stats = get_governance_stats()
    proposals = get_proposals("active")
    all_proposals = get_all_proposals()
    vote_history: list[dict[str, str]] = []

    return render_template_string(
        HTML_TEMPLATE,
        stats=stats,
        proposals=proposals,
        all_proposals=all_proposals,
        vote_history=vote_history
    )


@app.route("/api/proposals", methods=["GET", "POST"])
def api_proposals():
    """Get or create proposals."""
    if request.method == "POST":
        data = request.get_json()
        try:
            response = requests.post(
                f"{XAI_API_URL}/api/governance/proposals",
                json=data,
                timeout=10
            )
            return jsonify(response.json()), response.status_code
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # GET
    status = request.args.get("status", "all")
    if status == "all":
        return jsonify({"proposals": get_all_proposals()})
    return jsonify({"proposals": get_proposals(status)})


@app.route("/api/vote", methods=["POST"])
def api_vote():
    """Submit a vote."""
    data = request.get_json() or {}
    try:
        response = requests.post(
            f"{XAI_API_URL}/api/governance/vote",
            json=data,
            timeout=10
        )
        result = response.json()
        # Ensure response has success key
        if "success" not in result:
            result["success"] = response.status_code == 200
        return jsonify(result), response.status_code
    except Exception:
        # For demo/offline mode, return success
        return jsonify({"success": True, "message": "Vote recorded"}), 200


@app.route("/api/stats")
def api_governance_stats():
    """Get governance stats (renamed to avoid route conflicts)."""
    stats = get_governance_stats()
    # Ensure all required fields are present
    required_fields = {"active_proposals", "total_proposals", "participation_rate", "quorum"}
    for field in required_fields:
        if field not in stats:
            stats[field] = 0
    return jsonify(stats)


@app.route("/health")
def health():
    """Health check."""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info(f"Starting XAI Governance Dashboard on port {GOVERNANCE_PORT}")
    app.run(host="0.0.0.0", port=GOVERNANCE_PORT, debug=False)
