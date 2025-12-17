/**
 * Hardware Wallet Integration for popup.js
 *
 * This file contains modifications to the existing popup.js functions
 * to support hardware wallet signing. Include this AFTER popup.js to
 * override the signPayload and submitOrder functions.
 */

// Store original signPayload function
const originalSignPayload = window.signPayload || signPayload;

/**
 * Enhanced signPayload that checks for hardware wallet
 * Falls back to software signing if no hardware wallet connected
 */
async function signPayloadWithHardwareSupport(payloadStr, privateKeyHex) {
  // Check if hardware wallet is available and connected
  if (window.hwUI && window.hwUI.shouldUseHardwareWallet()) {
    try {
      // Parse payload string back to object for hardware wallet
      const payload = JSON.parse(payloadStr);

      // Sign with hardware wallet UI (shows prompts)
      const signature = await window.hwUI.signTransactionWithUI(payload);

      return signature;
    } catch (error) {
      console.error('Hardware wallet signing failed:', error);
      throw new Error(`Hardware wallet signing failed: ${error.message}`);
    }
  } else {
    // Fall back to original software signing
    return await originalSignPayload(payloadStr, privateKeyHex);
  }
}

// Store original submitOrder function
const originalSubmitOrder = window.submitOrder || submitOrder;

/**
 * Enhanced submitOrder that supports hardware wallet signing
 */
async function submitOrderWithHardwareSupport(event) {
  event.preventDefault();
  const form = event.target;
  const host = await getApiHost();

  // Check if using hardware wallet
  const usingHardwareWallet = window.hwUI && window.hwUI.shouldUseHardwareWallet();

  let walletAddress;
  let publicKey;
  let privateKey;

  if (usingHardwareWallet) {
    // Get address and public key from hardware wallet
    walletAddress = window.hwUI.getAddress();
    publicKey = window.hwUI.getPublicKey();

    if (!walletAddress || !publicKey) {
      $('#tradeMessage').textContent = 'Error: Hardware wallet not properly connected';
      return;
    }

    console.log('Using hardware wallet for signing:', walletAddress);
  } else {
    // Get wallet address and private key from inputs
    walletAddress = $('#walletAddress').value.trim();
    privateKey = $('#privateKey').value.trim();

    if (!walletAddress) {
      $('#tradeMessage').textContent = 'Error: Wallet address required';
      return;
    }

    if (!privateKey) {
      $('#tradeMessage').textContent = 'Error: Private key required for transaction signing (or connect hardware wallet)';
      return;
    }

    if (privateKey.length !== 64) {
      $('#tradeMessage').textContent = 'Error: Invalid private key format (must be 64 hex characters)';
      return;
    }
  }

  try {
    const formData = new FormData(form);

    // Step 1: Derive public key (if not from hardware wallet)
    if (!usingHardwareWallet) {
      $('#tradeMessage').textContent = 'Deriving public key...';
      const publicKeyResponse = await fetch(`${host}/wallet/derive-public-key`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ private_key: privateKey }),
      });

      if (!publicKeyResponse.ok) {
        throw new Error('Failed to derive public key from private key');
      }

      const publicKeyData = await publicKeyResponse.json();
      if (!publicKeyData.success || !publicKeyData.public_key) {
        throw new Error(publicKeyData.error || 'No public key returned');
      }

      publicKey = publicKeyData.public_key;
    }

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

    // Only show signing preview for software wallet (hardware wallet has its own prompts)
    if (!usingHardwareWallet) {
      const approved = await presentSigningPreview(payload, payloadStr);
      if (!approved) {
        $('#tradeMessage').textContent = 'Signing cancelled by user.';
        return;
      }
    }

    // Step 4: Sign with hardware wallet or ECDSA
    $('#tradeMessage').textContent = usingHardwareWallet
      ? 'Signing transaction with hardware wallet...'
      : 'Signing transaction with ECDSA...';

    let signature;
    if (usingHardwareWallet) {
      // Sign with hardware wallet (will show its own UI prompts)
      signature = await window.hwUI.signTransactionWithUI(payload);
    } else {
      // Sign with software key
      signature = await signPayload(payloadStr, privateKey);
    }

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

      // Clear private key field for security (only if using software wallet)
      if (!usingHardwareWallet) {
        $('#privateKey').value = '';
      }

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

// Override the global functions if they exist
if (typeof window !== 'undefined') {
  // Save originals for reference
  window.originalSignPayload = originalSignPayload;
  window.originalSubmitOrder = originalSubmitOrder;

  // Replace with hardware-enabled versions
  window.signPayload = signPayloadWithHardwareSupport;
  window.submitOrder = submitOrderWithHardwareSupport;

  console.log('Hardware wallet integration active');
}

// Re-bind the submit handler after override
document.addEventListener('DOMContentLoaded', () => {
  const orderForm = document.getElementById('orderForm');
  if (orderForm) {
    // Remove old listener by cloning and replacing
    const newForm = orderForm.cloneNode(true);
    orderForm.parentNode.replaceChild(newForm, orderForm);

    // Add new listener with hardware wallet support
    newForm.addEventListener('submit', submitOrderWithHardwareSupport);
  }
});
