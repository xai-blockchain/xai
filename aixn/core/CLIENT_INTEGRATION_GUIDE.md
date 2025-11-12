# Client Integration Guide
## Building Browser Plugins, Desktop Miners, and Node Dashboards

---

## Quick Start

### 1. Start XAI Node with API Extensions

```python
from node import BlockchainNode
from api_extensions import extend_node_api

# Create node
node = BlockchainNode(host='0.0.0.0', port=8545)

# Add API extensions
extensions = extend_node_api(node)

# Start node
node.run()
```

**Now available:**
- REST API: `http://localhost:8545`
- WebSocket: `ws://localhost:8545/ws`
- All endpoints from COMPREHENSIVE_API_DOCUMENTATION.md

---

## Browser Mining Plugin

### A. Setup

**manifest.json:**
```json
{
  "name": "XAI Browser Miner",
  "version": "1.0.0",
  "manifest_version": 3,
  "permissions": ["storage", "notifications"],
  "background": {
    "service_worker": "background.js"
  },
  "action": {
    "default_popup": "popup.html",
    "default_icon": "icon.png"
  }
}
```

### B. Background Mining Worker

**background.js:**
```javascript
const API_URL = 'http://localhost:8545';
let ws = null;
let minerAddress = null;
let isMining = false;

// Initialize WebSocket
function connectWebSocket() {
  ws = new WebSocket('ws://localhost:8545/ws');

  ws.onopen = () => {
    console.log('WebSocket connected');

    // Subscribe to mining updates
    ws.send(JSON.stringify({
      action: 'subscribe',
      channel: 'mining'
    }));

    // Subscribe to blocks
    ws.send(JSON.stringify({
      action: 'subscribe',
      channel: 'blocks'
    }));
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleWebSocketMessage(data);
  };

  ws.onclose = () => {
    console.log('WebSocket disconnected, reconnecting...');
    setTimeout(connectWebSocket, 5000);
  };
}

function handleWebSocketMessage(data) {
  if (data.channel === 'mining') {
    if (data.event === 'hashrate_update') {
      // Update UI with hashrate
      chrome.runtime.sendMessage({
        type: 'hashrate_update',
        hashrate: data.data.current_hashrate
      });
    }
  } else if (data.channel === 'blocks') {
    if (data.event === 'new_block') {
      // Check if we mined it
      if (data.data.miner === minerAddress) {
        // Show notification
        chrome.notifications.create({
          type: 'basic',
          iconUrl: 'icon.png',
          title: 'Block Mined!',
          message: `You mined block #${data.data.index} and earned ${data.data.reward} XAI!`
        });
      }
    }
  }
}

// Start mining
async function startMining() {
  if (!minerAddress) {
    // Create wallet first
    const response = await fetch(`${API_URL}/wallet/create`, {
      method: 'POST'
    });
    const wallet = await response.json();
    minerAddress = wallet.address;

    // Save to storage
    chrome.storage.local.set({
      minerAddress: wallet.address,
      privateKey: wallet.private_key
    });
  }

  // Start mining
  const response = await fetch(`${API_URL}/mining/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      miner_address: minerAddress,
      threads: 2, // Browser uses 2 threads
      intensity: 'low' // Low intensity for browser
    })
  });

  const result = await response.json();
  if (result.success) {
    isMining = true;
    console.log('Mining started:', result);
  }
}

// Stop mining
async function stopMining() {
  const response = await fetch(`${API_URL}/mining/stop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      miner_address: minerAddress
    })
  });

  const result = await response.json();
  if (result.success) {
    isMining = false;
    console.log('Mining stopped:', result);
  }
}

// Message handler
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'start_mining') {
    startMining().then(sendResponse);
    return true;
  } else if (request.action === 'stop_mining') {
    stopMining().then(sendResponse);
    return true;
  }
});

// Load saved address
chrome.storage.local.get(['minerAddress'], (result) => {
  if (result.minerAddress) {
    minerAddress = result.minerAddress;
    console.log('Loaded miner address:', minerAddress);
  }
});

// Connect WebSocket
connectWebSocket();
```

### C. Popup UI

**popup.html:**
```html
<!DOCTYPE html>
<html>
<head>
  <title>XAI Browser Miner</title>
  <style>
    body {
      width: 300px;
      padding: 15px;
      font-family: Arial, sans-serif;
    }
    .stat {
      margin: 10px 0;
      padding: 10px;
      background: #f0f0f0;
      border-radius: 5px;
    }
    .stat-label {
      font-weight: bold;
      color: #666;
    }
    .stat-value {
      font-size: 18px;
      color: #333;
    }
    button {
      width: 100%;
      padding: 12px;
      margin: 5px 0;
      font-size: 16px;
      cursor: pointer;
      border: none;
      border-radius: 5px;
    }
    #startBtn {
      background: #4CAF50;
      color: white;
    }
    #stopBtn {
      background: #f44336;
      color: white;
    }
  </style>
</head>
<body>
  <h2>XAI Browser Miner</h2>

  <div class="stat">
    <div class="stat-label">Status</div>
    <div class="stat-value" id="status">Idle</div>
  </div>

  <div class="stat">
    <div class="stat-label">Hashrate</div>
    <div class="stat-value" id="hashrate">0 MH/s</div>
  </div>

  <div class="stat">
    <div class="stat-label">Blocks Mined Today</div>
    <div class="stat-value" id="blocks">0</div>
  </div>

  <div class="stat">
    <div class="stat-label">XAI Earned Today</div>
    <div class="stat-value" id="earned">0 XAI</div>
  </div>

  <button id="startBtn">Start Mining</button>
  <button id="stopBtn" style="display:none;">Stop Mining</button>

  <script src="popup.js"></script>
</body>
</html>
```

**popup.js:**
```javascript
const API_URL = 'http://localhost:8545';
let minerAddress = null;
let updateInterval = null;

// Load miner address
chrome.storage.local.get(['minerAddress'], (result) => {
  if (result.minerAddress) {
    minerAddress = result.minerAddress;
    updateStats();
  }
});

// Start mining button
document.getElementById('startBtn').addEventListener('click', () => {
  chrome.runtime.sendMessage({ action: 'start_mining' }, (response) => {
    document.getElementById('status').textContent = 'Mining';
    document.getElementById('startBtn').style.display = 'none';
    document.getElementById('stopBtn').style.display = 'block';

    // Start updating stats
    updateInterval = setInterval(updateStats, 5000);
  });
});

// Stop mining button
document.getElementById('stopBtn').addEventListener('click', () => {
  chrome.runtime.sendMessage({ action: 'stop_mining' }, (response) => {
    document.getElementById('status').textContent = 'Idle';
    document.getElementById('startBtn').style.display = 'block';
    document.getElementById('stopBtn').style.display = 'none';

    // Stop updating stats
    clearInterval(updateInterval);
  });
});

// Update stats from API
async function updateStats() {
  if (!minerAddress) return;

  const response = await fetch(`${API_URL}/mining/status?address=${minerAddress}`);
  const data = await response.json();

  if (data.is_mining) {
    document.getElementById('status').textContent = 'Mining';
    document.getElementById('hashrate').textContent = data.hashrate;
    document.getElementById('blocks').textContent = data.blocks_mined_today;
    document.getElementById('earned').textContent = `${data.xai_earned_today} XAI`;
  }
}

// Listen for hashrate updates from background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'hashrate_update') {
    document.getElementById('hashrate').textContent = request.hashrate;
  }
});
```

---

## Desktop Miner

### A. Setup (Python)

**requirements.txt:**
```
requests
websocket-client
PyQt5  # For GUI
```

### B. Mining Core

**desktop_miner.py:**
```python
import requests
import websocket
import json
import threading
import time

class XAIMiner:
    def __init__(self, api_url='http://localhost:8545'):
        self.api_url = api_url
        self.ws_url = api_url.replace('http', 'ws') + '/ws'
        self.miner_address = None
        self.is_mining = False
        self.stats = {}
        self.ws = None

        # Load or create wallet
        self.load_wallet()

        # Connect WebSocket
        self.connect_websocket()

    def load_wallet(self):
        """Load existing wallet or create new one"""
        try:
            with open('wallet.json', 'r') as f:
                wallet = json.load(f)
                self.miner_address = wallet['address']
                print(f"Loaded wallet: {self.miner_address}")
        except FileNotFoundError:
            # Create new wallet
            response = requests.post(f'{self.api_url}/wallet/create')
            wallet = response.json()
            self.miner_address = wallet['address']

            # Save wallet
            with open('wallet.json', 'w') as f:
                json.dump(wallet, f, indent=2)

            print(f"Created new wallet: {self.miner_address}")
            print("⚠️ SAVE THIS FILE SECURELY!")

    def connect_websocket(self):
        """Connect to WebSocket for real-time updates"""
        def on_message(ws, message):
            data = json.loads(message)
            self.handle_ws_message(data)

        def on_open(ws):
            print("WebSocket connected")
            # Subscribe to mining updates
            ws.send(json.dumps({
                'action': 'subscribe',
                'channel': 'mining'
            }))
            ws.send(json.dumps({
                'action': 'subscribe',
                'channel': 'blocks'
            }))

        def run_ws():
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=on_message,
                on_open=on_open
            )
            self.ws.run_forever()

        ws_thread = threading.Thread(target=run_ws, daemon=True)
        ws_thread.start()

    def handle_ws_message(self, data):
        """Handle WebSocket messages"""
        if data.get('channel') == 'mining':
            if data.get('event') == 'hashrate_update':
                self.stats = data['data']
                print(f"\rHashrate: {self.stats.get('current_hashrate')}   ", end='')

        elif data.get('channel') == 'blocks':
            if data.get('event') == 'new_block':
                block = data['data']
                if block['miner'] == self.miner_address:
                    print(f"\n🎉 Block #{block['index']} mined! Reward: {block['reward']} XAI")

    def start_mining(self, threads=4, intensity='high'):
        """Start mining"""
        response = requests.post(f'{self.api_url}/mining/start', json={
            'miner_address': self.miner_address,
            'threads': threads,
            'intensity': intensity
        })

        result = response.json()
        if result['success']:
            self.is_mining = True
            print(f"✅ Mining started")
            print(f"   Threads: {threads}")
            print(f"   Intensity: {intensity}")
            print(f"   Expected hashrate: {result['expected_hashrate']}")
        else:
            print(f"❌ Failed to start mining: {result.get('error')}")

    def stop_mining(self):
        """Stop mining"""
        response = requests.post(f'{self.api_url}/mining/stop', json={
            'miner_address': self.miner_address
        })

        result = response.json()
        if result['success']:
            self.is_mining = False
            print(f"\n✅ Mining stopped")
            print(f"   Blocks mined: {result['total_blocks_mined']}")
            print(f"   XAI earned: {result['total_xai_earned']}")
        else:
            print(f"❌ Failed to stop mining: {result.get('error')}")

    def get_stats(self):
        """Get current mining statistics"""
        response = requests.get(f'{self.api_url}/mining/status', params={
            'address': self.miner_address
        })

        return response.json()

    def print_stats(self):
        """Print detailed statistics"""
        stats = self.get_stats()

        if stats['is_mining']:
            print("\n" + "="*50)
            print("MINING STATISTICS")
            print("="*50)
            print(f"Status:          Mining")
            print(f"Hashrate:        {stats['hashrate']}")
            print(f"Avg Hashrate:    {stats['avg_hashrate']}")
            print(f"Blocks Today:    {stats['blocks_mined_today']}")
            print(f"XAI Earned:      {stats['xai_earned_today']}")
            print(f"Shares:          {stats['shares_accepted']}/{stats['shares_submitted']}")
            print(f"Acceptance:      {stats['acceptance_rate']:.1f}%")
            print(f"Difficulty:      {stats['current_difficulty']}")
            print(f"Uptime:          {int(stats['uptime'])} seconds")
            print("="*50)
        else:
            print("Not mining")


if __name__ == '__main__':
    # Create miner
    miner = XAIMiner()

    # Start mining with 8 threads on high intensity
    miner.start_mining(threads=8, intensity='high')

    print("\nMining... Press Ctrl+C to stop\n")

    try:
        while True:
            time.sleep(30)
            miner.print_stats()

    except KeyboardInterrupt:
        print("\n\nStopping miner...")
        miner.stop_mining()
```

**Usage:**
```bash
python desktop_miner.py
```

---

## Node Operator Dashboard

### A. Web Dashboard (React Example)

**NodeOperatorDashboard.jsx:**
```javascript
import React, { useState, useEffect } from 'react';

const API_URL = 'http://localhost:8545';

function NodeOperatorDashboard() {
  const [questions, setQuestions] = useState([]);
  const [stats, setStats] = useState({});
  const [ws, setWs] = useState(null);

  useEffect(() => {
    // Connect WebSocket
    const socket = new WebSocket('ws://localhost:8545/ws');

    socket.onopen = () => {
      // Subscribe to questioning channel
      socket.send(JSON.stringify({
        action: 'subscribe',
        channel: 'questioning'
      }));

      // Subscribe to stats
      socket.send(JSON.stringify({
        action: 'subscribe',
        channel: 'stats'
      }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.channel === 'questioning' && data.event === 'new_question') {
        // Show notification
        new Notification('New AI Question', {
          body: data.data.question_text,
          icon: '/icon.png'
        });

        // Reload questions
        loadPendingQuestions();
      } else if (data.channel === 'stats') {
        setStats(data.data);
      }
    };

    setWs(socket);

    // Load initial data
    loadPendingQuestions();

    return () => socket.close();
  }, []);

  async function loadPendingQuestions() {
    const response = await fetch(`${API_URL}/questioning/pending`);
    const data = await response.json();
    setQuestions(data.questions);
  }

  async function submitAnswer(questionId, optionId) {
    const response = await fetch(`${API_URL}/questioning/answer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question_id: questionId,
        node_address: 'YOUR_NODE_ADDRESS',
        selected_option_id: optionId,
        private_key: 'YOUR_PRIVATE_KEY'
      })
    });

    const result = await response.json();
    if (result.success) {
      alert('Answer submitted successfully!');
      loadPendingQuestions();
    }
  }

  return (
    <div className="dashboard">
      <h1>XAI Node Operator Dashboard</h1>

      <div className="stats">
        <div className="stat-card">
          <h3>Chain Length</h3>
          <p>{stats.chain_length || 0}</p>
        </div>
        <div className="stat-card">
          <h3>Peers</h3>
          <p>{stats.peers || 0}</p>
        </div>
        <div className="stat-card">
          <h3>Pending TXs</h3>
          <p>{stats.pending_transactions || 0}</p>
        </div>
      </div>

      <h2>Pending AI Questions ({questions.length})</h2>

      {questions.map(q => (
        <div key={q.question_id} className="question-card">
          <div className="question-header">
            <span className={`priority-badge ${q.priority}`}>
              {q.priority}
            </span>
            <span>Task: {q.task_id}</span>
          </div>

          <h3>{q.question_text}</h3>
          <p className="context">{q.context}</p>

          <div className="voting-status">
            <progress
              value={q.total_votes}
              max={q.min_required}
            />
            <span>{q.total_votes}/{q.min_required} votes</span>
          </div>

          <div className="options">
            {q.options.map((opt, idx) => (
              <button
                key={idx}
                onClick={() => submitAnswer(q.question_id, `option_${idx}`)}
                className="option-btn"
              >
                {opt}
              </button>
            ))}
          </div>

          <div className="time-remaining">
            ⏰ {Math.floor(q.time_remaining / 3600)} hours remaining
          </div>
        </div>
      ))}
    </div>
  );
}

export default NodeOperatorDashboard;
```

---

## Summary

### ✅ Complete API System:
1. **REST API** - All CRUD operations
2. **WebSocket** - Real-time updates
3. **P2P Protocol** - Node-to-node sync

### ✅ Ready for Integration:
1. **Browser Plugins** - Lightweight mining, 2 threads
2. **Desktop Miners** - High-performance, 8+ threads
3. **Node Dashboards** - Governance voting, AI questions

### ✅ All Features Working:
- Mining control (start/stop/status)
- Real-time hashrate updates
- Block notifications
- Wallet creation
- Governance voting
- AI questioning
- WebSocket subscriptions

### 🚀 Next Steps:
1. Deploy to production server
2. Create public API documentation
3. Build official browser plugin
4. Build official desktop miner
5. Build node operator dashboard
6. Add rate limiting & API keys
7. Add SSL/TLS for security

**You now have everything needed to build complete XAI blockchain clients!** 🎉
