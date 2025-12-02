/**
 * XAI Browser Wallet - Secure Storage Module
 *
 * Implements client-side encryption for sensitive data using Web Crypto API.
 * All sensitive data (private keys, session secrets, API keys) is encrypted
 * with AES-256-GCM before storage in chrome.storage.local.
 *
 * Security features:
 * - AES-256-GCM authenticated encryption
 * - PBKDF2 key derivation with 600,000 iterations (NIST recommended)
 * - Unique salt per encryption operation
 * - Auto-lock after inactivity
 * - In-memory key storage only (never persisted)
 * - Migration from plaintext storage
 *
 * @module SecureStorage
 */

const PBKDF2_ITERATIONS = 600000; // NIST SP 800-132 recommendation
const SALT_LENGTH = 16; // 128 bits
const IV_LENGTH = 12; // 96 bits for GCM
const KEY_LENGTH = 256; // AES-256
const AUTO_LOCK_TIMEOUT = 15 * 60 * 1000; // 15 minutes in milliseconds

/**
 * Derives an AES-256-GCM key from a password using PBKDF2.
 *
 * @param {string} password - User password
 * @param {Uint8Array} salt - Cryptographic salt (16 bytes)
 * @returns {Promise<CryptoKey>} Derived encryption key
 */
async function deriveKey(password, salt) {
  const encoder = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    encoder.encode(password),
    'PBKDF2',
    false,
    ['deriveKey']
  );

  return await crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: salt,
      iterations: PBKDF2_ITERATIONS,
      hash: 'SHA-256'
    },
    keyMaterial,
    { name: 'AES-GCM', length: KEY_LENGTH },
    false,
    ['encrypt', 'decrypt']
  );
}

/**
 * Encrypts data with AES-256-GCM.
 *
 * Output format: [salt(16) || iv(12) || ciphertext || authTag(16)]
 * All encoded as base64 for storage.
 *
 * @param {any} data - Data to encrypt (will be JSON stringified)
 * @param {string} password - Encryption password
 * @returns {Promise<string>} Base64-encoded encrypted data
 * @throws {Error} If encryption fails
 */
async function encryptData(data, password) {
  try {
    // Generate random salt and IV
    const salt = crypto.getRandomValues(new Uint8Array(SALT_LENGTH));
    const iv = crypto.getRandomValues(new Uint8Array(IV_LENGTH));

    // Derive encryption key
    const key = await deriveKey(password, salt);

    // Encrypt data
    const encoder = new TextEncoder();
    const plaintext = encoder.encode(JSON.stringify(data));
    const ciphertext = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv: iv },
      key,
      plaintext
    );

    // Combine salt + iv + ciphertext
    const combined = new Uint8Array(
      SALT_LENGTH + IV_LENGTH + ciphertext.byteLength
    );
    combined.set(salt, 0);
    combined.set(iv, SALT_LENGTH);
    combined.set(new Uint8Array(ciphertext), SALT_LENGTH + IV_LENGTH);

    // Encode to base64 for storage
    return btoa(String.fromCharCode(...combined));
  } catch (error) {
    console.error('Encryption failed:', error);
    throw new Error(`Encryption failed: ${error.message}`);
  }
}

/**
 * Decrypts AES-256-GCM encrypted data.
 *
 * @param {string} encryptedBase64 - Base64-encoded encrypted data
 * @param {string} password - Decryption password
 * @returns {Promise<any>} Decrypted and parsed data
 * @throws {Error} If decryption fails (wrong password or corrupted data)
 */
async function decryptData(encryptedBase64, password) {
  try {
    // Decode from base64
    const combined = Uint8Array.from(
      atob(encryptedBase64),
      (c) => c.charCodeAt(0)
    );

    // Extract components
    const salt = combined.slice(0, SALT_LENGTH);
    const iv = combined.slice(SALT_LENGTH, SALT_LENGTH + IV_LENGTH);
    const ciphertext = combined.slice(SALT_LENGTH + IV_LENGTH);

    // Derive decryption key
    const key = await deriveKey(password, salt);

    // Decrypt data
    const decrypted = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: iv },
      key,
      ciphertext
    );

    // Parse JSON
    const decoder = new TextDecoder();
    return JSON.parse(decoder.decode(decrypted));
  } catch (error) {
    console.error('Decryption failed:', error);
    throw new Error(
      'Decryption failed: wrong password or corrupted data'
    );
  }
}

/**
 * SecureStorage class provides encrypted storage for sensitive data.
 *
 * Features:
 * - Transparent encryption/decryption
 * - Auto-lock after inactivity
 * - Migration from plaintext storage
 * - Session management
 *
 * @class
 */
class SecureStorage {
  constructor() {
    this.password = null;
    this.isLocked = true;
    this.autoLockTimer = null;
    this.encryptionEnabled = false;
  }

  /**
   * Initializes secure storage and checks encryption status.
   *
   * @returns {Promise<boolean>} True if encryption is enabled
   */
  async initialize() {
    const status = await this._getEncryptionStatus();
    this.encryptionEnabled = status.enabled;
    return this.encryptionEnabled;
  }

  /**
   * Checks if encryption is enabled in storage.
   *
   * @returns {Promise<{enabled: boolean, version: number}>}
   * @private
   */
  async _getEncryptionStatus() {
    return new Promise((resolve) => {
      chrome.storage.local.get(['_encryptionEnabled'], (result) => {
        resolve({
          enabled: result._encryptionEnabled || false,
          version: 1
        });
      });
    });
  }

  /**
   * Enables encryption and migrates existing plaintext data.
   *
   * @param {string} password - Password for encryption
   * @returns {Promise<void>}
   */
  async enableEncryption(password) {
    if (!password || password.length < 8) {
      throw new Error(
        'Password must be at least 8 characters'
      );
    }

    // Store password in memory
    this.password = password;
    this.isLocked = false;

    // Migrate existing plaintext data
    await this._migratePlaintextData(password);

    // Mark encryption as enabled
    await chrome.storage.local.set({ _encryptionEnabled: true });
    this.encryptionEnabled = true;

    // Start auto-lock timer
    this._resetAutoLockTimer();
  }

  /**
   * Migrates plaintext data to encrypted storage.
   *
   * @param {string} password - Encryption password
   * @returns {Promise<void>}
   * @private
   */
  async _migratePlaintextData(password) {
    const plaintextKeys = [
      'walletSessionToken',
      'walletSessionSecret',
      'walletSessionAddress',
      'personalAiApiKey',
      'walletAddress',
      'apiHost'
    ];

    return new Promise((resolve) => {
      chrome.storage.local.get(plaintextKeys, async (result) => {
        const migratedData = {};

        // Encrypt each plaintext value
        for (const key of plaintextKeys) {
          if (result[key]) {
            try {
              const encrypted = await encryptData(result[key], password);
              migratedData[`_encrypted_${key}`] = encrypted;
            } catch (error) {
              console.error(
                `Failed to migrate ${key}:`,
                error
              );
            }
          }
        }

        // Store encrypted data
        await chrome.storage.local.set(migratedData);

        // Remove plaintext data
        await chrome.storage.local.remove(plaintextKeys);

        resolve();
      });
    });
  }

  /**
   * Unlocks storage with password.
   *
   * @param {string} password - Unlock password
   * @returns {Promise<boolean>} True if unlock successful
   */
  async unlock(password) {
    if (!this.encryptionEnabled) {
      throw new Error('Encryption not enabled');
    }

    try {
      // Verify password by attempting to decrypt a known value
      const testKey = '_encrypted_walletSessionToken';
      const result = await new Promise((resolve) => {
        chrome.storage.local.get([testKey], (data) => resolve(data));
      });

      if (result[testKey]) {
        // Try decrypting to verify password
        await decryptData(result[testKey], password);
      }

      // Password is correct
      this.password = password;
      this.isLocked = false;
      this._resetAutoLockTimer();
      return true;
    } catch (error) {
      console.error('Unlock failed:', error);
      return false;
    }
  }

  /**
   * Locks storage and clears password from memory.
   */
  lock() {
    this.password = null;
    this.isLocked = true;
    if (this.autoLockTimer) {
      clearTimeout(this.autoLockTimer);
      this.autoLockTimer = null;
    }
  }

  /**
   * Resets auto-lock timer.
   *
   * @private
   */
  _resetAutoLockTimer() {
    if (this.autoLockTimer) {
      clearTimeout(this.autoLockTimer);
    }

    this.autoLockTimer = setTimeout(() => {
      this.lock();
      console.log('Auto-locked due to inactivity');
    }, AUTO_LOCK_TIMEOUT);
  }

  /**
   * Checks if storage is locked.
   *
   * @returns {boolean} True if locked
   */
  isStorageLocked() {
    return this.isLocked;
  }

  /**
   * Stores encrypted value.
   *
   * @param {string} key - Storage key
   * @param {any} value - Value to store
   * @returns {Promise<void>}
   * @throws {Error} If storage is locked
   */
  async set(key, value) {
    if (!this.encryptionEnabled) {
      // Encryption not enabled, store plaintext (backward compatibility)
      return new Promise((resolve) => {
        chrome.storage.local.set({ [key]: value }, () => resolve());
      });
    }

    if (this.isLocked) {
      throw new Error('Storage is locked. Unlock first.');
    }

    // Encrypt and store
    const encrypted = await encryptData(value, this.password);
    await chrome.storage.local.set({ [`_encrypted_${key}`]: encrypted });

    // Reset auto-lock timer on activity
    this._resetAutoLockTimer();
  }

  /**
   * Retrieves and decrypts value.
   *
   * @param {string} key - Storage key
   * @returns {Promise<any>} Decrypted value or null
   * @throws {Error} If storage is locked
   */
  async get(key) {
    if (!this.encryptionEnabled) {
      // Encryption not enabled, retrieve plaintext
      return new Promise((resolve) => {
        chrome.storage.local.get([key], (result) => {
          resolve(result[key] || null);
        });
      });
    }

    if (this.isLocked) {
      throw new Error('Storage is locked. Unlock first.');
    }

    // Retrieve and decrypt
    const encryptedKey = `_encrypted_${key}`;
    const result = await new Promise((resolve) => {
      chrome.storage.local.get([encryptedKey], (data) => resolve(data));
    });

    if (!result[encryptedKey]) {
      return null;
    }

    try {
      const decrypted = await decryptData(
        result[encryptedKey],
        this.password
      );

      // Reset auto-lock timer on activity
      this._resetAutoLockTimer();

      return decrypted;
    } catch (error) {
      console.error(`Failed to decrypt ${key}:`, error);
      return null;
    }
  }

  /**
   * Removes encrypted value.
   *
   * @param {string} key - Storage key
   * @returns {Promise<void>}
   */
  async remove(key) {
    if (!this.encryptionEnabled) {
      // Remove plaintext
      return new Promise((resolve) => {
        chrome.storage.local.remove([key], () => resolve());
      });
    }

    // Remove encrypted value
    const encryptedKey = `_encrypted_${key}`;
    return new Promise((resolve) => {
      chrome.storage.local.remove([encryptedKey], () => resolve());
    });
  }

  /**
   * Changes encryption password.
   *
   * @param {string} oldPassword - Current password
   * @param {string} newPassword - New password
   * @returns {Promise<boolean>} True if password changed successfully
   */
  async changePassword(oldPassword, newPassword) {
    if (!this.encryptionEnabled) {
      throw new Error('Encryption not enabled');
    }

    if (newPassword.length < 8) {
      throw new Error('New password must be at least 8 characters');
    }

    try {
      // Verify old password
      const unlocked = await this.unlock(oldPassword);
      if (!unlocked) {
        return false;
      }

      // Re-encrypt all data with new password
      const allKeys = [
        'walletSessionToken',
        'walletSessionSecret',
        'walletSessionAddress',
        'personalAiApiKey',
        'walletAddress',
        'apiHost'
      ];

      const reencryptedData = {};
      for (const key of allKeys) {
        const encryptedKey = `_encrypted_${key}`;
        const result = await new Promise((resolve) => {
          chrome.storage.local.get([encryptedKey], (data) => resolve(data));
        });

        if (result[encryptedKey]) {
          try {
            // Decrypt with old password
            const decrypted = await decryptData(
              result[encryptedKey],
              oldPassword
            );

            // Re-encrypt with new password
            const reencrypted = await encryptData(decrypted, newPassword);
            reencryptedData[encryptedKey] = reencrypted;
          } catch (error) {
            console.error(`Failed to re-encrypt ${key}:`, error);
            throw error;
          }
        }
      }

      // Store re-encrypted data
      await chrome.storage.local.set(reencryptedData);

      // Update password in memory
      this.password = newPassword;

      return true;
    } catch (error) {
      console.error('Password change failed:', error);
      return false;
    }
  }

  /**
   * Disables encryption and decrypts all data to plaintext.
   * WARNING: This is a security downgrade and should only be used
   * for testing or recovery purposes.
   *
   * @param {string} password - Current password
   * @returns {Promise<boolean>} True if successful
   */
  async disableEncryption(password) {
    if (!this.encryptionEnabled) {
      return true;
    }

    try {
      // Verify password
      const unlocked = await this.unlock(password);
      if (!unlocked) {
        return false;
      }

      // Decrypt all data to plaintext
      const allKeys = [
        'walletSessionToken',
        'walletSessionSecret',
        'walletSessionAddress',
        'personalAiApiKey',
        'walletAddress',
        'apiHost'
      ];

      const plaintextData = {};
      const encryptedKeys = [];

      for (const key of allKeys) {
        const encryptedKey = `_encrypted_${key}`;
        encryptedKeys.push(encryptedKey);

        const result = await new Promise((resolve) => {
          chrome.storage.local.get([encryptedKey], (data) => resolve(data));
        });

        if (result[encryptedKey]) {
          try {
            const decrypted = await decryptData(
              result[encryptedKey],
              password
            );
            plaintextData[key] = decrypted;
          } catch (error) {
            console.error(`Failed to decrypt ${key}:`, error);
          }
        }
      }

      // Store plaintext data
      await chrome.storage.local.set(plaintextData);

      // Remove encrypted versions
      await chrome.storage.local.remove(encryptedKeys);

      // Disable encryption flag
      await chrome.storage.local.remove(['_encryptionEnabled']);

      // Lock storage
      this.lock();
      this.encryptionEnabled = false;

      return true;
    } catch (error) {
      console.error('Failed to disable encryption:', error);
      return false;
    }
  }
}

// Export for use in popup.js
// eslint-disable-next-line no-unused-vars
const secureStorage = new SecureStorage();
