# Trezor Hardware Wallet Integration for XAI Browser Extension

Complete production-ready Trezor integration for the XAI blockchain browser extension.

## Overview

This implementation provides secure hardware wallet support using Trezor devices (Model One, Model T, Safe 3) for the XAI blockchain. All signing operations occur on the device, ensuring private keys never leave the hardware wallet.

## Files

- `trezor-hw.js` - Main Trezor integration module
- `trezor-hw-example.js` - Usage examples and patterns
- `TREZOR_INTEGRATION.md` - This documentation

## Security Features

- Private keys never leave the Trezor device
- All transactions verified on device screen
- User must physically confirm operations
- BIP32 HD wallet support with XAI coin type (22593)
- Canonical ECDSA signatures (prevents malleability)
- Comprehensive error handling

## Prerequisites

### 1. Add Trezor Connect to manifest.json

Update `manifest.json` to load Trezor Connect library:

```json
{
  "manifest_version": 3,
  "content_security_policy": {
    "extension_pages": "script-src 'self' https://connect.trezor.io; object-src 'self'"
  },
  "permissions": [
    "storage",
    "alarms"
  ],
  "host_permissions": [
    "https://connect.trezor.io/*"
  ]
}
```

### 2. Load Trezor Connect in HTML

Add to your `popup.html` or background page:

```html
<script src="https://connect.trezor.io/9/trezor-connect.js"></script>
<script type="module" src="trezor-hw.js"></script>
```

## API Reference

### Exported Functions

#### `isTrezorSupported()`
Check if Trezor Connect is available in the current environment.

```javascript
if (isTrezorSupported()) {
  console.log('Trezor is supported');
}
```

#### `initTrezorConnect(options)`
Initialize Trezor Connect before any operations.

```javascript
await initTrezorConnect({
  debug: false,        // Enable debug logging
  popup: true,         // Allow popup windows
});
```

#### `connectTrezor()`
Connect to Trezor device and retrieve device information.

```javascript
const device = await connectTrezor();
console.log('Model:', device.device.model);
console.log('Firmware:', device.device.firmwareVersion);
```

#### `getTrezorAddress(bip32Path, options)`
Get XAI address from Trezor device.

```javascript
// Default path
const result = await getTrezorAddress();

// Custom path
const result2 = await getTrezorAddress("m/44'/22593'/0'/0/0");

// Show on device
const result3 = await getTrezorAddress(XAI_DEFAULT_PATH, {
  showOnDevice: true
});

console.log('Address:', result.address);
console.log('Public Key:', result.publicKey);
```

#### `signWithTrezor(bip32Path, txPayload, options)`
Sign transaction on Trezor device.

```javascript
const txPayload = {
  from: 'XAI...',
  to: 'XAI...',
  amount: 100,
  fee: 1,
  nonce: 42,
};

const result = await signWithTrezor(XAI_DEFAULT_PATH, txPayload);
console.log('Signature:', result.signature);  // 128 hex chars (r || s)
console.log('Hash:', result.messageHash);
```

#### `verifyAddressOnDevice(bip32Path)`
Display address on Trezor screen for verification.

```javascript
const result = await verifyAddressOnDevice();
if (result.confirmed) {
  console.log('User confirmed address:', result.address);
}
```

#### `disconnectTrezor()`
Cleanup and disconnect from Trezor.

```javascript
await disconnectTrezor();
```

### Error Handling

All functions throw `TrezorError` with specific error codes:

```javascript
import { TrezorError, TrezorErrorCode } from './trezor-hw.js';

try {
  await signWithTrezor(path, tx);
} catch (error) {
  if (error instanceof TrezorError) {
    switch (error.code) {
      case TrezorErrorCode.USER_CANCELLED:
        console.log('User cancelled');
        break;
      case TrezorErrorCode.DEVICE_NOT_CONNECTED:
        console.error('Connect device');
        break;
      case TrezorErrorCode.POPUP_BLOCKED:
        console.error('Allow popups');
        break;
      default:
        console.error(error.message);
    }
  }
}
```

### Error Codes

- `NOT_SUPPORTED` - Trezor Connect not available
- `NOT_INITIALIZED` - Must call initTrezorConnect() first
- `DEVICE_NOT_CONNECTED` - No device found
- `USER_CANCELLED` - User rejected on device
- `WRONG_PASSPHRASE` - Incorrect passphrase entered
- `COMMUNICATION_ERROR` - Connection issue
- `POPUP_BLOCKED` - Browser blocked popup
- `INVALID_PATH` - Invalid BIP32 path
- `SIGNING_FAILED` - Transaction signing failed
- `DEVICE_BUSY` - Device in use
- `FIRMWARE_OUTDATED` - Firmware update required

## Integration into XAI Extension

### Step 1: Add UI Elements

Add Trezor option to your wallet UI:

```html
<div id="hardwareWalletSection">
  <button id="connectTrezor">Connect Trezor</button>
  <div id="trezorStatus" class="hidden">
    <span id="trezorAddress"></span>
    <button id="signWithTrezor">Sign Transaction</button>
  </div>
</div>
```

### Step 2: Initialize on Extension Load

```javascript
import { isTrezorSupported, initTrezorConnect } from './trezor-hw.js';

document.addEventListener('DOMContentLoaded', async () => {
  if (isTrezorSupported()) {
    try {
      await initTrezorConnect();
      document.getElementById('hardwareWalletSection').classList.remove('hidden');
    } catch (error) {
      console.error('Trezor init failed:', error);
    }
  }
});
```

### Step 3: Handle Connection

```javascript
import { connectTrezor, getTrezorAddress } from './trezor-hw.js';

document.getElementById('connectTrezor').addEventListener('click', async () => {
  try {
    // Connect to device
    const device = await connectTrezor();
    console.log('Connected:', device.device.label);

    // Get address
    const result = await getTrezorAddress();
    document.getElementById('trezorAddress').textContent = result.address;
    document.getElementById('trezorStatus').classList.remove('hidden');

    // Store address for transaction signing
    chrome.storage.local.set({ trezorAddress: result.address });
  } catch (error) {
    alert('Failed to connect: ' + error.message);
  }
});
```

### Step 4: Sign Transactions

```javascript
import { signWithTrezor, XAI_DEFAULT_PATH } from './trezor-hw.js';

async function submitTransaction(txPayload) {
  try {
    // Check if using Trezor
    const { trezorAddress } = await chrome.storage.local.get('trezorAddress');

    if (trezorAddress && txPayload.from === trezorAddress) {
      // Sign with Trezor
      const result = await signWithTrezor(XAI_DEFAULT_PATH, txPayload);

      // Add signature to transaction
      txPayload.signature = result.signature;
      txPayload.messageHash = result.messageHash;
    } else {
      // Sign with software wallet
      const privateKey = await getSoftwarePrivateKey();
      txPayload.signature = await signWithSoftware(txPayload, privateKey);
    }

    // Submit to network
    await submitToNetwork(txPayload);

  } catch (error) {
    if (error.code === 'USER_CANCELLED') {
      console.log('User cancelled on device');
    } else {
      console.error('Transaction failed:', error);
    }
  }
}
```

## BIP32 Derivation Paths

XAI uses coin type 22593 (registered for XAI blockchain).

### Standard Path Format

```
m/44'/22593'/account'/change/address_index
```

### Examples

```javascript
// Account 0, first address
"m/44'/22593'/0'/0/0"  // Default

// Account 0, second address
"m/44'/22593'/0'/0/1"

// Account 1, first address
"m/44'/22593'/1'/0/0"

// Change address (internal)
"m/44'/22593'/0'/1/0"
```

### Multiple Accounts

```javascript
import { getTrezorAddress, XAI_COIN_TYPE } from './trezor-hw.js';

// Get addresses for multiple accounts
for (let account = 0; account < 5; account++) {
  const path = `m/44'/${XAI_COIN_TYPE}'/${account}'/0/0`;
  const result = await getTrezorAddress(path);
  console.log(`Account ${account}: ${result.address}`);
}
```

## Testing

### Manual Testing Steps

1. Install XAI browser extension (unpacked)
2. Connect Trezor device via USB
3. Open extension popup
4. Click "Connect Trezor"
5. Follow Trezor prompts (PIN, passphrase)
6. Verify address displayed matches device
7. Create test transaction
8. Confirm transaction on Trezor device
9. Verify signature is valid

### Browser Console Testing

```javascript
// Load examples
import * as examples from './trezor-hw-example.js';

// Run complete workflow
await examples.example7_CompleteWorkflow();

// Test individual functions
await examples.example3_GetAddress();
await examples.example5_SignTransaction();
```

## Troubleshooting

### Issue: "Trezor Connect library not loaded"

**Solution:** Add Trezor Connect to manifest.json CSP and load script in HTML.

### Issue: "Popup blocked"

**Solution:** User must allow popups for the extension. Add UI notice.

### Issue: "Device not found"

**Solution:**
- Check USB connection
- Install Trezor Bridge (trezor.io/bridge)
- Enable WebUSB in browser settings

### Issue: "Firmware outdated"

**Solution:** Update Trezor firmware at wallet.trezor.io

### Issue: "Wrong passphrase"

**Solution:** User entered incorrect passphrase. Allow retry with correct passphrase.

## Security Best Practices

1. **Never log private keys** - Only device signatures
2. **Verify addresses on device** - Before large transactions
3. **Use HTTPS only** - For Trezor Connect CDN
4. **Clear sensitive data** - After operations complete
5. **Validate inputs** - Before sending to device
6. **Handle errors gracefully** - Don't expose internal details
7. **Rate limit requests** - Prevent device abuse
8. **Audit regularly** - Review integration code

## Production Checklist

- [ ] Trezor Connect loaded via CDN in manifest
- [ ] CSP configured for connect.trezor.io
- [ ] Error handling for all operations
- [ ] UI feedback for long operations (loading spinners)
- [ ] Address verification before first transaction
- [ ] Multiple account support (if needed)
- [ ] Proper cleanup on extension close
- [ ] Security audit completed
- [ ] User documentation written
- [ ] Testing with real Trezor devices

## Support

- Trezor Documentation: https://docs.trezor.io/
- Trezor Connect API: https://connect.trezor.io/docs/
- XAI Blockchain: https://xai-blockchain.com
- Issue Tracker: [Your repo]/issues

## License

Same as XAI blockchain project license.
