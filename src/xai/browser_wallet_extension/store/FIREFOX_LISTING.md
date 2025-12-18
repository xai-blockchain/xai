# Firefox Add-ons (AMO) Listing - XAI Browser Wallet

## Basic Information

**Extension Name**: XAI Browser Wallet

**Slug**: xai-browser-wallet

**Summary** (250 chars max):
Secure cryptocurrency wallet for XAI blockchain with hardware wallet support (Ledger/Trezor), mining controls, and decentralized trading. Full local control with no tracking.

## Description

XAI Browser Wallet is a secure, privacy-focused cryptocurrency wallet for the XAI blockchain ecosystem.

**Key Features:**

- **Hardware Wallet Support**: Full integration with Ledger and Trezor devices for maximum security
- **Secure Key Storage**: Military-grade encryption with PBKDF2 and AES-GCM
- **Mining Controls**: Monitor and control your mining operations directly from the browser
- **Decentralized Trading**: Access XAI's built-in DEX for trading without intermediaries
- **Account Abstraction**: Social recovery and multi-signature wallet support
- **Transaction Management**: View history, manage pending transactions, and monitor gas fees
- **Privacy First**: No tracking, no analytics, no third-party connections

**Security Features:**

- Hardware wallet support for cold storage security
- No private keys stored in plaintext
- Content Security Policy protection
- No third-party analytics or tracking
- Open-source and auditable code

**Perfect For:**

- XAI blockchain users and developers
- Cryptocurrency enthusiasts seeking hardware wallet integration
- Miners managing XAI operations
- Traders using decentralized exchanges
- Privacy-conscious users

**Permissions:**

- **storage**: Local wallet data and settings
- **alarms**: Periodic updates for balance and mining status
- **usb/hid**: Hardware wallet communication (Ledger/Trezor)
- **localhost access**: Connect to your local XAI node

## Categories

- **Other** (Cryptocurrency/Blockchain)
- **Web Development** (Developer Tools)

## Tags

- cryptocurrency
- blockchain
- wallet
- hardware-wallet
- ledger
- trezor
- mining
- dex
- privacy
- security

## License

**License**: [Your license - e.g., MIT, GPL-3.0]

**Link to Source Code**: [Your GitHub/GitLab repository URL]

Note: Firefox requires source code access for extensions using build processes.

## Privacy Policy

URL to hosted privacy policy (required): [Your privacy policy URL]

See `privacy-policy.md` for template.

## Support Information

- **Homepage**: [Your XAI website URL]
- **Support Site**: [Your support URL or GitHub issues]
- **Support Email**: [Your support email]

## Version Notes

### Version 0.2.0

- Hardware wallet support (Ledger & Trezor)
- Enhanced security with encrypted storage
- Mining controls and monitoring
- DEX trading interface
- Social recovery features
- Account abstraction support

## Firefox-Specific Settings

**Minimum Firefox Version**: 109.0 (Manifest V3 support)

**Strict Compatibility**: Enabled

**Gecko ID**: `{xai-wallet@example.com}` (update with your actual ID)

## Screenshots

Upload at least 3 screenshots (up to 10):

1. **Main Wallet Dashboard** - Balance, address, quick actions
2. **Hardware Wallet Setup** - Device connection wizard
3. **Transaction Signing** - Hardware wallet transaction approval
4. **Mining Dashboard** - Status, controls, and earnings
5. **DEX Trading** - Order book and trading interface

Recommended size: 1280x800 or similar

## Review Notes for Mozilla

This extension requires hardware wallet permissions (USB/HID) for connecting to Ledger and Trezor devices, which are industry-standard cryptocurrency hardware wallets.

**Key Points:**

- All blockchain communication is with user-specified nodes only
- No data collection or external tracking
- Localhost permissions are for local node development/testing
- Hardware wallet integration is core security functionality
- No remote code execution or dynamic imports

**Testing:**

- Can be tested with a local XAI node (instructions in repository)
- Hardware wallet features require physical Ledger/Trezor device
- Test credentials can be provided if needed

**Source Code:**

Full source code available at [repository URL]. No build process required - extension uses vanilla JavaScript. All files in the package are the actual source code.

## Manifest Permissions Justification

Submit detailed justification for each permission:

- **storage**: Required to save user wallet addresses, encrypted keys, and preferences locally in the browser
- **alarms**: Used for periodic background updates of wallet balance and mining status without keeping persistent connections
- **usb**: Essential for communication with Ledger hardware wallets via USB protocol for secure transaction signing
- **hid** (optional): Alternative communication method for Trezor hardware wallets and some Ledger models
- **host_permissions (localhost)**: Allows connection to local XAI blockchain nodes for development, testing, and users running their own nodes

No broad host permissions are requested - only localhost access.
