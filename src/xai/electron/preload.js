const { contextBridge, ipcRenderer } = require('electron');

function createWalletAPI() {
  let sessionToken;
  async function ensureSession() {
    if (sessionToken) return sessionToken;
    const { sessionToken: token } = await ipcRenderer.invoke('wallet:initSession');
    sessionToken = token;
    return sessionToken;
  }

  return {
    async importKeystore(keystorePath, password) {
      const token = await ensureSession();
      return ipcRenderer.invoke('wallet:importKeystore', { keystorePath, password, token });
    },
    async signDigest(keyId, digestHex) {
      const token = await ensureSession();
      return ipcRenderer.invoke('wallet:signDigest', { keyId, digestHex, token });
    },
    async clear() {
      const token = await ensureSession();
      return ipcRenderer.invoke('wallet:clearKeys', { token });
    }
  };
}

contextBridge.exposeInMainWorld('electronAPI', {
  nodeUrl: 'https://127.0.0.1:5443',
  mobileUrl: 'https://127.0.0.1:3443/mobile',
  wallet: createWalletAPI()
});
