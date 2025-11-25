// XAI P2P Exchange Frontend Application
// API and WebSocket Configuration
const API_BASE_URL = 'http://localhost:5000/api';
const WS_URL = 'ws://localhost:5000';

// Global State
let authToken = null;
let currentUser = null;
let ws = null;
let wsReconnectAttempts = 0;
let maxReconnectAttempts = 5;
let reconnectTimeout = null;

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    console.log('XAI Exchange initializing...');

    // Check for existing session
    authToken = localStorage.getItem('authToken');
    currentUser = JSON.parse(localStorage.getItem('currentUser') || 'null');

    if (authToken && currentUser) {
        showTradingSection();
        initializeWebSocket();
        loadUserBalance();
        loadOrderBook();
        loadRecentTrades();
    } else {
        showAuthSection();
    }

    // Setup Event Listeners
    setupAuthListeners();
    setupTradingListeners();
    setupTabListeners();
});

// ====== Authentication Functions ======
function setupAuthListeners() {
    // Tab switching
    document.getElementById('loginTab').addEventListener('click', () => {
        document.getElementById('loginTab').classList.add('border-blue-500', 'text-blue-400');
        document.getElementById('loginTab').classList.remove('text-gray-400');
        document.getElementById('registerTab').classList.remove('border-blue-500', 'text-blue-400');
        document.getElementById('registerTab').classList.add('text-gray-400');
        document.getElementById('loginForm').classList.remove('hidden');
        document.getElementById('registerForm').classList.add('hidden');
        hideError('authError');
    });

    document.getElementById('registerTab').addEventListener('click', () => {
        document.getElementById('registerTab').classList.add('border-blue-500', 'text-blue-400');
        document.getElementById('registerTab').classList.remove('text-gray-400');
        document.getElementById('loginTab').classList.remove('border-blue-500', 'text-blue-400');
        document.getElementById('loginTab').classList.add('text-gray-400');
        document.getElementById('registerForm').classList.remove('hidden');
        document.getElementById('loginForm').classList.add('hidden');
        hideError('authError');
    });

    // Form submissions
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    document.getElementById('registerForm').addEventListener('submit', handleRegister);
}

async function handleLogin(e) {
    e.preventDefault();
    hideError('authError');

    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;

    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (response.ok) {
            authToken = data.token;
            currentUser = { username: data.username, user_id: data.user_id };
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('currentUser', JSON.stringify(currentUser));

            showToast('Login successful!', 'success');
            showTradingSection();
            initializeWebSocket();
            loadUserBalance();
            loadOrderBook();
            loadRecentTrades();
        } else {
            showError('authError', data.error || 'Login failed');
        }
    } catch (error) {
        console.error('Login error:', error);
        showError('authError', 'Network error. Please check if the server is running.');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    hideError('authError');

    const username = document.getElementById('registerUsername').value.trim();
    const password = document.getElementById('registerPassword').value;
    const passwordConfirm = document.getElementById('registerPasswordConfirm').value;

    // Validation
    if (username.length < 3) {
        showError('authError', 'Username must be at least 3 characters');
        return;
    }

    if (password.length < 6) {
        showError('authError', 'Password must be at least 6 characters');
        return;
    }

    if (password !== passwordConfirm) {
        showError('authError', 'Passwords do not match');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (response.ok) {
            showToast('Registration successful! Please login.', 'success');
            document.getElementById('loginTab').click();
            document.getElementById('loginUsername').value = username;
        } else {
            showError('authError', data.error || 'Registration failed');
        }
    } catch (error) {
        console.error('Registration error:', error);
        showError('authError', 'Network error. Please check if the server is running.');
    }
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');

    if (ws) {
        ws.close();
        ws = null;
    }

    showAuthSection();
    showToast('Logged out successfully', 'info');
}

// ====== Trading Functions ======
function setupTradingListeners() {
    // Tab switching
    document.getElementById('buyTab').addEventListener('click', () => {
        document.getElementById('buyTab').classList.add('border-green-500', 'text-green-400');
        document.getElementById('buyTab').classList.remove('text-gray-400');
        document.getElementById('sellTab').classList.remove('border-green-500', 'text-green-400');
        document.getElementById('sellTab').classList.add('text-gray-400');
        document.getElementById('buyForm').classList.remove('hidden');
        document.getElementById('sellForm').classList.add('hidden');
        hideError('tradeError');
        hideError('tradeSuccess');
    });

    document.getElementById('sellTab').addEventListener('click', () => {
        document.getElementById('sellTab').classList.add('border-green-500', 'text-green-400');
        document.getElementById('sellTab').classList.remove('text-gray-400');
        document.getElementById('buyTab').classList.remove('border-green-500', 'text-green-400');
        document.getElementById('buyTab').classList.add('text-gray-400');
        document.getElementById('sellForm').classList.remove('hidden');
        document.getElementById('buyForm').classList.add('hidden');
        hideError('tradeError');
        hideError('tradeSuccess');
    });

    // Calculate totals on input
    document.getElementById('buyPrice').addEventListener('input', updateBuyTotal);
    document.getElementById('buyAmount').addEventListener('input', updateBuyTotal);
    document.getElementById('sellPrice').addEventListener('input', updateSellTotal);
    document.getElementById('sellAmount').addEventListener('input', updateSellTotal);

    // Form submissions
    document.getElementById('buyForm').addEventListener('submit', handleBuyOrder);
    document.getElementById('sellForm').addEventListener('submit', handleSellOrder);
}

function updateBuyTotal() {
    const price = parseFloat(document.getElementById('buyPrice').value) || 0;
    const amount = parseFloat(document.getElementById('buyAmount').value) || 0;
    const total = price * amount;
    document.getElementById('buyTotal').textContent = `$${total.toFixed(2)}`;
}

function updateSellTotal() {
    const price = parseFloat(document.getElementById('sellPrice').value) || 0;
    const amount = parseFloat(document.getElementById('sellAmount').value) || 0;
    const total = price * amount;
    document.getElementById('sellTotal').textContent = `$${total.toFixed(2)}`;
}

async function handleBuyOrder(e) {
    e.preventDefault();
    hideError('tradeError');
    hideError('tradeSuccess');

    const price = parseFloat(document.getElementById('buyPrice').value);
    const amount = parseFloat(document.getElementById('buyAmount').value);

    if (price <= 0 || amount <= 0) {
        showError('tradeError', 'Price and amount must be greater than 0');
        return;
    }

    setLoading('buy', true);

    try {
        const response = await fetch(`${API_BASE_URL}/orders/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                order_type: 'buy',
                price: price,
                amount: amount
            })
        });

        const data = await response.json();

        if (response.ok) {
            showSuccess('tradeSuccess', `Buy order placed successfully! Order ID: ${data.order_id}`);
            document.getElementById('buyForm').reset();
            updateBuyTotal();
            loadUserBalance();
            loadOrderBook();
        } else {
            showError('tradeError', data.error || 'Failed to place order');
        }
    } catch (error) {
        console.error('Buy order error:', error);
        showError('tradeError', 'Network error. Please try again.');
    } finally {
        setLoading('buy', false);
    }
}

async function handleSellOrder(e) {
    e.preventDefault();
    hideError('tradeError');
    hideError('tradeSuccess');

    const price = parseFloat(document.getElementById('sellPrice').value);
    const amount = parseFloat(document.getElementById('sellAmount').value);

    if (price <= 0 || amount <= 0) {
        showError('tradeError', 'Price and amount must be greater than 0');
        return;
    }

    setLoading('sell', true);

    try {
        const response = await fetch(`${API_BASE_URL}/orders/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                order_type: 'sell',
                price: price,
                amount: amount
            })
        });

        const data = await response.json();

        if (response.ok) {
            showSuccess('tradeSuccess', `Sell order placed successfully! Order ID: ${data.order_id}`);
            document.getElementById('sellForm').reset();
            updateSellTotal();
            loadUserBalance();
            loadOrderBook();
        } else {
            showError('tradeError', data.error || 'Failed to place order');
        }
    } catch (error) {
        console.error('Sell order error:', error);
        showError('tradeError', 'Network error. Please try again.');
    } finally {
        setLoading('sell', false);
    }
}

// ====== Data Loading Functions ======
async function loadUserBalance() {
    try {
        const response = await fetch(`${API_BASE_URL}/wallet/balance`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById('xaiBalance').textContent = parseFloat(data.xai_balance).toFixed(2);
            document.getElementById('usdBalance').textContent = `$${parseFloat(data.usd_balance).toFixed(2)}`;
        }
    } catch (error) {
        console.error('Error loading balance:', error);
    }
}

async function loadOrderBook() {
    try {
        const response = await fetch(`${API_BASE_URL}/orders/book`);
        const data = await response.json();

        if (response.ok) {
            displayOrderBook(data);
        }
    } catch (error) {
        console.error('Error loading order book:', error);
    }
}

function displayOrderBook(data) {
    const sellOrdersEl = document.getElementById('sellOrders');
    const buyOrdersEl = document.getElementById('buyOrders');

    // Display sell orders (asks) - sorted high to low for display
    if (data.asks && data.asks.length > 0) {
        const sortedAsks = [...data.asks].sort((a, b) => b.price - a.price);
        sellOrdersEl.innerHTML = sortedAsks.slice(0, 10).map(order => `
            <div class="flex justify-between text-sm p-2 bg-gray-700 rounded order-sell">
                <span class="text-red-400">${parseFloat(order.price).toFixed(2)}</span>
                <span class="text-gray-300">${parseFloat(order.amount).toFixed(2)}</span>
                <span class="text-gray-400">$${(order.price * order.amount).toFixed(2)}</span>
            </div>
        `).join('');
    } else {
        sellOrdersEl.innerHTML = '<div class="text-gray-500 text-sm text-center py-4">No sell orders</div>';
    }

    // Display buy orders (bids) - sorted high to low
    if (data.bids && data.bids.length > 0) {
        buyOrdersEl.innerHTML = data.bids.slice(0, 10).map(order => `
            <div class="flex justify-between text-sm p-2 bg-gray-700 rounded order-buy">
                <span class="text-green-400">${parseFloat(order.price).toFixed(2)}</span>
                <span class="text-gray-300">${parseFloat(order.amount).toFixed(2)}</span>
                <span class="text-gray-400">$${(order.price * order.amount).toFixed(2)}</span>
            </div>
        `).join('');
    } else {
        buyOrdersEl.innerHTML = '<div class="text-gray-500 text-sm text-center py-4">No buy orders</div>';
    }

    // Calculate spread
    if (data.asks && data.asks.length > 0 && data.bids && data.bids.length > 0) {
        const lowestAsk = Math.min(...data.asks.map(o => o.price));
        const highestBid = Math.max(...data.bids.map(o => o.price));
        const spread = lowestAsk - highestBid;
        document.getElementById('spread').textContent = `$${spread.toFixed(2)} (${((spread / lowestAsk) * 100).toFixed(2)}%)`;
    } else {
        document.getElementById('spread').textContent = '--';
    }
}

async function loadRecentTrades() {
    try {
        const response = await fetch(`${API_BASE_URL}/trades/recent?limit=20`);
        const data = await response.json();

        if (response.ok && data.trades && data.trades.length > 0) {
            displayRecentTrades(data.trades);
        }
    } catch (error) {
        console.error('Error loading recent trades:', error);
    }
}

function displayRecentTrades(trades) {
    const tradesEl = document.getElementById('recentTrades');

    if (trades.length === 0) {
        tradesEl.innerHTML = '<div class="text-gray-500 text-sm text-center py-4">No recent trades</div>';
        return;
    }

    tradesEl.innerHTML = trades.map(trade => {
        const time = new Date(trade.timestamp).toLocaleTimeString();
        const priceColor = trade.order_type === 'buy' ? 'text-green-400' : 'text-red-400';

        return `
            <div class="flex justify-between text-sm p-2 bg-gray-700 rounded">
                <span class="${priceColor} font-semibold">${parseFloat(trade.price).toFixed(2)}</span>
                <span class="text-gray-300">${parseFloat(trade.amount).toFixed(2)}</span>
                <span class="text-gray-400 text-xs">${time}</span>
            </div>
        `;
    }).join('');
}

// ====== WebSocket Functions ======
function initializeWebSocket() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        console.log('WebSocket already connected');
        return;
    }

    console.log('Connecting to WebSocket...');
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        console.log('WebSocket connected');
        wsReconnectAttempts = 0;
        updateWSStatus('connected');

        // Subscribe to price updates
        ws.send(JSON.stringify({ type: 'subscribe', channel: 'price' }));
        ws.send(JSON.stringify({ type: 'subscribe', channel: 'orderbook' }));
        ws.send(JSON.stringify({ type: 'subscribe', channel: 'trades' }));
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateWSStatus('error');
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        updateWSStatus('disconnected');
        ws = null;

        // Attempt reconnection
        if (authToken && wsReconnectAttempts < maxReconnectAttempts) {
            wsReconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, wsReconnectAttempts), 30000);
            console.log(`Reconnecting in ${delay}ms... (attempt ${wsReconnectAttempts})`);

            reconnectTimeout = setTimeout(() => {
                initializeWebSocket();
            }, delay);
        }
    };
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'price_update':
            updatePriceTicker(data.data);
            break;
        case 'orderbook_update':
            displayOrderBook(data.data);
            break;
        case 'new_trade':
            loadRecentTrades();
            if (authToken) {
                loadUserBalance();
            }
            break;
        case 'trade_executed':
            showToast('Trade executed!', 'success');
            loadOrderBook();
            loadRecentTrades();
            if (authToken) {
                loadUserBalance();
            }
            break;
        default:
            console.log('Unknown message type:', data.type);
    }
}

function updatePriceTicker(priceData) {
    const currentPriceEl = document.getElementById('currentPrice');
    const priceChangeEl = document.getElementById('priceChange');
    const priceHighEl = document.getElementById('priceHigh');
    const priceLowEl = document.getElementById('priceLow');

    if (priceData.current_price) {
        const oldPrice = parseFloat(currentPriceEl.textContent) || 0;
        const newPrice = parseFloat(priceData.current_price);

        currentPriceEl.textContent = `$${newPrice.toFixed(2)}`;

        // Add flash animation
        if (oldPrice !== newPrice) {
            currentPriceEl.classList.add('flash-animation');
            setTimeout(() => currentPriceEl.classList.remove('flash-animation'), 500);
        }
    }

    if (priceData.change_24h !== undefined) {
        const change = parseFloat(priceData.change_24h);
        const changePercent = parseFloat(priceData.change_percent_24h);
        const changeClass = change >= 0 ? 'price-up' : 'price-down';
        const changeSign = change >= 0 ? '+' : '';
        priceChangeEl.textContent = `${changeSign}$${change.toFixed(2)} (${changeSign}${changePercent.toFixed(2)}%)`;
        priceChangeEl.className = `text-2xl font-semibold ${changeClass}`;
    }

    if (priceData.high_24h) {
        priceHighEl.textContent = `$${parseFloat(priceData.high_24h).toFixed(2)}`;
    }

    if (priceData.low_24h) {
        priceLowEl.textContent = `$${parseFloat(priceData.low_24h).toFixed(2)}`;
    }
}

function updateWSStatus(status) {
    const statusEl = document.getElementById('wsStatus');
    const statusTextEl = document.getElementById('wsStatusText');

    switch (status) {
        case 'connected':
            statusEl.className = 'w-3 h-3 rounded-full bg-green-500 mr-2';
            statusTextEl.textContent = 'Connected';
            statusTextEl.className = 'text-sm text-green-400';
            break;
        case 'disconnected':
            statusEl.className = 'w-3 h-3 rounded-full bg-gray-600 mr-2';
            statusTextEl.textContent = 'Disconnected';
            statusTextEl.className = 'text-sm text-gray-400';
            break;
        case 'error':
            statusEl.className = 'w-3 h-3 rounded-full bg-red-500 mr-2';
            statusTextEl.textContent = 'Error';
            statusTextEl.className = 'text-sm text-red-400';
            break;
    }
}

// ====== UI Helper Functions ======
function setupTabListeners() {
    // Navigation
    updateNavigation();
}

function updateNavigation() {
    const navLinks = document.getElementById('navLinks');

    if (authToken && currentUser) {
        navLinks.innerHTML = `
            <span class="text-gray-400">Welcome, <span class="text-blue-400">${currentUser.username}</span></span>
            <button onclick="logout()" class="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg text-sm font-semibold transition">Logout</button>
        `;
    } else {
        navLinks.innerHTML = '<span class="text-gray-400">Please login to start trading</span>';
    }
}

function showAuthSection() {
    document.getElementById('authSection').classList.remove('hidden');
    document.getElementById('tradingSection').classList.add('hidden');
    updateNavigation();
}

function showTradingSection() {
    document.getElementById('authSection').classList.add('hidden');
    document.getElementById('tradingSection').classList.remove('hidden');
    updateNavigation();
}

function showError(elementId, message) {
    const el = document.getElementById(elementId);
    el.textContent = message;
    el.classList.remove('hidden');
}

function hideError(elementId) {
    const el = document.getElementById(elementId);
    el.classList.add('hidden');
}

function showSuccess(elementId, message) {
    const el = document.getElementById(elementId);
    el.textContent = message;
    el.classList.remove('hidden');
    el.classList.remove('bg-red-500/20', 'border-red-500', 'text-red-300');
    el.classList.add('bg-green-500/20', 'border-green-500', 'text-green-300');
}

function setLoading(type, isLoading) {
    if (type === 'buy') {
        document.getElementById('buyBtnText').textContent = isLoading ? 'Processing...' : 'Buy XAI';
        document.getElementById('buySpinner').classList.toggle('hidden', !isLoading);
        document.getElementById('buyForm').querySelectorAll('input, button').forEach(el => {
            el.disabled = isLoading;
        });
    } else if (type === 'sell') {
        document.getElementById('sellBtnText').textContent = isLoading ? 'Processing...' : 'Sell XAI';
        document.getElementById('sellSpinner').classList.toggle('hidden', !isLoading);
        document.getElementById('sellForm').querySelectorAll('input, button').forEach(el => {
            el.disabled = isLoading;
        });
    }
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');

    toastMessage.textContent = message;

    // Set color based on type
    toast.classList.remove('bg-blue-600', 'bg-green-600', 'bg-red-600', 'bg-yellow-600');
    switch (type) {
        case 'success':
            toast.classList.add('bg-green-600');
            break;
        case 'error':
            toast.classList.add('bg-red-600');
            break;
        case 'warning':
            toast.classList.add('bg-yellow-600');
            break;
        default:
            toast.classList.add('bg-blue-600');
    }

    toast.classList.remove('hidden');

    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

// Auto-refresh data periodically
setInterval(() => {
    if (authToken && document.getElementById('tradingSection').classList.contains('hidden') === false) {
        loadUserBalance();
        loadOrderBook();
        loadRecentTrades();
    }
}, 10000); // Refresh every 10 seconds

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (ws) {
        ws.close();
    }
    if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
    }
});
