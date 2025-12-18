# Changelog

All notable changes to the XAI React Native SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-18

### Added
- Initial release of XAI React Native SDK
- Secure wallet management with hardware-backed key storage
- Biometric authentication support (Face ID / Touch ID)
- React hooks for easy integration:
  - `useWallet` - Wallet management with auto-refresh
  - `useBalance` - Balance monitoring
  - `useTransactions` - Transaction sending and tracking
  - `useBlockchain` - Blockchain state monitoring
- Complete TypeScript support with full type definitions
- Encrypted secure storage using react-native-keychain
- Push notifications framework with Firebase integration hooks
- HTTP client with automatic retry logic
- Comprehensive error handling with typed errors
- Production-ready cryptographic utilities
- Complete API client for XAI blockchain nodes
- Extensive documentation and examples
- Unit tests with Jest

### Features
- Hardware-backed secure key storage
- Mnemonic phrase generation and import (BIP39)
- ECDSA signing with secp256k1
- Encrypted local storage for sensitive data
- Automatic balance and transaction updates
- Transaction fee estimation
- Governance proposal voting
- Network peer management
- Mining statistics
- Complete blockchain querying

### Security
- Private keys encrypted with random passwords
- Master encryption key stored in device keychain
- Biometric authentication for sensitive operations
- Keys never leave the device
- Secure enclave support (iOS) / Keystore support (Android)

### Documentation
- Comprehensive README with examples
- Complete API documentation
- Security best practices guide
- TypeScript type definitions
- Example implementations
- Testing guide

## [Unreleased]

### Planned
- WebSocket support for real-time updates
- Hardware wallet integration (Ledger, Trezor)
- Multi-wallet management
- Transaction history export
- QR code generation and scanning
- Deep linking support
- WalletConnect integration
- NFT support
- Contract interaction utilities
- Advanced transaction batching
- Gas optimization tools
