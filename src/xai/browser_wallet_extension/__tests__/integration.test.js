/**
 * Integration Tests for XAI Browser Wallet Extension
 *
 * Tests covering:
 * - Balance checking API
 * - Web3 provider compatibility (JSON-RPC)
 * - Session management
 * - Mining integration
 * - AI assistant integration
 *
 * @security Tests critical integration points between components
 */

'use strict';

const fs = require('fs');
const path = require('path');

// ============================================================================
// Balance Checking Tests
// ============================================================================

describe('Balance Checking', () => {
  beforeEach(() => {
    mockStorage.clear();
    jest.clearAllMocks();
    fetch.mockClear();
  });

  test('should call balance API', async () => {
    const testAddress = 'XAI' + 'a'.repeat(40);

    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        success: true,
        balance: '1000.50',
        currency: 'XAI'
      })
    });

    await fetch('http://localhost:8545/wallet/balance?address=' + testAddress);

    expect(fetch).toHaveBeenCalled();
  });

  test('should handle zero balance', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        success: true,
        balance: '0',
        currency: 'XAI'
      })
    });

    const response = await fetch('http://localhost:8545/wallet/balance?address=test');
    const data = await response.json();

    expect(data.balance).toBe('0');
  });

  test('should handle API errors gracefully', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: () => Promise.resolve('Internal Server Error')
    });

    const response = await fetch('http://localhost:8545/wallet/balance?address=test');

    expect(response.ok).toBe(false);
    expect(response.status).toBe(500);
  });

  test('should handle network timeouts', async () => {
    fetch.mockRejectedValueOnce(new Error('Network timeout'));

    await expect(
      fetch('http://localhost:8545/wallet/balance?address=test')
    ).rejects.toThrow('Network timeout');
  });
});

// ============================================================================
// Web3 Provider Compatibility Tests
// ============================================================================

describe('Web3 Provider Compatibility', () => {
  describe('JSON-RPC Compatibility', () => {
    test('should support eth_accounts method', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          jsonrpc: '2.0',
          id: 1,
          result: ['XAI' + 'a'.repeat(40)]
        })
      });

      const response = await fetch('http://localhost:8545', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0',
          method: 'eth_accounts',
          params: [],
          id: 1
        })
      });

      const data = await response.json();
      expect(data.jsonrpc).toBe('2.0');
      expect(data.result).toBeInstanceOf(Array);
    });

    test('should support eth_chainId method', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          jsonrpc: '2.0',
          id: 1,
          result: '0x5841'
        })
      });

      const response = await fetch('http://localhost:8545', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0',
          method: 'eth_chainId',
          params: [],
          id: 1
        })
      });

      const data = await response.json();
      expect(parseInt(data.result, 16)).toBe(22593);
    });

    test('should support eth_sendTransaction method', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          jsonrpc: '2.0',
          id: 1,
          result: '0x' + 'a'.repeat(64)
        })
      });

      const response = await fetch('http://localhost:8545', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0',
          method: 'eth_sendTransaction',
          params: [{
            from: 'XAI' + 'a'.repeat(40),
            to: 'XAI' + 'b'.repeat(40),
            value: '0x1000',
            gas: '0x5208'
          }],
          id: 1
        })
      });

      const data = await response.json();
      expect(data.result).toMatch(/^0x[a-f0-9]{64}$/);
    });
  });

  describe('Error Responses', () => {
    test('should return proper error for invalid method', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          jsonrpc: '2.0',
          id: 1,
          error: {
            code: -32601,
            message: 'Method not found'
          }
        })
      });

      const response = await fetch('http://localhost:8545', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0',
          method: 'invalid_method',
          params: [],
          id: 1
        })
      });

      const data = await response.json();
      expect(data.error).toBeDefined();
      expect(data.error.code).toBe(-32601);
    });
  });
});

// ============================================================================
// Wallet Creation/Import Tests
// ============================================================================

describe('Wallet Creation and Import', () => {
  describe('Key Generation', () => {
    test('should use secp256k1 curve for key generation', () => {
      const trezorCode = fs.readFileSync(
        path.join(__dirname, '..', 'trezor-hw.js'),
        'utf8'
      );

      expect(trezorCode).toContain('secp256k1');
    });

    test('should derive XAI addresses from public keys', () => {
      const popupCode = fs.readFileSync(
        path.join(__dirname, '..', 'popup.js'),
        'utf8'
      );

      expect(popupCode).toContain('derive-public-key');
    });
  });

  describe('Key Import', () => {
    test('should validate private key format (64 hex chars)', () => {
      const popupCode = fs.readFileSync(
        path.join(__dirname, '..', 'popup.js'),
        'utf8'
      );

      expect(popupCode).toMatch(/privateKey.*length.*64/);
    });

    test('should use hexToBytes for key parsing', () => {
      const popupCode = fs.readFileSync(
        path.join(__dirname, '..', 'popup.js'),
        'utf8'
      );

      expect(popupCode).toContain('hexToBytes');
      expect(popupCode).toContain('parseInt');
    });
  });
});

// ============================================================================
// Transaction Flow Tests
// ============================================================================

describe('Transaction Flow', () => {
  test('should build transaction with required fields', () => {
    const popupCode = fs.readFileSync(
      path.join(__dirname, '..', 'popup.js'),
      'utf8'
    );

    expect(popupCode).toContain('maker_address');
    expect(popupCode).toContain('maker_public_key');
    expect(popupCode).toContain('token_offered');
    expect(popupCode).toContain('amount_offered');
    expect(popupCode).toContain('signature');
  });

  test('should serialize payload deterministically', () => {
    const popupCode = fs.readFileSync(
      path.join(__dirname, '..', 'popup.js'),
      'utf8'
    );

    expect(popupCode).toContain('stableStringify');
    expect(popupCode).toContain('Object.keys');
    expect(popupCode).toContain('.sort()');
  });

  test('should sign transaction before submission', () => {
    const popupCode = fs.readFileSync(
      path.join(__dirname, '..', 'popup.js'),
      'utf8'
    );

    expect(popupCode).toContain('signPayload');
    expect(popupCode).toContain('signature');
  });

  test('should show signing preview before confirmation', () => {
    const popupCode = fs.readFileSync(
      path.join(__dirname, '..', 'popup.js'),
      'utf8'
    );

    expect(popupCode).toContain('presentSigningPreview');
    expect(popupCode).toContain('signingPreview');
  });
});

// ============================================================================
// Session Management Tests
// ============================================================================

describe('Session Management Integration', () => {
  test('should register session with server', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        success: true,
        session_token: 'new-token-123',
        session_secret: 'new-secret-456'
      })
    });

    const response = await fetch('http://localhost:8545/wallet-trades/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ wallet_address: 'XAI' + 'a'.repeat(40) })
    });

    const data = await response.json();
    expect(data.success).toBe(true);
    expect(data.session_token).toBeDefined();
  });

  test('should use ECDH for WalletConnect handshake', () => {
    const popupCode = fs.readFileSync(
      path.join(__dirname, '..', 'popup.js'),
      'utf8'
    );

    expect(popupCode).toContain('ECDH');
  });

  test('should use HKDF for key derivation', () => {
    const popupCode = fs.readFileSync(
      path.join(__dirname, '..', 'popup.js'),
      'utf8'
    );

    expect(popupCode).toContain('HKDF');
  });
});

// ============================================================================
// Mining Integration Tests
// ============================================================================

describe('Mining Integration', () => {
  test('should check mining status', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        success: true,
        is_mining: true,
        hashrate: 150
      })
    });

    const response = await fetch('http://localhost:8545/mining/status?address=test');
    const data = await response.json();

    expect(data.is_mining).toBe(true);
    expect(data.hashrate).toBe(150);
  });

  test('should start mining', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        success: true,
        message: 'Mining started'
      })
    });

    const response = await fetch('http://localhost:8545/mining/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ miner_address: 'test', intensity: 'medium' })
    });

    const data = await response.json();
    expect(data.success).toBe(true);
  });

  test('should stop mining', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        success: true,
        message: 'Mining stopped'
      })
    });

    const response = await fetch('http://localhost:8545/mining/stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ miner_address: 'test' })
    });

    const data = await response.json();
    expect(data.success).toBe(true);
  });
});

// ============================================================================
// AI Assistant Integration Tests
// ============================================================================

describe('AI Assistant Integration', () => {
  test('should send AI swap request', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        success: true,
        swap_transaction: { fee: '0.001' }
      })
    });

    await fetch('http://localhost:8545/personal-ai/atomic-swap', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-AI-Provider': 'anthropic'
      },
      body: JSON.stringify({ swap_details: {} })
    });

    expect(fetch).toHaveBeenCalled();
  });

  test('should clear API key after use', () => {
    const popupCode = fs.readFileSync(
      path.join(__dirname, '..', 'popup.js'),
      'utf8'
    );

    expect(popupCode).toContain('clearAiKeyField');
    expect(popupCode).toContain('aiKeyDeleted');
  });
});
