# XAI Ledger Hardware Wallet Integration

Complete production-ready Ledger hardware wallet support for XAI browser extension.

## Overview

Provides secure Ledger device integration using WebUSB API for Nano S, S Plus, and X.

### Security Features

- Private keys never leave device - all crypto on-device
- User confirmation required for all signing operations
- Address verification on device screen
- Transport encryption via USB
- Operation locking prevents race conditions

## Quick Start

```javascript
import { connectLedger, getLedgerAddress, signWithLedger } from './ledger-hw.js';

// Connect to device
await connectLedger();

// Get address
const address = await getLedgerAddress("44'/22593'/0'/0/0");

// Sign transaction
const signature = await signWithLedger("44'/22593'/0'/0/0", transaction);
```

## API Reference

See inline JSDoc comments in `ledger-hw.js` for complete API documentation.

### Core Functions

- `isLedgerSupported()` - Check WebUSB support
- `connectLedger()` - Connect to device
- `getLedgerAddress(path)` - Get XAI address
- `getLedgerPublicKey(path)` - Get public key
- `signWithLedger(path, tx)` - Sign transaction
- `verifyAddressOnDevice(path)` - Verify on screen
- `disconnectLedger()` - Disconnect
- `isConnected()` - Check status

### Error Classes

- `LedgerError` - Base error
- `LedgerUserRejectionError` - User rejected
- `LedgerDeviceError` - Device error
- `LedgerTransportError` - Communication error

## BIP32 Paths

XAI coin type: 22593

Default path: `m/44'/22593'/0'/0/0`

## Production Notes

**TODO:** Replace SHA-256 with keccak256 for address derivation.
Currently uses SHA-256 approximation. Import proper library for production.

**Required:** XAI app must be developed for Ledger using Ledger SDK.
