/**
 * XAI SDK Type Definitions
 * Complete type definitions for the XAI blockchain SDK
 */

export interface XAIClientConfig {
  baseUrl: string;
  wsUrl?: string;
  timeout?: number;
  retries?: number;
  retryDelay?: number;
  apiKey?: string;
}

export interface Block {
  index: number;
  timestamp: number;
  transactions: Transaction[];
  previous_hash: string;
  hash: string;
  nonce: number;
  difficulty: number;
  miner: string;
  merkle_root?: string;
  state_root?: string;
  receipts_root?: string;
}

export interface BlockHeader {
  index: number;
  timestamp: number;
  previous_hash: string;
  hash: string;
  merkle_root: string;
  state_root?: string;
  nonce: number;
  difficulty: number;
}

export interface Transaction {
  txid: string;
  sender: string;
  recipient: string;
  amount: number;
  fee: number;
  timestamp: number;
  signature?: string;
  public_key?: string;
  tx_type?: string;
  nonce?: number;
  inputs?: TransactionInput[];
  outputs?: TransactionOutput[];
  metadata?: Record<string, any>;
  rbf_enabled?: boolean;
  replaces_txid?: string;
  gas_sponsor?: string;
  gas_sponsor_signature?: string;
}

export interface TransactionInput {
  txid: string;
  output_index: number;
  signature?: string;
  public_key?: string;
}

export interface TransactionOutput {
  address: string;
  amount: number;
  script_pubkey?: string;
}

export interface UnsignedTransaction {
  sender: string;
  recipient: string;
  amount: number;
  fee: number;
  nonce?: number;
  tx_type?: string;
  inputs?: TransactionInput[];
  outputs?: TransactionOutput[];
  metadata?: Record<string, any>;
  rbf_enabled?: boolean;
  replaces_txid?: string;
  gas_sponsor?: string;
}

export interface SignedTransaction extends Transaction {
  txid: string;
  signature: string;
  public_key: string;
}

export interface BroadcastResult {
  success: boolean;
  txid?: string;
  error?: string;
  message?: string;
}

export interface Balance {
  address: string;
  balance: number;
  confirmed?: number;
  unconfirmed?: number;
}

export interface AddressNonce {
  address: string;
  confirmed_nonce: number;
  next_nonce: number;
  pending_nonce: number | null;
}

export interface TransactionHistory {
  address: string;
  total: number;
  limit: number;
  offset: number;
  transactions: Transaction[];
}

export interface BlockchainInfo {
  height: number;
  best_block_hash: string;
  difficulty: number;
  total_transactions: number;
  version?: string;
  network?: string;
}

export interface MempoolInfo {
  size: number;
  bytes?: number;
  transactions: Transaction[];
}

export interface MiningStats {
  mining_enabled: boolean;
  hashrate?: number;
  blocks_mined?: number;
  last_block_time?: number;
}

export interface PeerInfo {
  id: string;
  url: string;
  version?: string;
  height?: number;
  last_seen?: number;
}

export interface NetworkInfo {
  peers: PeerInfo[];
  peer_count: number;
  connections: number;
}

export interface WalletKeyPair {
  address: string;
  publicKey: string;
  privateKey: string;
}

export interface WalletBackup {
  address: string;
  public_key: string;
  encrypted_private_key?: string;
  private_key?: string;
  encrypted?: boolean;
  derivation_metadata?: HDMetadata;
}

export interface HDMetadata {
  mnemonic_path?: string;
  account_index?: number;
  address_index?: number;
  hardened_address?: string;
  coin_type?: number;
}

export interface EventSubscription {
  event: string;
  callback: (data: any) => void;
}

export interface WebSocketEvent {
  type: string;
  data: any;
  timestamp: number;
}

export interface ContractDeployment {
  address: string;
  txid: string;
  deployer: string;
  bytecode: string;
  abi?: any[];
}

export interface ContractCall {
  address: string;
  method: string;
  params: any[];
  from: string;
  value?: number;
  gas?: number;
}

export interface ContractCallResult {
  success: boolean;
  result?: any;
  error?: string;
  gas_used?: number;
}

export interface FeeEstimate {
  fast: number;
  medium: number;
  slow: number;
  recommended: number;
}

export interface GovernanceProposal {
  id: string;
  title: string;
  description: string;
  proposer: string;
  start_time: number;
  end_time: number;
  yes_votes: number;
  no_votes: number;
  status: 'pending' | 'active' | 'passed' | 'rejected' | 'executed';
}

export interface GovernanceVote {
  proposal_id: string;
  voter: string;
  vote: 'yes' | 'no' | 'abstain';
  weight: number;
  timestamp: number;
}

export interface SyncProgress {
  current_height: number;
  target_height: number;
  progress_percentage: number;
  syncing: boolean;
  estimated_time_remaining?: number;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  uptime: number;
  syncing: boolean;
  peers: number;
  height: number;
}

export interface APIError {
  error: string;
  code?: string;
  status?: number;
  details?: any;
}
