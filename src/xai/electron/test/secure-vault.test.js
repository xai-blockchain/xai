const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { verify } = require('@noble/secp256k1');

const { SecureKeyVault, deriveKey } = require('../secure-vault');

async function writeKeystore(tempDir, address, privateKeyHex, password) {
  const salt = crypto.randomBytes(32);
  const nonce = crypto.randomBytes(12);
  const key = await deriveKey(password, salt, 'pbkdf2');
  const walletData = {
    address,
    private_key: privateKeyHex,
    public_key: '',
    created_at: Date.now() / 1000,
    version: '2.0'
  };

  const cipher = crypto.createCipheriv('aes-256-gcm', key, nonce);
  const ciphertext = Buffer.concat([
    cipher.update(Buffer.from(JSON.stringify(walletData), 'utf-8')),
    cipher.final()
  ]);
  const tag = cipher.getAuthTag();
  const encrypted = Buffer.concat([ciphertext, tag]);

  const hmacKey = crypto
    .createHash('sha256')
    .update(Buffer.concat([key, Buffer.from('hmac')]))
    .digest();
  const signature = crypto.createHmac('sha256', hmacKey).update(Buffer.concat([salt, nonce, encrypted])).digest();

  const keystore = {
    version: '2.0',
    algorithm: 'AES-256-GCM',
    kdf: 'pbkdf2',
    iterations: 600000,
    encrypted_data: encrypted.toString('base64'),
    salt: salt.toString('base64'),
    nonce: nonce.toString('base64'),
    hmac: signature.toString('base64'),
    address
  };

  const ksPath = path.join(tempDir, `${address}.keystore`);
  fs.writeFileSync(ksPath, JSON.stringify(keystore), { mode: 0o600 });
  return ksPath;
}

test('SecureKeyVault imports keystore and signs digest without exposing key', async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'xai-vault-test-'));
  const password = 'StrongerPass!123';
  const privateKeyHex = '1'.repeat(64);
  const digestHex = crypto.createHash('sha256').update('hello-world').digest('hex');

  const ksPath = await writeKeystore(tmp, 'XAI_TEST_ADDR', privateKeyHex, password);
  const vault = new SecureKeyVault();
  const { keyId, publicKey } = await vault.importKeystore(ksPath, password);

  assert.equal(keyId, 'XAI_TEST_ADDR');
  assert.ok(publicKey.startsWith('02') || publicKey.startsWith('03'), 'public key must be compressed');
  assert.deepEqual(vault.listLoadedKeyIds(), ['XAI_TEST_ADDR']);

  const signed = await vault.signDigest(keyId, digestHex);
  assert.equal(signed.address, 'XAI_TEST_ADDR');
  assert.equal(signed.publicKey, publicKey);
  assert.ok(verify(signed.signature, digestHex, publicKey), 'signature must verify');
});

test('SecureKeyVault rejects tampered keystore HMAC', async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'xai-vault-test-'));
  const password = 'StrongerPass!123';
  const privateKeyHex = '2'.repeat(64);
  const ksPath = await writeKeystore(tmp, 'XAI_TAMPER_TEST', privateKeyHex, password);

  const keystore = JSON.parse(fs.readFileSync(ksPath, 'utf-8'));
  // Corrupt HMAC to trigger integrity failure
  keystore.hmac = Buffer.from(crypto.randomBytes(32)).toString('base64');
  fs.writeFileSync(ksPath, JSON.stringify(keystore));

  const vault = new SecureKeyVault();
  await assert.rejects(
    vault.importKeystore(ksPath, password),
    /integrity check failed/i
  );
});
