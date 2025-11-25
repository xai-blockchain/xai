const { app, BrowserWindow, Tray, Menu } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fetch = require('node-fetch');

const ROOT_DIR = path.resolve(__dirname, '..');
const XAI_DIR = path.join(ROOT_DIR, 'xai');
const DASHBOARD_URL = 'http://127.0.0.1:3000/dashboard';
const MOBILE_URL = 'http://127.0.0.1:3000/mobile';
const NODE_URL = 'http://127.0.0.1:5000';

const PYTHON_PATH = process.env.PYTHON_PATH || 'python';

let nodeProcess;
let explorerProcess;
let mainWindow;
let tray;

function spawnScript(script, args = []) {
  const scriptPath = path.join(XAI_DIR, script);
  const proc = spawn('powershell.exe', ['-ExecutionPolicy', 'Bypass', '-File', scriptPath, ...args], {
    cwd: XAI_DIR,
    env: {
      ...process.env,
      PYTHONPATH: `${ROOT_DIR};${XAI_DIR}`
    }
  });
  proc.stdout.on('data', data => console.log(`[${script}] ${data.toString()}`));
  proc.stderr.on('data', data => console.error(`[${script}] ${data.toString()}`));
  return proc;
}

async function waitForServer(url, timeout = 40000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(url, { method: 'GET' });
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
      nodeIntegration: false
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
  nodeProcess = spawnScript('run-python.ps1', ['core/node.py', '--miner', process.env.XAI_MINER_ADDRESS || 'XAI1miner000000000000000000000']);
  explorerProcess = spawnScript('run-python.ps1', ['explorer.py']);
  await waitForServer('http://127.0.0.1:3000/dashboard');
}

function stopProcesses() {
  [nodeProcess, explorerProcess].forEach(proc => {
    if (proc && !proc.killed) {
      proc.kill();
    }
  });
}

app.whenReady().then(async () => {
  try {
    await startProcesses();
    createWindow();
    createTray();
  } catch (err) {
    console.error('Failed to start XAI node + explorer:', err);
    app.quit();
  }
});

app.on('before-quit', () => {
  stopProcesses();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    stopProcesses();
    app.quit();
  }
});
