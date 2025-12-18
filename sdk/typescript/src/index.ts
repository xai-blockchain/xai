/**
 * XAI SDK
 * Production-ready TypeScript/JavaScript SDK for the XAI blockchain
 */

// Main client
export { XAIClient } from './client';

// Sub-clients
export { Wallet, WalletClient } from './clients/wallet-client';
export { TransactionBuilder, TransactionClient } from './clients/transaction-client';
export { BlockchainClient } from './clients/blockchain-client';
export { MiningClient } from './clients/mining-client';
export { GovernanceClient } from './clients/governance-client';

// Types
export * from './types';

// Errors
export * from './errors';

// Utilities
export {
  generatePrivateKey,
  derivePublicKey,
  generateAddress,
  signMessage,
  verifySignature,
  generateMnemonic,
  validateMnemonic,
  hash256,
  validateAddress,
} from './utils/crypto';
