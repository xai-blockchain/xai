#!/usr/bin/env python3
"""
XAI Testnet Faucet
Provides free testnet tokens for development purposes
"""

import os
import time
import logging
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
XAI_API_URL = os.getenv('XAI_API_URL', 'http://xai-testnet-bootstrap:8080')
FAUCET_PORT = int(os.getenv('FAUCET_PORT', '8086'))
FAUCET_AMOUNT = float(os.getenv('FAUCET_AMOUNT', '100'))
FAUCET_COOLDOWN = int(os.getenv('FAUCET_COOLDOWN', '3600'))  # 1 hour in seconds

# In-memory storage for cooldown tracking
request_history = {}

# HTML template
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>XAI Testnet Faucet</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { color: #333; }
        input {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        button {
            width: 100%;
            padding: 12px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover { background: #45a049; }
        .message {
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
        }
        .success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>XAI Testnet Faucet</h1>
        <div class="info message">
            <p>Get {{ amount }} testnet XAI tokens for development.</p>
            <p>Cooldown: {{ cooldown }} seconds between requests.</p>
        </div>
        <form id="faucetForm">
            <input type="text" id="address" placeholder="Enter your XAI address" required>
            <button type="submit">Request Tokens</button>
        </form>
        <div id="result"></div>
    </div>
    <script>
        document.getElementById('faucetForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const address = document.getElementById('address').value;
            const resultDiv = document.getElementById('result');

            resultDiv.innerHTML = '<div class="info message">Processing...</div>';

            try {
                const response = await fetch('/api/request', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ address })
                });

                const data = await response.json();

                if (data.success) {
                    resultDiv.innerHTML = `<div class="success message">${data.message}</div>`;
                } else {
                    resultDiv.innerHTML = `<div class="error message">${data.error}</div>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<div class="error message">Network error: ${error.message}</div>`;
            }
        });
    </script>
</body>
</html>
"""


def check_cooldown(address: str) -> tuple[bool, int]:
    """Check if address is in cooldown period"""
    if address not in request_history:
        return True, 0

    last_request = request_history[address]
    elapsed = time.time() - last_request
    remaining = FAUCET_COOLDOWN - elapsed

    if remaining <= 0:
        return True, 0

    return False, int(remaining)


def send_tokens(address: str, amount: float) -> dict:
    """Send tokens to the specified address via XAI API"""
    try:
        response = requests.post(
            f"{XAI_API_URL}/api/faucet",
            json={"address": address, "amount": amount},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error sending tokens: {e}")
        return {"success": False, "error": str(e)}


@app.route('/')
def index():
    """Render faucet interface"""
    return render_template_string(
        TEMPLATE,
        amount=FAUCET_AMOUNT,
        cooldown=FAUCET_COOLDOWN
    )


@app.route('/api/request', methods=['POST'])
def request_tokens():
    """Handle token request"""
    data = request.get_json()

    if not data or 'address' not in data:
        return jsonify({'success': False, 'error': 'Address is required'}), 400

    address = data['address']

    # Validate address format (basic check)
    if not address.startswith('AXN') or len(address) < 40:
        return jsonify({'success': False, 'error': 'Invalid XAI address'}), 400

    # Check cooldown
    can_request, remaining = check_cooldown(address)
    if not can_request:
        return jsonify({
            'success': False,
            'error': f'Please wait {remaining} seconds before requesting again'
        }), 429

    # Send tokens
    result = send_tokens(address, FAUCET_AMOUNT)

    if result.get('success'):
        request_history[address] = time.time()
        return jsonify({
            'success': True,
            'message': f'Successfully sent {FAUCET_AMOUNT} XAI to {address}',
            'txid': result.get('txid', 'N/A')
        })
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Unknown error occurred')
        }), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


if __name__ == '__main__':
    logger.info(f"Starting XAI Testnet Faucet on port {FAUCET_PORT}")
    logger.info(f"Faucet amount: {FAUCET_AMOUNT} XAI")
    logger.info(f"Cooldown period: {FAUCET_COOLDOWN} seconds")
    logger.info(f"XAI API URL: {XAI_API_URL}")

    app.run(host='0.0.0.0', port=FAUCET_PORT, debug=False)
