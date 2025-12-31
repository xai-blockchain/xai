import { MultiChainWallet } from '../src/services/MultiChainWallet';
import {
  AURA_CONFIG,
  PAW_CONFIG,
  XAI_CONFIG,
  SUPPORTED_CHAINS,
  toKeplrChainInfo,
  getChainConfig,
  getIBCChannel,
  canIBCTransfer,
} from '../src/chains';

describe('MultiChainWallet', () => {
  const TEST_MNEMONIC = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about';

  describe('Wallet Creation', () => {
    it('should create a new wallet with valid mnemonic', async () => {
      const wallet = await MultiChainWallet.create();
      const mnemonic = wallet.getMnemonic();
      expect(mnemonic.split(' ')).toHaveLength(24);
    });

    it('should create wallet with 12-word mnemonic when strength is 128', async () => {
      const wallet = await MultiChainWallet.create(128);
      const mnemonic = wallet.getMnemonic();
      expect(mnemonic.split(' ')).toHaveLength(12);
    });

    it('should import wallet from valid mnemonic', async () => {
      const wallet = await MultiChainWallet.fromMnemonic(TEST_MNEMONIC);
      expect(wallet.getMnemonic()).toBe(TEST_MNEMONIC);
    });

    it('should reject invalid mnemonic', async () => {
      await expect(MultiChainWallet.fromMnemonic('invalid mnemonic phrase'))
        .rejects.toThrow('Invalid mnemonic phrase');
    });
  });

  describe('Account Derivation', () => {
    let wallet: MultiChainWallet;

    beforeAll(async () => {
      wallet = await MultiChainWallet.fromMnemonic(TEST_MNEMONIC);
    });

    it('should derive Aura address with correct prefix', async () => {
      const account = await wallet.getAccount('aura-mainnet-1');
      expect(account.address).toMatch(/^aura1[a-z0-9]{38}$/);
      expect(account.chainId).toBe('aura-mainnet-1');
    });

    it('should derive PAW address with correct prefix', async () => {
      const account = await wallet.getAccount('paw-mainnet-1');
      expect(account.address).toMatch(/^paw1[a-z0-9]{38}$/);
      expect(account.chainId).toBe('paw-mainnet-1');
    });

    it('should derive XAI address with correct prefix', async () => {
      const account = await wallet.getAccount('xai-mainnet-1');
      expect(account.address).toMatch(/^xai1[a-z0-9]{38}$/);
      expect(account.chainId).toBe('xai-mainnet-1');
    });

    it('should derive consistent addresses from same mnemonic', async () => {
      const wallet2 = await MultiChainWallet.fromMnemonic(TEST_MNEMONIC);
      const account1 = await wallet.getAccount('aura-mainnet-1');
      const account2 = await wallet2.getAccount('aura-mainnet-1');
      expect(account1.address).toBe(account2.address);
    });

    it('should derive different addresses for different account indices', async () => {
      const account0 = await wallet.getAccount('aura-mainnet-1', 0);
      const account1 = await wallet.getAccount('aura-mainnet-1', 1);
      expect(account0.address).not.toBe(account1.address);
    });

    it('should cache accounts for performance', async () => {
      const account1 = await wallet.getAccount('aura-mainnet-1', 0);
      const account2 = await wallet.getAccount('aura-mainnet-1', 0);
      expect(account1).toBe(account2); // Same object reference
    });

    it('should throw for unknown chain', async () => {
      await expect(wallet.getAccount('unknown-chain'))
        .rejects.toThrow('Unknown chain: unknown-chain');
    });
  });

  describe('Linked Cosmos Addresses', () => {
    let wallet: MultiChainWallet;

    beforeAll(async () => {
      wallet = await MultiChainWallet.fromMnemonic(TEST_MNEMONIC);
    });

    it('should derive linked addresses for Aura and PAW', async () => {
      const linked = await wallet.getLinkedCosmosAddresses();
      expect(linked.aura).toMatch(/^aura1/);
      expect(linked.paw).toMatch(/^paw1/);
    });

    it('should allow address conversion between Aura and PAW', async () => {
      const auraAccount = await wallet.getAccount('aura-mainnet-1');
      const convertedPaw = MultiChainWallet.convertAddress(auraAccount.address, 'paw-mainnet-1');
      const pawAccount = await wallet.getAccount('paw-mainnet-1');
      expect(convertedPaw).toBe(pawAccount.address);
    });

    it('should throw when converting to unknown target chain', async () => {
      const auraAccount = await wallet.getAccount('aura-mainnet-1');
      expect(() => MultiChainWallet.convertAddress(auraAccount.address, 'unknown-chain'))
        .toThrow('Unknown target chain: unknown-chain');
    });

    it('should throw when converting invalid address format', () => {
      expect(() => MultiChainWallet.convertAddress('not-a-valid-bech32', 'paw-mainnet-1'))
        .toThrow('Invalid address format: not-a-valid-bech32');
    });
  });

  describe('Multi-Chain Accounts', () => {
    let wallet: MultiChainWallet;

    beforeAll(async () => {
      wallet = await MultiChainWallet.fromMnemonic(TEST_MNEMONIC);
    });

    it('should get all supported chain accounts', async () => {
      const accounts = await wallet.getAllAccounts();
      expect(accounts.length).toBe(Object.keys(SUPPORTED_CHAINS).length);
    });

    it('should get mainnet accounts only', async () => {
      const accounts = await wallet.getMainnetAccounts();
      expect(accounts.length).toBe(3);
      accounts.forEach(acc => {
        expect(acc.chainId).toMatch(/mainnet/);
      });
    });

    it('should get testnet accounts only', async () => {
      const accounts = await wallet.getTestnetAccounts();
      expect(accounts.length).toBe(3);
      accounts.forEach(acc => {
        expect(acc.chainId).toMatch(/testnet/);
      });
    });
  });

  describe('Signing', () => {
    let wallet: MultiChainWallet;

    beforeAll(async () => {
      wallet = await MultiChainWallet.fromMnemonic(TEST_MNEMONIC);
    });

    it('should sign message and return valid signature', async () => {
      const message = new TextEncoder().encode('test message');
      const signature = await wallet.sign('aura-mainnet-1', message);
      expect(signature).toBeInstanceOf(Uint8Array);
      expect(signature.length).toBe(64); // secp256k1 compact signature
    });

    it('should produce different signatures for different chains', async () => {
      const message = new TextEncoder().encode('test message');
      const auraSignature = await wallet.sign('aura-mainnet-1', message);
      const xaiSignature = await wallet.sign('xai-mainnet-1', message);
      // XAI uses different coin type, so different key, different signature
      expect(Buffer.from(auraSignature).toString('hex'))
        .not.toBe(Buffer.from(xaiSignature).toString('hex'));
    });

    it('should throw for unknown chain when signing', async () => {
      const message = new TextEncoder().encode('test message');
      await expect(wallet.sign('unknown-chain', message))
        .rejects.toThrow('Unknown chain: unknown-chain');
    });
  });

  describe('Address Verification', () => {
    let wallet: MultiChainWallet;

    beforeAll(async () => {
      wallet = await MultiChainWallet.fromMnemonic(TEST_MNEMONIC);
    });

    it('should verify valid Aura address with correct prefix', async () => {
      const account = await wallet.getAccount('aura-mainnet-1');
      expect(MultiChainWallet.verifyAddress(account.address, 'aura-mainnet-1')).toBe(true);
    });

    it('should verify valid PAW address with correct prefix', async () => {
      const account = await wallet.getAccount('paw-mainnet-1');
      expect(MultiChainWallet.verifyAddress(account.address, 'paw-mainnet-1')).toBe(true);
    });

    it('should reject address with wrong prefix for chain', async () => {
      const auraAccount = await wallet.getAccount('aura-mainnet-1');
      expect(MultiChainWallet.verifyAddress(auraAccount.address, 'paw-mainnet-1')).toBe(false);
    });

    it('should reject address with wrong prefix', () => {
      expect(MultiChainWallet.verifyAddress('cosmos1abc...', 'aura-mainnet-1')).toBe(false);
    });

    it('should reject invalid address format', () => {
      expect(MultiChainWallet.verifyAddress('invalid', 'aura-mainnet-1')).toBe(false);
    });

    it('should return false for unknown chain', () => {
      expect(MultiChainWallet.verifyAddress('aura1abc', 'unknown-chain')).toBe(false);
    });
  });

  describe('IBC Functionality', () => {
    let wallet: MultiChainWallet;

    beforeAll(async () => {
      wallet = await MultiChainWallet.fromMnemonic(TEST_MNEMONIC);
    });

    it('should detect IBC capability between Aura and PAW', () => {
      expect(wallet.canTransferIBC('aura-mainnet-1', 'paw-mainnet-1')).toBe(true);
      expect(wallet.canTransferIBC('paw-mainnet-1', 'aura-mainnet-1')).toBe(true);
    });

    it('should not detect IBC capability with XAI (different architecture)', () => {
      expect(wallet.canTransferIBC('aura-mainnet-1', 'xai-mainnet-1')).toBe(false);
    });

    it('should return correct IBC channel', () => {
      expect(wallet.getIBCChannel('aura-mainnet-1', 'paw-mainnet-1')).toBe('channel-0');
    });

    it('should build valid IBC transfer message', async () => {
      const auraAccount = await wallet.getAccount('aura-mainnet-1');
      const pawAccount = await wallet.getAccount('paw-mainnet-1');

      const msg = wallet.buildIBCTransferMsg({
        sourceChain: 'aura-mainnet-1',
        destChain: 'paw-mainnet-1',
        sender: auraAccount.address,
        receiver: pawAccount.address,
        amount: { denom: 'uaura', amount: '1000000' },
        sourceChannel: 'channel-0',
      });

      expect(msg['@type']).toBe('/ibc.applications.transfer.v1.MsgTransfer');
      expect(msg.source_port).toBe('transfer');
      expect(msg.source_channel).toBe('channel-0');
      expect(msg.sender).toBe(auraAccount.address);
      expect(msg.receiver).toBe(pawAccount.address);
    });

    it('should throw when building IBC message for chains without channel', async () => {
      const auraAccount = await wallet.getAccount('aura-mainnet-1');
      const xaiAccount = await wallet.getAccount('xai-mainnet-1');

      expect(() => wallet.buildIBCTransferMsg({
        sourceChain: 'aura-mainnet-1',
        destChain: 'xai-mainnet-1',
        sender: auraAccount.address,
        receiver: xaiAccount.address,
        amount: { denom: 'uaura', amount: '1000000' },
      })).toThrow('No IBC channel between aura-mainnet-1 and xai-mainnet-1');
    });

    it('should use default timeout if not provided', async () => {
      const auraAccount = await wallet.getAccount('aura-mainnet-1');
      const pawAccount = await wallet.getAccount('paw-mainnet-1');

      const msg = wallet.buildIBCTransferMsg({
        sourceChain: 'aura-mainnet-1',
        destChain: 'paw-mainnet-1',
        sender: auraAccount.address,
        receiver: pawAccount.address,
        amount: { denom: 'uaura', amount: '1000000' },
      });

      expect(msg.timeout_timestamp).toBeDefined();
      expect(typeof msg.timeout_timestamp).toBe('string');
      expect(msg.memo).toBe('');
    });

    it('should use provided timeout and memo', async () => {
      const auraAccount = await wallet.getAccount('aura-mainnet-1');
      const pawAccount = await wallet.getAccount('paw-mainnet-1');
      const customTimeout = '1700000000000000000';
      const customMemo = 'test transfer';

      const msg = wallet.buildIBCTransferMsg({
        sourceChain: 'aura-mainnet-1',
        destChain: 'paw-mainnet-1',
        sender: auraAccount.address,
        receiver: pawAccount.address,
        amount: { denom: 'uaura', amount: '1000000' },
        timeoutTimestamp: customTimeout,
        memo: customMemo,
      });

      expect(msg.timeout_timestamp).toBe(customTimeout);
      expect(msg.memo).toBe(customMemo);
    });
  });
});

describe('Chain Configurations', () => {
  describe('Chain Configs', () => {
    it('should have valid Aura config', () => {
      expect(AURA_CONFIG.chainId).toBe('aura-mainnet-1');
      expect(AURA_CONFIG.bech32Prefix).toBe('aura');
      expect(AURA_CONFIG.slip44).toBe(118);
    });

    it('should have valid PAW config', () => {
      expect(PAW_CONFIG.chainId).toBe('paw-mainnet-1');
      expect(PAW_CONFIG.bech32Prefix).toBe('paw');
      expect(PAW_CONFIG.slip44).toBe(118);
    });

    it('should have valid XAI config', () => {
      expect(XAI_CONFIG.chainId).toBe('xai-mainnet-1');
      expect(XAI_CONFIG.bech32Prefix).toBe('xai');
      expect(XAI_CONFIG.slip44).toBe(22593);
    });

    it('should have same coin type for Aura and PAW (Cosmos standard)', () => {
      expect(AURA_CONFIG.slip44).toBe(PAW_CONFIG.slip44);
    });

    it('should have different coin type for XAI (EVM compatible)', () => {
      expect(XAI_CONFIG.slip44).not.toBe(AURA_CONFIG.slip44);
    });
  });

  describe('Keplr Chain Info', () => {
    it('should convert Aura config to Keplr format', () => {
      const keplrInfo = toKeplrChainInfo(AURA_CONFIG);
      expect(keplrInfo.chainId).toBe('aura-mainnet-1');
      expect(keplrInfo.bip44.coinType).toBe(118);
      expect(keplrInfo.bech32Config.bech32PrefixAccAddr).toBe('aura');
      expect(keplrInfo.currencies[0].coinDenom).toBe('AURA');
    });

    it('should include gas price steps in fee currencies', () => {
      const keplrInfo = toKeplrChainInfo(PAW_CONFIG);
      expect(keplrInfo.feeCurrencies[0].gasPriceStep.low).toBe(0.001);
      expect(keplrInfo.feeCurrencies[0].gasPriceStep.average).toBe(0.005);
    });
  });

  describe('Chain Lookup', () => {
    it('should find chain config by ID', () => {
      const config = getChainConfig('aura-testnet-1');
      expect(config).toBeDefined();
      expect(config?.chainName).toBe('Aura Testnet');
    });

    it('should return undefined for unknown chain', () => {
      expect(getChainConfig('unknown-chain')).toBeUndefined();
    });
  });

  describe('IBC Channels', () => {
    it('should find IBC channel between Aura and PAW', () => {
      expect(getIBCChannel('aura-mainnet-1', 'paw-mainnet-1')).toBe('channel-0');
    });

    it('should detect IBC capability', () => {
      expect(canIBCTransfer('aura-testnet-1', 'paw-testnet-1')).toBe(true);
      expect(canIBCTransfer('aura-mainnet-1', 'xai-mainnet-1')).toBe(false);
    });
  });
});
