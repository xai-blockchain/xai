# Changelog

All notable changes to XAI Wallet will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2024-XX-XX

### Added
- Initial release
- Wallet creation and secure storage
- Wallet import from private key
- Send XAI tokens
- Receive via QR code display
- Transaction history
- Block explorer integration
- Biometric authentication (Face ID, Touch ID, Fingerprint)
- PIN protection
- Testnet faucet integration
- Dark mode UI
- Deep linking support (xaiwallet://)
- Universal links (xai.network/wallet)

### Security
- Private keys stored in Secure Enclave (iOS) / Keystore (Android)
- TLS-only connections for production
- Backup disabled to protect private keys
- Session timeout for inactivity
