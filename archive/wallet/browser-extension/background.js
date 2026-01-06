const DEFAULT_API_HOST = 'http://localhost:8545';

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ apiHost: DEFAULT_API_HOST }, () => {
    console.log('XAI Wallet Miner: default API host stored');
  });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'getApiHost') {
    chrome.storage.local.get(['apiHost'], result => {
      sendResponse({ apiHost: result.apiHost || DEFAULT_API_HOST });
    });
    return true;
  }
  if (message.type === 'setApiHost') {
    chrome.storage.local.set({ apiHost: message.apiHost }, () => {
      sendResponse({ apiHost: message.apiHost });
    });
    return true;
  }
});
