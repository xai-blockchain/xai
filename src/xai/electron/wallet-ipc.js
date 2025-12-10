const { ipcMain } = require('electron');
const crypto = require('crypto');
const { SecureKeyVault } = require('./secure-vault');

const DEFAULT_ALLOWED_ORIGINS = [
  'https://127.0.0.1:3000',
  'https://localhost:3000',
  'https://127.0.0.1',
  'https://localhost'
];

function normalizeOrigin(url) {
  if (!url) {
    return '';
  }
  try {
    const parsed = new URL(url);
    return `${parsed.protocol}//${parsed.hostname}${parsed.port ? `:${parsed.port}` : ''}`;
  } catch {
    return '';
  }
}

function createSessionToken() {
  return crypto.randomBytes(32).toString('hex');
}

function registerWalletIPC(options = {}) {
  const allowedOrigins = options.allowedOrigins || DEFAULT_ALLOWED_ORIGINS;
  const sessionToken = createSessionToken();
  const vault = new SecureKeyVault();

  function assertAuthorized(event, providedToken) {
    const origin = normalizeOrigin(event?.senderFrame?.url || '');
    if (!allowedOrigins.includes(origin)) {
      throw new Error('Origin not authorized for wallet IPC');
    }
    if (!providedToken || providedToken !== sessionToken) {
      throw new Error('Wallet IPC session token mismatch');
    }
  }

  ipcMain.handle('wallet:initSession', (event) => {
    const origin = normalizeOrigin(event?.senderFrame?.url || '');
    if (!allowedOrigins.includes(origin)) {
      throw new Error('Origin not authorized for wallet IPC');
    }
    return { sessionToken };
  });

  ipcMain.handle('wallet:importKeystore', async (event, payload = {}) => {
    const { keystorePath, password, token } = payload;
    assertAuthorized(event, token);
    const result = await vault.importKeystore(keystorePath, password);
    return { success: true, ...result };
  });

  ipcMain.handle('wallet:signDigest', async (event, payload = {}) => {
    const { keyId, digestHex, token } = payload;
    assertAuthorized(event, token);
    const result = await vault.signDigest(keyId, digestHex);
    return { success: true, ...result };
  });

  ipcMain.handle('wallet:clearKeys', (event, payload = {}) => {
    const { token } = payload;
    assertAuthorized(event, token);
    vault.clear();
    return { success: true };
  });

  return {
    vault,
    sessionToken,
    allowedOrigins
  };
}

module.exports = {
  registerWalletIPC,
  normalizeOrigin
};
