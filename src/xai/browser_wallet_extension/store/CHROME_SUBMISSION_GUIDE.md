# Chrome Web Store Submission Guide - XAI Browser Wallet

Step-by-step guide for submitting to Chrome Web Store.

## Before You Start

- [ ] Developer account created ($5 one-time fee)
- [ ] Privacy policy hosted at public URL
- [ ] Screenshots captured (1280x800)
- [ ] Package built: `xai-wallet-chrome-v0.2.0.zip`

## Step 1: Developer Dashboard

1. Go to https://chrome.google.com/webstore/devconsole
2. Sign in with Google account
3. Pay $5 registration fee (one-time, if not already paid)
4. Accept developer agreement

## Step 2: Upload Package

1. Click "New Item" button
2. Upload `xai-wallet-chrome-v0.2.0.zip`
3. Wait for validation (1-2 minutes)
4. Fix any errors reported

## Step 3: Store Listing

### Product Details

**Item Name**: XAI Browser Wallet

**Summary** (132 char limit):
```
Secure cryptocurrency wallet for XAI blockchain with hardware wallet support (Ledger/Trezor), mining controls, and decentralized trading.
```

**Description**:
```
XAI Browser Wallet is a secure, feature-rich cryptocurrency wallet for the XAI blockchain ecosystem.

Key Features:

• Hardware Wallet Support: Full integration with Ledger and Trezor devices for maximum security
• Secure Key Storage: Military-grade encryption with PBKDF2 and AES-GCM
• Mining Controls: Monitor and control your mining operations directly from the browser
• Decentralized Trading: Access XAI's built-in DEX for trading without intermediaries
• Account Abstraction: Social recovery and multi-signature wallet support
• Transaction Management: View history, manage pending transactions, and monitor gas fees
• Local Network Support: Connect to local XAI nodes for development and testing

Security Features:

• Hardware wallet support for cold storage security
• No private keys stored in plaintext
• Content Security Policy protection
• No third-party analytics or tracking
• Open-source and auditable code

Perfect For:

• XAI blockchain users and developers
• Cryptocurrency enthusiasts seeking hardware wallet integration
• Miners managing XAI operations
• Traders using decentralized exchanges
```

**Category**: Productivity

**Language**: English

### Privacy Practices

1. Click "Privacy practices"
2. Select data types handled:
   - [x] Financial and payment information
3. For each data type:
   - **Usage**: Essential functionality
   - **Is this data transmitted?**: Yes, encrypted
   - **Is this data sold?**: No
   - **Used for marketing?**: No
   - **Used by third parties?**: No

4. Privacy policy URL: [Your hosted URL]

### Permissions

**Justifications for each permission:**

**storage**
```
Required to save wallet addresses, encrypted private keys, transaction history, and user preferences locally in the browser. All data is encrypted and stored only on the user's device.
```

**alarms**
```
Used to periodically check wallet balance and mining status in the background without maintaining persistent connections. This enables the wallet to show updated information when the user opens it.
```

**usb**
```
Essential for communicating with Ledger hardware wallets via the WebUSB API. This allows secure transaction signing on the hardware device, ensuring private keys never leave the device. Core security feature of the wallet.
```

**hid** (optional_permissions)
```
Alternative communication protocol for Trezor hardware wallets and some Ledger models. This is an optional permission that users grant only when connecting their hardware wallet.
```

**host_permissions (localhost:12001, localhost:12001)**
```
Allows the wallet to connect to local XAI blockchain nodes running on the user's computer. Essential for developers testing smart contracts and users who run their own nodes for maximum privacy and decentralization.
```

**host_permissions (connect.trezor.io)**
```
Required for Trezor Connect library to function. This is the official Trezor bridge service for browser-based hardware wallet integration. No user data is sent to this domain.
```

## Step 4: Assets

### Icon
- Automatically extracted from extension (128x128)
- Verify it displays correctly

### Screenshots
Upload 3-5 screenshots at 1280x800 or 640x400:

1. **Main Dashboard** - Wallet balance, address, transaction list
2. **Hardware Wallet** - Device connection interface
3. **Send Transaction** - Transaction creation and signing
4. **Mining Dashboard** - Mining controls and status (optional)
5. **Trading Interface** - DEX order book (optional)

### Promotional Images (Optional)
- Small Promo Tile: 440x280 PNG
- Large Promo Tile: 920x680 PNG

## Step 5: Distribution

**Visibility**: Public

**Regions**: All regions (recommended)
- Or select specific countries if needed

**Pricing**: Free

## Step 6: Review

Before submitting, verify:

- [ ] All required fields filled
- [ ] Permission justifications detailed and clear
- [ ] Privacy policy URL accessible
- [ ] Screenshots show key features
- [ ] Description accurate and complete
- [ ] No prohibited content

## Step 7: Submit

1. Click "Submit for Review"
2. Note submission time
3. Monitor email for updates

**Expected Review Time**: 1-3 days (typically 1-2 days)

## Step 8: After Approval

1. Extension goes live automatically
2. Share your extension URL:
   ```
   https://chrome.google.com/webstore/detail/[extension-id]
   ```
3. Monitor user reviews in dashboard
4. Respond to user feedback

## Common Issues

### "Single Purpose" Violation
**Issue**: Extension does too many things
**Fix**: Focus description on wallet functionality as primary purpose

### "Overly Broad Permissions"
**Issue**: Requesting too many permissions
**Fix**: We already use minimal permissions. Justify each in detail.

### "Missing Privacy Policy"
**Issue**: Policy not accessible or incomplete
**Fix**: Ensure URL is public and includes all data handling practices

### "Poor Screenshots"
**Issue**: Low quality or unclear screenshots
**Fix**: Use 1280x800, show actual features, no placeholders

## Updates

To update the extension:

1. Increment version in manifest.json
2. Rebuild package: `./build.sh && ./package-chrome.sh`
3. Upload new package in dashboard
4. Update "What's new" section
5. Submit for review (faster than initial)

## Support Resources

- Developer Dashboard: https://chrome.google.com/webstore/devconsole
- Developer Docs: https://developer.chrome.com/docs/webstore/
- Support: https://support.google.com/chrome_webstore/

## Checklist

Final check before submit:

- [ ] Package uploaded successfully
- [ ] Extension name and description compelling
- [ ] All permissions justified in detail
- [ ] Privacy policy URL provided
- [ ] At least 1 screenshot uploaded (3-5 recommended)
- [ ] Category and language set
- [ ] Distribution settings configured
- [ ] No warnings or errors in dashboard
- [ ] Tested extension in Chrome
