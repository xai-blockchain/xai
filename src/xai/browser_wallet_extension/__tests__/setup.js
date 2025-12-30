/**
 * Jest Test Setup for XAI Browser Wallet Extension
 *
 * Provides comprehensive mocks for:
 * - Chrome Extension APIs (storage, runtime, tabs)
 * - Web Crypto API (SubtleCrypto)
 * - WebUSB API (for Ledger)
 * - WebHID API (for hardware wallets)
 * - DOM APIs
 */

'use strict';

// ============================================================================
// Chrome Extension API Mocks
// ============================================================================

const mockStorage = {
  data: {},
  clear() {
    this.data = {};
  },
  setData(key, value) {
    this.data[key] = value;
  },
  getData(key) {
    return this.data[key];
  }
};

global.chrome = {
  storage: {
    local: {
      get: jest.fn((keys, callback) => {
        const result = {};
        const keysArray = Array.isArray(keys) ? keys : [keys];
        keysArray.forEach(key => {
          if (mockStorage.data[key] !== undefined) {
            result[key] = mockStorage.data[key];
          }
        });
        if (callback) {
          setTimeout(() => callback(result), 0);
        }
        return Promise.resolve(result);
      }),
      set: jest.fn((items, callback) => {
        Object.assign(mockStorage.data, items);
        if (callback) {
          setTimeout(() => callback(), 0);
        }
        return Promise.resolve();
      }),
      remove: jest.fn((keys, callback) => {
        const keysArray = Array.isArray(keys) ? keys : [keys];
        keysArray.forEach(key => {
          delete mockStorage.data[key];
        });
        if (callback) {
          setTimeout(() => callback(), 0);
        }
        return Promise.resolve();
      }),
      clear: jest.fn((callback) => {
        mockStorage.clear();
        if (callback) {
          setTimeout(() => callback(), 0);
        }
        return Promise.resolve();
      })
    },
    sync: {
      get: jest.fn((keys, callback) => {
        if (callback) callback({});
        return Promise.resolve({});
      }),
      set: jest.fn((items, callback) => {
        if (callback) callback();
        return Promise.resolve();
      })
    }
  },
  runtime: {
    onInstalled: {
      addListener: jest.fn()
    },
    onMessage: {
      addListener: jest.fn()
    },
    sendMessage: jest.fn((message, callback) => {
      if (callback) {
        setTimeout(() => callback({ success: true }), 0);
      }
      return Promise.resolve({ success: true });
    }),
    lastError: null,
    getManifest: jest.fn(() => ({
      version: '0.2.0',
      name: 'XAI Wallet'
    }))
  },
  tabs: {
    query: jest.fn((queryInfo, callback) => {
      if (callback) callback([]);
      return Promise.resolve([]);
    }),
    sendMessage: jest.fn()
  }
};

// Export mock storage for test manipulation
global.mockStorage = mockStorage;

// ============================================================================
// Web Crypto API Mocks
// ============================================================================

// Web Crypto API mocks for Node.js environment
// These provide comprehensive mocking for all crypto operations

const nodeCrypto = require('crypto');

const mockCryptoKey = {
  type: 'secret',
  extractable: false,
  algorithm: { name: 'AES-GCM', length: 256 },
  usages: ['encrypt', 'decrypt']
};

// Create comprehensive crypto.subtle mock
const mockSubtle = {
  importKey: jest.fn().mockResolvedValue(mockCryptoKey),
  deriveKey: jest.fn().mockResolvedValue(mockCryptoKey),
  deriveBits: jest.fn().mockResolvedValue(new ArrayBuffer(32)),
  encrypt: jest.fn().mockImplementation(async (algo, key, data) => {
    // Simple mock encryption - XOR with key bytes for testing
    const inputBytes = data instanceof Uint8Array ? data : new Uint8Array(data);
    const result = new Uint8Array(inputBytes.length + 16);
    result.set(inputBytes, 0);
    return result.buffer;
  }),
  decrypt: jest.fn().mockImplementation(async (algo, key, data) => {
    // Simple mock decryption
    const bytes = new Uint8Array(data);
    return bytes.slice(0, bytes.length - 16).buffer;
  }),
  digest: jest.fn().mockImplementation(async (algo, data) => {
    const hash = nodeCrypto.createHash('sha256');
    const inputBytes = data instanceof Uint8Array ? data : new Uint8Array(data);
    hash.update(Buffer.from(inputBytes));
    return hash.digest().buffer;
  }),
  generateKey: jest.fn().mockResolvedValue({
    publicKey: mockCryptoKey,
    privateKey: mockCryptoKey
  }),
  exportKey: jest.fn().mockResolvedValue(new ArrayBuffer(65)),
  sign: jest.fn().mockResolvedValue(new ArrayBuffer(64))
};

// Always provide our mock crypto object
global.crypto = {
  getRandomValues: (array) => {
    const bytes = nodeCrypto.randomBytes(array.length);
    array.set(bytes);
    return array;
  },
  subtle: mockSubtle
};

// Export mockSubtle for test manipulation
global.mockSubtle = mockSubtle;

// ============================================================================
// TextEncoder/TextDecoder (should be available in jsdom)
// ============================================================================

if (typeof TextEncoder === 'undefined') {
  const { TextEncoder, TextDecoder } = require('util');
  global.TextEncoder = TextEncoder;
  global.TextDecoder = TextDecoder;
}

// ============================================================================
// btoa/atob (Base64 encoding/decoding)
// ============================================================================

if (typeof btoa === 'undefined') {
  global.btoa = (str) => Buffer.from(str, 'binary').toString('base64');
}

if (typeof atob === 'undefined') {
  global.atob = (str) => Buffer.from(str, 'base64').toString('binary');
}

// ============================================================================
// WebUSB API Mock (for Ledger)
// ============================================================================

const mockUSBDevice = {
  productName: 'Ledger Nano X',
  manufacturerName: 'Ledger',
  serialNumber: 'TEST-001',
  opened: false,
  configuration: {
    interfaces: [{
      interfaceNumber: 0,
      alternate: {
        interfaceClass: 0x0b, // CCID class
        endpoints: [
          { endpointNumber: 1, direction: 'out' },
          { endpointNumber: 2, direction: 'in' }
        ]
      }
    }]
  },
  open: jest.fn().mockResolvedValue(undefined),
  close: jest.fn().mockResolvedValue(undefined),
  selectConfiguration: jest.fn().mockResolvedValue(undefined),
  claimInterface: jest.fn().mockResolvedValue(undefined),
  releaseInterface: jest.fn().mockResolvedValue(undefined),
  transferOut: jest.fn().mockResolvedValue({ bytesWritten: 64 }),
  transferIn: jest.fn().mockResolvedValue({
    data: new DataView(new ArrayBuffer(64))
  })
};

global.navigator = global.navigator || {};
global.navigator.usb = {
  requestDevice: jest.fn().mockResolvedValue(mockUSBDevice),
  getDevices: jest.fn().mockResolvedValue([])
};

// ============================================================================
// WebHID API Mock (for hardware wallets)
// ============================================================================

const mockHIDDevice = {
  productName: 'Trezor Model T',
  vendorId: 0x1209,
  productId: 0x53c1,
  opened: false,
  collections: [{
    usagePage: 0xff00,
    usage: 0x01
  }],
  open: jest.fn().mockResolvedValue(undefined),
  close: jest.fn().mockResolvedValue(undefined),
  sendReport: jest.fn().mockResolvedValue(undefined),
  sendFeatureReport: jest.fn().mockResolvedValue(undefined),
  receiveFeatureReport: jest.fn().mockResolvedValue(new DataView(new ArrayBuffer(64))),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn()
};

global.navigator.hid = {
  requestDevice: jest.fn().mockResolvedValue([mockHIDDevice]),
  getDevices: jest.fn().mockResolvedValue([])
};

// Export mocks for test manipulation
global.mockUSBDevice = mockUSBDevice;
global.mockHIDDevice = mockHIDDevice;

// ============================================================================
// TrezorConnect Mock
// ============================================================================

global.TrezorConnect = {
  init: jest.fn().mockResolvedValue(undefined),
  dispose: jest.fn().mockResolvedValue(undefined),
  version: '9.0.0',
  getFeatures: jest.fn().mockResolvedValue({
    success: true,
    payload: {
      device_id: 'TEST-DEVICE-001',
      label: 'Test Trezor',
      model: 'T',
      major_version: 2,
      minor_version: 5,
      patch_version: 3,
      capabilities: ['Capability_Bitcoin'],
      initialized: true,
      pin_protection: true,
      passphrase_protection: false
    }
  }),
  getPublicKey: jest.fn().mockResolvedValue({
    success: true,
    payload: {
      publicKey: '04' + 'a'.repeat(128), // Mock uncompressed public key
      chainCode: '0'.repeat(64),
      path: "m/44'/22593'/0'/0/0"
    }
  }),
  getAddress: jest.fn().mockResolvedValue({
    success: true,
    payload: {
      address: 'XAI' + 'a'.repeat(40),
      path: "m/44'/22593'/0'/0/0",
      publicKey: '04' + 'a'.repeat(128)
    }
  }),
  signMessage: jest.fn().mockResolvedValue({
    success: true,
    payload: {
      signature: btoa('mock-signature-bytes'),
      address: 'XAI' + 'a'.repeat(40)
    }
  }),
  ethereumSignTransaction: jest.fn().mockResolvedValue({
    success: true,
    payload: {
      v: '0x1c',
      r: '0x' + 'a'.repeat(64),
      s: '0x' + 'b'.repeat(64)
    }
  })
};

// ============================================================================
// DOM Mocks
// ============================================================================

// Mock document.querySelector for popup tests
const mockElements = {};

global.createMockElement = (id, type = 'div') => {
  const el = document.createElement(type);
  el.id = id;
  el.value = '';
  el.textContent = '';
  el.classList = {
    _classes: new Set(),
    add: function(c) { this._classes.add(c); },
    remove: function(c) { this._classes.delete(c); },
    toggle: function(c, force) {
      if (force === undefined) {
        if (this._classes.has(c)) {
          this._classes.delete(c);
        } else {
          this._classes.add(c);
        }
      } else if (force) {
        this._classes.add(c);
      } else {
        this._classes.delete(c);
      }
    },
    contains: function(c) { return this._classes.has(c); }
  };
  mockElements[id] = el;
  return el;
};

// ============================================================================
// Fetch Mock
// ============================================================================

global.fetch = jest.fn().mockImplementation((url, options) => {
  // Default mock response
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({ success: true }),
    text: () => Promise.resolve(''),
    headers: new Map()
  });
});

// ============================================================================
// Alert/Confirm Mocks
// ============================================================================

global.alert = jest.fn();
global.confirm = jest.fn().mockReturnValue(true);
global.prompt = jest.fn().mockReturnValue('test');

// ============================================================================
// Timer Mocks
// ============================================================================

jest.useFakeTimers();

// ============================================================================
// Console Spy Setup
// ============================================================================

// Optionally silence console during tests
const originalConsole = { ...console };
global.originalConsole = originalConsole;

// ============================================================================
// Test Utilities
// ============================================================================

/**
 * Wait for all pending promises to resolve
 */
global.flushPromises = () => new Promise(resolve => setTimeout(resolve, 0));

/**
 * Create mock encrypted data for testing
 */
global.createMockEncryptedData = () => {
  const salt = new Uint8Array(16);
  const iv = new Uint8Array(12);
  const ciphertext = new Uint8Array([1, 2, 3, 4, 5]);
  const combined = new Uint8Array(salt.length + iv.length + ciphertext.length);
  combined.set(salt, 0);
  combined.set(iv, 16);
  combined.set(ciphertext, 28);
  return btoa(String.fromCharCode(...combined));
};

/**
 * Reset all mocks before each test
 */
beforeEach(() => {
  // Clear storage
  mockStorage.clear();

  // Reset all Jest mocks
  jest.clearAllMocks();

  // Reset fetch
  global.fetch.mockClear();

  // Reset Trezor Connect
  TrezorConnect.init.mockClear();
  TrezorConnect.getFeatures.mockClear();
  TrezorConnect.getPublicKey.mockClear();
  TrezorConnect.signMessage.mockClear();

  // Reset USB/HID devices
  mockUSBDevice.open.mockClear();
  mockUSBDevice.close.mockClear();
  mockHIDDevice.open.mockClear();
  mockHIDDevice.close.mockClear();
});

/**
 * Clean up after each test
 */
afterEach(() => {
  jest.clearAllTimers();
});

// ============================================================================
// Security Test Utilities
// ============================================================================

/**
 * Verify that sensitive data is properly cleared from memory
 */
global.verifySensitiveDataCleared = (obj, sensitiveFields) => {
  sensitiveFields.forEach(field => {
    expect(obj[field]).toBeUndefined();
  });
};

/**
 * Check if a string contains potential secrets
 */
global.containsSecrets = (str) => {
  const secretPatterns = [
    /[a-f0-9]{64}/i, // Private keys (64 hex chars)
    /[a-f0-9]{128}/i, // Full keys
    /sk-[a-zA-Z0-9]+/, // API keys
    /-----BEGIN PRIVATE KEY-----/, // PEM keys
  ];
  return secretPatterns.some(pattern => pattern.test(str));
};

console.log('Jest test setup complete');
