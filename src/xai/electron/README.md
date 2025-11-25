# XAI Desktop Electron Shell

This folder packages the XAI node + explorer dashboard into a single Electron wrapper so newcomers can run a desktop miner and wallet without touching the terminal.

## Quick start (developer)

```bash
cd electron
npm install
npm start
```

`npm start` will:

1. Spawn the Python node (`core/node.py`) and explorer (`explorer.py`) via the existing `run-python.ps1` helper.
2. Wait for `http://localhost:3000/dashboard` to be available.
3. Open that URL in an Electron window with tray controls and the QR-linked mobile view.

## Building distributables

Install dependencies once (`npm install`), then:

```bash
npm run dist
```

This runs `electron-builder` and emits installers under `electron/dist`. Customize `build` in `package.json` to add icons or change the app ID before shipping.

## Features

- Auto-starts the node + explorer Dashboard.
- Shows the mining dashboard/QR experience you created.
- Tray menu gives quick access to the mobile view and makes quitting clean.
- Uses `preload.js` to expose the node/mobile URLs to renderer code (if you need to extend the UI later).

Adjust `XAI_MINER_ADDRESS` via environment variable when launching Electron if you want a different miner address than the default.
