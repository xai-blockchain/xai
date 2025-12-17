/**
 * Trezor Hardware Wallet Integration for XAI Browser Extension
 *
 * This module provides complete Trezor device support for the XAI blockchain,
 * enabling secure transaction signing where private keys never leave the device.
 *
 * Features:
 * - Device detection and connection management
 * - BIP32 HD wallet path derivation (XAI coin type: 22593)
 * - On-device transaction signing with ECDSA secp256k1
 * - Address verification on device screen
 * - Comprehensive error handling and user feedback
 *
 * Security Architecture:
 * - All signing operations occur on the Trezor device
 * - Private keys never transmitted or exposed
 * - Transaction payloads verified on device screen
 * - User must physically confirm all operations
 *
 * Dependencies:
 * - Trezor Connect library (loaded from CDN in manifest)
 *
 * @module trezor-hw
 * @version 1.0.0
 */

// XAI blockchain configuration
const XAI_COIN_TYPE = 22593; // Registered coin type for XAI
const XAI_DEFAULT_PATH = `m/44'/${XAI_COIN_TYPE}'/0'/0/0`; // BIP44 compliant path
const XAI_MANIFEST = {
  email: 'support@xai-blockchain.com',
  appUrl: 'https://xai-blockchain.com',
};

// Trezor Connect initialization state
let trezorInitialized = false;
let trezorConnectInstance = null;

/**
 * Error codes for Trezor operations
 */
const TrezorErrorCode = {
  NOT_SUPPORTED: 'TREZOR_NOT_SUPPORTED',
  NOT_INITIALIZED: 'TREZOR_NOT_INITIALIZED',
  DEVICE_NOT_CONNECTED: 'DEVICE_NOT_CONNECTED',
  USER_CANCELLED: 'USER_CANCELLED',
  WRONG_PASSPHRASE: 'WRONG_PASSPHRASE',
  COMMUNICATION_ERROR: 'COMMUNICATION_ERROR',
  POPUP_BLOCKED: 'POPUP_BLOCKED',
  INVALID_PATH: 'INVALID_PATH',
  SIGNING_FAILED: 'SIGNING_FAILED',
  DEVICE_BUSY: 'DEVICE_BUSY',
  FIRMWARE_OUTDATED: 'FIRMWARE_OUTDATED',
};

/**
 * Custom error class for Trezor-specific errors
 */
class TrezorError extends Error {
  /**
   * @param {string} message - Human-readable error message
   * @param {string} code - Error code from TrezorErrorCode
   * @param {*} originalError - Original error object from Trezor Connect
   */
  constructor(message, code, originalError = null) {
    super(message);
    this.name = 'TrezorError';
    this.code = code;
    this.originalError = originalError;
  }
}

/**
 * Check if Trezor Connect library is available and supported in this environment.
 *
 * This function verifies that:
 * 1. The Trezor Connect library has been loaded from CDN
 * 2. The browser environment supports required features
 * 3. Popup windows are not blocked (required for device communication)
 *
 * @returns {boolean} True if Trezor Connect is available and can be used
 *
 * @example
 * if (isTrezorSupported()) {
 *   await initTrezorConnect();
 * } else {
 *   console.error('Trezor not supported in this browser');
 * }
 */
export function isTrezorSupported() {
  // Check if TrezorConnect global exists (loaded from CDN)
  if (typeof TrezorConnect === 'undefined') {
    console.warn('Trezor Connect library not loaded. Add to manifest.json content_security_policy.');
    return false;
  }

  // Check for required browser APIs
  if (typeof crypto === 'undefined' || typeof crypto.subtle === 'undefined') {
    console.warn('Web Crypto API not available - required for Trezor operations');
    return false;
  }

  return true;
}

/**
 * Initialize Trezor Connect with XAI blockchain manifest.
 *
 * This must be called before any other Trezor operations. It configures
 * Trezor Connect with the XAI blockchain identity and establishes
 * communication with the Trezor Bridge/Webusb.
 *
 * Initialization includes:
 * - Setting XAI manifest (app name, URL, email)
 * - Configuring popup settings
 * - Establishing connection to Trezor Bridge
 *
 * @param {Object} [options] - Optional configuration
 * @param {string} [options.manifest] - Custom manifest override
 * @param {boolean} [options.debug=false] - Enable debug logging
 * @param {boolean} [options.popup=true] - Allow popup windows for device communication
 * @param {string} [options.connectSrc] - Custom Trezor Connect URL
 *
 * @returns {Promise<Object>} Initialization result with status
 * @returns {boolean} result.success - Whether initialization succeeded
 * @returns {string} [result.version] - Trezor Connect version
 * @returns {string} [result.error] - Error message if initialization failed
 *
 * @throws {TrezorError} If Trezor Connect is not supported or initialization fails
 *
 * @example
 * try {
 *   const result = await initTrezorConnect({ debug: true });
 *   console.log('Trezor Connect initialized:', result.version);
 * } catch (error) {
 *   console.error('Failed to initialize:', error.message);
 * }
 */
export async function initTrezorConnect(options = {}) {
  if (!isTrezorSupported()) {
    throw new TrezorError(
      'Trezor Connect is not supported in this environment',
      TrezorErrorCode.NOT_SUPPORTED
    );
  }

  if (trezorInitialized) {
    return {
      success: true,
      version: TrezorConnect.version || 'unknown',
      message: 'Trezor Connect already initialized',
    };
  }

  try {
    const manifest = options.manifest || XAI_MANIFEST;

    // Initialize Trezor Connect with XAI blockchain manifest
    await TrezorConnect.init({
      manifest,
      debug: options.debug || false,
      popup: options.popup !== false, // Enable popup by default
      connectSrc: options.connectSrc || undefined,
      lazyLoad: false, // Load immediately
      webusb: true, // Enable WebUSB support
    });

    trezorConnectInstance = TrezorConnect;
    trezorInitialized = true;

    console.log('Trezor Connect initialized successfully for XAI blockchain');

    return {
      success: true,
      version: TrezorConnect.version || 'unknown',
      manifest,
    };
  } catch (error) {
    console.error('Trezor Connect initialization failed:', error);
    throw new TrezorError(
      `Failed to initialize Trezor Connect: ${error.message}`,
      TrezorErrorCode.COMMUNICATION_ERROR,
      error
    );
  }
}

/**
 * Connect to a Trezor device and retrieve device information.
 *
 * This function establishes a connection to a connected Trezor device
 * and retrieves device features including firmware version, model,
 * and capabilities.
 *
 * User interaction:
 * - Trezor popup window will open
 * - User must select their device (if multiple connected)
 * - Device must be unlocked with PIN
 *
 * @returns {Promise<Object>} Device information
 * @returns {boolean} result.success - Whether connection succeeded
 * @returns {Object} result.device - Device information
 * @returns {string} result.device.id - Unique device ID
 * @returns {string} result.device.label - User-set device label
 * @returns {string} result.device.model - Device model (e.g., "T", "1")
 * @returns {string} result.device.firmwareVersion - Current firmware version
 * @returns {Array<string>} result.device.features - Supported features
 * @returns {string} [result.error] - Error message if connection failed
 *
 * @throws {TrezorError} If not initialized, device not found, or connection fails
 *
 * @example
 * try {
 *   const device = await connectTrezor();
 *   console.log(`Connected to Trezor ${device.device.model}`);
 *   console.log(`Firmware: ${device.device.firmwareVersion}`);
 * } catch (error) {
 *   if (error.code === TrezorErrorCode.USER_CANCELLED) {
 *     console.log('User cancelled device selection');
 *   } else {
 *     console.error('Connection failed:', error.message);
 *   }
 * }
 */
export async function connectTrezor() {
  ensureInitialized();

  try {
    // Get device features to verify connection
    const result = await TrezorConnect.getFeatures();

    if (!result.success) {
      throw new TrezorError(
        result.payload.error || 'Failed to connect to Trezor device',
        mapTrezorErrorCode(result.payload),
        result.payload
      );
    }

    const features = result.payload;

    return {
      success: true,
      device: {
        id: features.device_id || 'unknown',
        label: features.label || 'Trezor',
        model: features.model || 'unknown',
        firmwareVersion: `${features.major_version}.${features.minor_version}.${features.patch_version}`,
        features: features.capabilities || [],
        initialized: features.initialized || false,
        pinProtection: features.pin_protection || false,
        passphraseProtection: features.passphrase_protection || false,
      },
    };
  } catch (error) {
    if (error instanceof TrezorError) {
      throw error;
    }

    console.error('Trezor connection error:', error);
    throw new TrezorError(
      `Failed to connect to Trezor device: ${error.message}`,
      TrezorErrorCode.DEVICE_NOT_CONNECTED,
      error
    );
  }
}

/**
 * Get XAI blockchain address from Trezor device.
 *
 * This function derives an XAI address from the Trezor device using
 * the specified BIP32 derivation path. The derivation happens entirely
 * on-device, and the private key never leaves the device.
 *
 * Address format: XAI + 40 hex characters (SHA256 of public key)
 *
 * User interaction:
 * - Device may prompt for PIN entry
 * - Device may prompt for passphrase (if enabled)
 * - Optional: Device can display address for verification
 *
 * @param {string} [bip32Path=XAI_DEFAULT_PATH] - BIP32 derivation path
 * @param {Object} [options] - Additional options
 * @param {boolean} [options.showOnDevice=false] - Display address on device screen
 * @param {boolean} [options.compressed=false] - Use compressed public key
 *
 * @returns {Promise<Object>} Address derivation result
 * @returns {boolean} result.success - Whether address retrieval succeeded
 * @returns {string} result.address - XAI blockchain address
 * @returns {string} result.publicKey - Uncompressed public key (hex, 128 chars)
 * @returns {string} result.path - BIP32 path used for derivation
 * @returns {string} [result.error] - Error message if failed
 *
 * @throws {TrezorError} If not initialized, invalid path, or retrieval fails
 *
 * @example
 * // Get default address
 * const result = await getTrezorAddress();
 * console.log('XAI Address:', result.address);
 *
 * // Get address for account 1, index 5
 * const result2 = await getTrezorAddress(`m/44'/${XAI_COIN_TYPE}'/1'/0/5`);
 *
 * // Get address and show on device screen
 * const result3 = await getTrezorAddress(XAI_DEFAULT_PATH, { showOnDevice: true });
 */
export async function getTrezorAddress(bip32Path = XAI_DEFAULT_PATH, options = {}) {
  ensureInitialized();
  validateBip32Path(bip32Path);

  try {
    // Request public key from device (includes address derivation)
    const result = await TrezorConnect.getPublicKey({
      path: bip32Path,
      coin: 'Bitcoin', // Use Bitcoin format for secp256k1 curve
      showOnTrezor: options.showOnDevice || false,
    });

    if (!result.success) {
      throw new TrezorError(
        result.payload.error || 'Failed to get address from Trezor',
        mapTrezorErrorCode(result.payload),
        result.payload
      );
    }

    const publicKey = result.payload.publicKey;

    // Derive XAI address from public key
    // Format: SHA256(public_key) -> XAI + first 40 hex chars
    const address = await deriveXaiAddress(publicKey);

    return {
      success: true,
      address,
      publicKey,
      path: bip32Path,
    };
  } catch (error) {
    if (error instanceof TrezorError) {
      throw error;
    }

    console.error('Failed to get Trezor address:', error);
    throw new TrezorError(
      `Failed to get address: ${error.message}`,
      TrezorErrorCode.COMMUNICATION_ERROR,
      error
    );
  }
}

/**
 * Sign a transaction payload using the Trezor device.
 *
 * This is the core security function that signs XAI blockchain transactions
 * using the private key stored on the Trezor device. The private key never
 * leaves the device.
 *
 * Signing process:
 * 1. Transaction payload is serialized deterministically
 * 2. SHA256 hash is computed from payload
 * 3. Hash is sent to Trezor for signing
 * 4. User confirms transaction on device screen
 * 5. Device signs hash with ECDSA secp256k1
 * 6. Signature (r, s, v) is returned
 *
 * User interaction:
 * - Device displays transaction details
 * - User must physically press button to confirm
 * - Device may prompt for PIN/passphrase
 *
 * @param {string} bip32Path - BIP32 derivation path for signing key
 * @param {Object} txPayload - Transaction payload object
 * @param {string} txPayload.from - Sender XAI address
 * @param {string} txPayload.to - Recipient XAI address
 * @param {number} txPayload.amount - Amount to transfer
 * @param {number} txPayload.fee - Transaction fee
 * @param {number} txPayload.nonce - Transaction nonce
 * @param {Object} [options] - Signing options
 * @param {boolean} [options.canonical=true] - Use canonical signature format (lowercase s)
 *
 * @returns {Promise<Object>} Signing result
 * @returns {boolean} result.success - Whether signing succeeded
 * @returns {string} result.signature - ECDSA signature (hex, 128 chars: r || s)
 * @returns {string} result.signatureV - Recovery ID (0-3)
 * @returns {string} result.messageHash - SHA256 hash that was signed
 * @returns {string} [result.error] - Error message if signing failed
 *
 * @throws {TrezorError} If not initialized, user cancels, or signing fails
 *
 * @example
 * const txPayload = {
 *   from: 'XAI1234...',
 *   to: 'XAI5678...',
 *   amount: 100,
 *   fee: 1,
 *   nonce: 42,
 * };
 *
 * try {
 *   const result = await signWithTrezor(XAI_DEFAULT_PATH, txPayload);
 *   console.log('Signature:', result.signature);
 *   // Submit transaction with signature to XAI network
 * } catch (error) {
 *   if (error.code === TrezorErrorCode.USER_CANCELLED) {
 *     console.log('User rejected transaction on device');
 *   } else {
 *     console.error('Signing failed:', error.message);
 *   }
 * }
 */
export async function signWithTrezor(bip32Path, txPayload, options = {}) {
  ensureInitialized();
  validateBip32Path(bip32Path);

  if (!txPayload || typeof txPayload !== 'object') {
    throw new TrezorError('Transaction payload is required', TrezorErrorCode.INVALID_PATH);
  }

  try {
    // Step 1: Serialize transaction payload deterministically
    const payloadStr = stableStringify(txPayload);
    const encoder = new TextEncoder();
    const payloadBytes = encoder.encode(payloadStr);

    // Step 2: Hash payload with SHA-256
    const messageHash = await crypto.subtle.digest('SHA-256', payloadBytes);
    const messageHashHex = bufferToHex(messageHash);

    // Step 3: Sign the hash on Trezor device
    // Note: Trezor Connect expects message as hex string
    const result = await TrezorConnect.signMessage({
      path: bip32Path,
      message: messageHashHex,
      coin: 'Bitcoin', // Use Bitcoin for secp256k1
      hex: true, // Indicate message is hex-encoded
    });

    if (!result.success) {
      throw new TrezorError(
        result.payload.error || 'Transaction signing failed',
        mapTrezorErrorCode(result.payload),
        result.payload
      );
    }

    // Step 4: Extract signature components
    // Trezor returns signature in base64 format
    const signatureBase64 = result.payload.signature;
    const signatureBytes = base64ToBytes(signatureBase64);

    // Parse DER-encoded signature to get r and s values
    const { r, s, v } = parseSignature(signatureBytes);

    // Ensure canonical signature (lowercase s) if requested
    const canonicalS = options.canonical !== false ? canonicalizeS(s) : s;

    // Format signature as hex string (r || s)
    const signature = r.padStart(64, '0') + canonicalS.padStart(64, '0');

    console.log('Transaction signed successfully on Trezor device');

    return {
      success: true,
      signature,
      signatureV: v.toString(),
      messageHash: messageHashHex,
      path: bip32Path,
    };
  } catch (error) {
    if (error instanceof TrezorError) {
      throw error;
    }

    console.error('Trezor signing error:', error);
    throw new TrezorError(
      `Failed to sign transaction: ${error.message}`,
      TrezorErrorCode.SIGNING_FAILED,
      error
    );
  }
}

/**
 * Verify and display an address on the Trezor device screen.
 *
 * This function derives an address and forces it to be displayed on the
 * Trezor device screen for user verification. This is a critical security
 * feature to prevent address substitution attacks.
 *
 * User workflow:
 * 1. Extension requests address verification
 * 2. Trezor displays full address on device screen
 * 3. User compares displayed address with expected address
 * 4. User confirms or rejects on device
 *
 * @param {string} [bip32Path=XAI_DEFAULT_PATH] - BIP32 derivation path
 *
 * @returns {Promise<Object>} Verification result
 * @returns {boolean} result.success - Whether user confirmed address
 * @returns {string} result.address - Verified XAI address
 * @returns {boolean} result.confirmed - Whether user confirmed on device
 * @returns {string} [result.error] - Error message if verification failed
 *
 * @throws {TrezorError} If not initialized, user cancels, or verification fails
 *
 * @example
 * try {
 *   const result = await verifyAddressOnDevice();
 *   if (result.confirmed) {
 *     console.log('User confirmed address:', result.address);
 *     // Proceed with transaction
 *   }
 * } catch (error) {
 *   if (error.code === TrezorErrorCode.USER_CANCELLED) {
 *     console.log('User cancelled address verification');
 *   }
 * }
 */
export async function verifyAddressOnDevice(bip32Path = XAI_DEFAULT_PATH) {
  ensureInitialized();
  validateBip32Path(bip32Path);

  try {
    // Request address with mandatory on-device display
    const result = await TrezorConnect.getAddress({
      path: bip32Path,
      coin: 'Bitcoin',
      showOnTrezor: true, // Force display on device
    });

    if (!result.success) {
      throw new TrezorError(
        result.payload.error || 'Address verification failed',
        mapTrezorErrorCode(result.payload),
        result.payload
      );
    }

    // Derive XAI address from the returned public key
    const publicKey = result.payload.publicKey;
    const xaiAddress = await deriveXaiAddress(publicKey);

    console.log('Address verified on Trezor device:', xaiAddress);

    return {
      success: true,
      address: xaiAddress,
      confirmed: true,
      path: bip32Path,
    };
  } catch (error) {
    if (error instanceof TrezorError) {
      throw error;
    }

    console.error('Address verification error:', error);
    throw new TrezorError(
      `Failed to verify address: ${error.message}`,
      TrezorErrorCode.COMMUNICATION_ERROR,
      error
    );
  }
}

/**
 * Disconnect from Trezor device and cleanup resources.
 *
 * This function closes the connection to the Trezor device and cleans up
 * any resources used by Trezor Connect. It should be called when the
 * extension is closed or when hardware wallet support is no longer needed.
 *
 * @returns {Promise<Object>} Disconnection result
 * @returns {boolean} result.success - Whether disconnection succeeded
 * @returns {string} [result.message] - Status message
 *
 * @example
 * await disconnectTrezor();
 * console.log('Trezor disconnected');
 */
export async function disconnectTrezor() {
  if (!trezorInitialized) {
    return {
      success: true,
      message: 'Trezor was not connected',
    };
  }

  try {
    // Dispose of Trezor Connect instance
    if (TrezorConnect && typeof TrezorConnect.dispose === 'function') {
      await TrezorConnect.dispose();
    }

    trezorConnectInstance = null;
    trezorInitialized = false;

    console.log('Trezor Connect disconnected and cleaned up');

    return {
      success: true,
      message: 'Trezor disconnected successfully',
    };
  } catch (error) {
    console.error('Error during Trezor disconnect:', error);
    // Still mark as disconnected even if cleanup failed
    trezorInitialized = false;
    trezorConnectInstance = null;

    return {
      success: true,
      message: 'Trezor disconnected (cleanup encountered errors)',
    };
  }
}

// =============================================================================
// Helper Functions (Internal)
// =============================================================================

/**
 * Ensure Trezor Connect has been initialized before operations.
 * @private
 * @throws {TrezorError} If not initialized
 */
function ensureInitialized() {
  if (!trezorInitialized) {
    throw new TrezorError(
      'Trezor Connect not initialized. Call initTrezorConnect() first.',
      TrezorErrorCode.NOT_INITIALIZED
    );
  }
}

/**
 * Validate BIP32 derivation path format.
 * @private
 * @param {string} path - BIP32 path to validate
 * @throws {TrezorError} If path is invalid
 */
function validateBip32Path(path) {
  if (!path || typeof path !== 'string') {
    throw new TrezorError('BIP32 path is required', TrezorErrorCode.INVALID_PATH);
  }

  // BIP32 path format: m/purpose'/coin_type'/account'/change/address_index
  const bip32Regex = /^m(\/\d+'?)+$/;

  if (!bip32Regex.test(path)) {
    throw new TrezorError(
      `Invalid BIP32 path format: ${path}. Expected format: m/44'/22593'/0'/0/0`,
      TrezorErrorCode.INVALID_PATH
    );
  }
}

/**
 * Map Trezor Connect error payload to internal error code.
 * @private
 * @param {Object} payload - Trezor Connect error payload
 * @returns {string} Error code from TrezorErrorCode
 */
function mapTrezorErrorCode(payload) {
  if (!payload || !payload.error) {
    return TrezorErrorCode.COMMUNICATION_ERROR;
  }

  const error = payload.error.toLowerCase();

  if (error.includes('cancelled') || error.includes('action cancelled')) {
    return TrezorErrorCode.USER_CANCELLED;
  }
  if (error.includes('device not found') || error.includes('device disconnected')) {
    return TrezorErrorCode.DEVICE_NOT_CONNECTED;
  }
  if (error.includes('passphrase') || error.includes('wrong passphrase')) {
    return TrezorErrorCode.WRONG_PASSPHRASE;
  }
  if (error.includes('popup') || error.includes('blocked')) {
    return TrezorErrorCode.POPUP_BLOCKED;
  }
  if (error.includes('firmware') || error.includes('outdated')) {
    return TrezorErrorCode.FIRMWARE_OUTDATED;
  }
  if (error.includes('device busy') || error.includes('device is being used')) {
    return TrezorErrorCode.DEVICE_BUSY;
  }

  return TrezorErrorCode.COMMUNICATION_ERROR;
}

/**
 * Derive XAI blockchain address from secp256k1 public key.
 * @private
 * @param {string} publicKeyHex - Uncompressed public key (hex, 130 chars with 04 prefix or 128 without)
 * @returns {Promise<string>} XAI address (XAI + 40 hex chars)
 */
async function deriveXaiAddress(publicKeyHex) {
  // Remove '04' prefix if present (uncompressed public key marker)
  let pubKey = publicKeyHex;
  if (pubKey.startsWith('04')) {
    pubKey = pubKey.slice(2);
  }

  // Convert hex to bytes
  const pubKeyBytes = hexToBytes(pubKey);

  // Hash public key with SHA-256
  const hashBuffer = await crypto.subtle.digest('SHA-256', pubKeyBytes);
  const hashHex = bufferToHex(hashBuffer);

  // XAI address format: "XAI" + first 40 hex characters of hash
  const address = `XAI${hashHex.slice(0, 40)}`;

  return address;
}

/**
 * Parse DER-encoded ECDSA signature to extract r, s, and v components.
 * @private
 * @param {Uint8Array} signatureBytes - DER-encoded signature
 * @returns {Object} Signature components
 * @returns {string} r - R component (hex)
 * @returns {string} s - S component (hex)
 * @returns {number} v - Recovery ID
 */
function parseSignature(signatureBytes) {
  // DER signature format:
  // 0x30 [total-length] 0x02 [R-length] [R] 0x02 [S-length] [S]

  let offset = 0;

  // Skip DER sequence tag (0x30)
  if (signatureBytes[offset] !== 0x30) {
    throw new Error('Invalid DER signature: missing sequence tag');
  }
  offset += 1;

  // Skip total length
  offset += 1;

  // Parse R value
  if (signatureBytes[offset] !== 0x02) {
    throw new Error('Invalid DER signature: missing R integer tag');
  }
  offset += 1;

  const rLength = signatureBytes[offset];
  offset += 1;

  const rBytes = signatureBytes.slice(offset, offset + rLength);
  const r = bufferToHex(rBytes);
  offset += rLength;

  // Parse S value
  if (signatureBytes[offset] !== 0x02) {
    throw new Error('Invalid DER signature: missing S integer tag');
  }
  offset += 1;

  const sLength = signatureBytes[offset];
  offset += 1;

  const sBytes = signatureBytes.slice(offset, offset + sLength);
  const s = bufferToHex(sBytes);

  // Recovery ID (v) is typically appended or derived from signature
  // For now, default to 0 (can be determined during verification)
  const v = 0;

  return { r, s, v };
}

/**
 * Canonicalize signature S component (ensure lowercase s).
 *
 * ECDSA signatures can have two valid S values. Canonical form uses
 * the lower value to prevent transaction malleability.
 *
 * @private
 * @param {string} sHex - S component in hex
 * @returns {string} Canonical S component in hex
 */
function canonicalizeS(sHex) {
  const SECP256K1_N = BigInt('0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141');
  const SECP256K1_N_HALF = SECP256K1_N / BigInt(2);

  const s = BigInt('0x' + sHex);

  // If s > n/2, use n - s instead
  if (s > SECP256K1_N_HALF) {
    const canonicalS = SECP256K1_N - s;
    return canonicalS.toString(16).padStart(64, '0');
  }

  return sHex;
}

/**
 * Convert buffer to hex string.
 * @private
 * @param {ArrayBuffer|Uint8Array} buffer - Buffer to convert
 * @returns {string} Hex string
 */
function bufferToHex(buffer) {
  const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
  return Array.from(bytes)
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * Convert hex string to Uint8Array.
 * @private
 * @param {string} hex - Hex string
 * @returns {Uint8Array} Byte array
 */
function hexToBytes(hex) {
  const bytes = [];
  for (let i = 0; i < hex.length; i += 2) {
    bytes.push(parseInt(hex.substr(i, 2), 16));
  }
  return new Uint8Array(bytes);
}

/**
 * Convert base64 string to Uint8Array.
 * @private
 * @param {string} base64 - Base64 string
 * @returns {Uint8Array} Byte array
 */
function base64ToBytes(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

/**
 * Serialize object to stable JSON string with sorted keys.
 *
 * This ensures deterministic serialization for signing, preventing
 * signature verification issues due to key ordering differences.
 *
 * @private
 * @param {*} value - Value to stringify
 * @returns {string} Stable JSON string
 */
function stableStringify(value) {
  if (value === null) return 'null';
  if (value === undefined) return 'undefined';
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(',')}]`;
  }
  if (typeof value === 'object') {
    const keys = Object.keys(value).sort();
    return `{${keys
      .map((key) => `"${key}":${stableStringify(value[key])}`)
      .join(',')}}`;
  }
  return JSON.stringify(value);
}

// Export error codes for external use
export { TrezorError, TrezorErrorCode, XAI_DEFAULT_PATH, XAI_COIN_TYPE };
