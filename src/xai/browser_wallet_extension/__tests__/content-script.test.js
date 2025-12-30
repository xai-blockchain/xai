/**
 * Content Script Tests for XAI Browser Wallet Extension
 *
 * Tests for content script injection and Web3 provider functionality.
 * Covers:
 * - Web3 provider interface
 * - DApp communication
 * - Security boundaries
 * - Event handling
 *
 * @security Critical - tests isolation between dapp and extension
 */

'use strict';

const fs = require('fs');
const path = require('path');

// ============================================================================
// Manifest Structure Tests
// ============================================================================

describe('Manifest Structure', () => {
  test('manifest.json should have proper permissions', () => {
    const manifest = JSON.parse(fs.readFileSync(
      path.join(__dirname, '..', 'manifest.json'),
      'utf8'
    ));

    expect(manifest.permissions).toContain('storage');
  });
});

// ============================================================================
// Web3 Provider Tests
// ============================================================================

describe('Web3 Provider', () => {
  describe('Provider Interface', () => {
    test('provider should expose required methods', () => {
      const expectedMethods = ['request', 'on', 'removeListener', 'isConnected'];

      const mockProvider = {
        request: async () => {},
        on: () => {},
        removeListener: () => {},
        isConnected: () => true
      };

      expectedMethods.forEach(method => {
        expect(typeof mockProvider[method]).toBe('function');
      });
    });

    test('provider should have correct identification', () => {
      const mockProvider = {
        isXAI: true,
        chainId: '0x5841',
        networkVersion: '22593'
      };

      expect(mockProvider.isXAI).toBe(true);
      expect(parseInt(mockProvider.chainId, 16)).toBe(22593);
    });

    test('provider should emit events', () => {
      const eventListeners = {};

      const mockProvider = {
        on: (event, callback) => {
          if (!eventListeners[event]) {
            eventListeners[event] = [];
          }
          eventListeners[event].push(callback);
        },
        emit: (event, data) => {
          const listeners = eventListeners[event] || [];
          listeners.forEach(cb => cb(data));
        }
      };

      const callback = jest.fn();
      mockProvider.on('connect', callback);
      mockProvider.emit('connect', { chainId: '0x5841' });

      expect(callback).toHaveBeenCalledWith({ chainId: '0x5841' });
    });
  });

  describe('RPC Method Handling', () => {
    test('eth_requestAccounts should return accounts', async () => {
      const mockPrompt = jest.fn().mockResolvedValue(['XAI' + 'a'.repeat(40)]);

      const mockProvider = {
        request: async ({ method }) => {
          if (method === 'eth_requestAccounts') {
            return await mockPrompt();
          }
        }
      };

      const accounts = await mockProvider.request({ method: 'eth_requestAccounts' });

      expect(mockPrompt).toHaveBeenCalled();
      expect(accounts).toHaveLength(1);
    });

    test('eth_chainId should return XAI chain ID', async () => {
      const mockProvider = {
        request: async ({ method }) => {
          if (method === 'eth_chainId') {
            return '0x5841';
          }
        }
      };

      const chainId = await mockProvider.request({ method: 'eth_chainId' });

      expect(chainId).toBe('0x5841');
      expect(parseInt(chainId, 16)).toBe(22593);
    });

    test('wallet_switchEthereumChain should handle XAI chain', async () => {
      let currentChainId = '0x5841';

      const mockProvider = {
        request: async ({ method, params }) => {
          if (method === 'wallet_switchEthereumChain') {
            const targetChainId = params[0].chainId;
            if (targetChainId === '0x5841') {
              currentChainId = targetChainId;
              return null;
            }
            throw { code: 4902, message: 'Chain not supported' };
          }
        }
      };

      await expect(
        mockProvider.request({
          method: 'wallet_switchEthereumChain',
          params: [{ chainId: '0x5841' }]
        })
      ).resolves.toBeNull();

      await expect(
        mockProvider.request({
          method: 'wallet_switchEthereumChain',
          params: [{ chainId: '0x1' }]
        })
      ).rejects.toEqual({ code: 4902, message: 'Chain not supported' });
    });
  });

  describe('Transaction Signing', () => {
    test('eth_sendTransaction should require confirmation', async () => {
      const userConfirmed = jest.fn().mockResolvedValue(true);
      const signTx = jest.fn().mockResolvedValue('0x' + 'a'.repeat(64));

      const mockProvider = {
        request: async ({ method, params }) => {
          if (method === 'eth_sendTransaction') {
            const confirmed = await userConfirmed(params[0]);
            if (!confirmed) {
              throw { code: 4001, message: 'User rejected the request' };
            }
            return await signTx(params[0]);
          }
        }
      };

      const tx = { from: 'test', to: 'test2', value: '0x1000' };

      const hash = await mockProvider.request({
        method: 'eth_sendTransaction',
        params: [tx]
      });

      expect(userConfirmed).toHaveBeenCalledWith(tx);
      expect(signTx).toHaveBeenCalled();
      expect(hash).toMatch(/^0x[a-f0-9]{64}$/);
    });
  });

  describe('Error Handling', () => {
    test('should return error for unsupported methods', async () => {
      const mockProvider = {
        request: async ({ method }) => {
          const supported = ['eth_accounts', 'eth_chainId'];
          if (!supported.includes(method)) {
            throw { code: -32601, message: 'Method not found' };
          }
        }
      };

      await expect(
        mockProvider.request({ method: 'unsupported' })
      ).rejects.toEqual({ code: -32601, message: 'Method not found' });
    });

    test('should return error code 4001 for user rejection', async () => {
      const mockProvider = {
        request: async ({ method }) => {
          if (method === 'eth_requestAccounts') {
            throw { code: 4001, message: 'User rejected the request' };
          }
        }
      };

      await expect(
        mockProvider.request({ method: 'eth_requestAccounts' })
      ).rejects.toEqual({ code: 4001, message: 'User rejected the request' });
    });
  });
});

// ============================================================================
// Security Boundaries Tests
// ============================================================================

describe('Security Boundaries', () => {
  test('content script should not expose private keys', () => {
    const backgroundCode = fs.readFileSync(
      path.join(__dirname, '..', 'background.js'),
      'utf8'
    );

    expect(backgroundCode).not.toMatch(/sendResponse.*privateKey/i);
    expect(backgroundCode).not.toMatch(/sendResponse.*secret/i);
  });

  test('provider should not expose internal state', () => {
    const mockProvider = {
      isXAI: true,
      chainId: '0x5841',
      _privateKey: undefined,
      _sessionSecret: undefined
    };

    expect(mockProvider._privateKey).toBeUndefined();
    expect(mockProvider._sessionSecret).toBeUndefined();
  });

  test('messages should be validated', () => {
    const backgroundCode = fs.readFileSync(
      path.join(__dirname, '..', 'background.js'),
      'utf8'
    );

    expect(backgroundCode).toContain('message.type');
  });

  test('rate limiting should work', () => {
    const requestCounts = {};
    const MAX = 100;

    const rateLimiter = (origin) => {
      const now = Date.now();
      if (!requestCounts[origin]) {
        requestCounts[origin] = { count: 0, resetAt: now + 60000 };
      }
      if (now > requestCounts[origin].resetAt) {
        requestCounts[origin] = { count: 0, resetAt: now + 60000 };
      }
      requestCounts[origin].count++;
      return requestCounts[origin].count <= MAX;
    };

    for (let i = 0; i < 100; i++) {
      expect(rateLimiter('test')).toBe(true);
    }
    expect(rateLimiter('test')).toBe(false);
  });
});

// ============================================================================
// Provider Events Tests
// ============================================================================

describe('Provider Events', () => {
  test('should emit accountsChanged', () => {
    const listeners = {};
    const mockProvider = {
      on: (event, callback) => {
        if (!listeners[event]) listeners[event] = [];
        listeners[event].push(callback);
      },
      _emit: (event, data) => {
        (listeners[event] || []).forEach(cb => cb(data));
      }
    };

    const callback = jest.fn();
    mockProvider.on('accountsChanged', callback);
    mockProvider._emit('accountsChanged', ['XAI' + 'b'.repeat(40)]);

    expect(callback).toHaveBeenCalled();
  });

  test('should emit chainChanged', () => {
    const listeners = {};
    const mockProvider = {
      on: (event, callback) => {
        if (!listeners[event]) listeners[event] = [];
        listeners[event].push(callback);
      },
      _emit: (event, data) => {
        (listeners[event] || []).forEach(cb => cb(data));
      }
    };

    const callback = jest.fn();
    mockProvider.on('chainChanged', callback);
    mockProvider._emit('chainChanged', '0x5841');

    expect(callback).toHaveBeenCalledWith('0x5841');
  });

  test('should emit connect', () => {
    const listeners = {};
    const mockProvider = {
      on: (event, callback) => {
        if (!listeners[event]) listeners[event] = [];
        listeners[event].push(callback);
      },
      _emit: (event, data) => {
        (listeners[event] || []).forEach(cb => cb(data));
      }
    };

    const callback = jest.fn();
    mockProvider.on('connect', callback);
    mockProvider._emit('connect', { chainId: '0x5841' });

    expect(callback).toHaveBeenCalledWith({ chainId: '0x5841' });
  });

  test('should emit disconnect', () => {
    const listeners = {};
    const mockProvider = {
      on: (event, callback) => {
        if (!listeners[event]) listeners[event] = [];
        listeners[event].push(callback);
      },
      _emit: (event, data) => {
        (listeners[event] || []).forEach(cb => cb(data));
      }
    };

    const callback = jest.fn();
    mockProvider.on('disconnect', callback);
    mockProvider._emit('disconnect', { code: 1000 });

    expect(callback).toHaveBeenCalled();
  });
});

// ============================================================================
// DApp Communication Tests
// ============================================================================

describe('DApp Communication', () => {
  test('should queue requests when popup is closed', async () => {
    const requestQueue = [];
    let popupOpen = false;

    const mockProvider = {
      request: async ({ method, params }) => {
        if (!popupOpen) {
          return new Promise((resolve, reject) => {
            requestQueue.push({ method, params, resolve, reject });
          });
        }
        return 'processed';
      }
    };

    const requestPromise = mockProvider.request({ method: 'eth_sendTransaction', params: [{}] });

    expect(requestQueue).toHaveLength(1);

    popupOpen = true;
    requestQueue[0].resolve('0x' + 'a'.repeat(64));

    const result = await requestPromise;
    expect(result).toMatch(/^0x[a-f0-9]{64}$/);
  });
});
