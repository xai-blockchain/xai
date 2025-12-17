# Ledger Hardware Wallet Technical Implementation Notes

## Architecture Overview

### Three-Layer Architecture

1. **Transport Layer** (`sendAPDU`, `exchangeAPDU`)
   - WebUSB HID packet framing
   - USB endpoint management
   - Error handling and timeouts

2. **Protocol Layer** (`createAPDU`, `parseAPDUResponse`)
   - APDU command construction
   - Response parsing and validation
   - Status code error mapping

3. **Application Layer** (Public API functions)
   - High-level operations (connect, sign, etc.)
   - BIP32 path handling
   - Operation locking for concurrency

## APDU Protocol Details

### Command Structure (5+ bytes)

```
[CLA] [INS] [P1] [P2] [Lc] [Data...]
```

- **CLA (0xe0):** Class byte, Ethereum-compatible
- **INS:** Instruction code (0x02=GetPubKey, 0x04=Sign)
- **P1/P2:** Parameters (display flags, chunk markers)
- **Lc:** Data length
- **Data:** BIP32 path, transaction hash, etc.

### Response Structure

```
[Data...] [SW1] [SW2]
```

- **Data:** Response payload (public key, signature, etc.)
- **SW1 SW2:** Status word (0x9000 = success)

### USB HID Packet Format (64 bytes)

```
[Channel:2] [Tag:1] [SeqHi:1] [SeqLo:1] [LenHi:1] [LenLo:1] [Data:57]
```

- **Channel:** 0x0101 (default)
- **Tag:** 0x05 (APDU)
- **Sequence:** Packet sequence number
- **Length:** APDU length (in first packet)
- **Data:** APDU payload

## BIP32 Path Encoding

### Binary Format

```
[PathLength:1] [Index0:4] [Index1:4] ... [IndexN:4]
```

Each index is 32-bit big-endian. Hardened derivation sets bit 31.

### Example: m/44'/22593'/0'/0/0

```
05                      // 5 components
8000002C                // 44' (0x8000002C)
80005841                // 22593' (0x80005841)
80000000                // 0' (0x80000000)
00000000                // 0 (0x00000000)
00000000                // 0 (0x00000000)
```

## Address Derivation

### Current Implementation (SHA-256)

```
PublicKey (64 bytes) -> SHA-256 -> Last 20 bytes -> EIP-55 checksum -> XAI prefix
```

### Production Implementation (keccak256)

```
PublicKey (64 bytes) -> keccak256 -> Last 20 bytes -> EIP-55 checksum -> XAI prefix
```

**Note:** keccak256 differs from SHA3-256. Use Ethereum's keccak256 library.

## Signature Format

### Input: Transaction Object

```javascript
{
  to: "XAI...",
  amount: 100,
  nonce: 1,
  timestamp: 1234567890
}
```

### Processing Pipeline

1. **Serialize:** Deterministic JSON (sorted keys)
2. **Hash:** SHA-256(serialized)
3. **Send to device:** BIP32 path + hash
4. **Device signs:** secp256k1 ECDSA
5. **Return:** Raw signature (r||s, 64 bytes hex)

## Error Handling Strategy

### Error Hierarchy

```
LedgerError (base)
├── LedgerUserRejectionError (0x6985)
├── LedgerDeviceError (device-specific codes)
└── LedgerTransportError (communication errors)
```

### Status Code Mapping

| Code | Meaning | Recovery |
|------|---------|----------|
| 0x9000 | Success | N/A |
| 0x6985 | User rejected | Prompt user to retry |
| 0x6d00 | Wrong app | Open XAI app on device |
| 0x6982 | Device locked | Unlock device |
| 0x6b00 | Invalid params | Check path/data format |

## Concurrency Control

### Operation Lock Pattern

```javascript
if (operationLock) throw new Error('BUSY');
operationLock = true;
try {
  // ... operation ...
} finally {
  operationLock = false;
}
```

Prevents race conditions from concurrent API calls.

## Security Considerations

### Threat Model

**Protected Against:**
- Private key extraction (keys never leave device)
- Transaction tampering (hash verified on device)
- Man-in-the-middle USB attacks (USB is encrypted)
- Concurrent operation exploits (operation locking)

**Requires Trust In:**
- Ledger device firmware
- XAI app on Ledger
- Browser WebUSB implementation
- This integration code

### Attack Vectors

1. **Malicious XAI app:** Could sign anything. Mitigated by Ledger app review.
2. **Browser compromise:** Could modify displayed transaction. Mitigated by device screen review.
3. **USB tampering:** Hardware attack. Mitigated by device's secure element.

## Performance Characteristics

### Operation Latencies

- **Connect:** ~2-5 seconds (USB enumeration + app check)
- **Get address:** ~1-2 seconds (device derivation)
- **Sign transaction:** ~5-10 seconds (user confirmation required)
- **Timeout:** 30 seconds (configurable)

### Optimization Opportunities

1. Cache public keys to avoid repeated device queries
2. Batch address derivation for multiple accounts
3. Pre-warm connection in background

## Browser Compatibility

### WebUSB Support Matrix

| Browser | Version | Support |
|---------|---------|---------|
| Chrome | 61+ | Full |
| Edge | 79+ | Full |
| Opera | 48+ | Full |
| Firefox | - | No (requires flag) |
| Safari | - | No |

### Polyfills

No polyfills available for WebUSB. Requires native browser support.

## Testing Strategy

### Unit Tests (No Hardware Required)

- BIP32 path parsing
- APDU packet construction
- Response parsing
- Error code mapping

### Integration Tests (Ledger Device Required)

- Device connection/disconnection
- Address derivation
- Transaction signing
- Error scenarios (wrong app, user rejection)

### Manual Test Checklist

- [ ] Connect/disconnect multiple times
- [ ] Test all derivation paths
- [ ] Sign with user confirmation
- [ ] Sign with user rejection
- [ ] Verify address on screen
- [ ] Device timeout handling
- [ ] Wrong app error handling
- [ ] Device lock error handling

## Future Enhancements

### Planned Features

1. **Multi-signature support:** Sign with multiple Ledger devices
2. **Batch signing:** Sign multiple transactions in one session
3. **Custom derivation paths:** UI for advanced users
4. **Connection persistence:** Auto-reconnect on USB events
5. **Transaction preview:** Parse and display on device

### XAI Ledger App Development

Required Ledger app features:

1. **Address derivation:** BIP32 path -> XAI address
2. **Transaction signing:** Parse and display transaction details
3. **Settings:** Coin type, network (mainnet/testnet)
4. **Security:** Signature canonicalization, replay protection

Ledger SDK: C/C++ using BOLOS platform

## Maintenance Notes

### Dependencies

- **Browser WebUSB API:** No external libraries required
- **Crypto:** Uses Web Crypto API (built-in)
- **Future:** Add keccak256 library for production

### Breaking Changes to Monitor

1. Ledger firmware updates (USB protocol changes)
2. Browser WebUSB spec changes
3. XAI address format changes
4. BIP32 derivation path changes

### Debugging Tips

1. Enable Chrome USB logging: chrome://device-log
2. Check Ledger firmware version compatibility
3. Test with different USB cables/ports
4. Monitor USB device events in DevTools
5. Log all APDU commands/responses for analysis

## References

- Ledger Developer Docs: https://developers.ledger.com
- WebUSB Spec: https://wicg.github.io/webusb/
- BIP-32: https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki
- BIP-44: https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki
- SLIP-44: https://github.com/satoshilabs/slips/blob/master/slip-0044.md
- EIP-55: https://eips.ethereum.org/EIPS/eip-55
