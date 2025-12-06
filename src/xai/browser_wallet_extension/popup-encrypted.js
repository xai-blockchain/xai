/**
 * XAI Browser Wallet - Main UI Controller (Encrypted Version)
 *
 * This is a drop-in replacement for popup.js that integrates secure storage.
 * All sensitive data (session secrets, API keys, wallet addresses) is encrypted.
 *
 * TO ACTIVATE: Rename this file to popup.js and rename original to popup-plaintext.js
 */

const API_KEY = 'apiHost';
const SESSION_TOKEN_KEY = 'walletSessionToken';
const SESSION_SECRET_KEY = 'walletSessionSecret';
const SESSION_ADDRESS_KEY = 'walletSessionAddress';
const HKDF_INFO = new TextEncoder().encode('walletconnect-trade');

function bufferToHex(buffer) {
  return Array.from(new Uint8Array(buffer))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}

function hexToBytes(hex) {
  const bytes = [];
  for (let c = 0; c < hex.length; c += 2) {
    bytes.push(parseInt(hex.substr(c, 2), 16));
  }
  return new Uint8Array(bytes);
}

function bufferToBase64(buffer) {
  return btoa(String.fromCharCode(...new Uint8Array(buffer)));
}

function base64ToBytes(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function stableStringify(value) {
  if (value === null) return 'null';
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(',')}]`;
  }
  if (typeof value === 'object') {
    const keys = Object.keys(value).sort();
    return `{${keys
      .map((key) => `"${key}":${stableStringify(value[key])}`)
      .join(',')}}`;
  }
  return JSON.stringify(value);
}

function $(selector) {
  return document.querySelector(selector);
}

async function presentSigningPreview(payload, payloadStr) {
  const modal = $('#signingPreview');
  if (!modal) {
    return true;
  }

  const previewEl = $('#signingPayloadPreview');
  const hashEl = $('#signingPayloadHash');
  const confirmBtn = $('#confirmSigning');
  const cancelBtn = $('#cancelSigning');
  const acknowledge = $('#signingAcknowledge');

  previewEl.textContent = JSON.stringify(payload, null, 2);
  acknowledge.checked = false;
  confirmBtn.disabled = true;
  hashEl.textContent = 'calculating…';
  modal.classList.remove('hidden');
  modal.setAttribute('aria-hidden', 'false');

  const encoder = new TextEncoder();
  const digestBuffer = await crypto.subtle.digest('SHA-256', encoder.encode(payloadStr));
  hashEl.textContent = bufferToHex(digestBuffer);

  return new Promise((resolve) => {
    const onAcknowledge = () => {
      confirmBtn.disabled = !acknowledge.checked;
    };

    const cleanup = () => {
      modal.classList.add('hidden');
      modal.setAttribute('aria-hidden', 'true');
      confirmBtn.removeEventListener('click', onConfirm);
      cancelBtn.removeEventListener('click', onCancel);
      acknowledge.removeEventListener('change', onAcknowledge);
      document.removeEventListener('keydown', onEsc);
    };

    const onConfirm = () => {
      cleanup();
      resolve(true);
    };

    const onCancel = () => {
      cleanup();
      resolve(false);
    };

    const onEsc = (event) => {
      if (event.key === 'Escape') {
        cleanup();
        resolve(false);
      }
    };

    acknowledge.addEventListener('change', onAcknowledge);
    confirmBtn.addEventListener('click', onConfirm);
    cancelBtn.addEventListener('click', onCancel);
    document.addEventListener('keydown', onEsc);
  });
}

/**
 * Sign payload with ECDSA (implemented in original popup.js)
 * Using HMAC as fallback until full ECDSA implementation is available.
 */
async function signPayload(payloadStr, secretHex) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    hexToBytes(secretHex),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const sig = await crypto.subtle.sign('HMAC', key, encoder.encode(payloadStr));
  return bufferToHex(sig);
}

// ====================
// SECURE STORAGE INTEGRATION
// ====================

/**
 * Save session data (encrypted).
 */
async function saveSession(token, secret, address) {
  try {
    await secureStorage.set(SESSION_TOKEN_KEY, token);
    await secureStorage.set(SESSION_SECRET_KEY, secret);
    await secureStorage.set(SESSION_ADDRESS_KEY, address);
  } catch (error) {
    console.error('Failed to save session:', error);
    if (secureStorage.isStorageLocked()) {
      const unlocked = await promptUnlock();
      if (unlocked) {
        await saveSession(token, secret, address);
      }
    } else {
      throw error;
    }
  }
}

/**
 * Get session data (decrypted).
 */
async function getSession() {
  try {
    const sessionToken = await secureStorage.get(SESSION_TOKEN_KEY);
    const sessionSecret = await secureStorage.get(SESSION_SECRET_KEY);
    const walletAddress = await secureStorage.get(SESSION_ADDRESS_KEY);

    return {
      sessionToken,
      sessionSecret,
      walletAddress
    };
  } catch (error) {
    console.error('Failed to get session:', error);
    if (secureStorage.isStorageLocked()) {
      const unlocked = await promptUnlock();
      if (unlocked) {
        return await getSession();
      }
    }
    return {
      sessionToken: null,
      sessionSecret: null,
      walletAddress: null
    };
  }
}

async function registerSession(address) {
  const host = await getApiHost();
  const response = await fetch(`${host}/wallet-trades/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ wallet_address: address })
  });
  const payload = await response.json();
  if (payload.success) {
    await saveSession(
      payload.session_token,
      payload.session_secret,
      address
    );
    return {
      sessionToken: payload.session_token,
      sessionSecret: payload.session_secret,
      walletAddress: address
    };
  }
  return null;
}

async function beginWalletConnectHandshake(address) {
  const host = await getApiHost();
  const response = await fetch(`${host}/wallet-trades/wc/handshake`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ wallet_address: address })
  });
  const payload = await response.json();
  return payload.success ? payload : null;
}

async function confirmWalletConnectHandshake(address, handshake) {
  const host = await getApiHost();
  const clientKeyPair = await crypto.subtle.generateKey(
    { name: 'ECDH', namedCurve: 'P-256' },
    true,
    ['deriveBits']
  );
  const clientPublicRaw = await crypto.subtle.exportKey('raw', clientKeyPair.publicKey);
  const serverPublicBytes = base64ToBytes(handshake.server_public);
  const serverKey = await crypto.subtle.importKey(
    'raw',
    serverPublicBytes,
    { name: 'ECDH', namedCurve: 'P-256' },
    false,
    []
  );
  const sharedBits = await crypto.subtle.deriveBits(
    { name: 'ECDH', public: serverKey },
    clientKeyPair.privateKey,
    256
  );
  const hkdfKey = await crypto.subtle.importKey(
    'raw',
    sharedBits,
    { name: 'HKDF', hash: 'SHA-256' },
    false,
    ['deriveBits']
  );
  const derivedBits = await crypto.subtle.deriveBits(
    {
      name: 'HKDF',
      hash: 'SHA-256',
      salt: new TextEncoder().encode(handshake.handshake_id),
      info: HKDF_INFO
    },
    hkdfKey,
    256
  );
  const derivedHex = bufferToHex(derivedBits);
  const clientPublicBase64 = bufferToBase64(clientPublicRaw);
  const confirmationPayload = {
    handshake_id: handshake.handshake_id,
    wallet_address: address,
    client_public: clientPublicBase64
  };

  const payloadStr = stableStringify(confirmationPayload);
  const approved = await presentSigningPreview(confirmationPayload, payloadStr);
  if (!approved) {
    return null;
  }

  const response = await fetch(`${host}/wallet-trades/wc/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: payloadStr
  });
  const payload = await response.json();
  if (!payload.success) return null;
  await saveSession(payload.session_token, derivedHex, address);
  return { sessionToken: payload.session_token, sessionSecret: derivedHex, walletAddress: address };
}

async function ensureSession() {
  const address = $('#walletAddress').value.trim();
  if (!address) return null;
  const session = await getSession();
  if (
    session &&
    session.walletAddress === address &&
    session.sessionToken &&
    session.sessionSecret
  ) {
    return session;
  }
  return registerSession(address);
}

/**
 * Get API host (decrypted).
 */
async function getApiHost() {
  try {
    const host = await secureStorage.get(API_KEY);
    return host || 'http://localhost:8545';
  } catch (error) {
    console.error('Failed to get API host:', error);
    return 'http://localhost:8545';
  }
}

/**
 * Set API host (encrypted).
 */
async function setApiHost(host) {
  try {
    await secureStorage.set(API_KEY, host);
  } catch (error) {
    console.error('Failed to set API host:', error);
    if (secureStorage.isStorageLocked()) {
      const unlocked = await promptUnlock();
      if (unlocked) {
        await setApiHost(host);
      }
    }
  }
}

function $(selector) {
  return document.querySelector(selector);
}

async function updateMiningStatus() {
  const host = await getApiHost();
  const address = $('#walletAddress').value.trim();
  if (!address) {
    $('#miningStatus').textContent = 'Status: wallet address required';
    return;
  }

  const statusRes = await fetch(`${host}/mining/status?address=${encodeURIComponent(address)}`);
  if (!statusRes.ok) {
    $('#miningStatus').textContent = 'Status: unable to reach miner API';
    return;
  }

  const data = await statusRes.json();
  $('#miningStatus').textContent = data.is_mining
    ? `Status: mining (${data.intensity || 'N/A'})`
    : 'Status: idle';
  $('#miningMeta').textContent = data.is_mining
    ? `Hashrate: ${data.hashrate}, Blocks: ${data.blocks_mined_today}`
    : 'Mining stopped';
}

async function startMining() {
  const host = await getApiHost();
  const address = $('#walletAddress').value.trim();
  if (!address) {
    alert('Enter a wallet address first');
    return;
  }

  await fetch(`${host}/mining/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ miner_address: address, intensity: 'medium' })
  });
  await updateMiningStatus();
  await refreshMinerStats();
}

async function stopMining() {
  const host = await getApiHost();
  const address = $('#walletAddress').value.trim();
  if (!address) return;

  await fetch(`${host}/mining/stop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ miner_address: address })
  });
  await updateMiningStatus();
  await refreshMinerStats();
}

async function refreshOrders() {
  const host = await getApiHost();
  const res = await fetch(`${host}/wallet-trades/orders`);
  const data = await res.json();
  const list = $('#ordersList');
  if (data?.orders?.length) {
    list.innerHTML = data.orders
      .map(
        (order) => `
        <div class="entry">
          <strong>${order.token_offered}</strong> → ${order.token_requested}
          <br />
          ${order.amount_offered} @ ${order.price} | status: ${order.status}
        </div>`
      )
      .join('');
  } else {
    list.innerHTML = '<div class="list-placeholder">No open orders</div>';
  }
}

async function refreshMatches() {
  const host = await getApiHost();
  const res = await fetch(`${host}/wallet-trades/matches`);
  const data = await res.json();
  const list = $('#matchesList');
  if (data?.matches?.length) {
    list.innerHTML = data.matches
      .map(
        (match) => `
        <div class="entry">
          ${match.maker_order_id} ↔ ${match.taker_order_id}
          <br />
          status: ${match.status} | expires @ ${new Date(match.expires_at * 1000).toLocaleTimeString()}
        </div>`
      )
      .join('');
  } else {
    list.innerHTML = '<div class="list-placeholder">No matches</div>';
  }
}

async function refreshTradeHistory() {
  const host = await getApiHost();
  const res = await fetch(`${host}/wallet-trades/history`);
  if (!res.ok) {
    $('#tradeHistory').innerHTML = '<div class="list-placeholder">Unable to fetch history</div>';
    return;
  }
  const data = await res.json();
  const container = $('#tradeHistory');
  if (data?.history?.length) {
    container.innerHTML = data.history
      .slice(-5)
      .reverse()
      .map(
        (entry) => `
        <div class="entry">
          ${entry.type.toUpperCase()} @ block ${entry.payload.block_height || 'soon'}
          <br />
          Fee: ${entry.payload.fee || 0} | transfers: ${entry.payload.transfers?.length || 0}
        </div>`
      )
      .join('');
  } else {
    container.innerHTML = '<div class="list-placeholder">No trade history found</div>';
  }
}

async function refreshMinerStats() {
  const host = await getApiHost();
  const address = $('#walletAddress').value.trim();
  if (!address) {
    $('#minerStats').textContent = 'Enter address for miner stats';
    return;
  }
  const res = await fetch(`${host}/mining/status?address=${encodeURIComponent(address)}`);
  if (!res.ok) {
    $('#minerStats').textContent = 'Unable to fetch miner status';
    return;
  }
  const data = await res.json();
  $('#minerStats').textContent = data.is_mining
    ? `Hashrate: ${data.hashrate || 0} MH/s | Blocks today: ${data.blocks_mined_today}`
    : 'Miner idle';
  $('#minerHistory').textContent = data.is_mining
    ? `Last shares: ${data.shares_accepted || 0}, uptime: ${Math.round(data.uptime || 0)}s`
    : 'Idle';
}

async function submitOrder(event) {
  event.preventDefault();
  const form = event.target;
  const host = await getApiHost();
  const session = await ensureSession();
  if (!session) {
    $('#tradeMessage').textContent = 'Session registration failed';
    return;
  }
  const formData = new FormData(form);
  const payload = {
    maker_address: $('#walletAddress').value.trim(),
    maker_public_key: '',
    token_offered: formData.get('tokenOffered'),
    amount_offered: parseFloat(formData.get('amountOffered')),
    token_requested: formData.get('tokenRequested'),
    amount_requested: parseFloat(formData.get('amountRequested')),
    price: parseFloat(formData.get('amountRequested')) / parseFloat(formData.get('amountOffered')),
    order_type: formData.get('orderType'),
    expiry: Math.floor(Date.now() / 1000) + 3600,
    nonce: Date.now(),
    session_token: session.sessionToken
  };

  const payloadStr = stableStringify(payload);
  const approved = await presentSigningPreview(payload, payloadStr);
  if (!approved) {
    $('#tradeMessage').textContent = 'Signing cancelled by user.';
    return;
  }
  const signature = await signPayload(payloadStr, session.sessionSecret);
  payload.signature = signature;

  const res = await fetch(`${host}/wallet-trades/orders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  $('#tradeMessage').textContent = data.message || 'Order request sent';
  await refreshOrders();
  if (data.match) {
    await refreshMatches();
  }
  refreshTradeHistory();
}

function setAiStatus(message, isError = false) {
  const aiStatus = $('#aiStatus');
  aiStatus.textContent = message;
  aiStatus.classList.toggle('error', isError);
}

function setKeyDeletionNotice(message) {
  $('#aiKeyDeleted').textContent = message;
}

function clearAiKeyField() {
  const keyInput = $('#aiApiKey');
  keyInput.value = '';
  setKeyDeletionNotice('Your AI API key has been deleted from this wallet.');
}

async function runPersonalAiSwap() {
  const host = await getApiHost();
  const userAddress = $('#walletAddress').value.trim();
  const mode = $('#aiKeyMode').value;
  let apiKey = $('#aiApiKey').value.trim();
  const provider = $('#aiProvider').value.trim() || 'anthropic';
  const model = $('#aiModel').value.trim() || 'claude-opus-4';
  const swapDetails = {
    from_coin: $('#aiFromCoin').value.trim() || 'XAI',
    to_coin: $('#aiToCoin').value.trim() || 'ADA',
    amount: parseFloat($('#aiAmount').value) || 0,
    recipient_address: $('#aiRecipient').value.trim() || userAddress
  };

  if (!userAddress) {
    setAiStatus('Provide your wallet address before using the assistant', true);
    return;
  }
  if (mode === 'session') {
    apiKey = apiKey || (await getStoredAiKey());
  }
  if (!apiKey) {
    setAiStatus('Enter your AI API key for this session', true);
    return;
  }
  if (mode === 'session') {
    await storeAiKey(apiKey);
  }
  if (!swapDetails.amount) {
    setAiStatus('Enter a swap amount before running the assistant', true);
    return;
  }

  setAiStatus('Calling AI assistant…');

  try {
    const res = await fetch(`${host}/personal-ai/atomic-swap`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Address': userAddress,
        'X-AI-Provider': provider,
        'X-AI-Model': model,
        'X-User-API-Key': apiKey
      },
      body: JSON.stringify({ swap_details: swapDetails })
    });
    const data = await res.json();
    if (data.success) {
      const fee = data.swap_transaction?.fee || 'N/A';
      setAiStatus(`AI swap prepared (fee: ${fee}). Key deleted.`);
      setKeyDeletionNotice('AI session complete. API key removed from this extension.');
    } else {
      throw new Error(data.message || 'Personal AI request failed');
    }
  } catch (error) {
    setAiStatus(`AI assistant error: ${error.message}`, true);
  } finally {
    if (mode === 'temporary' || mode === 'external') {
      clearAiKeyField();
    } else if (mode === 'session') {
      setKeyDeletionNotice('AI session complete. Stored key remains until you click Clear Key.');
    }
  }
}

/**
 * Get stored AI API key (decrypted).
 */
async function getStoredAiKey() {
  try {
    return await secureStorage.get('personalAiApiKey') || '';
  } catch (error) {
    console.error('Failed to get AI key:', error);
    if (secureStorage.isStorageLocked()) {
      const unlocked = await promptUnlock();
      if (unlocked) {
        return await getStoredAiKey();
      }
    }
    return '';
  }
}

/**
 * Store AI API key (encrypted).
 */
async function storeAiKey(value) {
  try {
    await secureStorage.set('personalAiApiKey', value);
  } catch (error) {
    console.error('Failed to store AI key:', error);
    if (secureStorage.isStorageLocked()) {
      const unlocked = await promptUnlock();
      if (unlocked) {
        await storeAiKey(value);
      }
    }
  }
}

/**
 * Clear stored AI API key.
 */
async function clearStoredAiKey() {
  try {
    await secureStorage.remove('personalAiApiKey');
    clearAiKeyField();
    setKeyDeletionNotice('Stored Personal AI key removed.');
  } catch (error) {
    console.error('Failed to clear AI key:', error);
  }
}

// ====================
// SECURITY UI FUNCTIONS
// ====================

/**
 * Prompts user to unlock storage.
 * Shows password modal and waits for unlock.
 */
async function promptUnlock() {
  return new Promise((resolve) => {
    const modal = $('#unlockModal');
    modal.style.display = 'block';

    const unlockBtn = $('#unlockBtn');
    const cancelBtn = $('#unlockCancelBtn');

    const handleUnlock = async () => {
      const password = $('#unlockPassword').value;
      const success = await secureStorage.unlock(password);

      if (success) {
        $('#unlockPassword').value = '';
        modal.style.display = 'none';
        $('#unlockError').textContent = '';
        updateLockStatus();
        resolve(true);
      } else {
        $('#unlockError').textContent = 'Incorrect password';
      }
    };

    const handleCancel = () => {
      $('#unlockPassword').value = '';
      modal.style.display = 'none';
      $('#unlockError').textContent = '';
      resolve(false);
    };

    unlockBtn.onclick = handleUnlock;
    cancelBtn.onclick = handleCancel;

    // Allow Enter key to unlock
    $('#unlockPassword').onkeypress = (e) => {
      if (e.key === 'Enter') {
        handleUnlock();
      }
    };
  });
}

/**
 * Prompts user to set up encryption (first time).
 */
async function promptSetupEncryption() {
  return new Promise((resolve) => {
    const modal = $('#setupEncryptionModal');
    modal.style.display = 'block';

    const setupBtn = $('#setupEncryptionBtn');
    const skipBtn = $('#skipEncryptionBtn');

    const handleSetup = async () => {
      const password = $('#setupPassword').value;
      const confirmPassword = $('#setupPasswordConfirm').value;

      if (password !== confirmPassword) {
        $('#setupError').textContent = 'Passwords do not match';
        return;
      }

      if (password.length < 8) {
        $('#setupError').textContent = 'Password must be at least 8 characters';
        return;
      }

      try {
        await secureStorage.enableEncryption(password);
        $('#setupPassword').value = '';
        $('#setupPasswordConfirm').value = '';
        modal.style.display = 'none';
        $('#setupError').textContent = '';
        $('#encryptionStatus').textContent = 'Encryption: Enabled';
        $('#encryptionStatus').classList.add('encryption-enabled');
        updateLockStatus();
        resolve(true);
      } catch (error) {
        $('#setupError').textContent = `Setup failed: ${error.message}`;
      }
    };

    const handleSkip = () => {
      $('#setupPassword').value = '';
      $('#setupPasswordConfirm').value = '';
      modal.style.display = 'none';
      $('#setupError').textContent = '';
      resolve(false);
    };

    setupBtn.onclick = handleSetup;
    skipBtn.onclick = handleSkip;
  });
}

/**
 * Initializes security features.
 */
async function initializeSecurity() {
  await secureStorage.initialize();

  const encryptionEnabled = secureStorage.encryptionEnabled;

  if (encryptionEnabled) {
    $('#encryptionStatus').textContent = 'Encryption: Enabled (Locked)';
    $('#encryptionStatus').classList.add('encryption-enabled');

    // Prompt for password immediately
    await promptUnlock();
  } else {
    $('#encryptionStatus').textContent = 'Encryption: Disabled';
    $('#encryptionStatus').classList.remove('encryption-enabled');

    // Offer to enable encryption
    const shouldSetup = confirm(
      'WARNING: Your wallet data is not encrypted.\n\n' +
      'Session secrets, private keys, and API keys are stored in plaintext.\n\n' +
      'Enable encryption now for better security?'
    );

    if (shouldSetup) {
      await promptSetupEncryption();
    }
  }

  // Update lock status display
  updateLockStatus();
}

/**
 * Updates lock status indicator.
 */
function updateLockStatus() {
  const statusElement = $('#lockStatus');
  if (!statusElement) return;

  if (secureStorage.isStorageLocked()) {
    statusElement.textContent = '🔒 Locked';
    statusElement.classList.add('locked');
    statusElement.classList.remove('unlocked');
  } else {
    statusElement.textContent = '🔓 Unlocked';
    statusElement.classList.add('unlocked');
    statusElement.classList.remove('locked');
  }
}

/**
 * Manually locks storage.
 */
function lockStorage() {
  secureStorage.lock();
  updateLockStatus();
  alert('Wallet locked. You will need to enter your password again.');
}

// ====================
// INITIALIZATION
// ====================

function bindActions() {
  $('#startMining').addEventListener('click', startMining);
  $('#stopMining').addEventListener('click', stopMining);
  $('#refreshOrders').addEventListener('click', refreshOrders);
  $('#refreshMatches').addEventListener('click', refreshMatches);
  $('#orderForm').addEventListener('submit', submitOrder);
  $('#runAiSwap').addEventListener('click', runPersonalAiSwap);
  $('#clearAiKey').addEventListener('click', clearStoredAiKey);

  // Security actions
  const lockBtn = $('#lockWallet');
  if (lockBtn) {
    lockBtn.addEventListener('click', lockStorage);
  }

  $('#apiHost').addEventListener('change', (event) => {
    setApiHost(event.target.value.trim());
  });
}

async function restoreSettings() {
  try {
    const walletAddress = await secureStorage.get('walletAddress');
    if (walletAddress) {
      $('#walletAddress').value = walletAddress;
    }

    const apiHost = await getApiHost();
    if (apiHost) {
      $('#apiHost').value = apiHost;
    }
  } catch (error) {
    console.error('Failed to restore settings:', error);
  }

  $('#walletAddress').addEventListener('change', async (event) => {
    try {
      await secureStorage.set('walletAddress', event.target.value.trim());
      await ensureSession();
    } catch (error) {
      console.error('Failed to save wallet address:', error);
      if (secureStorage.isStorageLocked()) {
        await promptUnlock();
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  // Initialize security first
  await initializeSecurity();

  // Then initialize rest of the app
  bindActions();
  await restoreSettings();
  $('#apiHost').value = await getApiHost();

  // Only continue if unlocked or encryption not enabled
  if (!secureStorage.encryptionEnabled || !secureStorage.isStorageLocked()) {
    await ensureSession();
    refreshOrders();
    refreshMatches();
    updateMiningStatus();
    refreshMinerStats();
    refreshTradeHistory();
  }
});
