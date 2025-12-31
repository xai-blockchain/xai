/**
 * Unified Multi-Chain Wallet Types
 * Supports Aura, PAW, and XAI chains
 */

export interface ChainConfig {
  chainId: string;
  chainName: string;
  bech32Prefix: string;
  slip44: number;
  assets: AssetConfig[];
  rpc: string[];
  rest: string[];
  gasPrice: GasPrice;
  features?: string[];
}

export interface AssetConfig {
  denom: string;
  minimalDenom: string;
  decimals: number;
  symbol: string;
  coingeckoId?: string;
}

export interface GasPrice {
  low: number;
  average: number;
  high: number;
  denom: string;
}

export interface WalletAccount {
  address: string;
  publicKey: Uint8Array;
  chainId: string;
  path: string;
}

export interface MultiChainWallet {
  mnemonic?: string;
  accounts: Map<string, WalletAccount>;
}

export interface Balance {
  denom: string;
  amount: string;
}

export interface SignDoc {
  chain_id: string;
  account_number: string;
  sequence: string;
  fee: {
    amount: { denom: string; amount: string }[];
    gas: string;
  };
  msgs: any[];
  memo: string;
}

export interface SignedTx {
  bodyBytes: Uint8Array;
  authInfoBytes: Uint8Array;
  signatures: Uint8Array[];
}

export interface IBCTransferParams {
  sourceChain: string;
  destChain: string;
  sender: string;
  receiver: string;
  amount: { denom: string; amount: string };
  sourceChannel?: string; // Optional - defaults to channel from IBC_CHANNELS lookup
  timeoutHeight?: { revisionNumber: string; revisionHeight: string };
  timeoutTimestamp?: string;
  memo?: string;
}

export interface KeplrChainInfo {
  chainId: string;
  chainName: string;
  rpc: string;
  rest: string;
  bip44: { coinType: number };
  bech32Config: {
    bech32PrefixAccAddr: string;
    bech32PrefixAccPub: string;
    bech32PrefixValAddr: string;
    bech32PrefixValPub: string;
    bech32PrefixConsAddr: string;
    bech32PrefixConsPub: string;
  };
  currencies: {
    coinDenom: string;
    coinMinimalDenom: string;
    coinDecimals: number;
    coinGeckoId?: string;
  }[];
  feeCurrencies: {
    coinDenom: string;
    coinMinimalDenom: string;
    coinDecimals: number;
    gasPriceStep: { low: number; average: number; high: number };
  }[];
  stakeCurrency: {
    coinDenom: string;
    coinMinimalDenom: string;
    coinDecimals: number;
  };
  features?: string[];
}
