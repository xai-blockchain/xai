const fs = require('fs');
const path = require('path');
const https = require('https');
const crypto = require('crypto');
const httpProxy = require('http-proxy');
const selfsigned = require('selfsigned');

const ONE_DAY_MS = 24 * 60 * 60 * 1000;

function ensureDir(dirPath, mode = 0o700) {
  fs.mkdirSync(dirPath, { recursive: true, mode });
}

function writeFileIfChanged(filePath, content, mode = 0o600) {
  if (fs.existsSync(filePath)) {
    const existing = fs.readFileSync(filePath, 'utf-8');
    if (existing === content) {
      return;
    }
  }
  fs.writeFileSync(filePath, content, { mode });
}

function certificateExpiringSoon(certPem, thresholdDays = 5) {
  try {
    const cert = new crypto.X509Certificate(certPem);
    const expiresAt = new Date(cert.validTo).getTime();
    return expiresAt - Date.now() < thresholdDays * ONE_DAY_MS;
  } catch {
    return true;
  }
}

function ensureCertificate(certDir) {
  ensureDir(certDir);
  const certPath = path.join(certDir, 'desktop-localhost.crt');
  const keyPath = path.join(certDir, 'desktop-localhost.key');

  const haveExisting = fs.existsSync(certPath) && fs.existsSync(keyPath);
  const maybeCert = haveExisting ? fs.readFileSync(certPath, 'utf-8') : null;
  const shouldRegenerate = !maybeCert || certificateExpiringSoon(maybeCert, 7);

  if (shouldRegenerate) {
    const attrs = [{ name: 'commonName', value: 'localhost' }];
    const pems = selfsigned.generate(attrs, {
      days: 30,
      keySize: 2048,
      algorithm: 'sha256',
      extensions: [
        { name: 'basicConstraints', cA: false },
        {
          name: 'subjectAltName',
          altNames: [
            { type: 2, value: 'localhost' },
            { type: 7, ip: '127.0.0.1' }
          ]
        }
      ]
    });
    writeFileIfChanged(certPath, pems.cert);
    writeFileIfChanged(keyPath, pems.private);
    return { cert: pems.cert, key: pems.private };
  }

  return {
    cert: fs.readFileSync(certPath, 'utf-8'),
    key: fs.readFileSync(keyPath, 'utf-8')
  };
}

function assertLocalTarget(target) {
  const parsed = new URL(target);
  if (!['localhost', '127.0.0.1'].includes(parsed.hostname)) {
    throw new Error(`Refusing to proxy non-local target: ${target}`);
  }
}

function createSecureProxy({ target, listenPort, certDir, name = 'proxy' }) {
  assertLocalTarget(target);
  const tlsMaterial = ensureCertificate(certDir);
  const proxy = httpProxy.createProxyServer({
    target,
    changeOrigin: true,
    ws: true,
    xfwd: true,
    secure: false
  });

  proxy.on('proxyReq', (proxyReq) => {
    proxyReq.setHeader('Connection', 'close');
  });

  proxy.on('error', (err, req, res) => {
    const context = { err: err.message, url: req?.url };
    console.error(`[${name}] Proxy error`, context);
    if (res && !res.headersSent) {
      res.writeHead(502, { 'Content-Type': 'application/json' });
    }
    if (res) {
      res.end(JSON.stringify({ error: 'Upstream unavailable' }));
    }
  });

  const server = https.createServer(
    {
      key: tlsMaterial.key,
      cert: tlsMaterial.cert,
      minVersion: 'TLSv1.2'
    },
    (req, res) => proxy.web(req, res)
  );

  server.on('upgrade', (req, socket, head) => {
    proxy.ws(req, socket, head);
  });

  return {
    listen: () =>
      new Promise((resolve, reject) => {
        server.once('error', reject);
        server.listen(listenPort, '127.0.0.1', () => {
          server.removeListener('error', reject);
          resolve(listenPort);
        });
      }),
    close: () => server.close(),
    cert: tlsMaterial.cert,
    key: tlsMaterial.key
  };
}

module.exports = {
  createSecureProxy,
  ensureCertificate
};
