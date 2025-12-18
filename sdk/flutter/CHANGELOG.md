# Changelog

All notable changes to the XAI SDK for Flutter will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-XX

### Added
- Initial release of XAI SDK for Flutter
- XAIClient for HTTP/WebSocket communication with blockchain nodes
  - Automatic retry logic with exponential backoff
  - Connection pooling and timeout handling
  - Real-time updates via WebSocket
  - Support for all node API endpoints
- XAIWallet for secure wallet management
  - ECDSA key generation (secp256k1)
  - Secure storage using flutter_secure_storage
  - Multi-wallet support
  - Import/export functionality
  - Biometric authentication integration
- XAITransaction for transaction building and signing
  - UTXO-based transaction model
  - Automatic nonce management
  - Balance validation
  - Transaction status tracking
  - Wait for confirmation functionality
- BiometricAuth service
  - Face ID support (iOS)
  - Touch ID support (iOS)
  - Fingerprint support (Android)
  - Transaction signing with biometric authentication
- PushNotifications service
  - Firebase Cloud Messaging integration
  - Transaction notifications
  - Block notifications
  - Price alerts
  - Security alerts
  - Topic-based subscriptions
- CryptoUtils for cryptographic operations
  - ECDSA key pair generation
  - Message signing and verification
  - Address generation and validation
  - Public key derivation
- Comprehensive error handling
- Full TypeScript-style API documentation
- Example app demonstrating all features
- Unit tests for core functionality

### Security
- Private keys stored securely using platform keychain
- Biometric authentication for sensitive operations
- Signature verification for all transactions
- Address validation before transaction submission
- Secure random number generation for key pairs

## [Unreleased]

### Planned Features
- Hardware wallet support (Ledger, Trezor)
- Multi-signature wallet support
- QR code scanner for addresses
- Transaction history caching
- Offline transaction signing
- Custom fee estimation
- Gas price oracle integration
- Contract interaction support
- NFT support
- Staking functionality
- Governance voting
- Advanced analytics
- Performance optimizations
- Additional test coverage

### Known Issues
- WebSocket reconnection may require manual intervention
- Large transaction histories may cause memory issues
- Firebase configuration must be done manually

## Release Notes

### Version 1.0.0

This is the initial production release of the XAI SDK for Flutter. It provides a complete, secure, and easy-to-use interface for building XAI blockchain applications on mobile devices.

**Key Features:**
- Complete blockchain client implementation
- Secure wallet management with biometric authentication
- Transaction building, signing, and validation
- Real-time blockchain updates via WebSocket
- Push notifications for important events
- Production-ready cryptography
- Comprehensive documentation and examples

**Platform Support:**
- iOS 12.0+
- Android API 23+ (Android 6.0+)
- Web (partial support)

**Dependencies:**
- Flutter 3.10.0+
- Dart 3.0.0+

For migration guides, tutorials, and API documentation, visit:
https://xai-blockchain.io/docs/sdk/flutter
