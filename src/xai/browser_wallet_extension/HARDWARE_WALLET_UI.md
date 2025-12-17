# Hardware Wallet UI Integration

This document describes the browser extension UI components for hardware wallet support in the XAI wallet.

## Overview

The hardware wallet UI provides a seamless, production-ready interface for connecting Ledger and Trezor devices to the XAI browser wallet extension. It handles device connection, address management, and transaction signing with clear user prompts and error handling.

## Architecture

### Components

1. **hw-manager.js** - Hardware wallet manager
   - Bridges browser extension and backend API
   - Manages connection state
   - Handles device communication via backend endpoints
   - Provides unified interface for Ledger and Trezor

2. **hw-ui.js** - UI controller
   - Manages modal dialogs and user prompts
   - Handles connection flow UX
   - Shows signing prompts with device confirmation
   - Provides error handling with user guidance

3. **hw-styles.css** - Styling
   - Dark theme matching existing extension
   - Responsive design
   - Animations and transitions
   - Accessibility support

4. **popup-hw.html** - Enhanced popup
   - Integrates hardware wallet UI into extension
   - Includes all necessary HTML elements
   - Loads scripts in correct order

5. **popup-hw-integration.js** - Integration layer
   - Overrides signing functions to support hardware wallets
   - Falls back to software signing when no HW connected
   - Maintains compatibility with existing code

## File Structure

```
browser_wallet_extension/
├── hw-manager.js           # Hardware wallet manager
├── hw-ui.js                # UI controller
├── hw-styles.css           # Hardware wallet styles
├── popup-hw.html           # Enhanced popup with HW support
├── popup-hw-integration.js # Integration overrides
├── popup.js                # Original popup logic (unchanged)
├── styles.css              # Original styles (unchanged)
└── HARDWARE_WALLET_UI.md   # This file
```

## Usage

### For Users

1. **Connect Hardware Wallet**
   - Click "Connect Hardware Wallet" button in Settings
   - Select device type (Ledger or Trezor)
   - Unlock device and open XAI app if prompted
   - Extension auto-populates address

2. **Sign Transactions**
   - Create order or transaction as usual
   - Extension detects hardware wallet
   - Prompt appears: "Please confirm on your Ledger/Trezor"
   - Confirm on device
   - Transaction submitted automatically

3. **Disconnect**
   - Click "Disconnect" button
   - Can switch to manual address entry

### For Developers

#### Using the Hardware Wallet Manager

```javascript
// Initialize
const hwManager = new HardwareWalletManager();
await hwManager.initialize('http://localhost:8545');

// Connect device
const result = await hwManager.connect('ledger'); // or 'trezor'
console.log(result.address);

// Sign transaction
const signature = await hwManager.signTransaction(payload);

// Check status
const state = hwManager.getState();
console.log(state.connected, state.deviceType, state.address);

// Disconnect
await hwManager.disconnect();
```

#### Using the UI Controller

```javascript
// Initialize UI
const hwUI = new HardwareWalletUI(hwManager);
hwUI.initialize();

// Check if hardware wallet should be used
if (hwUI.shouldUseHardwareWallet()) {
  // Sign with UI prompts
  const signature = await hwUI.signTransactionWithUI(payload);
} else {
  // Fall back to software signing
}
```

## Backend API Requirements

The UI expects these backend endpoints:

### POST /hardware-wallet/connect
Connect to hardware wallet device.

**Request:**
```json
{
  "device_type": "ledger"  // or "trezor"
}
```

**Response:**
```json
{
  "success": true,
  "address": "XAI1234...",
  "public_key": "04abcd..."
}
```

### POST /hardware-wallet/sign
Sign transaction with hardware wallet.

**Request:**
```json
{
  "device_type": "ledger",
  "payload": { /* transaction object */ }
}
```

**Response:**
```json
{
  "success": true,
  "signature": "abcd1234..."
}
```

### GET /hardware-wallet/status
Check device connection status.

**Request:**
```
?device_type=ledger
```

**Response:**
```json
{
  "connected": true,
  "device_type": "ledger"
}
```

## UI/UX Features

### Connection Flow

1. User clicks "Connect Hardware Wallet"
2. Modal shows device selection (Ledger/Trezor)
3. User selects device
4. Connecting spinner with device name
5. Success message (1.5s) or error with retry
6. Modal closes, status indicator updates

### Status Indicators

- **Disconnected**: Gray dot, "No Hardware Wallet"
- **Connected**: Pulsing blue dot, "Ledger Connected" or "Trezor Connected"
- Address display: Shortened format (XAI1234...abc789)

### Signing Flow

1. User submits transaction
2. Extension detects hardware wallet
3. Signing prompt appears with:
   - Device name
   - Transaction details (expandable)
   - Status: "Waiting for confirmation..."
4. User confirms on device
5. Status updates: "Transaction signed successfully!"
6. Prompt closes automatically

### Error Handling

User-friendly error messages:
- "Ledger not detected" → "Please connect your device and unlock it"
- "App not open" → "Please open the XAI app on your Ledger device"
- "User rejected" → "Connection was rejected on the device"
- "Timeout" → "Connection timed out. Ensure device is connected and unlocked"

## Styling

### Color Scheme

- Primary: `#7b4ef5` (purple gradient for hardware wallet)
- Success: `#5fe2fb` (cyan)
- Error: `#ff8ea2` (pink)
- Background: Dark gradient matching extension theme

### Key Visual Elements

- **Device Icons**: Ledger (blue), Trezor (green)
- **Status Dot**: Animated pulse when connected
- **Modals**: Glassmorphism with backdrop blur
- **Animations**: Smooth fade-in, slide-up, spin

### Responsive Design

- Desktop: 360px+ width
- Mobile: Optimized touch targets
- Keyboard navigation: Full support with focus indicators

## Security Considerations

1. **Private Keys Never Leave Device**
   - All signing happens on hardware wallet
   - Backend only sends/receives transaction data

2. **State Management**
   - Connection state stored in chrome.storage.local
   - No private keys or sensitive data stored
   - State cleared on disconnect

3. **User Confirmation Required**
   - Hardware device confirmation for all signatures
   - Clear transaction preview before signing

4. **Fallback to Software Signing**
   - If no hardware wallet connected
   - Uses existing private key flow
   - Clear separation of code paths

## Testing

### Manual Testing

1. **Connection**
   - Test Ledger connection
   - Test Trezor connection
   - Test error cases (locked, no device, wrong app)

2. **Signing**
   - Submit order with hardware wallet
   - Confirm on device
   - Verify signature accepted by backend
   - Test rejection on device

3. **Disconnect**
   - Disconnect and reconnect
   - Switch between devices
   - Fall back to manual entry

### Browser Compatibility

- Chrome/Chromium: Full support
- Edge: Full support
- Firefox: Full support (as WebExtension)
- Safari: Requires manifest v3 adjustments

## Troubleshooting

### Hardware wallet not detected

1. Check device is connected and unlocked
2. Verify XAI app is open on device
3. Check backend is running and accessible
4. Review browser console for errors

### Signing fails

1. Ensure transaction payload is valid
2. Check device has not timed out
3. Verify backend signing endpoint is working
4. Review device logs if available

### UI not appearing

1. Check all scripts are loaded in correct order
2. Verify popup-hw.html is being used
3. Check browser console for JavaScript errors
4. Ensure hw-styles.css is loaded

## Future Enhancements

Potential improvements:

1. **Multi-device Support**
   - Connect multiple hardware wallets
   - Switch between devices
   - Device management interface

2. **Advanced Settings**
   - Custom BIP32 derivation paths
   - Multiple addresses per device
   - Address book integration

3. **Enhanced Security**
   - Blind signing warnings
   - Transaction verification checksums
   - Rate limiting and timeouts

4. **Better Error Recovery**
   - Automatic reconnection
   - Device detection polling
   - Detailed diagnostic information

5. **Additional Device Support**
   - KeepKey
   - CoolWallet
   - BitBox
   - Other hardware wallets

## Integration Checklist

To integrate hardware wallet UI into your extension:

- [ ] Copy all hw-*.js and hw-*.css files
- [ ] Use popup-hw.html instead of popup.html
- [ ] Implement backend API endpoints
- [ ] Update manifest.json if needed (permissions)
- [ ] Test connection flow
- [ ] Test signing flow
- [ ] Test error handling
- [ ] Verify mobile responsiveness
- [ ] Check accessibility
- [ ] Update user documentation

## Resources

- Backend implementation: `src/xai/core/hardware_wallet.py`
- Ledger integration: `src/xai/core/hardware_wallet_ledger.py`
- Trezor integration: `src/xai/core/hardware_wallet_trezor.py`
- API documentation: `docs/api/HARDWARE_WALLET.md`

## Support

For issues or questions:
1. Check browser console for errors
2. Review backend logs for API errors
3. Test with mock hardware wallet first
4. Consult hardware wallet device documentation
