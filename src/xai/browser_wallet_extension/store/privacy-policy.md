# Privacy Policy - XAI Browser Wallet

**Last Updated**: December 18, 2025

## Overview

XAI Browser Wallet is committed to protecting your privacy. This extension is designed with privacy-first principles and does not collect, store, or transmit your personal information to any third parties.

## Information We Collect

### Stored Locally Only

All data is stored exclusively in your browser's local storage and never transmitted to our servers:

- **Wallet Addresses**: Your XAI blockchain addresses
- **Encrypted Private Keys**: Keys encrypted with your password (if not using hardware wallet)
- **Transaction History**: Retrieved from blockchain nodes you connect to
- **Preferences**: Settings like preferred RPC endpoint, display preferences
- **Mining Status**: Local cache of mining statistics

### Information We Do NOT Collect

- We do not collect analytics or usage data
- We do not track your browsing activity
- We do not collect personal identifying information
- We do not use cookies for tracking
- We do not share data with third parties
- We do not sell your data

## How We Use Information

All data processing happens locally in your browser:

- **Transaction Signing**: Private keys are used locally to sign blockchain transactions
- **Balance Updates**: Periodic queries to blockchain nodes you specify
- **Mining Controls**: Communication with XAI nodes for mining management
- **Hardware Wallets**: USB/HID communication directly with your Ledger/Trezor device

## Data Transmission

The extension communicates only with:

1. **Blockchain Nodes**: User-specified XAI blockchain nodes for transaction submission and balance queries
2. **Hardware Wallets**: Direct USB/HID communication with your Ledger/Trezor device (no internet required)
3. **Trezor Connect** (optional): If using Trezor, communication via Trezor's official bridge at `https://connect.trezor.io`

All blockchain communications use HTTPS/WSS encryption.

## Third-Party Services

The extension uses no third-party services except:

- **Trezor Connect**: Official Trezor service required for Trezor hardware wallet functionality (optional)

We do not use:
- Analytics services (Google Analytics, etc.)
- Crash reporting services
- Advertising networks
- Social media integrations

## Data Security

We implement industry-standard security practices:

- **Encryption**: Private keys encrypted with PBKDF2 and AES-GCM
- **Hardware Wallet Support**: Encourages use of hardware wallets for maximum security
- **Content Security Policy**: Prevents injection attacks
- **No Remote Code**: All code is bundled with the extension
- **Local Storage Only**: No cloud backups or syncing

## Your Rights and Controls

You have complete control over your data:

- **Export**: Export your encrypted wallet data at any time
- **Delete**: Remove all extension data via browser settings
- **No Account**: No registration or account creation required
- **Portable**: Your wallet can be used with any XAI-compatible software

## Children's Privacy

This extension is not intended for use by children under 13 years of age. We do not knowingly collect information from children.

## Changes to Privacy Policy

We may update this privacy policy to reflect changes in our practices or for legal compliance. Updates will be posted with a new "Last Updated" date.

## Open Source

XAI Browser Wallet is open source. You can review the source code to verify our privacy claims at [repository URL].

## Contact

For privacy questions or concerns:

- **Email**: [Your support email]
- **GitHub Issues**: [Your repository URL]/issues
- **Website**: [Your website URL]

## Legal Compliance

This extension complies with:

- GDPR (General Data Protection Regulation)
- CCPA (California Consumer Privacy Act)
- Chrome Web Store Developer Program Policies
- Firefox Add-on Policies

## Data Retention

- **Local Storage**: Data persists until you manually delete it or uninstall the extension
- **No Server Storage**: We do not store any of your data on servers
- **Blockchain Data**: Transaction history is public on the XAI blockchain (inherent to blockchain technology)

## Blockchain Privacy Note

Important: Blockchain transactions are public by design. While this extension does not collect your data, transactions you broadcast to the XAI blockchain are publicly visible on the blockchain. Use appropriate privacy practices when transacting on public blockchains.

## Your Consent

By using XAI Browser Wallet, you consent to this privacy policy.

---

**Questions?** Contact us at [your email] or open an issue at [repository URL].
