export const API_CONFIG = {
  DEFAULT_ENDPOINT: 'http://localhost:12001',
  DEFAULT_WS_ENDPOINT: 'ws://localhost:12001',
  TIMEOUT: 30000,
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000,
};

export const SECURITY = {
  SESSION_TIMEOUT: 5 * 60 * 1000, // 5 minutes
  MAX_PIN_ATTEMPTS: 5,
  PIN_LENGTH: 6,
  KEYCHAIN_SERVICE: 'XAIWallet',
  ENCRYPTION_ALGORITHM: 'AES-256-GCM',
};

export const WALLET = {
  MNEMONIC_STRENGTH: 256, // 24 words
  DERIVATION_PATH: "m/44'/60'/0'/0/0", // Ethereum-compatible
  MIN_TRANSACTION_AMOUNT: 0.000001,
  MAX_TRANSACTION_AMOUNT: 1000000,
  DEFAULT_GAS_LIMIT: 21000,
};

export const UI = {
  ANIMATION_DURATION: 300,
  TOAST_DURATION: 3000,
  QR_SIZE: 250,
  PAGINATION_LIMIT: 20,
};

export const COLORS = {
  primary: '#6366F1',
  secondary: '#8B5CF6',
  success: '#10B981',
  error: '#EF4444',
  warning: '#F59E0B',
  background: '#FFFFFF',
  backgroundDark: '#111827',
  text: '#1F2937',
  textDark: '#F9FAFB',
  border: '#E5E7EB',
  borderDark: '#374151',
  card: '#F9FAFB',
  cardDark: '#1F2937',
};

export const TRANSACTION_STATUS = {
  PENDING: 'pending',
  CONFIRMED: 'confirmed',
  FAILED: 'failed',
} as const;

export const BIOMETRIC_PROMPT = {
  title: 'Authenticate',
  subtitle: 'Use biometric authentication to continue',
  description: 'Place your finger on the sensor or look at the camera',
  cancelButton: 'Use PIN instead',
};

export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network connection failed. Please check your internet connection.',
  INVALID_ADDRESS: 'Invalid XAI address format.',
  INSUFFICIENT_BALANCE: 'Insufficient balance for this transaction.',
  TRANSACTION_FAILED: 'Transaction failed. Please try again.',
  WALLET_CREATION_FAILED: 'Failed to create wallet. Please try again.',
  BIOMETRIC_NOT_AVAILABLE: 'Biometric authentication is not available on this device.',
  SESSION_EXPIRED: 'Your session has expired. Please authenticate again.',
  INVALID_PIN: 'Invalid PIN. Please try again.',
  MAX_ATTEMPTS_EXCEEDED: 'Maximum PIN attempts exceeded. Please wait.',
};

export const STORAGE_KEYS = {
  WALLET: '@xai:wallet',
  SETTINGS: '@xai:settings',
  BIOMETRIC_CONFIG: '@xai:biometric',
  PENDING_TRANSACTIONS: '@xai:pending_txs',
  TRANSACTION_CACHE: '@xai:tx_cache',
  LAST_SYNC: '@xai:last_sync',
  SESSION_ACTIVE: '@xai:session_active',
};
