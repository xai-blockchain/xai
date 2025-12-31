/**
 * Chain Configurations for Aura, PAW, and XAI
 * All three chains under common ownership with independent governance
 */

import { ChainConfig, KeplrChainInfo } from '../types';

// Cosmos standard coin type (shared by Aura and PAW)
const COSMOS_COIN_TYPE = 118;

// XAI uses custom coin type (EVM-compatible)
const XAI_COIN_TYPE = 22593;

export const AURA_CONFIG: ChainConfig = {
  chainId: 'aura-mainnet-1',
  chainName: 'Aura',
  bech32Prefix: 'aura',
  slip44: COSMOS_COIN_TYPE,
  assets: [{
    denom: 'AURA',
    minimalDenom: 'uaura',
    decimals: 6,
    symbol: 'AURA',
  }],
  rpc: ['https://rpc.aura.network', 'http://localhost:10657'],
  rest: ['https://api.aura.network', 'http://localhost:10317'],
  gasPrice: {
    low: 0.015,
    average: 0.025,
    high: 0.04,
    denom: 'uaura',
  },
  features: ['ibc-transfer', 'cosmwasm'],
};

export const AURA_TESTNET_CONFIG: ChainConfig = {
  chainId: 'aura-testnet-1',
  chainName: 'Aura Testnet',
  bech32Prefix: 'aura',
  slip44: COSMOS_COIN_TYPE,
  assets: [{
    denom: 'AURA',
    minimalDenom: 'uaura',
    decimals: 6,
    symbol: 'AURA',
  }],
  rpc: ['http://localhost:10657'],
  rest: ['http://localhost:10317'],
  gasPrice: {
    low: 0.015,
    average: 0.025,
    high: 0.04,
    denom: 'uaura',
  },
  features: ['ibc-transfer', 'cosmwasm'],
};

export const PAW_CONFIG: ChainConfig = {
  chainId: 'paw-mainnet-1',
  chainName: 'PAW',
  bech32Prefix: 'paw',
  slip44: COSMOS_COIN_TYPE,
  assets: [{
    denom: 'PAW',
    minimalDenom: 'upaw',
    decimals: 6,
    symbol: 'PAW',
  }],
  rpc: ['https://rpc.paw.network', 'http://localhost:11657'],
  rest: ['https://api.paw.network', 'http://localhost:11317'],
  gasPrice: {
    low: 0.001,
    average: 0.005,
    high: 0.01,
    denom: 'upaw',
  },
  features: ['ibc-transfer', 'ibc-go', 'dex'],
};

export const PAW_TESTNET_CONFIG: ChainConfig = {
  chainId: 'paw-testnet-1',
  chainName: 'PAW Testnet',
  bech32Prefix: 'paw',
  slip44: COSMOS_COIN_TYPE,
  assets: [{
    denom: 'PAW',
    minimalDenom: 'upaw',
    decimals: 6,
    symbol: 'PAW',
  }],
  rpc: ['http://localhost:11657'],
  rest: ['http://localhost:11317'],
  gasPrice: {
    low: 0.001,
    average: 0.005,
    high: 0.01,
    denom: 'upaw',
  },
  features: ['ibc-transfer', 'ibc-go', 'dex'],
};

export const XAI_CONFIG: ChainConfig = {
  chainId: 'xai-mainnet-1',
  chainName: 'XAI',
  bech32Prefix: 'xai',
  slip44: XAI_COIN_TYPE,
  assets: [{
    denom: 'XAI',
    minimalDenom: 'uxai',
    decimals: 18,
    symbol: 'XAI',
  }],
  rpc: ['https://rpc.xai.network', 'http://localhost:12657'],
  rest: ['https://api.xai.network', 'http://localhost:12317'],
  gasPrice: {
    low: 0.0001,
    average: 0.001,
    high: 0.01,
    denom: 'uxai',
  },
  features: ['ai-trading', 'evm-compatible'],
};

export const XAI_TESTNET_CONFIG: ChainConfig = {
  chainId: 'xai-testnet-1',
  chainName: 'XAI Testnet',
  bech32Prefix: 'xai',
  slip44: XAI_COIN_TYPE,
  assets: [{
    denom: 'XAI',
    minimalDenom: 'uxai',
    decimals: 18,
    symbol: 'XAI',
  }],
  rpc: ['http://localhost:12657'],
  rest: ['http://localhost:12317'],
  gasPrice: {
    low: 0.0001,
    average: 0.001,
    high: 0.01,
    denom: 'uxai',
  },
  features: ['ai-trading', 'evm-compatible'],
};

// All supported chains
export const SUPPORTED_CHAINS: Record<string, ChainConfig> = {
  'aura-mainnet-1': AURA_CONFIG,
  'aura-testnet-1': AURA_TESTNET_CONFIG,
  'paw-mainnet-1': PAW_CONFIG,
  'paw-testnet-1': PAW_TESTNET_CONFIG,
  'xai-mainnet-1': XAI_CONFIG,
  'xai-testnet-1': XAI_TESTNET_CONFIG,
};

// IBC Channel mappings between chains
export const IBC_CHANNELS: Record<string, Record<string, string>> = {
  'aura-mainnet-1': {
    'paw-mainnet-1': 'channel-0',
  },
  'paw-mainnet-1': {
    'aura-mainnet-1': 'channel-0',
  },
  'aura-testnet-1': {
    'paw-testnet-1': 'channel-0',
  },
  'paw-testnet-1': {
    'aura-testnet-1': 'channel-0',
  },
};

/**
 * Convert ChainConfig to Keplr-compatible chain info
 */
export function toKeplrChainInfo(config: ChainConfig): KeplrChainInfo {
  const asset = config.assets[0];
  return {
    chainId: config.chainId,
    chainName: config.chainName,
    rpc: config.rpc[0],
    rest: config.rest[0],
    bip44: { coinType: config.slip44 },
    bech32Config: {
      bech32PrefixAccAddr: config.bech32Prefix,
      bech32PrefixAccPub: `${config.bech32Prefix}pub`,
      bech32PrefixValAddr: `${config.bech32Prefix}valoper`,
      bech32PrefixValPub: `${config.bech32Prefix}valoperpub`,
      bech32PrefixConsAddr: `${config.bech32Prefix}valcons`,
      bech32PrefixConsPub: `${config.bech32Prefix}valconspub`,
    },
    currencies: [{
      coinDenom: asset.denom,
      coinMinimalDenom: asset.minimalDenom,
      coinDecimals: asset.decimals,
      coinGeckoId: asset.coingeckoId,
    }],
    feeCurrencies: [{
      coinDenom: asset.denom,
      coinMinimalDenom: asset.minimalDenom,
      coinDecimals: asset.decimals,
      gasPriceStep: {
        low: config.gasPrice.low,
        average: config.gasPrice.average,
        high: config.gasPrice.high,
      },
    }],
    stakeCurrency: {
      coinDenom: asset.denom,
      coinMinimalDenom: asset.minimalDenom,
      coinDecimals: asset.decimals,
    },
    features: config.features,
  };
}

/**
 * Get chain config by chain ID
 */
export function getChainConfig(chainId: string): ChainConfig | undefined {
  return SUPPORTED_CHAINS[chainId];
}

/**
 * Get IBC channel between two chains
 */
export function getIBCChannel(sourceChainId: string, destChainId: string): string | undefined {
  return IBC_CHANNELS[sourceChainId]?.[destChainId];
}

/**
 * Check if two chains can communicate via IBC
 */
export function canIBCTransfer(sourceChainId: string, destChainId: string): boolean {
  return !!getIBCChannel(sourceChainId, destChainId);
}
