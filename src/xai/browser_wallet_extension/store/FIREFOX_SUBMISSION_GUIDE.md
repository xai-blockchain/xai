# Firefox Add-ons Submission Guide - XAI Browser Wallet

Step-by-step guide for submitting to Firefox Add-ons (AMO).

## Before You Start

- [ ] Developer account created (free)
- [ ] Privacy policy hosted at public URL
- [ ] Screenshots captured (1280x800)
- [ ] Package built: `xai-wallet-firefox-v0.2.0.zip`
- [ ] Source code repository accessible (GitHub/GitLab)

## Step 1: Developer Hub

1. Go to https://addons.mozilla.org/developers/
2. Sign in with Firefox Account (or create one)
3. Complete developer profile
4. Read and accept developer agreement

## Step 2: Submit Add-on

1. Click "Submit a New Add-on"
2. Choose distribution:
   - **On this site** ✓ (recommended - listed on AMO)
   - **On your own** (self-hosted, not listed)

3. Upload `xai-wallet-firefox-v0.2.0.zip`
4. Wait for validation (1-2 minutes)
5. Review validation results

## Step 3: Basic Information

**Name**: XAI Browser Wallet

**Slug**: xai-browser-wallet
(This becomes your AMO URL: addons.mozilla.org/firefox/addon/xai-browser-wallet/)

**Summary** (250 char limit):
```
Secure cryptocurrency wallet for XAI blockchain with hardware wallet support (Ledger/Trezor), mining controls, and decentralized trading. Full local control with no tracking.
```

**Description**:
```
XAI Browser Wallet is a secure, privacy-focused cryptocurrency wallet for the XAI blockchain ecosystem.

Key Features:

• Hardware Wallet Support: Full integration with Ledger and Trezor devices for maximum security
• Secure Key Storage: Military-grade encryption with PBKDF2 and AES-GCM
• Mining Controls: Monitor and control your mining operations directly from the browser
• Decentralized Trading: Access XAI's built-in DEX for trading without intermediaries
• Account Abstraction: Social recovery and multi-signature wallet support
• Transaction Management: View history, manage pending transactions, and monitor gas fees
• Privacy First: No tracking, no analytics, no third-party connections

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
• Privacy-conscious users

Permissions:
- storage: Local wallet data and settings
- alarms: Periodic updates for balance and mining status
- usb/hid: Hardware wallet communication (Ledger/Trezor)
- localhost access: Connect to your local XAI node
```

**Categories**:
- Primary: Other
- Secondary: Web Development

**Tags** (space-separated):
```
cryptocurrency blockchain wallet hardware-wallet ledger trezor mining dex privacy security
```

## Step 4: Version Information

**Version Number**: 0.2.0 (auto-detected from manifest)

**Release Notes**:
```
Version 0.2.0 - Initial Release

Features:
- Hardware wallet support (Ledger & Trezor)
- Encrypted local key storage
- Mining controls and monitoring
- DEX trading interface
- Social recovery features
- Account abstraction support
```

**License**: Choose one:
- MIT License
- GPL 3.0
- Apache 2.0
- Custom (provide URL)

**Source Code URL**: [Your GitHub/GitLab repository URL]

Example: `https://github.com/yourusername/xai-blockchain`

## Step 5: Support Information

**Homepage URL**: [Your XAI website]

**Support Email**: [Your support email]

**Support URL**: [GitHub issues or support site]

Example: `https://github.com/yourusername/xai-blockchain/issues`

## Step 6: Privacy Policy

**Privacy Policy URL**: [Your hosted privacy policy URL]

Must be publicly accessible without login.

## Step 7: Screenshots

Upload at least 1 (up to 10 recommended):

1. **Main Wallet Dashboard**
   - Caption: "Wallet dashboard with balance, address, and transaction history"

2. **Hardware Wallet Setup**
   - Caption: "Connect Ledger or Trezor hardware wallet for enhanced security"

3. **Transaction Signing**
   - Caption: "Sign transactions securely on your hardware wallet"

4. **Mining Dashboard**
   - Caption: "Monitor and control XAI mining operations"

5. **DEX Trading**
   - Caption: "Decentralized trading with XAI built-in DEX"

**Recommended Size**: 1280x800

**Drag to reorder** - First screenshot is primary

## Step 8: Permissions Justification

Firefox requires detailed explanation for sensitive permissions:

### storage
```
Required to save user wallet addresses, encrypted private keys, transaction history, and preferences locally in the browser. All data is encrypted using PBKDF2 and AES-GCM and stored only on the user's device.
```

### alarms
```
Used for periodic background updates of wallet balance and mining status without maintaining persistent connections. This enables the wallet to show fresh information when the user opens it, while minimizing resource usage.
```

### usb
```
Essential for communicating with Ledger hardware wallets via the WebUSB API. This allows secure transaction signing on the hardware device itself, ensuring private keys never leave the device. This is a core security feature of the wallet, providing cold storage security for user funds.
```

### hid (optional_permissions)
```
Alternative communication protocol for Trezor hardware wallets and some Ledger models using the WebHID API. This is an optional permission that users explicitly grant only when connecting their hardware wallet device.
```

### host_permissions (localhost:12001, localhost:12001)
```
Allows the wallet to connect to local XAI blockchain nodes running on the user's computer at standard JSON-RPC ports. This is essential for:
1. Developers testing smart contracts and blockchain features
2. Users who run their own nodes for maximum privacy and decentralization
3. Testing the extension against local testnets

No remote servers are contacted unless the user configures them.
```

### host_permissions (connect.trezor.io)
```
Required for Trezor Connect library to function properly. This is the official Trezor bridge service for browser-based hardware wallet integration, provided by SatoshiLabs (Trezor manufacturer). No user data or private keys are sent to this domain - it only facilitates communication with the hardware device.
```

## Step 9: Source Code (Important)

Firefox may request source code access. Prepare this information:

**Our Extension**:
- No build process used
- All JavaScript is vanilla/unminified
- Package contains actual source code
- Repository: [Your GitHub URL]

**If asked for build instructions**:
```
No build process required. Extension uses vanilla JavaScript with no compilation,
transpilation, or minification. All files in the package are human-readable source code.

To package:
1. git clone [repository-url]
2. cd src/xai/browser_wallet_extension
3. ./build.sh (copies files to build/ directory)
4. ./package-firefox.sh (creates zip)

The build.sh script only copies files and removes documentation.
No code transformation occurs.
```

## Step 10: Review

Before submitting, verify:

- [ ] All required fields filled
- [ ] Permission justifications detailed
- [ ] Privacy policy URL accessible
- [ ] Screenshots uploaded with captions
- [ ] Source code repository accessible
- [ ] License selected
- [ ] Support information provided
- [ ] Description accurate and complete

## Step 11: Submit

1. Click "Submit Version"
2. Note submission time
3. Monitor email for updates

**Expected Review Time**: 1-7 days (manual review)

## Step 12: After Approval

1. Extension goes live on AMO
2. Share your extension URL:
   ```
   https://addons.mozilla.org/firefox/addon/xai-browser-wallet/
   ```
3. Monitor user reviews
4. Respond to user feedback
5. Check developer hub for metrics

## Common Issues

### "Source Code Not Accessible"
**Issue**: Reviewer cannot access repository
**Fix**: Ensure GitHub/GitLab repository is public

### "Insufficient Permission Justification"
**Issue**: Permissions not explained in detail
**Fix**: Use detailed justifications above, explain exact use case

### "Remote Code Execution"
**Issue**: Suspected dynamic code loading
**Fix**: Explain no eval(), no remote scripts, all code in package

### "Missing CSP"
**Issue**: Content Security Policy not configured
**Fix**: We have CSP in manifest, point it out in review notes

### "Privacy Policy Incomplete"
**Issue**: Policy doesn't cover all data handling
**Fix**: Ensure policy mentions all permissions and data types

## Updates

To update the extension:

1. Increment version in manifest.json
2. Rebuild package: `./build.sh && ./package-firefox.sh`
3. Go to developer hub
4. Click "Upload New Version"
5. Add release notes explaining changes
6. Submit for review

**Update Review**: Usually faster than initial (1-3 days)

## Review Notes for Mozilla

Include this in the "Notes to Reviewer" section:

```
This extension requires hardware wallet permissions (USB/HID) for connecting to
Ledger and Trezor devices, which are industry-standard cryptocurrency hardware wallets.

Key Points:
- All blockchain communication is with user-specified nodes only
- No data collection or external tracking
- Localhost permissions are for local node development/testing
- Hardware wallet integration is core security functionality
- No remote code execution or dynamic imports
- All code is vanilla JavaScript with no build process

Testing:
- Can be tested with a local XAI node (instructions in repository)
- Hardware wallet features require physical Ledger/Trezor device
- Test credentials can be provided if needed

Source Code:
Full source code available at [repository URL]. No build process required -
extension uses vanilla JavaScript. All files in the package are the actual
source code. The build.sh script only copies files and removes documentation.
```

## Support Resources

- Developer Hub: https://addons.mozilla.org/developers/
- Extension Workshop: https://extensionworkshop.com/
- Documentation: https://extensionworkshop.com/documentation/
- Policies: https://extensionworkshop.com/documentation/publish/add-on-policies/
- Support: https://discourse.mozilla.org/c/add-ons/

## Checklist

Final check before submit:

- [ ] Package uploaded successfully
- [ ] Name, slug, and description compelling
- [ ] All permissions justified in detail
- [ ] Privacy policy URL provided
- [ ] At least 1 screenshot uploaded with caption
- [ ] Source code repository URL provided
- [ ] License selected
- [ ] Support information complete
- [ ] Categories and tags set
- [ ] Release notes written
- [ ] Review notes added
- [ ] No validation errors
- [ ] Tested extension in Firefox
