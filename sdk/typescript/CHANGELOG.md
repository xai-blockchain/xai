# Changelog

All notable changes to the XAI TypeScript SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-XX

### Added
- Initial release of XAI TypeScript/JavaScript SDK
- Full TypeScript type definitions
- HTTP client with automatic retry and exponential backoff
- Connection pooling for efficient HTTP requests
- WebSocket client for real-time event streaming
- Comprehensive error handling with typed exceptions
- WalletClient for wallet operations (create, balance, transactions)
- TransactionClient for transaction operations (send, get, estimate fees)
- BlockchainClient for blockchain queries (blocks, stats, sync status)
- MiningClient for mining operations (start, stop, status, rewards)
- GovernanceClient for governance operations (proposals, voting)
- Support for both Node.js and browser environments
- Comprehensive documentation and examples
- ESM and CommonJS module support

### Features
- Create and manage wallets
- Send and track transactions
- Query blockchain data and statistics
- Start and monitor mining operations
- Create and vote on governance proposals
- Real-time blockchain event notifications
- Automatic transaction confirmation tracking
- Fee estimation
- Embedded wallet support

## [Unreleased]

### Planned
- Smart contract interaction support
- Batch transaction support
- Enhanced WebSocket reconnection strategies
- Rate limiting utilities
- Transaction signing utilities
- Hardware wallet integration
- Multi-signature wallet support
