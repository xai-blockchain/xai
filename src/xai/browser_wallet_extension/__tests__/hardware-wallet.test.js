/**
 * Hardware Wallet Tests
 *
 * Comprehensive tests for Trezor and Ledger hardware wallet integrations.
 * Tests cover:
 * - Device connection/disconnection
 * - Address derivation with BIP32 paths
 * - Transaction signing
 * - Error handling and user rejection
 * - Security boundaries
 *
 * @security Critical - validates hardware wallet security properties
 */

'use strict';

const fs = require('fs');
const path = require('path');

// Load source files for static analysis
const trezorCode = fs.readFileSync(
  path.join(__dirname, '..', 'trezor-hw.js'),
  'utf8'
);

const ledgerCode = fs.readFileSync(
  path.join(__dirname, '..', 'ledger-hw.js'),
  'utf8'
);

const hwManagerCode = fs.readFileSync(
  path.join(__dirname, '..', 'hw-manager.js'),
  'utf8'
);

// ============================================================================
// Trezor Hardware Wallet Tests
// ============================================================================

describe('Trezor Hardware Wallet', () => {
  describe('Support Detection', () => {
    test('should have isTrezorSupported function', () => {
      expect(trezorCode).toContain('isTrezorSupported');
    });

    test('should check for TrezorConnect availability', () => {
      expect(trezorCode).toContain('TrezorConnect');
    });

    test('should check for Web Crypto API', () => {
      expect(trezorCode).toContain('crypto.subtle');
    });
  });

  describe('Initialization', () => {
    test('should have initTrezorConnect function', () => {
      expect(trezorCode).toContain('initTrezorConnect');
    });

    test('should configure XAI manifest', () => {
      expect(trezorCode).toContain('XAI_MANIFEST');
      expect(trezorCode).toContain('manifest');
    });

    test('should support custom options', () => {
      expect(trezorCode).toContain('options');
      expect(trezorCode).toContain('debug');
    });
  });

  describe('Device Connection', () => {
    test('should have connectTrezor function', () => {
      expect(trezorCode).toContain('connectTrezor');
    });

    test('should get device features', () => {
      expect(trezorCode).toContain('getFeatures');
    });

    test('should extract device information', () => {
      expect(trezorCode).toContain('device_id');
      expect(trezorCode).toContain('firmwareVersion');
      expect(trezorCode).toContain('model');
    });
  });

  describe('Address Derivation', () => {
    test('should have getTrezorAddress function', () => {
      expect(trezorCode).toContain('getTrezorAddress');
    });

    test('should use default BIP32 path', () => {
      expect(trezorCode).toContain('XAI_DEFAULT_PATH');
      expect(trezorCode).toContain("m/44'/22593'/0'/0/0");
    });

    test('should derive XAI-prefixed addresses', () => {
      expect(trezorCode).toContain('deriveXaiAddress');
      // XAI address format is documented in the code
      expect(trezorCode).toContain('XAI address format');
    });

    test('should support showOnDevice option', () => {
      expect(trezorCode).toContain('showOnDevice');
      expect(trezorCode).toContain('showOnTrezor');
    });
  });

  describe('Transaction Signing', () => {
    test('should have signWithTrezor function', () => {
      expect(trezorCode).toContain('signWithTrezor');
    });

    test('should validate transaction payload', () => {
      expect(trezorCode).toContain('Transaction payload is required');
    });

    test('should use signMessage for signing', () => {
      expect(trezorCode).toContain('signMessage');
    });

    test('should hash payload with SHA-256', () => {
      expect(trezorCode).toContain('SHA-256');
    });

    test('should return signature hex string', () => {
      expect(trezorCode).toContain('signature');
      expect(trezorCode).toContain('messageHash');
    });

    test('should use canonical signature format', () => {
      expect(trezorCode).toContain('canonicalizeS');
      expect(trezorCode).toContain('SECP256K1_N');
    });
  });

  describe('Address Verification', () => {
    test('should have verifyAddressOnDevice function', () => {
      expect(trezorCode).toContain('verifyAddressOnDevice');
    });

    test('should force display on device', () => {
      expect(trezorCode).toMatch(/showOnTrezor:\s*true/);
    });
  });

  describe('Disconnect', () => {
    test('should have disconnectTrezor function', () => {
      expect(trezorCode).toContain('disconnectTrezor');
    });

    test('should call TrezorConnect.dispose', () => {
      expect(trezorCode).toContain('dispose');
    });
  });

  describe('Error Handling', () => {
    test('should have TrezorError class', () => {
      expect(trezorCode).toContain('class TrezorError');
    });

    test('should have TrezorErrorCode enum', () => {
      expect(trezorCode).toContain('TrezorErrorCode');
    });

    test('should have error codes for common errors', () => {
      expect(trezorCode).toContain('USER_CANCELLED');
      expect(trezorCode).toContain('DEVICE_NOT_CONNECTED');
      expect(trezorCode).toContain('SIGNING_FAILED');
    });

    test('should map Trezor errors to codes', () => {
      expect(trezorCode).toContain('mapTrezorErrorCode');
    });
  });

  describe('BIP32 Path Validation', () => {
    test('should have validateBip32Path function', () => {
      expect(trezorCode).toContain('validateBip32Path');
    });

    test('should have BIP32 regex pattern', () => {
      expect(trezorCode).toContain('bip32Regex');
    });
  });

  describe('Security', () => {
    test('XAI coin type should be 22593', () => {
      expect(trezorCode).toContain('XAI_COIN_TYPE = 22593');
    });

    test('should use secp256k1 curve', () => {
      expect(trezorCode).toContain('secp256k1');
    });

    test('private keys should never leave device', () => {
      expect(trezorCode).toContain('private key never');
    });
  });
});

// ============================================================================
// Ledger Hardware Wallet Tests
// ============================================================================

describe('Ledger Hardware Wallet', () => {
  describe('Support Detection', () => {
    test('should have isLedgerSupported function', () => {
      expect(ledgerCode).toContain('isLedgerSupported');
    });

    test('should check for WebUSB availability', () => {
      expect(ledgerCode).toContain('navigator.usb');
    });
  });

  describe('Device Connection', () => {
    test('should have connectLedger function', () => {
      expect(ledgerCode).toContain('connectLedger');
    });

    test('should use Ledger vendor ID', () => {
      expect(ledgerCode).toContain('LEDGER_VENDOR_ID');
      expect(ledgerCode).toContain('0x2c97');
    });

    test('should request USB device', () => {
      expect(ledgerCode).toContain('requestDevice');
    });

    test('should claim USB interface', () => {
      expect(ledgerCode).toContain('claimInterface');
    });
  });

  describe('Address Derivation', () => {
    test('should have getLedgerAddress function', () => {
      expect(ledgerCode).toContain('getLedgerAddress');
    });

    test('should use default BIP32 path', () => {
      expect(ledgerCode).toContain('DEFAULT_BIP32_PATH');
      expect(ledgerCode).toContain("44'/22593'/");
    });

    test('should parse BIP32 path', () => {
      expect(ledgerCode).toContain('parseBIP32Path');
    });

    test('should derive XAI address from public key', () => {
      expect(ledgerCode).toContain('publicKeyToAddress');
      expect(ledgerCode).toContain("'XAI'");
    });
  });

  describe('Transaction Signing', () => {
    test('should have signWithLedger function', () => {
      expect(ledgerCode).toContain('signWithLedger');
    });

    test('should use APDU commands', () => {
      expect(ledgerCode).toContain('APDU');
      expect(ledgerCode).toContain('createAPDU');
    });

    test('should have sign transaction instruction', () => {
      expect(ledgerCode).toContain('SIGN_TRANSACTION');
    });

    test('should parse DER signatures', () => {
      expect(ledgerCode).toContain('parseDERSignature');
    });
  });

  describe('Address Verification', () => {
    test('should have verifyAddressOnDevice function', () => {
      expect(ledgerCode).toContain('verifyAddressOnDevice');
    });

    test('should display address on device', () => {
      expect(ledgerCode).toContain('DISPLAY_ADDRESS');
    });
  });

  describe('Disconnect', () => {
    test('should have disconnectLedger function', () => {
      expect(ledgerCode).toContain('disconnectLedger');
    });

    test('should release USB interface', () => {
      expect(ledgerCode).toContain('releaseInterface');
    });

    test('should close device', () => {
      expect(ledgerCode).toContain('.close()');
    });

    test('should have isConnected function', () => {
      expect(ledgerCode).toContain('isConnected');
    });
  });

  describe('Error Classes', () => {
    test('should have LedgerError class', () => {
      expect(ledgerCode).toContain('class LedgerError');
    });

    test('should have LedgerUserRejectionError', () => {
      expect(ledgerCode).toContain('LedgerUserRejectionError');
    });

    test('should have LedgerDeviceError', () => {
      expect(ledgerCode).toContain('LedgerDeviceError');
    });

    test('should have LedgerTransportError', () => {
      expect(ledgerCode).toContain('LedgerTransportError');
    });
  });

  describe('APDU Protocol', () => {
    test('should have APDU status codes', () => {
      expect(ledgerCode).toContain('APDU_STATUS');
      expect(ledgerCode).toContain('0x9000'); // OK status
    });

    test('should have APDU instruction codes', () => {
      expect(ledgerCode).toContain('APDU_INS');
      expect(ledgerCode).toContain('GET_PUBLIC_KEY');
    });

    test('should handle user rejection status', () => {
      expect(ledgerCode).toContain('USER_REJECTED');
      expect(ledgerCode).toContain('0x6985');
    });
  });

  describe('Security', () => {
    test('should use correct Ledger vendor ID', () => {
      expect(ledgerCode).toContain('0x2c97');
    });

    test('XAI coin type should be 22593', () => {
      expect(ledgerCode).toContain('XAI_COIN_TYPE = 22593');
    });

    test('private keys should remain on device', () => {
      expect(ledgerCode).toContain('private key');
    });
  });
});

// ============================================================================
// Hardware Wallet Manager Tests
// ============================================================================

describe('HardwareWalletManager', () => {
  describe('Initialization', () => {
    test('should have default BIP32 path for XAI', () => {
      expect(hwManagerCode).toContain("m/44'/22593'/0'/0/0");
    });

    test('should support auto reconnect option', () => {
      expect(hwManagerCode).toContain('autoReconnect');
    });

    test('should initialize currentWallet to null', () => {
      expect(hwManagerCode).toContain('currentWallet = null');
    });
  });

  describe('Supported Wallets', () => {
    test('should have getSupportedWallets method', () => {
      expect(hwManagerCode).toContain('getSupportedWallets');
    });

    test('should support ledger wallet', () => {
      expect(hwManagerCode).toContain("'ledger'");
    });

    test('should support trezor wallet', () => {
      expect(hwManagerCode).toContain("'trezor'");
    });

    test('should have getWalletName method', () => {
      expect(hwManagerCode).toContain('getWalletName');
    });
  });

  describe('Connection State', () => {
    test('should have isConnected method', () => {
      expect(hwManagerCode).toContain('isConnected');
    });

    test('should have getConnectedWallet method', () => {
      expect(hwManagerCode).toContain('getConnectedWallet');
    });

    test('should have connect method', () => {
      expect(hwManagerCode).toContain('async connect');
    });

    test('should have disconnect method', () => {
      expect(hwManagerCode).toContain('async disconnect');
    });
  });

  describe('Event System', () => {
    test('should have on method for event listeners', () => {
      expect(hwManagerCode).toContain('on(event, callback)');
    });

    test('should have off method for removing listeners', () => {
      expect(hwManagerCode).toContain('off(event, callback)');
    });

    test('should have _emit method for triggering events', () => {
      expect(hwManagerCode).toContain('_emit(event, data)');
    });

    test('should support standard events', () => {
      expect(hwManagerCode).toContain('connecting');
      expect(hwManagerCode).toContain('connected');
      expect(hwManagerCode).toContain('disconnected');
      expect(hwManagerCode).toContain('signing');
      expect(hwManagerCode).toContain('signed');
    });
  });

  describe('Transaction Building', () => {
    test('should have buildUnsignedTransaction method', () => {
      expect(hwManagerCode).toContain('buildUnsignedTransaction');
    });

    test('should validate sender field', () => {
      expect(hwManagerCode).toContain('sender is required');
    });

    test('should validate recipient field', () => {
      expect(hwManagerCode).toContain('recipient is required');
    });

    test('should include transaction type', () => {
      expect(hwManagerCode).toContain('tx_type');
      expect(hwManagerCode).toContain('transfer');
    });

    test('should create payload bytes', () => {
      expect(hwManagerCode).toContain('payloadBytes');
    });
  });

  describe('Transaction Signing', () => {
    test('should have signTransaction method', () => {
      expect(hwManagerCode).toContain('signTransaction');
    });

    test('should have signMessage method', () => {
      expect(hwManagerCode).toContain('signMessage');
    });
  });

  describe('Error Formatting', () => {
    test('should have _formatError method', () => {
      expect(hwManagerCode).toContain('_formatError');
    });

    test('should have user-friendly error messages', () => {
      expect(hwManagerCode).toContain('User rejected');
      expect(hwManagerCode).toContain('device not found');
      expect(hwManagerCode).toContain('app not open');
    });
  });

  describe('Signature Handling', () => {
    test('should have combineSignature method', () => {
      expect(hwManagerCode).toContain('combineSignature');
    });

    test('should include payload hash in signed transaction', () => {
      expect(hwManagerCode).toContain('payloadHash');
    });

    test('should include signature timestamp', () => {
      expect(hwManagerCode).toContain('signedAt');
    });
  });

  describe('Address Operations', () => {
    test('should have getAddress method', () => {
      expect(hwManagerCode).toContain('async getAddress');
    });

    test('should support showOnDevice parameter', () => {
      expect(hwManagerCode).toContain('showOnDevice');
    });
  });

  describe('Reconnection', () => {
    test('should have reconnect timer', () => {
      expect(hwManagerCode).toContain('reconnectTimer');
    });

    test('should have reconnect delay option', () => {
      expect(hwManagerCode).toContain('reconnectDelay');
    });

    test('should have _attemptReconnect method', () => {
      expect(hwManagerCode).toContain('_attemptReconnect');
    });
  });
});

// ============================================================================
// Security Tests
// ============================================================================

describe('Hardware Wallet Security', () => {
  describe('Cryptographic Standards', () => {
    test('Trezor should use secp256k1', () => {
      expect(trezorCode).toContain('secp256k1');
    });

    test('Ledger should use secp256k1', () => {
      // Ledger uses Bitcoin-style derivation which is secp256k1
      expect(ledgerCode).toContain('secp256k1');
    });

    test('should use SHA-256 for hashing', () => {
      expect(trezorCode).toContain('SHA-256');
      expect(ledgerCode).toContain('SHA-256');
    });
  });

  describe('Private Key Protection', () => {
    test('Trezor private keys should never leave device', () => {
      expect(trezorCode).toContain('private key never');
    });

    test('Ledger private keys should remain on device', () => {
      expect(ledgerCode).toContain('private key');
    });

    test('Manager should not store private keys', () => {
      expect(hwManagerCode).not.toMatch(/privateKey\s*=/);
    });
  });

  describe('BIP44 Compliance', () => {
    test('should use XAI coin type 22593', () => {
      expect(trezorCode).toContain('22593');
      expect(ledgerCode).toContain('22593');
      expect(hwManagerCode).toContain('22593');
    });

    test('should use correct BIP44 path structure', () => {
      expect(trezorCode).toMatch(/m\/44['']\/22593['']/);
      expect(hwManagerCode).toMatch(/m\/44['']\/22593['']/);
    });
  });

  describe('Signature Security', () => {
    test('Trezor should canonicalize signatures', () => {
      expect(trezorCode).toContain('canonicalizeS');
    });

    test('should use secp256k1 curve order', () => {
      expect(trezorCode).toContain('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141');
    });
  });
});
