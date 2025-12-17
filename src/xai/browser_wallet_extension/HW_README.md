# XAI Hardware Wallet Integration

Complete hardware wallet support for the XAI blockchain browser extension, providing unified access to both Ledger and Trezor devices.

## Overview

This implementation provides direct client-side communication with hardware wallets through WebHID (Ledger) and Trezor Connect (Trezor), eliminating the need for backend API dependencies.

### Features

- **Unified API**: Single interface for both Ledger and Trezor devices
- **Direct Communication**: No backend required - talks directly to devices
- **Event-Driven**: Real-time UI updates via event listeners
- **Transaction Signing**: Full XAI transaction format support
- **Message Signing**: Arbitrary message signing for authentication
- **BIP32 Path Support**: Configurable derivation paths
- **Error Handling**: User-friendly error messages
- **Connection Management**: Auto-reconnection and state tracking

## Architecture

```
hw-manager.js (Unified Manager)
    ├── ledger-hw.js (Ledger Communication)
    │   └── WebHID / WebUSB (Browser APIs)
    └── trezor-hw.js (Trezor Communication)
        └── Trezor Connect (Official SDK)
```

## Files

- **`hw-manager.js`**: Unified hardware wallet manager
- **`ledger-hw.js`**: Ledger device communication via WebHID/WebUSB
- **`trezor-hw.js`**: Trezor device communication via Trezor Connect
- **`hw-demo.html`**: Interactive demo and testing page

## Quick Start

### 1. Include the Modules

```html
<!-- Load hardware wallet modules -->
<script src="ledger-hw.js"></script>
<script src="trezor-hw.js"></script>
<script src="hw-manager.js"></script>
```

### 2. Initialize Manager

```javascript
const hwManager = new HardwareWalletManager({
    bip32Path: "m/44'/22593'/0'/0/0",  // XAI coin type
    autoReconnect: false,
});
```

### 3. Connect to Device

```javascript
try {
    const walletInfo = await hwManager.connect('ledger');
    // or
    const walletInfo = await hwManager.connect('trezor');

    console.log('Address:', walletInfo.address);
    console.log('Public Key:', walletInfo.publicKey);
} catch (err) {
    console.error('Connection failed:', err.message);
}
```

### 4. Sign Transaction

```javascript
const txPayload = {
    sender: walletInfo.address,
    recipient: 'XAI0123456789abcdef...',
    amount: 1.5,
    fee: 0.001,
    nonce: 0,
    memo: 'Payment',
    network: 'mainnet',
};

const signedTx = await hwManager.signTransaction(txPayload);
console.log('Signature:', signedTx.signature);
```

## API Reference

### HardwareWalletManager

#### Static Methods

##### `getSupportedWallets()`
Returns array of supported wallet types based on browser capabilities.

```javascript
const supported = HardwareWalletManager.getSupportedWallets();
// => ['ledger', 'trezor']
```

##### `getWalletName(type)`
Get user-friendly name for wallet type.

```javascript
const name = HardwareWalletManager.getWalletName('ledger');
// => 'Ledger'
```

#### Instance Methods

##### `connect(walletType, options)`
Connect to a hardware wallet device.

**Parameters:**
- `walletType` (string): 'ledger' or 'trezor'
- `options` (object, optional):
  - `bip32Path` (string): Override default BIP32 path

**Returns:** `Promise<WalletInfo>`

```javascript
const info = await hwManager.connect('ledger', {
    bip32Path: "m/44'/22593'/0'/0/1"  // Use account 1
});
```

##### `disconnect()`
Disconnect from the current device.

```javascript
await hwManager.disconnect();
```

##### `isConnected()`
Check if a wallet is currently connected.

```javascript
if (hwManager.isConnected()) {
    console.log('Wallet is connected');
}
```

##### `getConnectedWallet()`
Get information about the connected wallet.

**Returns:** `WalletInfo | null`

```javascript
const info = hwManager.getConnectedWallet();
if (info) {
    console.log('Type:', info.type);
    console.log('Address:', info.address);
}
```

##### `getAddress(showOnDevice)`
Get XAI address from the connected wallet.

**Parameters:**
- `showOnDevice` (boolean): Display address on device for verification

**Returns:** `Promise<string>`

```javascript
// Silent retrieval
const address = await hwManager.getAddress(false);

// Verify on device
const address = await hwManager.getAddress(true);
```

##### `signTransaction(txPayload)`
Sign a transaction with the hardware wallet.

**Parameters:**
- `txPayload` (object): Transaction payload

**Returns:** `Promise<SignedTransaction>`

```javascript
const signedTx = await hwManager.signTransaction({
    sender: 'XAI...',
    recipient: 'XAI...',
    amount: 1.0,
    fee: 0.001,
    nonce: 0,
    memo: 'Test',
    network: 'mainnet',
});
```

##### `signMessage(message)`
Sign an arbitrary message.

**Parameters:**
- `message` (string | Uint8Array): Message to sign

**Returns:** `Promise<string>` - Signature as hex string

```javascript
const signature = await hwManager.signMessage('Hello, XAI!');
```

##### `on(event, callback)`
Register an event listener.

**Events:**
- `connecting`: Wallet connection started
- `connected`: Wallet successfully connected
- `disconnected`: Wallet disconnected
- `signing`: Signature operation started
- `signed`: Signature completed
- `error`: Error occurred

```javascript
hwManager.on('connected', (walletInfo) => {
    console.log('Connected to:', walletInfo.type);
});

hwManager.on('error', (data) => {
    console.error('Error:', data.error);
});
```

##### `off(event, callback)`
Unregister an event listener.

```javascript
const handler = (data) => console.log(data);
hwManager.on('connected', handler);
hwManager.off('connected', handler);
```

### Helper Functions

#### `buildUnsignedTransaction(from, to, amount, fee, nonce, options)`
Build an unsigned transaction object.

```javascript
const unsignedTx = buildUnsignedTransaction(
    'XAI_sender...',
    'XAI_recipient...',
    1.5,      // amount
    0.001,    // fee
    0,        // nonce
    {
        memo: 'Payment',
        network: 'mainnet',
    }
);
```

#### `combineSignature(unsignedTx, signature, publicKey)`
Combine unsigned transaction with signature.

```javascript
const signedTx = await combineSignature(
    unsignedTx,
    'a1b2c3d4...',  // signature hex
    'e5f6g7h8...'   // public key hex
);
```

## Data Types

### WalletInfo

```typescript
{
    type: 'ledger' | 'trezor',
    address: string,        // XAI address
    publicKey: string,      // 64-byte hex public key
    bip32Path: string,      // BIP32 derivation path
    connectedAt: number,    // Connection timestamp (ms)
}
```

### TransactionPayload

```typescript
{
    sender: string,         // Sender XAI address
    recipient: string,      // Recipient XAI address
    amount: number,         // Amount to send
    fee: number,           // Transaction fee
    nonce: number,         // Transaction nonce
    memo?: string,         // Optional memo
    network?: string,      // 'mainnet' or 'testnet'
    chainId?: number,      // Chain ID (default: 22593)
}
```

### SignedTransaction

```typescript
{
    transaction: {
        version: string,
        tx_type: string,
        sender: string,
        recipient: string,
        amount: number,
        fee: number,
        nonce: number,
        memo: string,
        network: string,
        created_at: number,
    },
    signature: string,      // 128-char hex (64 bytes)
    publicKey: string,      // 128-char hex (64 bytes)
    payloadHash: string,    // SHA-256 hash
    signedAt: number,       // Signature timestamp
}
```

## Browser Compatibility

### Ledger (via WebHID/WebUSB)
- Chrome/Edge 89+
- Opera 76+
- Brave (with shields down)
- **Not supported:** Firefox, Safari

### Trezor (via Trezor Connect)
- All modern browsers
- Works in Firefox and Safari

## Security Considerations

### Private Keys
- **Never leave the device**: All signing happens on-device
- **User confirmation required**: Every transaction must be approved on device
- **No caching**: Private keys are never stored in memory or disk

### Connection State
- Connection state is ephemeral (not persisted)
- Must reconnect after page reload
- Auto-reconnection can be enabled for convenience

### Transaction Review
- All transaction details shown on device screen
- User must verify recipient, amount, and fee before signing
- Device buttons required for confirmation

## Error Handling

The manager provides user-friendly error messages:

```javascript
try {
    await hwManager.connect('ledger');
} catch (err) {
    // Common errors:
    // "Transaction was rejected on the device."
    // "Ledger device not found. Please connect it and unlock."
    // "Please open the XAI (or Ethereum) app on your Ledger."
    console.error(err.message);
}
```

## XAI Transaction Format

The hardware wallet manager uses the XAI blockchain's canonical transaction format:

```json
{
    "version": "1.0",
    "tx_type": "transfer",
    "sender": "XAI...",
    "recipient": "XAI...",
    "amount": 1.0,
    "fee": 0.001,
    "nonce": 0,
    "memo": "",
    "network": "mainnet",
    "created_at": 1234567890
}
```

The payload is canonicalized (sorted keys) and hashed with SHA-256 before signing.

## BIP32 Derivation Paths

XAI uses coin type `22593` (registered in SLIP-44).

Default path: `m/44'/22593'/0'/0/0`

Path components:
- `44'`: BIP44 purpose (hardened)
- `22593'`: XAI coin type (hardened)
- `0'`: Account (hardened)
- `0`: Change (external addresses)
- `0`: Address index

To use different accounts:
```javascript
const hwManager = new HardwareWalletManager({
    bip32Path: "m/44'/22593'/1'/0/0"  // Account 1
});
```

## Testing

Open `hw-demo.html` in a supported browser to test:

1. Connect your hardware wallet
2. Verify address on device
3. Sign test transactions
4. Sign messages
5. Monitor events in the log

## Integration with Browser Extension

### manifest.json

Add permissions for hardware wallet access:

```json
{
    "permissions": [
        "usb",
        "hid"
    ],
    "host_permissions": [
        "https://connect.trezor.io/*"
    ]
}
```

### Content Security Policy

Allow Trezor Connect iframe:

```json
{
    "content_security_policy": {
        "extension_pages": "script-src 'self' https://connect.trezor.io; object-src 'self'"
    }
}
```

### Example Integration

```javascript
// In popup.js or background.js
import { HardwareWalletManager } from './hw-manager.js';

const hwManager = new HardwareWalletManager();

// Listen for connection events
hwManager.on('connected', (walletInfo) => {
    chrome.storage.local.set({ hwAddress: walletInfo.address });
    updateUI(walletInfo);
});

// Connect button handler
document.getElementById('connectLedger').addEventListener('click', async () => {
    try {
        await hwManager.connect('ledger');
    } catch (err) {
        showError(err.message);
    }
});

// Sign transaction handler
async function signAndBroadcast(txPayload) {
    try {
        const signedTx = await hwManager.signTransaction(txPayload);

        // Broadcast to XAI network
        const response = await fetch('https://api.xai.network/broadcast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(signedTx),
        });

        const result = await response.json();
        return result.txHash;
    } catch (err) {
        throw new Error(`Transaction failed: ${err.message}`);
    }
}
```

## Troubleshooting

### Ledger Not Detected
- Ensure device is unlocked
- Open the Ethereum app on Ledger
- Enable "Contract data" in Ethereum app settings
- Try disconnecting and reconnecting the USB cable
- Check browser compatibility (Chrome/Edge only)

### Trezor Connection Fails
- Check that Trezor Bridge or Trezor Suite is running
- Allow popup from connect.trezor.io
- Ensure device firmware is up to date

### Transaction Rejected
- Verify transaction details on device screen
- Check that amounts and addresses match expectations
- Ensure sufficient device battery (for wireless models)

### "App not open" Error
- Open the Ethereum app on your Ledger
- XAI transactions use Ethereum app for signing
- Future: Dedicated XAI app for Ledger

## Future Enhancements

- [ ] Native XAI app for Ledger devices
- [ ] Multi-signature transaction support
- [ ] Account discovery (scanning multiple addresses)
- [ ] Connection persistence across sessions
- [ ] Support for additional hardware wallets (GridPlus, etc.)
- [ ] EIP-712 typed data signing
- [ ] WebAuthn integration for 2FA

## License

Part of the XAI blockchain project. See main repository LICENSE.

## Support

For issues or questions:
- GitHub: [XAI Blockchain Repository]
- Documentation: [XAI Docs]
- Discord: [XAI Community]
