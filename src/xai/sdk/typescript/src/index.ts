/**
 * XAI SDK - Production-ready TypeScript/JavaScript SDK for the XAI blockchain
 *
 * @packageDocumentation
 */

// Main client
export { XAIClient } from './client';
export { default } from './client';

// Clients
export { WalletClient } from './clients/wallet-client';
export { TransactionClient } from './clients/transaction-client';
export { BlockchainClient } from './clients/blockchain-client';
export { MiningClient } from './clients/mining-client';
export { GovernanceClient } from './clients/governance-client';

// Utilities
export { HTTPClient } from './utils/http-client';
export { WebSocketClient } from './utils/websocket-client';

// Types
export * from './types';

// Errors
export * from './errors';
