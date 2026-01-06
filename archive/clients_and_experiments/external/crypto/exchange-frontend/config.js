// Configuration Management
const config = {
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api',
  WS_URL: import.meta.env.VITE_WS_URL || 'ws://localhost:5000',
  ENABLE_CSP: import.meta.env.VITE_ENABLE_CSP === 'true',
  CSRF_ENABLED: import.meta.env.VITE_CSRF_ENABLED === 'true',
  MAX_API_CALLS_PER_MINUTE: parseInt(import.meta.env.VITE_MAX_API_CALLS_PER_MINUTE || '60', 10),
  MAX_WEBSOCKET_RECONNECT_ATTEMPTS: parseInt(
    import.meta.env.VITE_MAX_WEBSOCKET_RECONNECT_ATTEMPTS || '5',
    10
  ),
  SESSION_TIMEOUT: parseInt(import.meta.env.VITE_SESSION_TIMEOUT || '3600000', 10),
  AUTO_REFRESH_INTERVAL: parseInt(import.meta.env.VITE_AUTO_REFRESH_INTERVAL || '10000', 10),
  DEBUG_MODE: import.meta.env.VITE_DEBUG_MODE === 'true',
};

// Validate configuration
if (!config.API_BASE_URL || !config.WS_URL) {
  console.error('Missing required configuration: API_BASE_URL or WS_URL');
}

// Freeze configuration to prevent tampering
Object.freeze(config);

export default config;
