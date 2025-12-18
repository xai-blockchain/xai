export interface Transaction {
  txid: string;
  sender: string;
  recipient: string;
  amount: number;
  fee: number;
  timestamp: number;
  signature: string;
  nonce: number;
  data?: string;
  confirmations?: number;
  status?: 'pending' | 'confirmed' | 'failed';
}

export interface Block {
  index: number;
  timestamp: number;
  transactions: Transaction[];
  previous_hash: string;
  hash: string;
  nonce: number;
  difficulty: number;
  miner?: string;
}

export interface Wallet {
  address: string;
  privateKey?: string;
  publicKey: string;
  mnemonic?: string;
  balance?: number;
  name?: string;
  createdAt: number;
}

export interface KeychainCredentials {
  username: string;
  password: string;
  service?: string;
}

export interface BiometricConfig {
  enabled: boolean;
  biometryType?: 'TouchID' | 'FaceID' | 'Fingerprint';
}

export interface AppSettings {
  biometricEnabled: boolean;
  sessionTimeout: number;
  autoLockEnabled: boolean;
  apiEndpoint: string;
  wsEndpoint: string;
  lightClientMode: boolean;
  pushNotificationsEnabled: boolean;
  language: string;
  currency: string;
  theme: 'light' | 'dark';
}

export interface PendingTransaction {
  transaction: Transaction;
  signedData: string;
  timestamp: number;
  retryCount: number;
}

export interface TransactionHistory {
  address: string;
  transaction_count: number;
  limit: number;
  offset: number;
  transactions: Transaction[];
}

export interface NodeInfo {
  version: string;
  chain_length: number;
  pending_transactions: number;
  peers: number;
  mining: boolean;
  difficulty: number;
}

export interface BalanceResponse {
  address: string;
  balance: number;
}

export interface NonceResponse {
  address: string;
  confirmed_nonce: number;
  next_nonce: number;
  pending_nonce: number | null;
}

export interface SendTransactionRequest {
  sender: string;
  recipient: string;
  amount: number;
  signature: string;
  timestamp: number;
  nonce: number;
  data?: string;
}

export interface SendTransactionResponse {
  success: boolean;
  txid?: string;
  message?: string;
  error?: string;
}

export type RootStackParamList = {
  Onboarding: undefined;
  Welcome: undefined;
  CreateWallet: undefined;
  ImportWallet: undefined;
  BackupMnemonic: { mnemonic: string };
  VerifyMnemonic: { mnemonic: string };
  BiometricSetup: undefined;
  MainTabs: undefined;
  Dashboard: undefined;
  Send: undefined;
  Receive: undefined;
  History: undefined;
  Settings: undefined;
  TransactionDetail: { txid: string };
  QRScanner: { onScan: (data: string) => void };
  ChangePin: undefined;
  About: undefined;
};

export type MainTabParamList = {
  Dashboard: undefined;
  Send: undefined;
  Receive: undefined;
  History: undefined;
  Settings: undefined;
};
