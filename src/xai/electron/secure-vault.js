const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const argon2 = require('argon2');
const { utils, sign, getPublicKey, etc } = require('@noble/secp256k1');

const PBKDF2_ITERATIONS = 600000;
const ARGON2_TIME_COST = 3;
const ARGON2_MEMORY_COST = 65536; // 64 MB
const ARGON2_PARALLELISM = 4;
const KEY_SIZE = 32;
const MAX_KEYS = 8;
const MAX_KEYSTORE_SIZE_BYTES = 256 * 1024; // Defensive limit to avoid feeding huge files

function ensureSecpPrimitives() {
  if (!etc.hmacSha256Sync) {
    etc.hmacSha256Sync = (key, ...msgs) => {
      const h = crypto.createHmac('sha256', key);
      for (const msg of msgs) {
        h.update(msg);
      }
      return h.digest();
    };
  }
}

ensureSecpPrimitives();

function toHex(data) {
  return Buffer.from(data).toString('hex');
}

function fromHex(hex) {
  const normalized = hex.startsWith('0x') ? hex.slice(2) : hex;
  if (!/^[0-9a-fA-F]+$/.test(normalized)) {
    throw new Error('Hex value contains invalid characters');
  }
  return Buffer.from(normalized, 'hex');
}

function normalizeKeystorePath(keystorePath) {
  const resolved = path.resolve(keystorePath);
  const stats = fs.statSync(resolved, { throwIfNoEntry: true });
  if (!stats.isFile()) {
    throw new Error('Keystore path must point to a file');
  }
  if (stats.size > MAX_KEYSTORE_SIZE_BYTES) {
    throw new Error('Keystore file too large');
  }
  return resolved;
}

async function deriveKey(password, salt, kdf) {
  if (kdf === 'argon2id') {
    // Match wallet CLI defaults (argon2id with deterministic salt input)
    const hash = await argon2.hash(password, {
      type: argon2.argon2id,
      salt,
      timeCost: ARGON2_TIME_COST,
      memoryCost: ARGON2_MEMORY_COST,
      parallelism: ARGON2_PARALLELISM,
      hashLength: KEY_SIZE,
      raw: true
    });
    return Buffer.from(hash);
  }

  if (kdf && kdf !== 'pbkdf2') {
    throw new Error(`Unsupported keystore KDF: ${kdf}`);
  }

  return crypto.pbkdf2Sync(password, salt, PBKDF2_ITERATIONS, KEY_SIZE, 'sha256');
}

function verifyHmac(key, salt, nonce, ciphertext, expectedSignature) {
  const hmacKey = crypto.createHash('sha256').update(Buffer.concat([key, Buffer.from('hmac')])).digest();
  const signature = crypto.createHmac('sha256', hmacKey).update(Buffer.concat([salt, nonce, ciphertext])).digest();
  return crypto.timingSafeEqual(signature, expectedSignature);
}

function decryptAesGcm(key, nonce, ciphertext) {
  // Python cryptography AESGCM appends the 16-byte tag to the ciphertext
  const tag = ciphertext.slice(ciphertext.length - 16);
  const data = ciphertext.slice(0, ciphertext.length - 16);
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, nonce);
  decipher.setAuthTag(tag);
  const plaintext = Buffer.concat([decipher.update(data), decipher.final()]);
  return plaintext;
}

class SecureKeyVault {
  constructor() {
    this.keys = new Map();
  }

  listLoadedKeyIds() {
    return Array.from(this.keys.keys());
  }

  clear() {
    this.keys.clear();
  }

  async importKeystore(keystorePath, password) {
    if (!password || password.length < 8) {
      throw new Error('A keystore password is required');
    }

    if (this.keys.size >= MAX_KEYS) {
      throw new Error('Key vault capacity reached');
    }

    const resolved = normalizeKeystorePath(keystorePath);
    const raw = fs.readFileSync(resolved, { encoding: 'utf-8' });
    const keystore = JSON.parse(raw);

    if (keystore.version !== '2.0') {
      throw new Error('Unsupported keystore version');
    }
    if (keystore.algorithm !== 'AES-256-GCM') {
      throw new Error('Unsupported keystore cipher');
    }

    const encryptedData = Buffer.from(keystore.encrypted_data, 'base64');
    const salt = Buffer.from(keystore.salt, 'base64');
    const nonce = Buffer.from(keystore.nonce, 'base64');
    const signature = Buffer.from(keystore.hmac, 'base64');
    const kdf = keystore.kdf || 'pbkdf2';

    const key = await deriveKey(password, salt, kdf);
    if (!verifyHmac(key, salt, nonce, encryptedData, signature)) {
      throw new Error('Keystore integrity check failed');
    }

    const plaintext = decryptAesGcm(key, nonce, encryptedData);
    const walletData = JSON.parse(plaintext.toString('utf-8'));

    const privateKeyHex = walletData.private_key || walletData.privateKey || '';
    if (!privateKeyHex) {
      throw new Error('Keystore missing private key');
    }

    const privateKey = fromHex(privateKeyHex);
    const publicKeyHex =
      walletData.public_key ||
      walletData.publicKey ||
      toHex(getPublicKey(privateKey, true));

    const keyId = walletData.address || publicKeyHex.slice(0, 16);
    this.keys.set(keyId, {
      privateKey,
      publicKey: publicKeyHex,
      address: walletData.address || null,
      createdAt: walletData.created_at || walletData.createdAt || null,
      source: resolved
    });

    return {
      keyId,
      address: walletData.address || null,
      publicKey: publicKeyHex
    };
  }

  async signDigest(keyId, digestHex) {
    const keyEntry = this.keys.get(keyId);
    if (!keyEntry) {
      throw new Error('Key not loaded');
    }

    const digest = fromHex(digestHex);
    if (digest.length !== 32) {
      throw new Error('Digest must be 32 bytes (SHA-256 hash expected)');
    }

    const signature = await sign(digest, keyEntry.privateKey, { lowS: true });
    const signatureBytes =
      typeof signature === 'string'
        ? fromHex(signature)
        : signature.toCompactRawBytes
          ? signature.toCompactRawBytes()
          : signature;

    return {
      signature: etc.bytesToHex
        ? etc.bytesToHex(signatureBytes)
        : Buffer.from(signatureBytes).toString('hex'),
      recoveryId: signature.recovery ?? null,
      publicKey: keyEntry.publicKey,
      address: keyEntry.address
    };
  }
}

module.exports = {
  SecureKeyVault,
  deriveKey,
  decryptAesGcm
};
