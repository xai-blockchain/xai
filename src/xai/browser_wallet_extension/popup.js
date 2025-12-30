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

/**
 * Sign a transaction payload using ECDSA with secp256k1.
 *
 * SECURITY ARCHITECTURE:
 * =====================
 * This uses CLIENT-SIDE signing with noble-secp256k1 library.
 * Private keys NEVER leave the browser - all signing happens locally.
 *
 * Key differences from previous implementation:
 * - OLD: Private key sent to backend (INSECURE)
 * - NEW: Private key stays in browser, signing done client-side (SECURE)
 *
 * IMPLEMENTATION:
 * ==============
 * Uses @noble/secp256k1 for pure JavaScript secp256k1 ECDSA signing.
 * This is an audited, zero-dependency implementation.
 *
 * Flow:
 * 1. Hash payload with SHA-256 (deterministic, sorted JSON)
 * 2. Sign hash locally using noble-secp256k1
 * 3. Normalize signature to low-S form (BIP-62)
 * 4. Return signature for inclusion in transaction
 *
 * Security Note:
 * - Private key NEVER leaves the browser
 * - No network requests during signing
 * - Signatures use low-S normalization to prevent malleability
 *
 * @param {string} payloadStr - Serialized JSON (with sorted keys via stableStringify)
 * @param {string} privateKeyHex - Wallet's secp256k1 private key (64 hex chars)
 * @returns {Promise<string>} - ECDSA signature in hex format (r || s, 128 hex chars)
 */
async function signPayload(payloadStr, privateKeyHex) {
  // Validate inputs
  if (!payloadStr) {
    throw new Error('Payload string required for signing');
  }

  if (!privateKeyHex || privateKeyHex.length !== 64) {
    throw new Error(
      'Valid private key required: must be 64 hexadecimal characters.'
    );
  }

  // Validate hex format
  if (!/^[0-9a-fA-F]+$/.test(privateKeyHex)) {
    throw new Error('Private key must be valid hexadecimal');
  }

  try {
    // Step 1: Hash the payload with SHA-256
    const encoder = new TextEncoder();
    const payloadBytes = encoder.encode(payloadStr);
    const msgHashBuffer = await crypto.subtle.digest('SHA-256', payloadBytes);
    const msgHashHex = bufferToHex(msgHashBuffer);

    // Step 2: Sign locally using XAICrypto (noble-secp256k1)
    // Private key NEVER leaves the browser
    if (typeof XAICrypto === 'undefined') {
      throw new Error(
        'XAICrypto not loaded. Ensure crypto-secp256k1.js and noble-secp256k1 are included.'
      );
    }

    const signature = await XAICrypto.signMessageHash(msgHashHex, privateKeyHex);

    // Validate signature format
    if (!signature || signature.length !== 128) {
      throw new Error('Invalid signature generated');
    }

    // Step 3: Return the ECDSA signature
    // Signature format: hex-encoded (r || s), 64 bytes = 128 hex characters
    return signature;
  } catch (error) {
    console.error('Transaction signing failed:', error);
    throw new Error(`Failed to sign transaction: ${error.message}`);
  }
}

async function saveSession(token, secret, address) {
  return new Promise((resolve) => {
    chrome.storage.local.set(
      {
        [SESSION_TOKEN_KEY]: token,
        [SESSION_SECRET_KEY]: secret,
        [SESSION_ADDRESS_KEY]: address
      },
      () => resolve()
    );
  });
}

async function getSession() {
  return new Promise((resolve) => {
    chrome.storage.local.get(
      [SESSION_TOKEN_KEY, SESSION_SECRET_KEY, SESSION_ADDRESS_KEY],
      (result) => {
        resolve({
          sessionToken: result[SESSION_TOKEN_KEY],
          sessionSecret: result[SESSION_SECRET_KEY],
          walletAddress: result[SESSION_ADDRESS_KEY]
        });
      }
    );
  });
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

async function getApiHost() {
  return new Promise((resolve) => {
    chrome.storage.local.get([API_KEY], (result) => {
      resolve(result[API_KEY] || 'http://localhost:8545');
    });
  });
}

async function setApiHost(host) {
  chrome.storage.local.set({ [API_KEY]: host });
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

  // Get wallet address and private key
  const walletAddress = $('#walletAddress').value.trim();
  const privateKey = $('#privateKey').value.trim();

  if (!walletAddress) {
    $('#tradeMessage').textContent = 'Error: Wallet address required';
    return;
  }

  if (!privateKey) {
    $('#tradeMessage').textContent = 'Error: Private key required for transaction signing';
    return;
  }

  if (privateKey.length !== 64) {
    $('#tradeMessage').textContent = 'Error: Invalid private key format (must be 64 hex characters)';
    return;
  }

  try {
    const formData = new FormData(form);

    // Step 1: Derive public key from private key (CLIENT-SIDE - key never leaves browser)
    $('#tradeMessage').textContent = 'Deriving public key...';

    if (typeof XAICrypto === 'undefined') {
      throw new Error('XAICrypto not loaded. Ensure crypto-secp256k1.js and noble-secp256k1 are included.');
    }

    // Derive public key locally - private key NEVER sent over network
    const publicKey = XAICrypto.derivePublicKey(privateKey, true);

    // Step 2: Build transaction payload
    const payload = {
      maker_address: walletAddress,
      maker_public_key: publicKey,
      token_offered: formData.get('tokenOffered'),
      amount_offered: parseFloat(formData.get('amountOffered')),
      token_requested: formData.get('tokenRequested'),
      amount_requested: parseFloat(formData.get('amountRequested')),
      price:
        parseFloat(formData.get('amountRequested')) /
        parseFloat(formData.get('amountOffered')),
      order_type: formData.get('orderType'),
      expiry: Math.floor(Date.now() / 1000) + 3600,
      nonce: Date.now(),
    };

    // Step 3: Serialize deterministically for signing and show verification UI
    const payloadStr = stableStringify(payload);
    const approved = await presentSigningPreview(payload, payloadStr);
    if (!approved) {
      $('#tradeMessage').textContent = 'Signing cancelled by user.';
      return;
    }

    // Step 4: Sign with ECDSA using private key
    $('#tradeMessage').textContent = 'Signing transaction with ECDSA...';
    const signature = await signPayload(payloadStr, privateKey);

    // Step 5: Add signature to payload
    payload.signature = signature;

    // Step 6: Submit signed transaction
    $('#tradeMessage').textContent = 'Submitting signed transaction...';
    const res = await fetch(`${host}/wallet-trades/orders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (data.success) {
      $('#tradeMessage').textContent = `✓ Success: ${data.message || 'Order created and verified'}`;
      // Clear private key field for security
      $('#privateKey').value = '';
      await refreshOrders();
      if (data.match) {
        await refreshMatches();
      }
      refreshTradeHistory();
    } else {
      $('#tradeMessage').textContent = `✗ Error: ${data.error || data.message || 'Order submission failed'}`;
    }
  } catch (error) {
    console.error('Order submission failed:', error);
    $('#tradeMessage').textContent = `✗ Error: ${error.message}`;
  }
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
    storeAiKey(apiKey);
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

async function getStoredAiKey() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['personalAiApiKey'], (result) => {
      resolve(result.personalAiApiKey || '');
    });
  });
}

function storeAiKey(value) {
  chrome.storage.local.set({ personalAiApiKey: value });
}

function clearStoredAiKey() {
  chrome.storage.local.remove('personalAiApiKey');
  clearAiKeyField();
  setKeyDeletionNotice('Stored Personal AI key removed.');
}

function bindActions() {
  $('#startMining').addEventListener('click', startMining);
  $('#stopMining').addEventListener('click', stopMining);
  $('#refreshOrders').addEventListener('click', refreshOrders);
  $('#refreshMatches').addEventListener('click', refreshMatches);
  $('#orderForm').addEventListener('submit', submitOrder);
  $('#runAiSwap').addEventListener('click', runPersonalAiSwap);
  $('#clearAiKey').addEventListener('click', clearStoredAiKey);

  $('#apiHost').addEventListener('change', (event) => {
    setApiHost(event.target.value.trim());
  });
}

function restoreSettings() {
  chrome.storage.local.get(['walletAddress', API_KEY], (result) => {
    if (result.walletAddress) {
      $('#walletAddress').value = result.walletAddress;
    }
    if (result[API_KEY]) {
      $('#apiHost').value = result[API_KEY];
    }
  });

  $('#walletAddress').addEventListener('change', async (event) => {
    chrome.storage.local.set({ walletAddress: event.target.value.trim() });
    await ensureSession();
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  bindActions();
  restoreSettings();
  $('#apiHost').value = await getApiHost();
  await ensureSession();
  refreshOrders();
  refreshMatches();
  updateMiningStatus();
  refreshMinerStats();
  refreshTradeHistory();
});
