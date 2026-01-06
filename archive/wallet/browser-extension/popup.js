// Import Cosmos SDK module
/* global COSMOS_SDK */

const API_KEY = 'apiHost';
const PRIVATE_KEY_STORAGE = 'walletPrivateKey';
const SESSION_TOKEN_KEY = 'walletSessionToken';
const SESSION_SECRET_KEY = 'walletSessionSecret';
const SESSION_ADDRESS_KEY = 'walletSessionAddress';
const HKDF_INFO = new TextEncoder().encode('walletconnect-trade');

function bufferToHex(buffer) {
  return Array.from(new Uint8Array(buffer))
    .map(byte => byte.toString(16).padStart(2, '0'))
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
  if (value === null) {return 'null';}
  if (Array.isArray(value)) {
    return `[${value.map(item => stableStringify(item)).join(',')}]`;
  }
  if (typeof value === 'object') {
    const keys = Object.keys(value).sort();
    return `{${keys.map(key => `"${key}":${stableStringify(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

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

async function saveSession(token, secret, address) {
  return new Promise(resolve => {
    chrome.storage.local.set(
      {
        [SESSION_TOKEN_KEY]: token,
        [SESSION_SECRET_KEY]: secret,
        [SESSION_ADDRESS_KEY]: address,
      },
      () => resolve()
    );
  });
}

async function getSession() {
  return new Promise(resolve => {
    chrome.storage.local.get(
      [SESSION_TOKEN_KEY, SESSION_SECRET_KEY, SESSION_ADDRESS_KEY],
      result => {
        resolve({
          sessionToken: result[SESSION_TOKEN_KEY],
          sessionSecret: result[SESSION_SECRET_KEY],
          walletAddress: result[SESSION_ADDRESS_KEY],
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
    body: JSON.stringify({ wallet_address: address }),
  });
  const payload = await response.json();
  if (payload.success) {
    await saveSession(payload.session_token, payload.session_secret, address);
    return {
      sessionToken: payload.session_token,
      sessionSecret: payload.session_secret,
      walletAddress: address,
    };
  }
  return null;
}

// eslint-disable-next-line no-unused-vars
async function beginWalletConnectHandshake(address) {
  const host = await getApiHost();
  const response = await fetch(`${host}/wallet-trades/wc/handshake`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ wallet_address: address }),
  });
  const payload = await response.json();
  return payload.success ? payload : null;
}

// eslint-disable-next-line no-unused-vars
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
      info: HKDF_INFO,
    },
    hkdfKey,
    256
  );
  const derivedHex = bufferToHex(derivedBits);
  const clientPublicBase64 = bufferToBase64(clientPublicRaw);
  const response = await fetch(`${host}/wallet-trades/wc/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      handshake_id: handshake.handshake_id,
      wallet_address: address,
      client_public: clientPublicBase64,
    }),
  });
  const payload = await response.json();
  if (!payload.success) {return null;}
  await saveSession(payload.session_token, derivedHex, address);
  return { sessionToken: payload.session_token, sessionSecret: derivedHex, walletAddress: address };
}

async function ensureSession() {
  const address = $('#walletAddress').value.trim();
  if (!address) {return null;}
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
  return new Promise(resolve => {
    chrome.storage.local.get([API_KEY], result => {
      resolve(result[API_KEY] || 'http://localhost:1317');
    });
  });
}

/**
 * Cosmos SDK Integration Functions
 */

async function getPrivateKey() {
  return new Promise(resolve => {
    chrome.storage.local.get([PRIVATE_KEY_STORAGE], result => {
      resolve(result[PRIVATE_KEY_STORAGE] || null);
    });
  });
}

async function savePrivateKey(privateKeyHex) {
  return new Promise(resolve => {
    chrome.storage.local.set({ [PRIVATE_KEY_STORAGE]: privateKeyHex }, () => resolve());
  });
}

async function generateNewWallet() {
  try {
    // Confirm wallet creation
    const existingKey = await getPrivateKey();
    if (existingKey) {
      const confirmed = confirm(
        'You already have a wallet. Creating a new one will replace it. ' +
        'Make sure you have backed up your current private key! Continue?'
      );
      if (!confirmed) {
        return;
      }
    }

    showMessage('walletMessage', 'Generating new wallet...');

    const privateKey = COSMOS_SDK.generatePrivateKey();
    if (privateKey.length !== 32) {
      throw new Error('Invalid private key length');
    }

    const privateKeyHex = COSMOS_SDK.bytesToHex(privateKey);
    const publicKey = await COSMOS_SDK.getPublicKey(privateKey);
    const address = COSMOS_SDK.publicKeyToAddress(publicKey);

    if (!validateCosmosAddress(address)) {
      throw new Error('Generated address validation failed');
    }

    await savePrivateKey(privateKeyHex);
    $('#walletAddress').value = address;
    chrome.storage.local.set({ walletAddress: address });

    showMessage('walletMessage', `New wallet created: ${address}`);

    // Show backup warning
    setTimeout(() => {
      alert(
        'IMPORTANT: Back up your private key!\n\n' +
        'Use the "Export Private Key" button to view and save your private key. ' +
        'Without it, you cannot recover your wallet if you lose access to this browser.'
      );
    }, 500);

    await updateBalance();
  } catch (error) {
    showMessage('walletMessage', `Error creating wallet: ${error.message}`, true);
    console.error('Wallet generation error:', error);
  }
}

async function importWallet(privateKeyHex) {
  try {
    // Validate input
    if (!privateKeyHex || typeof privateKeyHex !== 'string') {
      throw new Error('Private key is required');
    }

    // Remove whitespace and validate hex format
    privateKeyHex = privateKeyHex.trim().toLowerCase();
    if (!/^[0-9a-f]{64}$/i.test(privateKeyHex)) {
      throw new Error('Invalid private key format. Must be 64 hex characters (32 bytes)');
    }

    showMessage('walletMessage', 'Importing wallet...');

    const privateKey = COSMOS_SDK.hexToBytes(privateKeyHex);
    if (privateKey.length !== 32) {
      throw new Error('Invalid private key length. Must be 32 bytes');
    }

    const publicKey = await COSMOS_SDK.getPublicKey(privateKey);
    const address = COSMOS_SDK.publicKeyToAddress(publicKey);

    if (!validateCosmosAddress(address)) {
      throw new Error('Generated address validation failed');
    }

    // Confirm if overwriting existing wallet
    const existingKey = await getPrivateKey();
    if (existingKey && existingKey !== privateKeyHex) {
      const confirmed = confirm(
        'You already have a wallet. Importing will replace it. ' +
        'Make sure you have backed up your current private key! Continue?'
      );
      if (!confirmed) {
        return;
      }
    }

    await savePrivateKey(privateKeyHex);
    $('#walletAddress').value = address;
    chrome.storage.local.set({ walletAddress: address });

    showMessage('walletMessage', `Wallet imported successfully: ${address}`);
    await updateBalance();
  } catch (error) {
    showMessage('walletMessage', `Error importing wallet: ${error.message}`, true);
    console.error('Wallet import error:', error);
  }
}

async function updateBalance() {
  const address = $('#walletAddress').value.trim();
  if (!address) {
    $('#balanceDisplay').textContent = 'Balance: Enter address';
    return;
  }

  try {
    const balances = await COSMOS_SDK.getBalance(address);
    if (balances.length === 0) {
      $('#balanceDisplay').textContent = 'Balance: 0 XAI';
      return;
    }

    const balanceText = balances
      .map(b => {
        const amount = parseInt(b.amount) / Math.pow(10, COSMOS_SDK.config.coinDecimals);
        const denom = b.denom === 'uxai' ? 'XAI' : b.denom;
        return `${amount} ${denom}`;
      })
      .join(', ');

    $('#balanceDisplay').textContent = `Balance: ${balanceText}`;
  } catch (error) {
    $('#balanceDisplay').textContent = `Balance: Error - ${error.message}`;
  }
}

async function sendTokens(toAddress, amount, denom = 'uxai') {
  const fromAddress = $('#walletAddress').value.trim();

  // Validation
  if (!fromAddress) {
    showMessage('transactionMessage', 'Please enter your wallet address', true);
    return null;
  }

  if (!validateCosmosAddress(fromAddress)) {
    showMessage('transactionMessage', 'Invalid sender address format', true);
    return null;
  }

  if (!validateCosmosAddress(toAddress)) {
    showMessage('transactionMessage', 'Invalid recipient address format', true);
    return null;
  }

  if (!amount || amount <= 0) {
    showMessage('transactionMessage', 'Invalid amount. Must be greater than 0', true);
    return null;
  }

  const privateKeyHex = await getPrivateKey();
  if (!privateKeyHex) {
    showMessage('transactionMessage', 'No private key found. Create or import a wallet first.', true);
    return null;
  }

  try {
    showMessage('transactionMessage', 'Preparing transaction...');

    const privateKey = COSMOS_SDK.hexToBytes(privateKeyHex);
    const publicKey = await COSMOS_SDK.getPublicKey(privateKey);
    const accountInfo = await COSMOS_SDK.getAccount(fromAddress);

    const amountInMicroDenom = Math.floor(amount * Math.pow(10, COSMOS_SDK.config.coinDecimals));

    if (amountInMicroDenom <= 0) {
      throw new Error('Amount too small to send');
    }

    const tx = COSMOS_SDK.buildTransferTx({
      fromAddress,
      toAddress,
      amount: amountInMicroDenom,
      denom,
      memo: 'Sent from XAI Browser Wallet',
    });

    showMessage('transactionMessage', 'Signing transaction...');
    const signedTx = await COSMOS_SDK.signTx(tx, privateKey, accountInfo, publicKey);

    showMessage('transactionMessage', 'Broadcasting transaction...');
    const result = await COSMOS_SDK.broadcastTx(signedTx);

    showMessage('transactionMessage', `Transaction successful! Hash: ${result.txhash}`);
    await updateBalance();
    await refreshTradeHistory();
    return result;
  } catch (error) {
    const errorMsg = error.message || 'Unknown error occurred';
    showMessage('transactionMessage', `Transaction failed: ${errorMsg}`, true);
    console.error('Send tokens error:', error);
    return null;
  }
}

async function executeSwap(poolId, tokenInDenom, tokenInAmount, tokenOutDenom, minAmountOut) {
  const sender = $('#walletAddress').value.trim();

  // Validation
  if (!sender) {
    showMessage('tradeMessage', 'Please enter your wallet address', true);
    return null;
  }

  if (!validateCosmosAddress(sender)) {
    showMessage('tradeMessage', 'Invalid wallet address format', true);
    return null;
  }

  if (!poolId || poolId <= 0) {
    showMessage('tradeMessage', 'Invalid pool ID', true);
    return null;
  }

  if (!tokenInAmount || tokenInAmount <= 0) {
    showMessage('tradeMessage', 'Invalid swap amount. Must be greater than 0', true);
    return null;
  }

  if (!tokenInDenom || !tokenOutDenom) {
    showMessage('tradeMessage', 'Token denominations required', true);
    return null;
  }

  const privateKeyHex = await getPrivateKey();
  if (!privateKeyHex) {
    showMessage('tradeMessage', 'No private key found. Create or import a wallet first.', true);
    return null;
  }

  try {
    showMessage('tradeMessage', 'Preparing swap transaction...');

    const privateKey = COSMOS_SDK.hexToBytes(privateKeyHex);
    const publicKey = await COSMOS_SDK.getPublicKey(privateKey);
    const accountInfo = await COSMOS_SDK.getAccount(sender);

    const tx = COSMOS_SDK.buildSwapTx({
      sender,
      poolId,
      tokenIn: {
        denom: tokenInDenom,
        amount: tokenInAmount.toString(),
      },
      tokenOutDenom,
      minAmountOut: minAmountOut.toString(),
      memo: 'DEX Swap from XAI Browser Wallet',
    });

    showMessage('tradeMessage', 'Signing swap transaction...');
    const signedTx = await COSMOS_SDK.signTx(tx, privateKey, accountInfo, publicKey);

    showMessage('tradeMessage', 'Broadcasting swap transaction...');
    const result = await COSMOS_SDK.broadcastTx(signedTx);

    showMessage('tradeMessage', `Swap successful! Hash: ${result.txhash}`);
    await updateBalance();
    await refreshPools();
    await refreshTradeHistory();
    return result;
  } catch (error) {
    const errorMsg = error.message || 'Unknown swap error occurred';
    showMessage('tradeMessage', `Swap failed: ${errorMsg}`, true);
    console.error('Swap execution error:', error);
    return null;
  }
}

function showMessage(elementId, message, isError = false) {
  const element = $(`#${elementId}`);
  if (element) {
    element.textContent = message;
    element.classList.toggle('error', isError);
    setTimeout(() => {
      element.textContent = '';
      element.classList.remove('error');
    }, 10000);
  }
}

async function setApiHost(host) {
  chrome.storage.local.set({ [API_KEY]: host });
  // Update Cosmos SDK config
  COSMOS_SDK.config.restEndpoint = host;
  COSMOS_SDK.config.rpcEndpoint = host.replace('1317', '26657');
}

/**
 * Additional Helper Functions
 */

async function exportPrivateKey() {
  const privateKeyHex = await getPrivateKey();
  if (!privateKeyHex) {
    showMessage('walletMessage', 'No private key found', true);
    return;
  }

  const confirmed = confirm(
    'WARNING: Never share your private key with anyone! ' +
    'Anyone with access to your private key can steal your funds. ' +
    'Are you sure you want to view it?'
  );

  if (confirmed) {
    alert(`Your private key:\n\n${privateKeyHex}\n\nStore this securely and never share it!`);
  }
}

async function deleteWallet() {
  const confirmed = confirm(
    'WARNING: This will delete your private key from this browser. ' +
    'Make sure you have backed up your private key first! ' +
    'This action cannot be undone. Continue?'
  );

  if (confirmed) {
    await chrome.storage.local.remove([PRIVATE_KEY_STORAGE, 'walletAddress']);
    $('#walletAddress').value = '';
    $('#balanceDisplay').textContent = 'Balance: Wallet deleted';
    showMessage('walletMessage', 'Wallet deleted successfully');
  }
}

async function queryAccountInfo() {
  const address = $('#walletAddress').value.trim();
  if (!address) {
    showMessage('walletMessage', 'Enter a wallet address first', true);
    return;
  }

  try {
    const accountInfo = await COSMOS_SDK.getAccount(address);
    const message = `Account Number: ${accountInfo.accountNumber}\n` +
                   `Sequence: ${accountInfo.sequence}\n` +
                   `Address: ${accountInfo.address}`;
    alert(message);
  } catch (error) {
    showMessage('walletMessage', `Error fetching account: ${error.message}`, true);
  }
}

function validateCosmosAddress(address) {
  // Basic validation for Cosmos Bech32 addresses
  if (!address || typeof address !== 'string') {
    return false;
  }
  return address.startsWith(COSMOS_SDK.config.bech32Prefix) && address.length >= 39;
}

async function checkNetworkConnection() {
  try {
    const response = await fetch(`${COSMOS_SDK.config.rpcEndpoint}/status`);
    if (response.ok) {
      const data = await response.json();
      return {
        connected: true,
        chainId: data.result?.node_info?.network,
        latestHeight: data.result?.sync_info?.latest_block_height,
      };
    }
    return { connected: false };
  } catch (error) {
    return { connected: false, error: error.message };
  }
}

function $(selector) {
  return document.querySelector(selector);
}

async function updateMiningStatus() {
  const address = $('#walletAddress').value.trim();
  if (!address) {
    $('#miningStatus').textContent = 'Status: wallet address required';
    return;
  }

  try {
    // Query validator status from Cosmos SDK
    const validatorUrl = `${COSMOS_SDK.config.rpcEndpoint}/validators`;
    const statusRes = await fetch(validatorUrl);
    if (!statusRes.ok) {
      $('#miningStatus').textContent = 'Status: unable to reach validator API';
      return;
    }

    const data = await statusRes.json();
    $('#miningStatus').textContent = 'Status: Network connected';
    $('#miningMeta').textContent = `Validators: ${data.result?.validators?.length || 0}`;
  } catch (error) {
    $('#miningStatus').textContent = `Status: ${error.message}`;
    $('#miningMeta').textContent = 'Network unavailable';
  }
}

async function startMining() {
  const address = $('#walletAddress').value.trim();
  if (!address) {
    showMessage('miningMessage', 'Enter a wallet address first', true);
    return;
  }

  showMessage('miningMessage', 'Note: XAI uses Proof-of-Stake. Use staking instead of mining.');
  await updateMiningStatus();
}

async function stopMining() {
  showMessage('miningMessage', 'Note: XAI uses Proof-of-Stake. Check staking section.');
  await updateMiningStatus();
}

async function refreshPools() {
  try {
    const pools = await COSMOS_SDK.queryPools();
    const list = $('#ordersList');

    if (pools && pools.length > 0) {
      list.innerHTML = pools
        .slice(0, 10)
        .map(
          pool => `
        <div class="entry">
          <strong>Pool ${pool.id}</strong>
          <br />
          ${pool.token0} / ${pool.token1} | Liquidity: ${pool.liquidity || 'N/A'}
        </div>`
        )
        .join('');
    } else {
      list.innerHTML = '<div class="list-placeholder">No pools available</div>';
    }
  } catch (error) {
    $('#ordersList').innerHTML = `<div class="list-placeholder">Error loading pools: ${error.message}</div>`;
  }
}

async function refreshOrders() {
  await refreshPools();
}

async function refreshMatches() {
  try {
    const prices = await COSMOS_SDK.queryOraclePrices();
    const list = $('#matchesList');

    if (prices && prices.length > 0) {
      list.innerHTML = prices
        .slice(0, 10)
        .map(
          price => `
        <div class="entry">
          ${price.symbol}: $${price.price}
          <br />
          Updated: ${new Date(price.timestamp * 1000).toLocaleTimeString()}
        </div>`
        )
        .join('');
    } else {
      list.innerHTML = '<div class="list-placeholder">No price feeds available</div>';
    }
  } catch (error) {
    $('#matchesList').innerHTML = `<div class="list-placeholder">Error loading prices: ${error.message}</div>`;
  }
}

async function refreshTradeHistory() {
  const address = $('#walletAddress').value.trim();
  if (!address) {
    $('#tradeHistory').innerHTML = '<div class="list-placeholder">Enter wallet address</div>';
    return;
  }

  try {
    const url = `${COSMOS_SDK.config.restEndpoint}/cosmos/tx/v1beta1/txs?events=message.sender='${address}'&order_by=ORDER_BY_DESC&limit=5`;
    const res = await fetch(url);

    if (!res.ok) {
      $('#tradeHistory').innerHTML = '<div class="list-placeholder">Unable to fetch history</div>';
      return;
    }

    const data = await res.json();
    const container = $('#tradeHistory');

    if (data.txs && data.txs.length > 0) {
      container.innerHTML = data.txs
        .map(
          tx => `
        <div class="entry">
          TX @ height ${tx.height || 'pending'}
          <br />
          Hash: ${tx.txhash?.substring(0, 12)}... | Fee: ${tx.auth_info?.fee?.amount?.[0]?.amount || 0}
        </div>`
        )
        .join('');
    } else {
      container.innerHTML = '<div class="list-placeholder">No transactions found</div>';
    }
  } catch (error) {
    $('#tradeHistory').innerHTML = `<div class="list-placeholder">Error: ${error.message}</div>`;
  }
}

async function refreshMinerStats() {
  const address = $('#walletAddress').value.trim();
  if (!address) {
    $('#minerStats').textContent = 'Enter address for staking stats';
    return;
  }

  try {
    const url = `${COSMOS_SDK.config.restEndpoint}/cosmos/staking/v1beta1/delegations/${address}`;
    const res = await fetch(url);

    if (!res.ok) {
      $('#minerStats').textContent = 'No staking data';
      $('#minerHistory').textContent = 'Not staking';
      return;
    }

    const data = await res.json();
    const delegations = data.delegation_responses || [];

    if (delegations.length > 0) {
      const totalStaked = delegations.reduce((sum, del) => {
        return sum + parseInt(del.balance?.amount || 0);
      }, 0) / Math.pow(10, COSMOS_SDK.config.coinDecimals);

      $('#minerStats').textContent = `Staked: ${totalStaked} XAI | Delegations: ${delegations.length}`;
      $('#minerHistory').textContent = 'Active validator delegations';
    } else {
      $('#minerStats').textContent = 'No active delegations';
      $('#minerHistory').textContent = 'Not staking';
    }
  } catch (error) {
    $('#minerStats').textContent = `Error: ${error.message}`;
    $('#minerHistory').textContent = 'Unable to fetch staking data';
  }
}

async function submitOrder(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);

  const tokenOffered = formData.get('tokenOffered');
  const amountOffered = parseFloat(formData.get('amountOffered'));
  const tokenRequested = formData.get('tokenRequested');
  const amountRequested = parseFloat(formData.get('amountRequested'));

  if (!tokenOffered || !tokenRequested || !amountOffered || !amountRequested) {
    showMessage('tradeMessage', 'Please fill in all fields', true);
    return;
  }

  try {
    // For now, use the swap function
    // In a real implementation, this would map to DEX order creation
    const poolId = 1; // Default pool - should be dynamically selected
    const minAmountOut = Math.floor(amountRequested * 0.95); // 5% slippage tolerance

    const result = await executeSwap(
      poolId,
      tokenOffered,
      Math.floor(amountOffered * Math.pow(10, COSMOS_SDK.config.coinDecimals)),
      tokenRequested,
      minAmountOut
    );

    if (result) {
      showMessage('tradeMessage', `Swap successful! Hash: ${result.txhash}`);
      await refreshPools();
      await refreshTradeHistory();
    }
  } catch (error) {
    showMessage('tradeMessage', `Swap failed: ${error.message}`, true);
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
  const userAddress = $('#walletAddress').value.trim();
  const mode = $('#aiKeyMode').value;
  let apiKey = $('#aiApiKey').value.trim();
  const provider = $('#aiProvider').value.trim() || 'anthropic';
  const model = $('#aiModel').value.trim() || 'claude-sonnet-4-5';
  const swapDetails = {
    from_coin: $('#aiFromCoin').value.trim() || 'XAI',
    to_coin: $('#aiToCoin').value.trim() || 'USDC',
    amount: parseFloat($('#aiAmount').value) || 0,
    recipient_address: $('#aiRecipient').value.trim() || userAddress,
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

  setAiStatus('Preparing AI-assisted swap...');

  try {
    // Execute the swap using Cosmos SDK
    const poolId = 1; // Default pool
    const amountInMicroDenom = Math.floor(
      swapDetails.amount * Math.pow(10, COSMOS_SDK.config.coinDecimals)
    );
    const minAmountOut = Math.floor(amountInMicroDenom * 0.95); // 5% slippage

    const result = await executeSwap(
      poolId,
      swapDetails.from_coin.toLowerCase(),
      amountInMicroDenom,
      swapDetails.to_coin.toLowerCase(),
      minAmountOut
    );

    if (result) {
      setAiStatus(`Swap successful! Hash: ${result.txhash}`);
      setKeyDeletionNotice('Transaction complete. API key removed from this extension.');
      await updateBalance();
      await refreshTradeHistory();
    } else {
      throw new Error('Swap transaction failed');
    }
  } catch (error) {
    setAiStatus(`Swap error: ${error.message}`, true);
  } finally {
    if (mode === 'temporary' || mode === 'external') {
      clearAiKeyField();
    } else if (mode === 'session') {
      setKeyDeletionNotice('Transaction complete. Stored key remains until you click Clear Key.');
    }
  }
}

async function getStoredAiKey() {
  return new Promise(resolve => {
    chrome.storage.local.get(['personalAiApiKey'], result => {
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
  // Wallet management
  const generateWalletBtn = $('#generateWallet');
  const importWalletBtn = $('#importWallet');
  const refreshBalanceBtn = $('#refreshBalance');
  const exportKeyBtn = $('#exportPrivateKey');
  const deleteWalletBtn = $('#deleteWallet');
  const accountInfoBtn = $('#accountInfo');

  if (generateWalletBtn) {
    generateWalletBtn.addEventListener('click', generateNewWallet);
  }
  if (importWalletBtn) {
    importWalletBtn.addEventListener('click', () => {
      const privateKey = prompt('Enter your private key (hex):');
      if (privateKey) {
        importWallet(privateKey);
      }
    });
  }
  if (refreshBalanceBtn) {
    refreshBalanceBtn.addEventListener('click', updateBalance);
  }
  if (exportKeyBtn) {
    exportKeyBtn.addEventListener('click', exportPrivateKey);
  }
  if (deleteWalletBtn) {
    deleteWalletBtn.addEventListener('click', deleteWallet);
  }
  if (accountInfoBtn) {
    accountInfoBtn.addEventListener('click', queryAccountInfo);
  }

  // Mining/Staking
  const startMiningBtn = $('#startMining');
  const stopMiningBtn = $('#stopMining');
  if (startMiningBtn) startMiningBtn.addEventListener('click', startMining);
  if (stopMiningBtn) stopMiningBtn.addEventListener('click', stopMining);

  // Trading
  const refreshOrdersBtn = $('#refreshOrders');
  const refreshMatchesBtn = $('#refreshMatches');
  const orderForm = $('#orderForm');

  if (refreshOrdersBtn) refreshOrdersBtn.addEventListener('click', refreshOrders);
  if (refreshMatchesBtn) refreshMatchesBtn.addEventListener('click', refreshMatches);
  if (orderForm) orderForm.addEventListener('submit', submitOrder);

  // AI Assistant
  const runAiSwapBtn = $('#runAiSwap');
  const clearAiKeyBtn = $('#clearAiKey');

  if (runAiSwapBtn) runAiSwapBtn.addEventListener('click', runPersonalAiSwap);
  if (clearAiKeyBtn) clearAiKeyBtn.addEventListener('click', clearStoredAiKey);

  // API Host
  const apiHostInput = $('#apiHost');
  if (apiHostInput) {
    apiHostInput.addEventListener('change', event => {
      const newHost = event.target.value.trim();
      setApiHost(newHost);
      // Update Cosmos SDK config
      COSMOS_SDK.config.restEndpoint = newHost;
      COSMOS_SDK.config.rpcEndpoint = newHost.replace('1317', '26657');
    });
  }
}

function restoreSettings() {
  chrome.storage.local.get(['walletAddress', API_KEY], result => {
    const walletAddressInput = $('#walletAddress');
    const apiHostInput = $('#apiHost');

    if (result.walletAddress && walletAddressInput) {
      walletAddressInput.value = result.walletAddress;
    }
    if (result[API_KEY] && apiHostInput) {
      apiHostInput.value = result[API_KEY];
      // Update Cosmos SDK config
      COSMOS_SDK.config.restEndpoint = result[API_KEY];
      COSMOS_SDK.config.rpcEndpoint = result[API_KEY].replace('1317', '26657');
    }
  });

  const walletAddressInput = $('#walletAddress');
  if (walletAddressInput) {
    walletAddressInput.addEventListener('change', async event => {
      chrome.storage.local.set({ walletAddress: event.target.value.trim() });
      await updateBalance();
    });
  }
}

async function initializeWallet() {
  try {
    // Check network connection first
    const networkStatus = await checkNetworkConnection();
    const statusElement = $('#networkStatus');

    if (networkStatus.connected) {
      if (statusElement) {
        statusElement.textContent = `Connected to ${networkStatus.chainId || 'XAI'} | Block: ${networkStatus.latestHeight || 'N/A'}`;
        statusElement.classList.remove('error');
      }
    } else {
      if (statusElement) {
        statusElement.textContent = `Disconnected: ${networkStatus.error || 'Network unavailable'}`;
        statusElement.classList.add('error');
      }
    }

    // Check if we have a stored private key
    const privateKeyHex = await getPrivateKey();
    if (privateKeyHex) {
      const privateKey = COSMOS_SDK.hexToBytes(privateKeyHex);
      const publicKey = await COSMOS_SDK.getPublicKey(privateKey);
      const address = COSMOS_SDK.publicKeyToAddress(publicKey);

      const walletAddressInput = $('#walletAddress');
      if (walletAddressInput && !walletAddressInput.value) {
        walletAddressInput.value = address;
        chrome.storage.local.set({ walletAddress: address });
      }

      // Validate the address format
      if (!validateCosmosAddress(address)) {
        console.warn('Generated address may be invalid:', address);
      }
    }
  } catch (error) {
    console.error('Error initializing wallet:', error);
    showMessage('walletMessage', `Initialization error: ${error.message}`, true);
  }
}

async function updateNetworkStatus() {
  const networkStatus = await checkNetworkConnection();
  const statusElement = $('#networkStatus');

  if (statusElement) {
    if (networkStatus.connected) {
      statusElement.textContent = `Connected to ${networkStatus.chainId || 'XAI'} | Block: ${networkStatus.latestHeight || 'N/A'}`;
      statusElement.classList.remove('error');
    } else {
      statusElement.textContent = `Disconnected: ${networkStatus.error || 'Network unavailable'}`;
      statusElement.classList.add('error');
    }
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  try {
    bindActions();
    restoreSettings();

    const apiHostInput = $('#apiHost');
    if (apiHostInput) {
      const host = await getApiHost();
      apiHostInput.value = host;
      COSMOS_SDK.config.restEndpoint = host;
      COSMOS_SDK.config.rpcEndpoint = host.replace('1317', '26657');
    }

    await initializeWallet();

    // Safe async calls with error handling
    await safeAsyncCall(updateBalance, 'balance update');
    await safeAsyncCall(refreshOrders, 'pools refresh');
    await safeAsyncCall(refreshMatches, 'prices refresh');
    await safeAsyncCall(updateMiningStatus, 'network status');
    await safeAsyncCall(refreshMinerStats, 'staking stats');
    await safeAsyncCall(refreshTradeHistory, 'transaction history');

    // Set up auto-refresh every 30 seconds
    setInterval(async () => {
      await safeAsyncCall(updateNetworkStatus, 'network status');
      await safeAsyncCall(updateBalance, 'balance update');
      await safeAsyncCall(refreshPools, 'pools refresh');
      await safeAsyncCall(refreshMatches, 'prices refresh');
      await safeAsyncCall(updateMiningStatus, 'network status');
    }, 30000);

    console.log('XAI Browser Wallet initialized successfully');
  } catch (error) {
    console.error('Fatal initialization error:', error);
    showMessage('walletMessage', `Failed to initialize wallet: ${error.message}`, true);
  }
});

/**
 * Safe async call wrapper with error handling
 */
async function safeAsyncCall(fn, operationName) {
  try {
    await fn();
  } catch (error) {
    console.error(`Error during ${operationName}:`, error);
    // Don't show UI errors for background operations to avoid spam
  }
}
