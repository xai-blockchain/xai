const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  nodeUrl: 'http://127.0.0.1:5000',
  mobileUrl: 'http://127.0.0.1:3000/mobile'
});
