# Trezor Integration Quick Start Guide

Fast setup guide for integrating Trezor hardware wallet support into XAI browser extension.

## 5-Minute Integration

### 1. Update manifest.json

```json
{
  "manifest_version": 3,
  "content_security_policy": {
    "extension_pages": "script-src 'self' https://connect.trezor.io; object-src 'self'"
  },
  "host_permissions": [
    "https://connect.trezor.io/*"
  ]
}
```

### 2. Load in HTML

Add to `popup.html`:

```html
<script src="https://connect.trezor.io/9/trezor-connect.js"></script>
<script type="module" src="trezor-hw.js"></script>
```

### 3. Initialize

```javascript
import { isTrezorSupported, initTrezorConnect } from './trezor-hw.js';

// On extension load
if (isTrezorSupported()) {
  await initTrezorConnect();
}
```

### 4. Get Address

```javascript
import { getTrezorAddress } from './trezor-hw.js';

const result = await getTrezorAddress();
console.log('Address:', result.address);
```

### 5. Sign Transaction

```javascript
import { signWithTrezor, XAI_DEFAULT_PATH } from './trezor-hw.js';

const txPayload = {
  from: 'XAI...',
  to: 'XAI...',
  amount: 100,
  fee: 1,
  nonce: 42,
};

const result = await signWithTrezor(XAI_DEFAULT_PATH, txPayload);
console.log('Signature:', result.signature);
```

## Complete Example

```javascript
import {
  isTrezorSupported,
  initTrezorConnect,
  connectTrezor,
  getTrezorAddress,
  signWithTrezor,
  verifyAddressOnDevice,
  disconnectTrezor,
  TrezorError,
  TrezorErrorCode,
  XAI_DEFAULT_PATH,
} from './trezor-hw.js';

async function useTrezor() {
  try {
    // 1. Check support
    if (!isTrezorSupported()) {
      throw new Error('Trezor not supported');
    }

    // 2. Initialize
    await initTrezorConnect();

    // 3. Connect
    const device = await connectTrezor();
    console.log('Connected:', device.device.label);

    // 4. Get address
    const addressResult = await getTrezorAddress();
    console.log('Address:', addressResult.address);

    // 5. Verify on device (optional but recommended)
    await verifyAddressOnDevice();

    // 6. Sign transaction
    const tx = {
      from: addressResult.address,
      to: 'XAI5678...',
      amount: 100,
      fee: 1,
      nonce: 1,
    };

    const signature = await signWithTrezor(XAI_DEFAULT_PATH, tx);
    console.log('Signed:', signature.signature);

    // 7. Cleanup
    await disconnectTrezor();

  } catch (error) {
    if (error instanceof TrezorError) {
      switch (error.code) {
        case TrezorErrorCode.USER_CANCELLED:
          console.log('User cancelled');
          break;
        case TrezorErrorCode.DEVICE_NOT_CONNECTED:
          console.error('Connect device');
          break;
        default:
          console.error('Error:', error.message);
      }
    }
  }
}
```

## Error Handling

```javascript
try {
  await signWithTrezor(path, tx);
} catch (error) {
  if (error.code === TrezorErrorCode.USER_CANCELLED) {
    // User cancelled on device - don't show error
    return;
  }
  if (error.code === TrezorErrorCode.DEVICE_NOT_CONNECTED) {
    alert('Please connect your Trezor device');
    return;
  }
  if (error.code === TrezorErrorCode.POPUP_BLOCKED) {
    alert('Please allow popups for this extension');
    return;
  }
  // Other errors
  console.error('Trezor error:', error.message);
}
```

## Multiple Accounts

```javascript
import { getTrezorAddress, XAI_COIN_TYPE } from './trezor-hw.js';

// Get first 5 addresses
for (let i = 0; i < 5; i++) {
  const path = `m/44'/${XAI_COIN_TYPE}'/${i}'/0/0`;
  const result = await getTrezorAddress(path);
  console.log(`Account ${i}:`, result.address);
}
```

## UI Integration Example

```html
<div id="trezor-section">
  <button id="connect-trezor">Connect Trezor</button>
  <div id="trezor-info" class="hidden">
    <p>Address: <span id="trezor-address"></span></p>
    <button id="sign-tx">Sign Transaction</button>
    <button id="disconnect-trezor">Disconnect</button>
  </div>
</div>
```

```javascript
import { connectTrezor, getTrezorAddress, disconnectTrezor } from './trezor-hw.js';

document.getElementById('connect-trezor').onclick = async () => {
  try {
    await connectTrezor();
    const result = await getTrezorAddress();

    document.getElementById('trezor-address').textContent = result.address;
    document.getElementById('trezor-info').classList.remove('hidden');

    // Store for later use
    localStorage.setItem('trezorAddress', result.address);
  } catch (error) {
    alert('Failed to connect: ' + error.message);
  }
};

document.getElementById('disconnect-trezor').onclick = async () => {
  await disconnectTrezor();
  document.getElementById('trezor-info').classList.add('hidden');
  localStorage.removeItem('trezorAddress');
};
```

## Testing

Run examples in browser console:

```javascript
// Load examples module
import * as examples from './trezor-hw-example.js';

// Test complete workflow
await examples.example7_CompleteWorkflow();

// Test individual functions
await examples.example3_GetAddress();
await examples.example5_SignTransaction();
```

## Common Issues

**"Popup blocked"**
- User must allow popups for the extension

**"Device not found"**
- Check USB connection
- Install Trezor Bridge from trezor.io/bridge

**"Firmware outdated"**
- Update at wallet.trezor.io

## API Reference

See `TREZOR_INTEGRATION.md` for complete API documentation.

## Files

- `trezor-hw.js` - Main module (869 lines)
- `trezor-hw-example.js` - Usage examples (345 lines)
- `TREZOR_INTEGRATION.md` - Full documentation
- `TREZOR_QUICK_START.md` - This guide

## Support

- Trezor Docs: https://docs.trezor.io/
- Connect API: https://connect.trezor.io/docs/
- XAI Issues: [Your repo]/issues
