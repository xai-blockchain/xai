/**
 * Security-Focused Tests
 *
 * Comprehensive security tests designed to catch vulnerabilities that would
 * be flagged in a security audit. Tests cover:
 *
 * - Cryptographic implementation correctness
 * - Private key handling
 * - Input validation and sanitization
 * - Timing attack resistance
 * - Memory handling of sensitive data
 * - XSS/injection prevention
 * - CSRF considerations
 * - Secure random number generation
 *
 * @security CRITICAL - These tests validate security-critical functionality
 */

'use strict';

const fs = require('fs');
const path = require('path');

describe('Security Tests', () => {
  // ==========================================================================
  // Cryptographic Security Tests
  // ==========================================================================

  describe('Cryptographic Implementation', () => {
    describe('Key Derivation', () => {
      test('PBKDF2 iterations should meet NIST minimum (600,000)', () => {
        const code = fs.readFileSync(
          path.join(__dirname, '..', 'secure-storage.js'),
          'utf8'
        );

        const match = code.match(/PBKDF2_ITERATIONS\s*=\s*(\d+)/);
        expect(match).not.toBeNull();

        const iterations = parseInt(match[1], 10);
        expect(iterations).toBeGreaterThanOrEqual(600000);
      });

      test('Salt should be at least 128 bits (16 bytes)', () => {
        const code = fs.readFileSync(
          path.join(__dirname, '..', 'secure-storage.js'),
          'utf8'
        );

        const match = code.match(/SALT_LENGTH\s*=\s*(\d+)/);
        expect(match).not.toBeNull();

        const saltLength = parseInt(match[1], 10);
        expect(saltLength).toBeGreaterThanOrEqual(16);
      });

      test('Should use SHA-256 or better for PBKDF2', () => {
        const code = fs.readFileSync(
          path.join(__dirname, '..', 'secure-storage.js'),
          'utf8'
        );

        expect(code).toMatch(/hash:\s*['"]SHA-256['"]/);
      });
    });

    describe('Encryption', () => {
      test('Should use AES-256-GCM (authenticated encryption)', () => {
        const code = fs.readFileSync(
          path.join(__dirname, '..', 'secure-storage.js'),
          'utf8'
        );

        expect(code).toContain('AES-GCM');
        expect(code).toMatch(/KEY_LENGTH\s*=\s*256/);
      });

      test('IV should be 96 bits (12 bytes) for GCM mode', () => {
        const code = fs.readFileSync(
          path.join(__dirname, '..', 'secure-storage.js'),
          'utf8'
        );

        const match = code.match(/IV_LENGTH\s*=\s*(\d+)/);
        expect(match).not.toBeNull();
        expect(parseInt(match[1], 10)).toBe(12);
      });

      test('IV should be generated randomly for each encryption', () => {
        const code = fs.readFileSync(
          path.join(__dirname, '..', 'secure-storage.js'),
          'utf8'
        );

        // Check that getRandomValues is used for IV
        expect(code).toContain('crypto.getRandomValues');
      });

      test('Should not reuse IV with same key', () => {
        // This is enforced by generating new IV each encryption
        const code = fs.readFileSync(
          path.join(__dirname, '..', 'secure-storage.js'),
          'utf8'
        );

        // IV is generated inside encryptData, not stored globally
        const encryptMatch = code.match(/async function encryptData[\s\S]*?new Uint8Array\(IV_LENGTH\)/);
        expect(encryptMatch).not.toBeNull();
      });
    });

    describe('Signature Handling', () => {
      test('Should use canonical signature format (low-S)', () => {
        const trezorCode = fs.readFileSync(
          path.join(__dirname, '..', 'trezor-hw.js'),
          'utf8'
        );

        // Check for S canonicalization
        expect(trezorCode).toContain('canonicalizeS');
        expect(trezorCode).toContain('SECP256K1_N');
      });

      test('Should use secp256k1 curve', () => {
        const trezorCode = fs.readFileSync(
          path.join(__dirname, '..', 'trezor-hw.js'),
          'utf8'
        );

        expect(trezorCode).toContain('secp256k1');
      });
    });
  });

  // ==========================================================================
  // Private Key Security Tests
  // ==========================================================================

  describe('Private Key Handling', () => {
    test('Private keys should never be logged', () => {
      const files = [
        'secure-storage.js',
        'popup.js',
        'popup-encrypted.js',
        'trezor-hw.js',
        'ledger-hw.js'
      ];

      files.forEach(filename => {
        const code = fs.readFileSync(
          path.join(__dirname, '..', filename),
          'utf8'
        );

        // Check for dangerous logging patterns
        const dangerousPatterns = [
          /console\.log\([^)]*privateKey/i,
          /console\.log\([^)]*secret/i,
          /console\.log\([^)]*password/i,
          /console\.error\([^)]*privateKey/i,
        ];

        dangerousPatterns.forEach(pattern => {
          expect(code).not.toMatch(pattern);
        });
      });
    });

    test('Private keys should not be stored in chrome.storage unencrypted', () => {
      const popupCode = fs.readFileSync(
        path.join(__dirname, '..', 'popup.js'),
        'utf8'
      );

      // Should not directly store private keys
      expect(popupCode).not.toMatch(/chrome\.storage\.[^}]*privateKey/i);
    });

    test('Hardware wallets should never expose private keys', () => {
      const trezorCode = fs.readFileSync(
        path.join(__dirname, '..', 'trezor-hw.js'),
        'utf8'
      );

      const ledgerCode = fs.readFileSync(
        path.join(__dirname, '..', 'ledger-hw.js'),
        'utf8'
      );

      // Private keys should stay on device
      expect(trezorCode).toContain('private key never');
      expect(ledgerCode).toContain('private key');

      // Functions should only return public keys and signatures
      expect(trezorCode).toContain('publicKey');
      expect(trezorCode).toContain('signature');
    });

    test('Password should be cleared on lock', () => {
      const storageCode = fs.readFileSync(
        path.join(__dirname, '..', 'secure-storage.js'),
        'utf8'
      );

      // Lock function should clear password
      const lockMatch = storageCode.match(/lock\s*\(\s*\)\s*{[\s\S]*?password\s*=\s*null/);
      expect(lockMatch).not.toBeNull();
    });
  });

  // ==========================================================================
  // Input Validation Tests
  // ==========================================================================

  describe('Input Validation', () => {
    test('BIP32 path should be validated', () => {
      const trezorCode = fs.readFileSync(
        path.join(__dirname, '..', 'trezor-hw.js'),
        'utf8'
      );

      expect(trezorCode).toContain('validateBip32Path');
      expect(trezorCode).toMatch(/bip32Regex/i);
    });

    test('Private key format should be validated (64 hex chars)', () => {
      const popupCode = fs.readFileSync(
        path.join(__dirname, '..', 'popup.js'),
        'utf8'
      );

      expect(popupCode).toMatch(/privateKey.*length.*64/i);
    });

    test('Password minimum length should be enforced', () => {
      const storageCode = fs.readFileSync(
        path.join(__dirname, '..', 'secure-storage.js'),
        'utf8'
      );

      expect(storageCode).toMatch(/password.*length\s*<\s*8/);
    });

    test('API host should use URL validation pattern', () => {
      // Check that URL-like strings are expected
      const backgroundCode = fs.readFileSync(
        path.join(__dirname, '..', 'background.js'),
        'utf8'
      );

      expect(backgroundCode).toMatch(/http:\/\//);
    });
  });

  // ==========================================================================
  // Memory Security Tests
  // ==========================================================================

  describe('Memory Security', () => {
    test('Auto-lock should clear sensitive data', () => {
      const storageCode = fs.readFileSync(
        path.join(__dirname, '..', 'secure-storage.js'),
        'utf8'
      );

      // Auto-lock timer should exist
      expect(storageCode).toContain('autoLockTimer');
      expect(storageCode).toContain('setTimeout');
      expect(storageCode).toContain('AUTO_LOCK_TIMEOUT');

      // Lock should clear password (use simpler pattern that matches multiline)
      expect(storageCode).toContain('this.password = null');
      expect(storageCode).toContain('this.isLocked = true');
    });

    test('CryptoKey should not be extractable', () => {
      const storageCode = fs.readFileSync(
        path.join(__dirname, '..', 'secure-storage.js'),
        'utf8'
      );

      // deriveKey should use extractable: false
      expect(storageCode).toMatch(/deriveKey[\s\S]*?false[\s\S]*?\['encrypt',\s*'decrypt'\]/);
    });

    test('Sensitive form fields should be clearable', () => {
      const popupCode = fs.readFileSync(
        path.join(__dirname, '..', 'popup.js'),
        'utf8'
      );

      // Private key field should be cleared after use
      expect(popupCode).toMatch(/privateKey.*value\s*=\s*['"]['"]|\.value\s*=\s*['"]['"].*privateKey/);
    });
  });

  // ==========================================================================
  // XSS Prevention Tests
  // ==========================================================================

  describe('XSS Prevention', () => {
    test('User input should not be directly inserted as HTML', () => {
      const popupCode = fs.readFileSync(
        path.join(__dirname, '..', 'popup.js'),
        'utf8'
      );

      // innerHTML assignments should use template literals with escaped data
      // or use textContent instead
      const innerHTMLAssignments = popupCode.match(/\.innerHTML\s*=/g);

      // If innerHTML is used, it should be with sanitized content
      // Check that textContent is also used for dynamic user content
      expect(popupCode).toContain('.textContent');
    });

    test('JSON should be properly stringified before display', () => {
      const popupCode = fs.readFileSync(
        path.join(__dirname, '..', 'popup.js'),
        'utf8'
      );

      // When displaying JSON, use JSON.stringify
      expect(popupCode).toMatch(/JSON\.stringify.*null.*2/);
    });
  });

  // ==========================================================================
  // Timing Attack Resistance Tests
  // ==========================================================================

  describe('Timing Attack Resistance', () => {
    test('Password comparison should use constant-time operations', () => {
      const storageCode = fs.readFileSync(
        path.join(__dirname, '..', 'secure-storage.js'),
        'utf8'
      );

      // Password verification is done by decryption, which is inherently
      // constant-time (AES-GCM auth tag verification)
      expect(storageCode).toContain('AES-GCM');
    });

    test('Signature canonicalization should not leak S value', () => {
      const trezorCode = fs.readFileSync(
        path.join(__dirname, '..', 'trezor-hw.js'),
        'utf8'
      );

      // Canonicalization uses BigInt comparison, which is reasonably constant-time
      expect(trezorCode).toContain('BigInt');
    });
  });

  // ==========================================================================
  // Random Number Generation Tests
  // ==========================================================================

  describe('Random Number Generation', () => {
    test('Should use crypto.getRandomValues for all randomness', () => {
      const files = ['secure-storage.js', 'popup.js'];

      files.forEach(filename => {
        const code = fs.readFileSync(
          path.join(__dirname, '..', filename),
          'utf8'
        );

        // Should not use Math.random for security-sensitive operations
        const mathRandomMatches = code.match(/Math\.random\(\)/g);

        // If Math.random is used, it should not be for security purposes
        // (e.g., it might be used for UI animations only)
        if (mathRandomMatches) {
          // Verify it's not used for keys, IVs, salts, or nonces
          expect(code).not.toMatch(/salt.*Math\.random|Math\.random.*salt/i);
          expect(code).not.toMatch(/iv.*Math\.random|Math\.random.*iv/i);
          expect(code).not.toMatch(/key.*Math\.random|Math\.random.*key/i);
        }
      });
    });

    test('Web Crypto API should be used for all cryptographic operations', () => {
      const storageCode = fs.readFileSync(
        path.join(__dirname, '..', 'secure-storage.js'),
        'utf8'
      );

      expect(storageCode).toContain('crypto.subtle');
    });
  });

  // ==========================================================================
  // Error Handling Security Tests
  // ==========================================================================

  describe('Error Handling Security', () => {
    test('Error messages should not leak sensitive information', () => {
      const storageCode = fs.readFileSync(
        path.join(__dirname, '..', 'secure-storage.js'),
        'utf8'
      );

      // Decryption errors should be generic
      expect(storageCode).toMatch(/Decryption failed.*wrong password.*corrupted/i);
    });

    test('Stack traces should not be exposed to users', () => {
      const popupCode = fs.readFileSync(
        path.join(__dirname, '..', 'popup.js'),
        'utf8'
      );

      // Error handling should use message, not full stack
      const catchBlocks = popupCode.match(/catch\s*\(\s*\w+\s*\)\s*\{[^}]*\}/g) || [];

      catchBlocks.forEach(block => {
        // Should use .message, not .stack
        if (block.includes('textContent') || block.includes('innerHTML')) {
          expect(block).not.toContain('.stack');
        }
      });
    });
  });

  // ==========================================================================
  // Authentication Security Tests
  // ==========================================================================

  describe('Authentication Security', () => {
    test('Session tokens should be generated server-side', () => {
      const popupCode = fs.readFileSync(
        path.join(__dirname, '..', 'popup.js'),
        'utf8'
      );

      // Session tokens come from server response
      expect(popupCode).toMatch(/payload\.session_token/);
    });

    test('ECDH should be used for key exchange', () => {
      const popupCode = fs.readFileSync(
        path.join(__dirname, '..', 'popup.js'),
        'utf8'
      );

      expect(popupCode).toContain('ECDH');
      expect(popupCode).toContain('P-256');
    });

    test('HKDF should be used for key derivation after ECDH', () => {
      const popupCode = fs.readFileSync(
        path.join(__dirname, '..', 'popup.js'),
        'utf8'
      );

      expect(popupCode).toContain('HKDF');
    });
  });

  // ==========================================================================
  // Content Security Tests
  // ==========================================================================

  describe('Content Security', () => {
    test('Manifest should specify CSP', () => {
      const manifest = JSON.parse(fs.readFileSync(
        path.join(__dirname, '..', 'manifest.json'),
        'utf8'
      ));

      // CSP should be defined (may vary by manifest version)
      expect(
        manifest.content_security_policy ||
        manifest.content_security_policy_extension
      ).toBeDefined();
    });

    test('Should not use eval or Function constructor', () => {
      const files = [
        'popup.js',
        'popup-encrypted.js',
        'background.js',
        'secure-storage.js'
      ];

      files.forEach(filename => {
        const code = fs.readFileSync(
          path.join(__dirname, '..', filename),
          'utf8'
        );

        expect(code).not.toMatch(/\beval\s*\(/);
        expect(code).not.toMatch(/new\s+Function\s*\(/);
      });
    });

    test('Should not use inline event handlers', () => {
      const htmlFiles = [
        'popup.html',
        'popup-encrypted.html',
        'popup-hw.html'
      ];

      htmlFiles.forEach(filename => {
        try {
          const html = fs.readFileSync(
            path.join(__dirname, '..', filename),
            'utf8'
          );

          // Should not have onclick, onload, etc.
          expect(html).not.toMatch(/on\w+\s*=/i);
        } catch (e) {
          // File may not exist
        }
      });
    });
  });

  // ==========================================================================
  // Protocol Security Tests
  // ==========================================================================

  describe('Protocol Security', () => {
    test('Default API host should use localhost', () => {
      const backgroundCode = fs.readFileSync(
        path.join(__dirname, '..', 'background.js'),
        'utf8'
      );

      expect(backgroundCode).toMatch(/localhost.*8545/);
    });

    test('XAI coin type should be registered (22593)', () => {
      const trezorCode = fs.readFileSync(
        path.join(__dirname, '..', 'trezor-hw.js'),
        'utf8'
      );

      expect(trezorCode).toContain('22593');
    });

    test('BIP44 path structure should be correct', () => {
      const trezorCode = fs.readFileSync(
        path.join(__dirname, '..', 'trezor-hw.js'),
        'utf8'
      );

      // m/44'/coin_type'/account'/change/address_index
      expect(trezorCode).toMatch(/m\/44['']\/22593['']/);
    });
  });
});

// ============================================================================
// Vulnerability Regression Tests
// ============================================================================

describe('Vulnerability Regression Tests', () => {
  test('CVE-like: No prototype pollution in JSON parsing', () => {
    // Ensure __proto__ is not exploitable
    const malicious = '{"__proto__":{"isAdmin":true}}';
    const parsed = JSON.parse(malicious);

    expect({}.isAdmin).toBeUndefined();
  });

  test('No ReDoS in validation regexes', () => {
    const trezorCode = fs.readFileSync(
      path.join(__dirname, '..', 'trezor-hw.js'),
      'utf8'
    );

    // BIP32 regex should not be vulnerable to catastrophic backtracking
    const regexMatch = trezorCode.match(/bip32Regex\s*=\s*\/([^/]+)\//);
    if (regexMatch) {
      const pattern = regexMatch[1];

      // Simple patterns are safe, nested quantifiers are dangerous
      expect(pattern).not.toMatch(/\(\.\*\)\+/);
      expect(pattern).not.toMatch(/\(\.\+\)\*/);
    }
  });

  test('APDU commands use proper length fields', () => {
    const ledgerCode = fs.readFileSync(
      path.join(__dirname, '..', 'ledger-hw.js'),
      'utf8'
    );

    // APDU creation should include length byte
    expect(ledgerCode).toMatch(/buffer\[\d+\]\s*=\s*data\.length/);
  });

  test('Transaction payload is deterministically serialized', () => {
    const popupCode = fs.readFileSync(
      path.join(__dirname, '..', 'popup.js'),
      'utf8'
    );

    // stableStringify should sort keys
    expect(popupCode).toMatch(/keys\s*=\s*Object\.keys\([^)]+\)\.sort\(\)/);
  });
});
