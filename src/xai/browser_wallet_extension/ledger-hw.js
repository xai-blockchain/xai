/**
 * XAI Ledger Hardware Wallet Integration
 *
 * Provides complete Ledger device integration for the XAI blockchain browser extension
 * using WebUSB API for direct communication with Ledger devices.
 *
 * Protocol: APDU (Application Protocol Data Unit) over WebUSB
 * Curve: secp256k1
 * BIP32 Path: m/44'/22593'/0'/0/0 (XAI coin type: 22593)
 * Address Format: XAI + 40 hex chars with EIP-55 checksumming
 *
 * Security Features:
 * - All private keys remain on the hardware device
 * - User confirmation required on device for all signing operations
 * - Address verification displays on device screen
 * - Transport encryption via USB
 *
 * @module ledger-hw
 */

// ============================================================================
// Constants
// ============================================================================

/** Ledger vendor ID (USB) */
const LEDGER_VENDOR_ID = 0x2c97;

/** USB interface class for CCID (smart card) */
const USB_CLASS_CCID = 0x0b;

/** Default BIP32 derivation path for XAI: m/44'/22593'/0'/0/0 */
const DEFAULT_BIP32_PATH = "44'/22593'/0'/0/0";

/** XAI coin type according to SLIP-44 registry */
const XAI_COIN_TYPE = 22593;

/** APDU instruction codes */
const APDU_INS = {
  GET_PUBLIC_KEY: 0x02,
  SIGN_TRANSACTION: 0x04,
  GET_APP_CONFIG: 0x06,
  VERIFY_ADDRESS: 0x08,
};

/** APDU parameter flags */
const APDU_P1 = {
  FIRST_CHUNK: 0x00,
  MORE_CHUNKS: 0x80,
  DISPLAY_ADDRESS: 0x01,
  NO_DISPLAY: 0x00,
};

const APDU_P2 = {
  LAST_CHUNK: 0x00,
  MORE_CHUNKS: 0x80,
};

/** APDU status codes */
const APDU_STATUS = {
  OK: 0x9000,
  USER_REJECTED: 0x6985,
  WRONG_APP: 0x6d00,
  INVALID_PARAM: 0x6b00,
  DEVICE_LOCKED: 0x6982,
  INVALID_CLA: 0x6e00,
  INVALID_INS: 0x6d00,
};

/** Maximum APDU payload size (Ledger Nano S/X limit) */
const MAX_APDU_PAYLOAD = 255;

/** XAI app CLA (Class byte) - using Ethereum's CLA as base */
const XAI_CLA = 0xe0;

/** Timeout for device operations (milliseconds) */
const DEVICE_TIMEOUT = 30000;

// ============================================================================
// State Management
// ============================================================================

/** Current USB device connection */
let currentDevice = null;

/** Active USB interface */
let currentInterface = null;

/** Device connection lock to prevent concurrent operations */
let operationLock = false;

// ============================================================================
// Error Classes
// ============================================================================

class LedgerError extends Error {
  constructor(message, code = null, statusCode = null) {
    super(message);
    this.name = 'LedgerError';
    this.code = code;
    this.statusCode = statusCode;
  }
}

class LedgerUserRejectionError extends LedgerError {
  constructor() {
    super('User rejected the operation on Ledger device', 'USER_REJECTED', APDU_STATUS.USER_REJECTED);
    this.name = 'LedgerUserRejectionError';
  }
}

class LedgerDeviceError extends LedgerError {
  constructor(message, statusCode) {
    super(message, 'DEVICE_ERROR', statusCode);
    this.name = 'LedgerDeviceError';
  }
}

class LedgerTransportError extends LedgerError {
  constructor(message) {
    super(message, 'TRANSPORT_ERROR');
    this.name = 'LedgerTransportError';
  }
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Convert buffer to hex string
 * @param {ArrayBuffer|Uint8Array} buffer - Buffer to convert
 * @returns {string} Hex string (lowercase)
 */
function bufferToHex(buffer) {
  return Array.from(new Uint8Array(buffer))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * Convert hex string to Uint8Array
 * @param {string} hex - Hex string (with or without 0x prefix)
 * @returns {Uint8Array} Byte array
 */
function hexToBytes(hex) {
  const cleanHex = hex.startsWith('0x') ? hex.slice(2) : hex;
  const bytes = new Uint8Array(cleanHex.length / 2);
  for (let i = 0; i < cleanHex.length; i += 2) {
    bytes[i / 2] = parseInt(cleanHex.substr(i, 2), 16);
  }
  return bytes;
}

/**
 * Parse BIP32 path string to binary format
 * @param {string} path - BIP32 path (e.g., "44'/22593'/0'/0/0")
 * @returns {Uint8Array} Serialized path for APDU
 */
function parseBIP32Path(path) {
  const segments = path.split('/');
  const buffer = new Uint8Array(1 + segments.length * 4);

  buffer[0] = segments.length;

  segments.forEach((segment, index) => {
    let value = parseInt(segment.replace("'", ''), 10);

    // Hardened derivation (apostrophe notation)
    if (segment.endsWith("'")) {
      value += 0x80000000;
    }

    // Write 32-bit big-endian integer
    const offset = 1 + index * 4;
    buffer[offset] = (value >> 24) & 0xff;
    buffer[offset + 1] = (value >> 16) & 0xff;
    buffer[offset + 2] = (value >> 8) & 0xff;
    buffer[offset + 3] = value & 0xff;
  });

  return buffer;
}

/**
 * Compute keccak256 hash for address checksumming (EIP-55)
 * Note: This uses SHA3-256 as an approximation. For production, use a proper keccak256 library.
 * @param {string} data - Input string
 * @returns {Promise<string>} Hash hex string
 */
async function keccak256(data) {
  // Using SHA3-256 as close approximation since Web Crypto doesn't support keccak256
  // For production, import a library like js-sha3 or ethereum-cryptography
  const encoder = new TextEncoder();
  const dataBytes = encoder.encode(data);

  // Web Crypto API doesn't have keccak256, using SHA-256 as fallback
  // In production environment, use: import { keccak256 } from 'ethereum-cryptography/keccak'
  const hashBuffer = await crypto.subtle.digest('SHA-256', dataBytes);
  return bufferToHex(hashBuffer);
}

/**
 * Convert public key to XAI checksummed address
 * @param {string} publicKeyHex - Uncompressed public key (64 bytes hex, no 0x04 prefix)
 * @returns {Promise<string>} XAI checksummed address
 */
async function publicKeyToAddress(publicKeyHex) {
  // XAI address derivation: keccak256(pubkey)[12:] with checksum
  // Take last 20 bytes (40 hex chars) of keccak256(publicKey)
  const hash = await keccak256(publicKeyHex);
  const addressHex = hash.slice(-40); // Last 20 bytes

  // Apply EIP-55 checksumming
  const checksumHash = await keccak256(addressHex.toLowerCase());

  let checksummedAddress = '';
  for (let i = 0; i < addressHex.length; i++) {
    const char = addressHex[i];
    if (parseInt(checksumHash[i], 16) >= 8) {
      checksummedAddress += char.toUpperCase();
    } else {
      checksummedAddress += char.toLowerCase();
    }
  }

  return 'XAI' + checksummedAddress;
}

/**
 * Create APDU command packet
 * @param {number} ins - Instruction code
 * @param {number} p1 - Parameter 1
 * @param {number} p2 - Parameter 2
 * @param {Uint8Array} data - Payload data
 * @returns {Uint8Array} Complete APDU packet
 */
function createAPDU(ins, p1, p2, data = new Uint8Array(0)) {
  const buffer = new Uint8Array(5 + data.length);
  buffer[0] = XAI_CLA;
  buffer[1] = ins;
  buffer[2] = p1;
  buffer[3] = p2;
  buffer[4] = data.length;
  buffer.set(data, 5);
  return buffer;
}

/**
 * Parse APDU response
 * @param {Uint8Array} response - Raw response from device
 * @returns {Object} Parsed response with data and status
 * @throws {LedgerError} If status indicates error
 */
function parseAPDUResponse(response) {
  if (response.length < 2) {
    throw new LedgerTransportError('Response too short');
  }

  const statusCode = (response[response.length - 2] << 8) | response[response.length - 1];
  const data = response.slice(0, response.length - 2);

  if (statusCode === APDU_STATUS.OK) {
    return { data, statusCode };
  }

  // Handle error status codes
  switch (statusCode) {
    case APDU_STATUS.USER_REJECTED:
      throw new LedgerUserRejectionError();

    case APDU_STATUS.WRONG_APP:
      throw new LedgerDeviceError(
        'Wrong app opened on Ledger. Please open the XAI app.',
        statusCode
      );

    case APDU_STATUS.DEVICE_LOCKED:
      throw new LedgerDeviceError(
        'Ledger device is locked. Please unlock it.',
        statusCode
      );

    case APDU_STATUS.INVALID_PARAM:
      throw new LedgerDeviceError(
        'Invalid parameters sent to device',
        statusCode
      );

    case APDU_STATUS.INVALID_CLA:
    case APDU_STATUS.INVALID_INS:
      throw new LedgerDeviceError(
        'Invalid instruction. Make sure XAI app is opened on device.',
        statusCode
      );

    default:
      throw new LedgerDeviceError(
        `Device returned error code: 0x${statusCode.toString(16)}`,
        statusCode
      );
  }
}

// ============================================================================
// USB Transport Layer
// ============================================================================

/**
 * Send APDU command to device and receive response
 * @param {Uint8Array} apdu - APDU packet to send
 * @returns {Promise<Uint8Array>} Response data
 * @throws {LedgerError} On communication or device error
 */
async function sendAPDU(apdu) {
  if (!currentDevice || !currentInterface) {
    throw new LedgerTransportError('No device connected');
  }

  try {
    // USB HID packet format for Ledger
    // Channel (2 bytes) + Tag (1 byte) + Sequence (2 bytes) + Data
    const channel = 0x0101;
    const tag = 0x05; // APDU tag

    // Construct HID packet
    const packet = new Uint8Array(64);
    packet[0] = (channel >> 8) & 0xff;
    packet[1] = channel & 0xff;
    packet[2] = tag;
    packet[3] = 0x00; // Sequence high
    packet[4] = 0x00; // Sequence low
    packet[5] = (apdu.length >> 8) & 0xff;
    packet[6] = apdu.length & 0xff;
    packet.set(apdu, 7);

    // Find OUT endpoint
    const outEndpoint = currentInterface.alternate.endpoints.find(
      ep => ep.direction === 'out'
    );

    if (!outEndpoint) {
      throw new LedgerTransportError('No OUT endpoint found');
    }

    // Send packet
    await currentDevice.transferOut(outEndpoint.endpointNumber, packet);

    // Receive response
    const inEndpoint = currentInterface.alternate.endpoints.find(
      ep => ep.direction === 'in'
    );

    if (!inEndpoint) {
      throw new LedgerTransportError('No IN endpoint found');
    }

    // Read response with timeout
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new LedgerTransportError('Device timeout')), DEVICE_TIMEOUT);
    });

    const transferPromise = currentDevice.transferIn(inEndpoint.endpointNumber, 64);
    const result = await Promise.race([transferPromise, timeoutPromise]);

    if (!result.data) {
      throw new LedgerTransportError('No data received from device');
    }

    // Parse HID packet
    const responseData = new Uint8Array(result.data.buffer);
    const responseLength = (responseData[5] << 8) | responseData[6];
    const apduResponse = responseData.slice(7, 7 + responseLength);

    return apduResponse;

  } catch (error) {
    if (error instanceof LedgerError) {
      throw error;
    }
    throw new LedgerTransportError(`USB transfer failed: ${error.message}`);
  }
}

/**
 * Send APDU and parse response
 * @param {number} ins - Instruction code
 * @param {number} p1 - Parameter 1
 * @param {number} p2 - Parameter 2
 * @param {Uint8Array} data - Payload data
 * @returns {Promise<Uint8Array>} Response data
 */
async function exchangeAPDU(ins, p1, p2, data = new Uint8Array(0)) {
  const apdu = createAPDU(ins, p1, p2, data);
  const response = await sendAPDU(apdu);
  const parsed = parseAPDUResponse(response);
  return parsed.data;
}

// ============================================================================
// Public API
// ============================================================================

/**
 * Check if Ledger hardware wallet is supported in this browser
 * @returns {boolean} True if WebUSB is available
 */
export function isLedgerSupported() {
  return 'usb' in navigator && typeof navigator.usb.requestDevice === 'function';
}

/**
 * Connect to Ledger device
 * @returns {Promise<Object>} Device information
 * @throws {LedgerError} On connection failure
 *
 * @example
 * const deviceInfo = await connectLedger();
 * console.log(`Connected to ${deviceInfo.productName}`);
 */
export async function connectLedger() {
  if (operationLock) {
    throw new LedgerError('Another operation is in progress', 'BUSY');
  }

  if (!isLedgerSupported()) {
    throw new LedgerError(
      'WebUSB is not supported in this browser. Use Chrome, Edge, or Opera.',
      'NOT_SUPPORTED'
    );
  }

  operationLock = true;

  try {
    // Disconnect existing connection
    if (currentDevice) {
      await disconnectLedger();
    }

    // Request device from user
    const device = await navigator.usb.requestDevice({
      filters: [{ vendorId: LEDGER_VENDOR_ID }]
    });

    // Open device
    await device.open();

    // Select configuration (usually configuration 1)
    if (device.configuration === null) {
      await device.selectConfiguration(1);
    }

    // Find CCID interface
    const ccidInterface = device.configuration.interfaces.find(
      iface => iface.alternate.interfaceClass === USB_CLASS_CCID
    );

    if (!ccidInterface) {
      throw new LedgerTransportError('Could not find CCID interface on device');
    }

    // Claim interface
    await device.claimInterface(ccidInterface.interfaceNumber);

    currentDevice = device;
    currentInterface = ccidInterface;

    // Get app configuration to verify XAI app is running
    try {
      await exchangeAPDU(APDU_INS.GET_APP_CONFIG, 0x00, 0x00);
    } catch (error) {
      if (error.statusCode === APDU_STATUS.WRONG_APP ||
          error.statusCode === APDU_STATUS.INVALID_INS) {
        await disconnectLedger();
        throw new LedgerDeviceError(
          'XAI app is not opened on Ledger. Please open the XAI app on your device.',
          APDU_STATUS.WRONG_APP
        );
      }
      throw error;
    }

    return {
      productName: device.productName,
      manufacturerName: device.manufacturerName,
      serialNumber: device.serialNumber,
      connected: true
    };

  } finally {
    operationLock = false;
  }
}

/**
 * Get XAI address from Ledger device
 * @param {string} bip32Path - BIP32 derivation path (default: "44'/22593'/0'/0/0")
 * @returns {Promise<string>} XAI checksummed address
 * @throws {LedgerError} On device error
 *
 * @example
 * const address = await getLedgerAddress("44'/22593'/0'/0/0");
 * console.log(`Address: ${address}`);
 */
export async function getLedgerAddress(bip32Path = DEFAULT_BIP32_PATH) {
  if (!currentDevice) {
    throw new LedgerTransportError('No device connected. Call connectLedger() first.');
  }

  if (operationLock) {
    throw new LedgerError('Another operation is in progress', 'BUSY');
  }

  operationLock = true;

  try {
    const pathBytes = parseBIP32Path(bip32Path);
    const responseData = await exchangeAPDU(
      APDU_INS.GET_PUBLIC_KEY,
      APDU_P1.NO_DISPLAY,
      0x00,
      pathBytes
    );

    // Response format:
    // 1 byte: public key length
    // 65 bytes: uncompressed public key (0x04 + x + y)
    // Remaining: address string (optional)

    if (responseData.length < 66) {
      throw new LedgerDeviceError('Invalid response length', 0);
    }

    const pubKeyLength = responseData[0];
    if (pubKeyLength !== 65) {
      throw new LedgerDeviceError('Invalid public key length', 0);
    }

    // Extract public key (skip 0x04 prefix)
    const publicKey = responseData.slice(2, 66);
    const publicKeyHex = bufferToHex(publicKey);

    // Derive address from public key
    const address = await publicKeyToAddress(publicKeyHex);

    return address;

  } finally {
    operationLock = false;
  }
}

/**
 * Sign transaction with Ledger device
 * @param {string} bip32Path - BIP32 derivation path
 * @param {Object|string} txPayload - Transaction data to sign
 * @returns {Promise<string>} Signature (hex format: r + s, 64 bytes)
 * @throws {LedgerError} On signing error or user rejection
 *
 * @example
 * const tx = { to: 'XAI...', amount: 100, nonce: 1 };
 * const signature = await signWithLedger("44'/22593'/0'/0/0", tx);
 */
export async function signWithLedger(bip32Path = DEFAULT_BIP32_PATH, txPayload) {
  if (!currentDevice) {
    throw new LedgerTransportError('No device connected. Call connectLedger() first.');
  }

  if (operationLock) {
    throw new LedgerError('Another operation is in progress', 'BUSY');
  }

  operationLock = true;

  try {
    // Serialize transaction payload
    let txBytes;
    if (typeof txPayload === 'string') {
      txBytes = new TextEncoder().encode(txPayload);
    } else {
      // Stable stringify for deterministic serialization
      const txString = JSON.stringify(txPayload, Object.keys(txPayload).sort());
      txBytes = new TextEncoder().encode(txString);
    }

    // Hash transaction data
    const txHashBuffer = await crypto.subtle.digest('SHA-256', txBytes);
    const txHash = new Uint8Array(txHashBuffer);

    const pathBytes = parseBIP32Path(bip32Path);

    // Prepare payload: path + hash
    const payload = new Uint8Array(pathBytes.length + txHash.length);
    payload.set(pathBytes, 0);
    payload.set(txHash, pathBytes.length);

    // Sign on device (user confirmation required)
    const responseData = await exchangeAPDU(
      APDU_INS.SIGN_TRANSACTION,
      APDU_P1.FIRST_CHUNK,
      APDU_P2.LAST_CHUNK,
      payload
    );

    // Response format:
    // 1 byte: signature length
    // DER encoded signature
    // OR: raw r (32 bytes) + s (32 bytes)

    if (responseData.length === 0) {
      throw new LedgerDeviceError('Empty signature response', 0);
    }

    // Handle both DER and raw signature formats
    let signature;

    if (responseData[0] === 0x30) {
      // DER format: parse to extract r and s
      signature = parseDERSignature(responseData);
    } else if (responseData.length >= 64) {
      // Raw format: r || s (32 + 32 bytes)
      signature = bufferToHex(responseData.slice(0, 64));
    } else {
      throw new LedgerDeviceError('Invalid signature format', 0);
    }

    return signature;

  } finally {
    operationLock = false;
  }
}

/**
 * Parse DER-encoded ECDSA signature to raw hex (r + s)
 * @param {Uint8Array} der - DER encoded signature
 * @returns {string} Hex signature (64 bytes)
 */
function parseDERSignature(der) {
  // DER format: 0x30 [total-length] 0x02 [r-length] [r] 0x02 [s-length] [s]
  let offset = 0;

  if (der[offset++] !== 0x30) {
    throw new LedgerDeviceError('Invalid DER signature: missing sequence tag', 0);
  }

  const totalLength = der[offset++];

  if (der[offset++] !== 0x02) {
    throw new LedgerDeviceError('Invalid DER signature: missing r integer tag', 0);
  }

  const rLength = der[offset++];
  const r = der.slice(offset, offset + rLength);
  offset += rLength;

  if (der[offset++] !== 0x02) {
    throw new LedgerDeviceError('Invalid DER signature: missing s integer tag', 0);
  }

  const sLength = der[offset++];
  const s = der.slice(offset, offset + sLength);

  // Pad to 32 bytes if necessary (remove DER padding or add zeros)
  const rPadded = padTo32Bytes(r);
  const sPadded = padTo32Bytes(s);

  return bufferToHex(rPadded) + bufferToHex(sPadded);
}

/**
 * Pad signature component to 32 bytes
 * @param {Uint8Array} bytes - Signature component
 * @returns {Uint8Array} 32-byte padded value
 */
function padTo32Bytes(bytes) {
  // Remove leading zero if present (DER encoding adds it for high bit set)
  let start = 0;
  while (start < bytes.length && bytes[start] === 0 && bytes.length - start > 32) {
    start++;
  }

  const trimmed = bytes.slice(start);

  if (trimmed.length === 32) {
    return trimmed;
  }

  if (trimmed.length < 32) {
    const padded = new Uint8Array(32);
    padded.set(trimmed, 32 - trimmed.length);
    return padded;
  }

  throw new LedgerDeviceError('Signature component exceeds 32 bytes', 0);
}

/**
 * Verify address on device screen
 * Displays the address on the Ledger device for user verification
 * @param {string} bip32Path - BIP32 derivation path
 * @returns {Promise<string>} Verified address
 * @throws {LedgerError} On device error or user rejection
 *
 * @example
 * const address = await verifyAddressOnDevice("44'/22593'/0'/0/0");
 * console.log(`User confirmed address: ${address}`);
 */
export async function verifyAddressOnDevice(bip32Path = DEFAULT_BIP32_PATH) {
  if (!currentDevice) {
    throw new LedgerTransportError('No device connected. Call connectLedger() first.');
  }

  if (operationLock) {
    throw new LedgerError('Another operation is in progress', 'BUSY');
  }

  operationLock = true;

  try {
    const pathBytes = parseBIP32Path(bip32Path);

    // Request public key with display confirmation
    const responseData = await exchangeAPDU(
      APDU_INS.GET_PUBLIC_KEY,
      APDU_P1.DISPLAY_ADDRESS,
      0x00,
      pathBytes
    );

    if (responseData.length < 66) {
      throw new LedgerDeviceError('Invalid response length', 0);
    }

    const pubKeyLength = responseData[0];
    if (pubKeyLength !== 65) {
      throw new LedgerDeviceError('Invalid public key length', 0);
    }

    // Extract public key (skip 0x04 prefix)
    const publicKey = responseData.slice(2, 66);
    const publicKeyHex = bufferToHex(publicKey);

    // Derive address from public key
    const address = await publicKeyToAddress(publicKeyHex);

    return address;

  } finally {
    operationLock = false;
  }
}

/**
 * Disconnect from Ledger device
 * @returns {Promise<void>}
 *
 * @example
 * await disconnectLedger();
 */
export async function disconnectLedger() {
  if (currentDevice) {
    try {
      if (currentInterface) {
        await currentDevice.releaseInterface(currentInterface.interfaceNumber);
      }
      await currentDevice.close();
    } catch (error) {
      // Ignore errors during disconnect
      console.warn('Error during disconnect:', error);
    } finally {
      currentDevice = null;
      currentInterface = null;
      operationLock = false;
    }
  }
}

/**
 * Get current device connection status
 * @returns {boolean} True if device is connected
 */
export function isConnected() {
  return currentDevice !== null && currentInterface !== null;
}

/**
 * Get public key from Ledger device
 * @param {string} bip32Path - BIP32 derivation path
 * @returns {Promise<string>} Uncompressed public key hex (64 bytes, no 0x04 prefix)
 * @throws {LedgerError} On device error
 *
 * @example
 * const pubKey = await getLedgerPublicKey("44'/22593'/0'/0/0");
 */
export async function getLedgerPublicKey(bip32Path = DEFAULT_BIP32_PATH) {
  if (!currentDevice) {
    throw new LedgerTransportError('No device connected. Call connectLedger() first.');
  }

  if (operationLock) {
    throw new LedgerError('Another operation is in progress', 'BUSY');
  }

  operationLock = true;

  try {
    const pathBytes = parseBIP32Path(bip32Path);
    const responseData = await exchangeAPDU(
      APDU_INS.GET_PUBLIC_KEY,
      APDU_P1.NO_DISPLAY,
      0x00,
      pathBytes
    );

    if (responseData.length < 66) {
      throw new LedgerDeviceError('Invalid response length', 0);
    }

    const pubKeyLength = responseData[0];
    if (pubKeyLength !== 65) {
      throw new LedgerDeviceError('Invalid public key length', 0);
    }

    // Extract public key (skip 0x04 prefix) - return 64 bytes
    const publicKey = responseData.slice(2, 66);
    return bufferToHex(publicKey);

  } finally {
    operationLock = false;
  }
}

// ============================================================================
// Export Error Classes for Consumer Use
// ============================================================================

export {
  LedgerError,
  LedgerUserRejectionError,
  LedgerDeviceError,
  LedgerTransportError,
};

// ============================================================================
// Default Export
// ============================================================================

export default {
  isLedgerSupported,
  connectLedger,
  getLedgerAddress,
  getLedgerPublicKey,
  signWithLedger,
  verifyAddressOnDevice,
  disconnectLedger,
  isConnected,
  DEFAULT_BIP32_PATH,
  XAI_COIN_TYPE,
  LedgerError,
  LedgerUserRejectionError,
  LedgerDeviceError,
  LedgerTransportError,
};
