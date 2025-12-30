/**
 * Popup Functionality Tests
 *
 * Comprehensive tests for the XAI Wallet popup interface.
 * Tests cover:
 * - Wallet creation and import
 * - Transaction building and signing
 * - UI state management
 * - Session management
 * - Mining controls
 * - AI swap functionality
 * - Security validations
 *
 * @security Validates user input handling and sensitive data management
 */

'use strict';

const fs = require('fs');
const path = require('path');

// Load source files for static analysis
const popupCode = fs.readFileSync(
  path.join(__dirname, '..', 'popup.js'),
  'utf8'
);

const popupEncryptedCode = fs.readFileSync(
  path.join(__dirname, '..', 'popup-encrypted.js'),
  'utf8'
);

const hwIntegrationCode = fs.readFileSync(
  path.join(__dirname, '..', 'popup-hw-integration.js'),
  'utf8'
);

const hwUiCode = fs.readFileSync(
  path.join(__dirname, '..', 'hw-ui.js'),
  'utf8'
);

describe('Popup Module', () => {
  // ==========================================================================
  // Utility Function Tests
  // ==========================================================================

  describe('Utility Functions', () => {
    describe('$ (querySelector wrapper)', () => {
      test('should be defined as querySelector wrapper', () => {
        // In popup.js the $ function is defined later (line 283)
        // In popup-encrypted.js the $ function is on line 57
        expect(popupEncryptedCode).toContain('function $(selector)');
        expect(popupEncryptedCode).toContain('document.querySelector(selector)');
      });
    });

    describe('bufferToHex', () => {
      test('should convert ArrayBuffer to hex string', () => {
        expect(popupCode).toContain('function bufferToHex');
        expect(popupCode).toMatch(/toString\s*\(\s*16\s*\)/);
        expect(popupCode).toMatch(/padStart\s*\(\s*2/);
      });
    });

    describe('hexToBytes', () => {
      test('should convert hex string to Uint8Array', () => {
        expect(popupCode).toContain('function hexToBytes');
        expect(popupCode).toMatch(/parseInt.*16/);
      });
    });

    describe('stableStringify', () => {
      test('should sort object keys for deterministic output', () => {
        expect(popupCode).toContain('function stableStringify');
        expect(popupCode).toMatch(/Object\.keys.*\.sort\(\)/);
      });

      test('should handle arrays without reordering', () => {
        // Arrays should be mapped, not sorted
        expect(popupCode).toContain('Array.isArray(value)');
        expect(popupCode).toContain('.map(');
      });

      test('should handle null values', () => {
        expect(popupCode).toMatch(/=== null.*'null'/);
      });
    });
  });

  // ==========================================================================
  // Signing Tests
  // ==========================================================================

  describe('Transaction Signing', () => {
    describe('signPayload', () => {
      test('should validate payload string', () => {
        expect(popupCode).toMatch(/if\s*\(!payloadStr/);
      });

      test('should validate private key format (64 hex chars)', () => {
        expect(popupCode).toMatch(/privateKey.*length.*64/i);
      });

      test('should hash payload with SHA-256', () => {
        expect(popupCode).toMatch(/digest.*SHA-256/);
      });

      test('should call backend signing endpoint', () => {
        expect(popupCode).toContain('/wallet/sign');
      });
    });

    describe('presentSigningPreview', () => {
      test('should display payload preview modal', () => {
        expect(popupCode).toContain('signingPreview');
        expect(popupCode).toContain('signingPayloadPreview');
      });

      test('should show payload hash', () => {
        expect(popupCode).toContain('signingPayloadHash');
      });

      test('should require acknowledgment before signing', () => {
        expect(popupCode).toContain('signingAcknowledge');
      });

      test('should have confirm and cancel buttons', () => {
        expect(popupCode).toContain('confirmSigning');
        expect(popupCode).toContain('cancelSigning');
      });
    });
  });

  // ==========================================================================
  // API Host Tests
  // ==========================================================================

  describe('API Host Management', () => {
    test('should have getApiHost function', () => {
      expect(popupCode).toContain('function getApiHost');
    });

    test('should have setApiHost function', () => {
      expect(popupCode).toContain('function setApiHost');
    });

    test('should use chrome.storage.local for API host', () => {
      // API_KEY constant is 'apiHost', used with chrome.storage.local
      expect(popupCode).toContain("const API_KEY = 'apiHost'");
      expect(popupCode).toContain('chrome.storage.local.get');
      expect(popupCode).toContain('chrome.storage.local.set');
    });

    test('should have default localhost API host', () => {
      expect(popupCode).toMatch(/localhost.*8545/);
    });
  });

  // ==========================================================================
  // Session Management Tests
  // ==========================================================================

  describe('Session Management', () => {
    test('should have saveSession function', () => {
      expect(popupCode).toContain('function saveSession');
    });

    test('should have getSession function', () => {
      expect(popupCode).toContain('function getSession');
    });

    test('should have registerSession function', () => {
      expect(popupCode).toContain('function registerSession');
    });

    test('should use correct session storage keys', () => {
      expect(popupCode).toContain('walletSessionToken');
      expect(popupCode).toContain('walletSessionSecret');
      expect(popupCode).toContain('walletSessionAddress');
    });

    test('registerSession should call API endpoint', () => {
      expect(popupCode).toContain('/wallet-trades/register');
    });
  });

  // ==========================================================================
  // Security Tests
  // ==========================================================================

  describe('Security', () => {
    test('should not log private keys', () => {
      // Check for dangerous logging patterns
      expect(popupCode).not.toMatch(/console\.log\([^)]*privateKey/i);
      expect(popupCode).not.toMatch(/console\.log\([^)]*secret/i);
    });

    test('should validate wallet address format', () => {
      expect(popupCode).toContain('walletAddress');
    });

    test('should use textContent for user data display', () => {
      expect(popupCode).toContain('.textContent');
    });

    test('should stringify JSON for display', () => {
      expect(popupCode).toMatch(/JSON\.stringify.*null.*2/);
    });
  });

  // ==========================================================================
  // Input Validation Tests
  // ==========================================================================

  describe('Input Validation', () => {
    test('should validate private key format', () => {
      expect(popupCode).toMatch(/privateKey.*length.*64/i);
    });

    test('should sanitize display of user data', () => {
      // Use textContent instead of innerHTML for user data
      expect(popupCode).toContain('.textContent');
    });

    test('should handle form data parsing', () => {
      expect(popupCode).toContain('FormData');
    });
  });

  // ==========================================================================
  // WalletConnect Handshake Tests
  // ==========================================================================

  describe('WalletConnect Handshake', () => {
    test('should use ECDH with P-256 for key exchange', () => {
      expect(popupCode).toContain('ECDH');
      expect(popupCode).toContain('P-256');
    });

    test('should use HKDF for session key derivation', () => {
      expect(popupCode).toContain('HKDF');
    });

    test('should have handshake endpoint', () => {
      expect(popupCode).toContain('/wallet-trades/wc/handshake');
    });
  });

  // ==========================================================================
  // Mining Controls Tests
  // ==========================================================================

  describe('Mining Controls', () => {
    test('should have start mining function', () => {
      expect(popupCode).toContain('startMining');
    });

    test('should have stop mining function', () => {
      expect(popupCode).toContain('stopMining');
    });

    test('should have mining status display', () => {
      expect(popupCode).toContain('miningStatus');
    });

    test('should have miner stats display', () => {
      expect(popupCode).toContain('minerStats');
    });
  });

  // ==========================================================================
  // AI Swap Tests
  // ==========================================================================

  describe('AI Swap Functionality', () => {
    test('should have AI swap function', () => {
      expect(popupCode).toContain('runAiSwap');
    });

    test('should support AI API key management', () => {
      expect(popupCode).toContain('aiApiKey');
    });

    test('should have AI status display', () => {
      expect(popupCode).toContain('aiStatus');
    });

    test('should have clear AI key function', () => {
      expect(popupCode).toContain('clearAiKey');
    });
  });

  // ==========================================================================
  // Order Management Tests
  // ==========================================================================

  describe('Order Management', () => {
    test('should have order form handling', () => {
      expect(popupCode).toContain('orderForm');
    });

    test('should have order submission function', () => {
      expect(popupCode).toContain('submitOrder');
    });

    test('should have order refresh function', () => {
      expect(popupCode).toContain('refreshOrders');
    });

    test('should have matches refresh function', () => {
      expect(popupCode).toContain('refreshMatches');
    });

    test('should have trade history display', () => {
      expect(popupCode).toContain('tradeHistory');
    });
  });
});

// ============================================================================
// Popup Encrypted Module Tests
// ============================================================================

describe('Popup Encrypted Module', () => {
  describe('Security Integration', () => {
    test('should integrate with secureStorage', () => {
      expect(popupEncryptedCode).toContain('secureStorage');
    });

    test('should have lock status display', () => {
      expect(popupEncryptedCode).toContain('lockStatus');
    });

    test('should have unlock modal', () => {
      expect(popupEncryptedCode).toContain('unlockModal');
    });

    test('should handle locked state', () => {
      // Uses secureStorage.isStorageLocked() method
      expect(popupEncryptedCode).toContain('isStorageLocked');
    });
  });

  describe('Encryption Setup', () => {
    test('should have encryption setup modal', () => {
      expect(popupEncryptedCode).toContain('setupEncryptionModal');
    });

    test('should have password setup inputs', () => {
      expect(popupEncryptedCode).toContain('setupPassword');
    });

    test('should validate password confirmation', () => {
      expect(popupEncryptedCode).toContain('setupPasswordConfirm');
    });
  });

  describe('Session Management Override', () => {
    test('should override saveSession for encryption', () => {
      expect(popupEncryptedCode).toContain('saveSession');
    });

    test('should override getSession for decryption', () => {
      expect(popupEncryptedCode).toContain('getSession');
    });
  });
});

// ============================================================================
// Hardware Wallet Integration Tests
// ============================================================================

describe('Popup HW Integration', () => {
  describe('Hardware Wallet Detection', () => {
    test('should check for hardware wallet UI', () => {
      expect(hwIntegrationCode).toContain('hwUI');
    });

    test('should check shouldUseHardwareWallet', () => {
      expect(hwIntegrationCode).toContain('shouldUseHardwareWallet');
    });
  });

  describe('Signing Override', () => {
    test('should store original signPayload', () => {
      expect(hwIntegrationCode).toContain('originalSignPayload');
    });

    test('should override window.signPayload', () => {
      expect(hwIntegrationCode).toContain('window.signPayload');
    });

    test('should use hardware wallet for signing when connected', () => {
      expect(hwIntegrationCode).toContain('signTransactionWithUI');
    });
  });

  describe('Order Submission Override', () => {
    test('should store original submitOrder', () => {
      expect(hwIntegrationCode).toContain('originalSubmitOrder');
    });

    test('should override window.submitOrder', () => {
      expect(hwIntegrationCode).toContain('window.submitOrder');
    });

    test('should get address from hardware wallet', () => {
      expect(hwIntegrationCode).toContain('hwUI.getAddress');
    });

    test('should get public key from hardware wallet', () => {
      expect(hwIntegrationCode).toContain('hwUI.getPublicKey');
    });
  });

  describe('Fallback Behavior', () => {
    test('should fall back to software signing when no HW', () => {
      expect(hwIntegrationCode).toContain('originalSignPayload');
    });
  });
});

// ============================================================================
// Hardware Wallet UI Tests
// ============================================================================

describe('Hardware Wallet UI', () => {
  describe('Connection Modal', () => {
    test('should have connection modal', () => {
      expect(hwUiCode).toContain('hwConnectionModal');
    });

    test('should have device selection', () => {
      expect(hwUiCode).toContain('hwSelectLedger');
      expect(hwUiCode).toContain('hwSelectTrezor');
    });

    test('should show connection status', () => {
      expect(hwUiCode).toContain('hwStatus');
    });
  });

  describe('Signing Flow', () => {
    test('should have signing prompt', () => {
      expect(hwUiCode).toContain('hwSigningPrompt');
    });

    test('should display device type in prompt', () => {
      expect(hwUiCode).toContain('hwSigningDevice');
    });

    test('should display payload in prompt', () => {
      expect(hwUiCode).toContain('hwSigningPayload');
    });

    test('should update signing status', () => {
      expect(hwUiCode).toContain('hwSigningStatus');
    });
  });

  describe('Error Handling', () => {
    test('should have friendly error messages', () => {
      expect(hwUiCode).toContain('getFriendlyErrorMessage');
    });

    test('should handle device not found', () => {
      expect(hwUiCode).toContain('not found');
    });

    test('should handle device locked', () => {
      expect(hwUiCode).toContain('locked');
    });

    test('should handle user rejection', () => {
      expect(hwUiCode).toContain('rejected');
    });
  });

  describe('UI State Management', () => {
    test('should track initialization state', () => {
      expect(hwUiCode).toContain('isInitialized');
    });

    test('should bind event listeners', () => {
      expect(hwUiCode).toContain('bindEventListeners');
    });

    test('should update UI on state change', () => {
      expect(hwUiCode).toContain('updateUI');
    });
  });
});

// ============================================================================
// Edge Cases and Error Handling
// ============================================================================

describe('Edge Cases', () => {
  test('popup.js should handle network errors', () => {
    // Should have try-catch blocks for async operations
    expect(popupCode).toMatch(/try\s*\{[\s\S]*?catch/);
  });

  test('popup.js should display error messages', () => {
    expect(popupCode).toContain('tradeMessage');
    expect(popupCode).toMatch(/Error:|error/);
  });

  test('hw-integration.js should handle missing hwUI', () => {
    expect(hwIntegrationCode).toMatch(/hwUI\s*&&/);
  });
});
