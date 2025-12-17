# Hardware Wallet UI - Quick Start Guide

## Installation

The hardware wallet UI is already integrated into the browser extension. No additional installation required.

## Files Created

1. **hw-manager.js** - Hardware wallet connection and signing logic
2. **hw-ui.js** - UI controller for modals, prompts, and status
3. **hw-styles.css** - Styling for hardware wallet components
4. **popup-hw.html** - Enhanced popup with hardware wallet support
5. **popup-hw-integration.js** - Integration layer with existing popup.js

## Quick Test

### 1. Load Extension

```bash
cd /home/hudson/blockchain-projects/xai/src/xai/browser_wallet_extension
# In Chrome: chrome://extensions → Load unpacked → Select this directory
# Ensure popup-hw.html is set as default_popup in manifest.json (already done)
```

### 2. Connect Hardware Wallet

1. Open extension popup
2. Go to Settings section
3. Click "🔐 Connect Hardware Wallet"
4. Select Ledger or Trezor
5. Follow device prompts

### 3. Sign Transaction

1. Fill in Trade Studio form
2. Click "Create Order"
3. Signing prompt appears automatically
4. Confirm on hardware device
5. Order submitted

## API Endpoints Required

Ensure your backend implements these endpoints:

```python
@app.post("/hardware-wallet/connect")
async def connect_hardware_wallet(request: dict):
    """
    Connect to hardware wallet device.
    Request: {"device_type": "ledger" or "trezor"}
    Response: {"success": bool, "address": str, "public_key": str}
    """
    pass

@app.post("/hardware-wallet/sign")
async def sign_with_hardware_wallet(request: dict):
    """
    Sign transaction with hardware wallet.
    Request: {"device_type": str, "payload": dict}
    Response: {"success": bool, "signature": str}
    """
    pass

@app.get("/hardware-wallet/status")
async def hardware_wallet_status(device_type: str):
    """
    Check hardware wallet status.
    Response: {"connected": bool, "device_type": str}
    """
    pass
```

## Testing Without Hardware Device

Use the mock hardware wallet:

```bash
# Backend: Enable mock hardware wallet
export XAI_HARDWARE_WALLET_ENABLED=true
export XAI_HARDWARE_WALLET_PROVIDER=mock
export XAI_ALLOW_MOCK_HARDWARE_WALLET=true

# Start backend
python -m xai.core.node
```

## UI Elements

### Status Indicator
- **Disconnected**: Gray dot, "No Hardware Wallet"
- **Connected**: Blue pulsing dot, "Ledger Connected" or "Trezor Connected"

### Connection Modal
- Device selection: Ledger / Trezor buttons
- Connecting view: Spinner with device name
- Error messages: User-friendly guidance
- Success message: Brief confirmation

### Signing Prompt
- Device name display
- Transaction details (expandable)
- Status updates: Waiting → Success/Error
- Auto-closes on success

## Customization

### Colors

Edit `hw-styles.css`:
```css
/* Primary hardware wallet color */
.hw-button--connect {
  background: linear-gradient(120deg, #7b4ef5, #9b6efb);
}

/* Connected status color */
.hw-status--connected {
  background: rgba(94, 226, 251, 0.15);
  color: #5fe2fb;
}
```

### Device Icons

Update device icons in `popup-hw.html`:
```html
<div class="hw-device-icon hw-device-icon--ledger">L</div>
<div class="hw-device-icon hw-device-icon--trezor">T</div>
```

Replace `L` and `T` with emoji or SVG icons.

## Troubleshooting

### UI Not Appearing

**Check script load order:**
```html
<script src="hw-manager.js"></script>
<script src="hw-ui.js"></script>
<script src="popup.js"></script>
<script src="popup-hw-integration.js"></script>
```

**Check console:**
- Should see: "Hardware wallet support initialized"
- Look for JavaScript errors

### Connection Fails

**Backend issues:**
- Verify backend is running
- Check `/hardware-wallet/connect` endpoint exists
- Review backend logs for errors

**Device issues:**
- Ensure device is connected and unlocked
- Verify XAI app is open on device
- Check USB/HID permissions

### Signing Fails

**Check payload format:**
```javascript
// Valid payload structure
{
  maker_address: "XAI1234...",
  maker_public_key: "04abcd...",
  token_offered: "XAI",
  amount_offered: 100,
  // ... etc
}
```

**Verify signature format:**
- Should be hex string
- 128 characters (64 bytes)
- r || s format

## Integration with Existing Code

The integration layer (`popup-hw-integration.js`) automatically:
1. Detects if hardware wallet is connected
2. Routes signing to hardware wallet OR software key
3. Maintains compatibility with existing functions
4. No changes needed to popup.js

## Production Checklist

- [ ] Backend API endpoints implemented
- [ ] Hardware wallet drivers installed (ledgerblue, trezor)
- [ ] USB/HID permissions granted
- [ ] Error handling tested
- [ ] User documentation updated
- [ ] Security review completed
- [ ] UI/UX tested on target browsers
- [ ] Mobile responsive testing done
- [ ] Accessibility compliance verified

## Common Issues

### "No Hardware Wallet" always showing

**Fix:** Check initialization
```javascript
// In browser console
console.log(window.hwManager);
console.log(window.hwUI);
// Should not be undefined
```

### Modal doesn't close

**Fix:** Check ESC key handler
```javascript
// hw-ui.js should have ESC listener
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    this.hideConnectionModal();
  }
});
```

### Private key still required

**Fix:** Hardware wallet integration should hide private key requirement
```javascript
// popup-hw-integration.js checks:
if (usingHardwareWallet) {
  // Skip private key check
} else {
  // Require private key
}
```

## Architecture Diagram

```
User Action (Submit Order)
        ↓
popup-hw-integration.js
        ↓
    Check if HW connected? ──No──> Software Signing (popup.js)
        ↓ Yes
    hw-ui.js (Show prompts)
        ↓
    hw-manager.js (API calls)
        ↓
    Backend API (/hardware-wallet/sign)
        ↓
    Hardware Device (User confirms)
        ↓
    Signature returned
        ↓
    Transaction submitted
```

## Support

For detailed documentation, see:
- **HARDWARE_WALLET_UI.md** - Complete documentation
- **Backend:** `src/xai/core/hardware_wallet.py`
- **Ledger:** `src/xai/core/hardware_wallet_ledger.py`
- **Trezor:** `src/xai/core/hardware_wallet_trezor.py`
