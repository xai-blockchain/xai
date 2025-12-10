const { app, BrowserWindow, Tray, Menu } = require('electron');
const path = require('path');
const https = require('https');
const { spawn } = require('child_process');
const fetch = require('node-fetch');
const { registerWalletIPC } = require('./wallet-ipc');
const { createSecureProxy } = require('./secure-local-proxy');

const ROOT_DIR = path.resolve(__dirname, '..');
const XAI_DIR = path.join(ROOT_DIR, 'xai');
const DASHBOARD_HTTP_URL = 'http://127.0.0.1:3000/dashboard';
const DASHBOARD_PROXY_PORT = 3443;
const API_PROXY_PORT = 5443;
const DASHBOARD_URL = `https://127.0.0.1:${DASHBOARD_PROXY_PORT}/dashboard`;
const MOBILE_URL = `https://127.0.0.1:${DASHBOARD_PROXY_PORT}/mobile`;
const NODE_URL = `https://127.0.0.1:${API_PROXY_PORT}`;

app.commandLine.appendSwitch('enable-sandbox');

const PYTHON_PATH = process.env.PYTHON_PATH || 'python';

const isWindows = process.platform === 'win32';
const powershellExec = isWindows ? 'powershell.exe' : 'pwsh';

let nodeProcess;
let explorerProcess;
let mainWindow;
let tray;
let walletSession;
let dashboardProxy;
let apiProxy;

function spawnScript(script, args = [], extraEnv = {}) {
  const scriptPath = path.join(XAI_DIR, script);
  let command;
  let commandArgs;

  if (script.endsWith('.ps1')) {
    // Respect system execution policy instead of forcing Bypass
    command = powershellExec;
    commandArgs = ['-NoProfile', '-File', scriptPath, ...args];
  } else if (script.endsWith('.py')) {
    command = PYTHON_PATH;
    commandArgs = [scriptPath, ...args];
  } else {
    command = scriptPath;
    commandArgs = args;
  }

  const proc = spawn(command, commandArgs, {
    cwd: XAI_DIR,
    env: {
      ...process.env,
      PYTHONPATH: `${ROOT_DIR};${XAI_DIR}`,
      ...extraEnv
    }
  });
  proc.stdout.on('data', data => console.log(`[${script}] ${data.toString()}`));
  proc.stderr.on('data', data => console.error(`[${script}] ${data.toString()}`));
  return proc;
}

async function waitForServer(url, timeout = 40000, allowSelfSigned = false) {
  const deadline = Date.now() + timeout;
  const isHttps = url.startsWith('https://');
  const agent = isHttps
    ? new https.Agent({ rejectUnauthorized: !allowSelfSigned })
    : undefined;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(url, { method: 'GET', agent });
      if (res.ok) return true;
    } catch (err) {
      // ignore; keep retrying
    }
    await new Promise(resolve => setTimeout(resolve, 800));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 1000,
    minHeight: 720,
    icon: path.join(__dirname, 'assets', 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true
    }
  });
  mainWindow.loadURL(DASHBOARD_URL);
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
  mainWindow.on('close', () => {
    app.quit();
  });
}

function createTray() {
  tray = new Tray(path.join(__dirname, 'assets', 'icon.png'));
  const contextMenu = Menu.buildFromTemplate([
    { label: 'Open Dashboard', click: () => mainWindow && mainWindow.show() },
    { label: 'Open Mobile Monitor', click: () => require('electron').shell.openExternal(MOBILE_URL) },
    { type: 'separator' },
    {
      label: 'Quit XAI Desktop',
      click: () => app.quit()
    }
  ]);
  tray.setToolTip('XAI Desktop Dashboard');
  tray.setContextMenu(contextMenu);
}

async function startProcesses() {
  const allowedOrigins = JSON.stringify([
    `https://127.0.0.1:${DASHBOARD_PROXY_PORT}`,
    `https://localhost:${DASHBOARD_PROXY_PORT}`
  ]);
  const sharedEnv = {
    XAI_PUBLIC_NODE_URL: NODE_URL,
    XAI_PUBLIC_DASHBOARD_ORIGIN: DASHBOARD_URL,
    XAI_API_ALLOWED_ORIGINS: allowedOrigins,
    XAI_ENABLE_PROCESS_SANDBOX: '1',
    XAI_SANDBOX_MAX_MEM_MB: process.env.XAI_SANDBOX_MAX_MEM_MB || '2048',
    XAI_SANDBOX_MAX_CPU_SECONDS: process.env.XAI_SANDBOX_MAX_CPU_SECONDS || '7200',
    XAI_SANDBOX_MAX_OPEN_FILES: process.env.XAI_SANDBOX_MAX_OPEN_FILES || '2048'
  };

  nodeProcess = spawnScript('run-python.ps1', ['core/node.py', '--miner', process.env.XAI_MINER_ADDRESS || 'XAI1miner000000000000000000000'], sharedEnv);
  explorerProcess = spawnScript('run-python.ps1', ['explorer.py'], sharedEnv);
  await waitForServer(DASHBOARD_HTTP_URL);
  await startSecureProxies();
  await waitForServer(DASHBOARD_URL, 30000, true);
  await waitForServer(`${NODE_URL}/stats`, 30000, true);
}

function stopProcesses() {
  [nodeProcess, explorerProcess].forEach(proc => {
    if (proc && !proc.killed) {
      proc.kill();
    }
  });
}

async function startSecureProxies() {
  const certDir = path.join(app.getPath('userData'), 'certs');
  dashboardProxy = createSecureProxy({
    target: 'http://127.0.0.1:3000',
    listenPort: DASHBOARD_PROXY_PORT,
    certDir,
    name: 'dashboard-proxy'
  });
  apiProxy = createSecureProxy({
    target: 'http://127.0.0.1:5000',
    listenPort: API_PROXY_PORT,
    certDir,
    name: 'api-proxy'
  });

  await dashboardProxy.listen();
  await apiProxy.listen();
}

function stopProxies() {
  if (dashboardProxy) {
    dashboardProxy.close();
    dashboardProxy = null;
  }
  if (apiProxy) {
    apiProxy.close();
    apiProxy = null;
  }
}

app.whenReady().then(async () => {
  try {
    walletSession = registerWalletIPC({
      allowedOrigins: [
        `https://127.0.0.1:${DASHBOARD_PROXY_PORT}`,
        `https://localhost:${DASHBOARD_PROXY_PORT}`
      ]
    });
    await startProcesses();
    createWindow();
    createTray();
  } catch (err) {
    console.error('Failed to start XAI node + explorer:', err);
    app.quit();
  }
});

app.on('before-quit', () => {
  stopProxies();
  stopProcesses();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    stopProxies();
    stopProcesses();
    app.quit();
  }
});
