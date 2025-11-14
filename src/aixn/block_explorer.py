"""
XAI Block Explorer - Local Testing Interface

Simple web interface for exploring the XAI blockchain locally.
NOT for production - only for local testing and debugging!

Usage:
    python block_explorer.py

Then visit: http://localhost:8080
"""

import os
import sys
from flask import Flask, render_template, request, jsonify
import yaml
from flask_cors import CORS

def get_allowed_origins():
    """Get allowed origins from config file"""
    cors_config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'cors.yaml')
    if os.path.exists(cors_config_path):
        with open(cors_config_path, 'r') as f:
            cors_config = yaml.safe_load(f)
            return cors_config.get('origins', [])
    return []

app = Flask(__name__)
allowed_origins = get_allowed_origins()
CORS(app, origins=allowed_origins)

# Configuration
NODE_URL = os.getenv('XAI_NODE_URL', 'http://localhost:8545')

def get_from_node(endpoint):
    """Fetch data from XAI node"""
    try:
        response = requests.get(f"{NODE_URL}{endpoint}", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching {endpoint}: {e}")
        return None

def post_to_node(endpoint, data):
    """Post data to XAI node"""
    try:
        response = requests.post(f"{NODE_URL}{endpoint}", json=data, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error posting to {endpoint}: {e}")
        return None

def format_timestamp(timestamp):
    """Convert timestamp to readable UTC format"""
    if timestamp:
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    return 'N/A'

def format_amount(amount):
    """Format XAI amount"""
    return f"{amount:,.4f}" if amount else "0.0000"

@app.route('/')
def index():
    """Homepage - Blockchain overview"""
    stats = get_from_node('/stats')

    # Get recent blocks
    blocks_data = get_from_node('/blocks?limit=10')
    recent_blocks = blocks_data.get('blocks', [])[-10:] if blocks_data else []
    recent_blocks.reverse()  # Show newest first

    return render_template('index.html',
                          stats=stats,
                          recent_blocks=recent_blocks,
                          format_timestamp=format_timestamp,
                          format_amount=format_amount)

@app.route('/blocks')
def blocks():
    """View all blocks"""
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))

    blocks_data = get_from_node(f'/blocks?limit={limit}&offset={offset}')
    blocks_list = blocks_data.get('blocks', []) if blocks_data else []
    blocks_list.reverse()  # Show newest first

    return render_template('blocks.html',
                          blocks=blocks_list,
                          limit=limit,
                          offset=offset,
                          format_timestamp=format_timestamp)

@app.route('/block/<int:index>')
def block_detail(index):
    """View specific block"""
    block = get_from_node(f'/blocks/{index}')

    return render_template('block.html',
                          block=block,
                          format_timestamp=format_timestamp,
                          format_amount=format_amount)

@app.route('/transaction/<txid>')
def transaction_detail(txid):
    """View specific transaction"""
    tx = get_from_node(f'/transaction/{txid}')

    return render_template('transaction.html',
                          tx=tx,
                          format_timestamp=format_timestamp,
                          format_amount=format_amount)

@app.route('/address/<address>')
def address_detail(address):
    """View address balance and history"""
    balance_data = get_from_node(f'/balance/{address}')
    history_data = get_from_node(f'/history/{address}')

    balance = balance_data.get('balance', 0) if balance_data else 0
    history = history_data.get('history', []) if history_data else []
    history.reverse()  # Show newest first

    return render_template('address.html',
                          address=address,
                          balance=balance,
                          history=history,
                          format_timestamp=format_timestamp,
                          format_amount=format_amount)

@app.route('/search', methods=['POST'])
def search():
    """Search for block, transaction, or address"""
    query = request.form.get('query', '').strip()

    if not query:
        return render_template('search.html', error='Please enter a search query')

    # Try to interpret the query
    # Check if it's a number (block index)
    if query.isdigit():
        return render_template('search.html', redirect=f'/block/{query}')

    # Check if it's an address (starts with AIXN or TXAI)
    if query.startswith('AIXN') or query.startswith('TXAI'):
        return render_template('search.html', redirect=f'/address/{query}')

    # Assume it's a transaction ID
    return render_template('search.html', redirect=f'/transaction/{query}')

@app.route('/api/stats')
def api_stats():
    """API endpoint for stats (for auto-refresh)"""
    stats = get_from_node('/stats')
    return jsonify(stats) if stats else jsonify({'error': 'Could not fetch stats'})

if __name__ == '__main__':
    print("=" * 60)
    print("XAI BLOCK EXPLORER")
    print("=" * 60)
    print(f"Connected to node: {NODE_URL}")
    print(f"Explorer running at: http://localhost:8080")
    print("=" * 60)
    print("\nNOTE: This is for LOCAL TESTING ONLY!")
    print("      Not intended for production use.\n")

    app.run(host='0.0.0.0', port=8080, debug=True)
