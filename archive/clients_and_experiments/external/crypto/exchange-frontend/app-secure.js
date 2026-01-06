// AIXN P2P Exchange Frontend Application - Secure Version
import config from './config.js';
import apiClient, { APIError } from './api-client.js';
import WebSocketClient from './websocket-client.js';
import { Sanitizer, SecureStorage, PasswordValidator } from './security.js';

// Global State
let currentUser = null;
let wsClient = null;

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
  console.log('AIXN Exchange initializing...');

  // Check for existing session
  const authToken = SecureStorage.get('authToken');
  const userData = SecureStorage.get('currentUser');

  if (authToken && userData) {
    apiClient.setAuthToken(authToken);
    currentUser = userData;
    showTradingSection();
    initializeWebSocket(authToken);
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

  // Setup session timeout
  setupSessionTimeout();
});

// ====== Authentication Functions ======
function setupAuthListeners() {
  // Tab switching
  document.getElementById('loginTab').addEventListener('click', () => {
    switchAuthTab('login');
  });

  document.getElementById('registerTab').addEventListener('click', () => {
    switchAuthTab('register');
  });

  // Form submissions
  document.getElementById('loginForm').addEventListener('submit', handleLogin);
  document.getElementById('registerForm').addEventListener('submit', handleRegister);

  // Real-time password validation
  const registerPassword = document.getElementById('registerPassword');
  if (registerPassword) {
    registerPassword.addEventListener('input', e => {
      const strength = PasswordValidator.getStrength(e.target.value);
      updatePasswordStrengthIndicator(strength);
    });
  }
}

function switchAuthTab(tab) {
  const loginTab = document.getElementById('loginTab');
  const registerTab = document.getElementById('registerTab');
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');

  if (tab === 'login') {
    loginTab.classList.add('border-blue-500', 'text-blue-400');
    loginTab.classList.remove('text-gray-400');
    registerTab.classList.remove('border-blue-500', 'text-blue-400');
    registerTab.classList.add('text-gray-400');
    loginForm.classList.remove('hidden');
    registerForm.classList.add('hidden');
  } else {
    registerTab.classList.add('border-blue-500', 'text-blue-400');
    registerTab.classList.remove('text-gray-400');
    loginTab.classList.remove('border-blue-500', 'text-blue-400');
    loginTab.classList.add('text-gray-400');
    registerForm.classList.remove('hidden');
    loginForm.classList.add('hidden');
  }

  hideError('authError');
}

async function handleLogin(e) {
  e.preventDefault();
  hideError('authError');

  const username = Sanitizer.username(document.getElementById('loginUsername').value);
  const password = document.getElementById('loginPassword').value;

  if (!username || !password) {
    showError('authError', 'Username and password are required');
    return;
  }

  try {
    const data = await apiClient.login(username, password);

    if (data.token) {
      currentUser = { username: data.username, user_id: data.user_id };
      SecureStorage.set('authToken', data.token, config.SESSION_TIMEOUT);
      SecureStorage.set('currentUser', currentUser, config.SESSION_TIMEOUT);

      showToast('Login successful!', 'success');
      showTradingSection();
      initializeWebSocket(data.token);
      loadUserBalance();
      loadOrderBook();
      loadRecentTrades();
    } else {
      showError('authError', 'Login failed: No token received');
    }
  } catch (error) {
    console.error('Login error:', error);
    if (error instanceof APIError) {
      showError('authError', error.message);
    } else {
      showError('authError', 'Network error. Please check if the server is running.');
    }
  }
}

async function handleRegister(e) {
  e.preventDefault();
  hideError('authError');

  const username = Sanitizer.username(document.getElementById('registerUsername').value);
  const password = document.getElementById('registerPassword').value;
  const passwordConfirm = document.getElementById('registerPasswordConfirm').value;

  // Validation
  if (username.length < 3) {
    showError('authError', 'Username must be at least 3 characters');
    return;
  }

  const passwordValidation = PasswordValidator.validate(password);
  if (!passwordValidation.isValid) {
    showError('authError', passwordValidation.errors[0]);
    return;
  }

  if (password !== passwordConfirm) {
    showError('authError', 'Passwords do not match');
    return;
  }

  try {
    await apiClient.register(username, password);
    showToast('Registration successful! Please login.', 'success');
    switchAuthTab('login');
    document.getElementById('loginUsername').value = username;
  } catch (error) {
    console.error('Registration error:', error);
    if (error instanceof APIError) {
      showError('authError', error.message);
    } else {
      showError('authError', 'Network error. Please check if the server is running.');
    }
  }
}

async function logout() {
  try {
    await apiClient.logout();
  } catch (error) {
    console.error('Logout error:', error);
  }

  currentUser = null;
  SecureStorage.remove('authToken');
  SecureStorage.remove('currentUser');
  apiClient.clearAuthToken();

  if (wsClient) {
    wsClient.close();
    wsClient = null;
  }

  showAuthSection();
  showToast('Logged out successfully', 'info');
}

// ====== Trading Functions ======
function setupTradingListeners() {
  // Tab switching
  document.getElementById('buyTab').addEventListener('click', () => {
    switchTradingTab('buy');
  });

  document.getElementById('sellTab').addEventListener('click', () => {
    switchTradingTab('sell');
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

function switchTradingTab(tab) {
  const buyTab = document.getElementById('buyTab');
  const sellTab = document.getElementById('sellTab');
  const buyForm = document.getElementById('buyForm');
  const sellForm = document.getElementById('sellForm');

  if (tab === 'buy') {
    buyTab.classList.add('border-green-500', 'text-green-400');
    buyTab.classList.remove('text-gray-400');
    sellTab.classList.remove('border-green-500', 'text-green-400');
    sellTab.classList.add('text-gray-400');
    buyForm.classList.remove('hidden');
    sellForm.classList.add('hidden');
  } else {
    sellTab.classList.add('border-green-500', 'text-green-400');
    sellTab.classList.remove('text-gray-400');
    buyTab.classList.remove('border-green-500', 'text-green-400');
    buyTab.classList.add('text-gray-400');
    sellForm.classList.remove('hidden');
    buyForm.classList.add('hidden');
  }

  hideError('tradeError');
  hideError('tradeSuccess');
}

function updateBuyTotal() {
  const price = Sanitizer.number(document.getElementById('buyPrice').value, 0);
  const amount = Sanitizer.number(document.getElementById('buyAmount').value, 0);
  const total = price * amount;
  document.getElementById('buyTotal').textContent = `$${total.toFixed(2)}`;
}

function updateSellTotal() {
  const price = Sanitizer.number(document.getElementById('sellPrice').value, 0);
  const amount = Sanitizer.number(document.getElementById('sellAmount').value, 0);
  const total = price * amount;
  document.getElementById('sellTotal').textContent = `$${total.toFixed(2)}`;
}

async function handleBuyOrder(e) {
  e.preventDefault();
  hideError('tradeError');
  hideError('tradeSuccess');

  const price = Sanitizer.number(document.getElementById('buyPrice').value, 0.01);
  const amount = Sanitizer.number(document.getElementById('buyAmount').value, 0.01);

  if (price <= 0 || amount <= 0) {
    showError('tradeError', 'Price and amount must be greater than 0');
    return;
  }

  setLoading('buy', true);

  try {
    const data = await apiClient.createOrder('buy', price, amount);
    showSuccess('tradeSuccess', `Buy order placed successfully! Order ID: ${data.order_id}`);
    document.getElementById('buyForm').reset();
    updateBuyTotal();
    loadUserBalance();
    loadOrderBook();
  } catch (error) {
    console.error('Buy order error:', error);
    if (error instanceof APIError) {
      if (error.isAuthError()) {
        logout();
        showError('tradeError', 'Session expired. Please login again.');
      } else {
        showError('tradeError', error.message);
      }
    } else {
      showError('tradeError', 'Network error. Please try again.');
    }
  } finally {
    setLoading('buy', false);
  }
}

async function handleSellOrder(e) {
  e.preventDefault();
  hideError('tradeError');
  hideError('tradeSuccess');

  const price = Sanitizer.number(document.getElementById('sellPrice').value, 0.01);
  const amount = Sanitizer.number(document.getElementById('sellAmount').value, 0.01);

  if (price <= 0 || amount <= 0) {
    showError('tradeError', 'Price and amount must be greater than 0');
    return;
  }

  setLoading('sell', true);

  try {
    const data = await apiClient.createOrder('sell', price, amount);
    showSuccess('tradeSuccess', `Sell order placed successfully! Order ID: ${data.order_id}`);
    document.getElementById('sellForm').reset();
    updateSellTotal();
    loadUserBalance();
    loadOrderBook();
  } catch (error) {
    console.error('Sell order error:', error);
    if (error instanceof APIError) {
      if (error.isAuthError()) {
        logout();
        showError('tradeError', 'Session expired. Please login again.');
      } else {
        showError('tradeError', error.message);
      }
    } else {
      showError('tradeError', 'Network error. Please try again.');
    }
  } finally {
    setLoading('sell', false);
  }
}

// ====== Data Loading Functions ======
async function loadUserBalance() {
  try {
    const data = await apiClient.getBalance();
    const aixnBalance = Sanitizer.number(data.aixn_balance, 0);
    const usdBalance = Sanitizer.number(data.usd_balance, 0);

    document.getElementById('aixnBalance').textContent = aixnBalance.toFixed(2);
    document.getElementById('usdBalance').textContent = `$${usdBalance.toFixed(2)}`;
  } catch (error) {
    console.error('Error loading balance:', error);
    if (error instanceof APIError && error.isAuthError()) {
      logout();
    }
  }
}

async function loadOrderBook() {
  try {
    const data = await apiClient.getOrderBook();
    displayOrderBook(data);
  } catch (error) {
    console.error('Error loading order book:', error);
  }
}

function displayOrderBook(data) {
  const sellOrdersEl = document.getElementById('sellOrders');
  const buyOrdersEl = document.getElementById('buyOrders');

  // Display sell orders (asks)
  if (data.asks && data.asks.length > 0) {
    const sortedAsks = [...data.asks].sort((a, b) => b.price - a.price);
    sellOrdersEl.innerHTML = sortedAsks
      .slice(0, 10)
      .map(order => {
        const price = Sanitizer.number(order.price, 0);
        const amount = Sanitizer.number(order.amount, 0);
        return `
        <div class="flex justify-between text-sm p-2 bg-gray-700 rounded order-sell">
          <span class="text-red-400">${price.toFixed(2)}</span>
          <span class="text-gray-300">${amount.toFixed(2)}</span>
          <span class="text-gray-400">$${(price * amount).toFixed(2)}</span>
        </div>
      `;
      })
      .join('');
  } else {
    sellOrdersEl.innerHTML =
      '<div class="text-gray-500 text-sm text-center py-4">No sell orders</div>';
  }

  // Display buy orders (bids)
  if (data.bids && data.bids.length > 0) {
    buyOrdersEl.innerHTML = data.bids
      .slice(0, 10)
      .map(order => {
        const price = Sanitizer.number(order.price, 0);
        const amount = Sanitizer.number(order.amount, 0);
        return `
        <div class="flex justify-between text-sm p-2 bg-gray-700 rounded order-buy">
          <span class="text-green-400">${price.toFixed(2)}</span>
          <span class="text-gray-300">${amount.toFixed(2)}</span>
          <span class="text-gray-400">$${(price * amount).toFixed(2)}</span>
        </div>
      `;
      })
      .join('');
  } else {
    buyOrdersEl.innerHTML =
      '<div class="text-gray-500 text-sm text-center py-4">No buy orders</div>';
  }

  // Calculate spread
  if (data.asks && data.asks.length > 0 && data.bids && data.bids.length > 0) {
    const lowestAsk = Math.min(...data.asks.map(o => Sanitizer.number(o.price, 0)));
    const highestBid = Math.max(...data.bids.map(o => Sanitizer.number(o.price, 0)));
    const spread = lowestAsk - highestBid;
    document.getElementById('spread').textContent =
      `$${spread.toFixed(2)} (${((spread / lowestAsk) * 100).toFixed(2)}%)`;
  } else {
    document.getElementById('spread').textContent = '--';
  }
}

async function loadRecentTrades() {
  try {
    const data = await apiClient.getRecentTrades(20);
    if (data.trades && data.trades.length > 0) {
      displayRecentTrades(data.trades);
    }
  } catch (error) {
    console.error('Error loading recent trades:', error);
  }
}

function displayRecentTrades(trades) {
  const tradesEl = document.getElementById('recentTrades');

  if (trades.length === 0) {
    tradesEl.innerHTML =
      '<div class="text-gray-500 text-sm text-center py-4">No recent trades</div>';
    return;
  }

  tradesEl.innerHTML = trades
    .map(trade => {
      const time = new Date(trade.timestamp).toLocaleTimeString();
      const priceColor = trade.order_type === 'buy' ? 'text-green-400' : 'text-red-400';
      const price = Sanitizer.number(trade.price, 0);
      const amount = Sanitizer.number(trade.amount, 0);

      return `
      <div class="flex justify-between text-sm p-2 bg-gray-700 rounded">
        <span class="${priceColor} font-semibold">${price.toFixed(2)}</span>
        <span class="text-gray-300">${amount.toFixed(2)}</span>
        <span class="text-gray-400 text-xs">${Sanitizer.html(time)}</span>
      </div>
    `;
    })
    .join('');
}

// ====== WebSocket Functions ======
function initializeWebSocket(authToken) {
  if (wsClient && wsClient.isConnected()) {
    console.log('WebSocket already connected');
    return;
  }

  console.log('Connecting to WebSocket...');
  wsClient = new WebSocketClient();

  // Setup connection status listener
  wsClient.onConnectionChange(status => {
    updateWSStatus(status);
  });

  // Setup message handlers
  wsClient.on('price_update', data => {
    updatePriceTicker(data);
  });

  wsClient.on('orderbook_update', data => {
    displayOrderBook(data);
  });

  wsClient.on('new_trade', () => {
    loadRecentTrades();
    if (currentUser) {
      loadUserBalance();
    }
  });

  wsClient.on('trade_executed', () => {
    showToast('Trade executed!', 'success');
    loadOrderBook();
    loadRecentTrades();
    if (currentUser) {
      loadUserBalance();
    }
  });

  // Connect
  wsClient.connect(authToken);

  // Subscribe to channels
  setTimeout(() => {
    if (wsClient.isConnected()) {
      wsClient.subscribe('price');
      wsClient.subscribe('orderbook');
      wsClient.subscribe('trades');
    }
  }, 1000);
}

function updatePriceTicker(priceData) {
  const currentPriceEl = document.getElementById('currentPrice');
  const priceChangeEl = document.getElementById('priceChange');
  const priceHighEl = document.getElementById('priceHigh');
  const priceLowEl = document.getElementById('priceLow');

  if (priceData.current_price) {
    const oldPrice = parseFloat(currentPriceEl.textContent.replace('$', '')) || 0;
    const newPrice = Sanitizer.number(priceData.current_price, 0);

    currentPriceEl.textContent = `$${newPrice.toFixed(2)}`;

    if (oldPrice !== newPrice) {
      currentPriceEl.classList.add('flash-animation');
      setTimeout(() => currentPriceEl.classList.remove('flash-animation'), 500);
    }
  }

  if (priceData.change_24h !== undefined) {
    const change = Sanitizer.number(priceData.change_24h, 0);
    const changePercent = Sanitizer.number(priceData.change_percent_24h, 0);
    const changeClass = change >= 0 ? 'price-up' : 'price-down';
    const changeSign = change >= 0 ? '+' : '';
    priceChangeEl.textContent = `${changeSign}$${change.toFixed(2)} (${changeSign}${changePercent.toFixed(2)}%)`;
    priceChangeEl.className = `text-2xl font-semibold ${changeClass}`;
  }

  if (priceData.high_24h) {
    priceHighEl.textContent = `$${Sanitizer.number(priceData.high_24h, 0).toFixed(2)}`;
  }

  if (priceData.low_24h) {
    priceLowEl.textContent = `$${Sanitizer.number(priceData.low_24h, 0).toFixed(2)}`;
  }
}

function updateWSStatus(status) {
  const statusEl = document.getElementById('wsStatus');
  const statusTextEl = document.getElementById('wsStatusText');

  const statusConfig = {
    connected: {
      color: 'bg-green-500',
      text: 'Connected',
      textColor: 'text-green-400',
    },
    disconnected: {
      color: 'bg-gray-600',
      text: 'Disconnected',
      textColor: 'text-gray-400',
    },
    reconnecting: {
      color: 'bg-yellow-500',
      text: 'Reconnecting...',
      textColor: 'text-yellow-400',
    },
    error: {
      color: 'bg-red-500',
      text: 'Error',
      textColor: 'text-red-400',
    },
    failed: {
      color: 'bg-red-600',
      text: 'Connection Failed',
      textColor: 'text-red-400',
    },
  };

  const config = statusConfig[status] || statusConfig.disconnected;
  statusEl.className = `w-3 h-3 rounded-full ${config.color} mr-2`;
  statusTextEl.textContent = config.text;
  statusTextEl.className = `text-sm ${config.textColor}`;
}

// ====== UI Helper Functions ======
function setupTabListeners() {
  updateNavigation();
}

function updateNavigation() {
  const navLinks = document.getElementById('navLinks');

  if (currentUser) {
    const username = Sanitizer.html(currentUser.username);
    navLinks.innerHTML = `
      <span class="text-gray-400">Welcome, <span class="text-blue-400">${username}</span></span>
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
  el.textContent = Sanitizer.html(message);
  el.classList.remove('hidden');
}

function hideError(elementId) {
  const el = document.getElementById(elementId);
  el.classList.add('hidden');
}

function showSuccess(elementId, message) {
  const el = document.getElementById(elementId);
  el.textContent = Sanitizer.html(message);
  el.classList.remove('hidden');
  el.classList.remove('bg-red-500/20', 'border-red-500', 'text-red-300');
  el.classList.add('bg-green-500/20', 'border-green-500', 'text-green-300');
}

function setLoading(type, isLoading) {
  const formId = type === 'buy' ? 'buyForm' : 'sellForm';
  const btnTextId = type === 'buy' ? 'buyBtnText' : 'sellBtnText';
  const spinnerId = type === 'buy' ? 'buySpinner' : 'sellSpinner';

  document.getElementById(btnTextId).textContent = isLoading
    ? 'Processing...'
    : type === 'buy'
      ? 'Buy AIXN'
      : 'Sell AIXN';
  document.getElementById(spinnerId).classList.toggle('hidden', !isLoading);
  document
    .getElementById(formId)
    .querySelectorAll('input, button')
    .forEach(el => {
      el.disabled = isLoading;
    });
}

function showToast(message, type = 'info') {
  const toast = document.getElementById('toast');
  const toastMessage = document.getElementById('toastMessage');

  toastMessage.textContent = Sanitizer.html(message);

  toast.classList.remove('bg-blue-600', 'bg-green-600', 'bg-red-600', 'bg-yellow-600');
  const colorMap = {
    success: 'bg-green-600',
    error: 'bg-red-600',
    warning: 'bg-yellow-600',
    info: 'bg-blue-600',
  };
  toast.classList.add(colorMap[type] || 'bg-blue-600');

  toast.classList.remove('hidden');
  setTimeout(() => {
    toast.classList.add('hidden');
  }, 3000);
}

function updatePasswordStrengthIndicator(strength) {
  // This function can be enhanced with a visual indicator
  console.log('Password strength:', strength);
}

function setupSessionTimeout() {
  let timeoutId;

  const resetTimeout = () => {
    if (timeoutId) {clearTimeout(timeoutId);}

    if (currentUser) {
      timeoutId = setTimeout(() => {
        showToast('Session expired due to inactivity', 'warning');
        logout();
      }, config.SESSION_TIMEOUT);
    }
  };

  // Reset timeout on user activity
  ['mousedown', 'keydown', 'scroll', 'touchstart'].forEach(event => {
    document.addEventListener(event, resetTimeout, true);
  });

  resetTimeout();
}

// Auto-refresh data periodically
setInterval(() => {
  if (currentUser && !document.getElementById('tradingSection').classList.contains('hidden')) {
    loadUserBalance();
    loadOrderBook();
    loadRecentTrades();
  }
}, config.AUTO_REFRESH_INTERVAL);

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  if (wsClient) {
    wsClient.close();
  }
});

// Make logout function available globally
window.logout = logout;
