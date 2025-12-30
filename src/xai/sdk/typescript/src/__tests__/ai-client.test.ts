/**
 * AIClient Unit Tests
 *
 * Comprehensive tests for AI operations including:
 * - Atomic swaps
 * - Smart contract creation and deployment
 * - Transaction optimization
 * - Blockchain and wallet analysis
 * - Node setup recommendations
 * - Liquidity alerts
 * - AI assistants listing
 * - Error handling
 */

import { AIClient } from '../clients/ai-client';
import { HTTPClient } from '../utils/http-client';
import { AIError } from '../errors';

// Mock HTTPClient
jest.mock('../utils/http-client');

const MockHTTPClient = HTTPClient as jest.MockedClass<typeof HTTPClient>;

describe('AIClient', () => {
  let aiClient: AIClient;
  let mockHttpClient: jest.Mocked<HTTPClient>;

  beforeEach(() => {
    jest.clearAllMocks();
    mockHttpClient = new MockHTTPClient({
      baseUrl: 'http://localhost:5000',
    }) as jest.Mocked<HTTPClient>;
    aiClient = new AIClient(mockHttpClient);
  });

  describe('atomicSwap', () => {
    it('should execute atomic swap', async () => {
      const mockResponse = {
        swap_id: 'swap_123',
        status: 'initiated',
        from_amount: 100,
        to_amount: 0.0025,
        estimated_time: '30 minutes',
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await aiClient.atomicSwap({
        fromCurrency: 'XAI',
        toCurrency: 'BTC',
        amount: 100,
        recipientAddress: 'bc1qxyz...',
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/personal-ai/atomic-swap', {
        from_currency: 'XAI',
        to_currency: 'BTC',
        amount: 100,
        recipient_address: 'bc1qxyz...',
      });
      expect(result).toEqual(mockResponse);
    });

    it('should wrap errors in AIError', async () => {
      mockHttpClient.post = jest.fn().mockRejectedValue(new Error('Insufficient liquidity'));

      await expect(
        aiClient.atomicSwap({
          fromCurrency: 'XAI',
          toCurrency: 'BTC',
          amount: 100,
          recipientAddress: 'bc1q...',
        })
      ).rejects.toThrow(AIError);
      await expect(
        aiClient.atomicSwap({
          fromCurrency: 'XAI',
          toCurrency: 'BTC',
          amount: 100,
          recipientAddress: 'bc1q...',
        })
      ).rejects.toThrow('Atomic swap failed');
    });
  });

  describe('createContract', () => {
    it('should create smart contract with required fields', async () => {
      const mockResponse = {
        contract_id: 'contract_456',
        code: '0x608060...',
        abi: [],
        bytecode: '0x...',
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await aiClient.createContract({
        contractType: 'token',
        parameters: { name: 'MyToken', symbol: 'MTK', supply: 1000000 },
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/personal-ai/smart-contract/create', {
        contract_type: 'token',
        parameters: { name: 'MyToken', symbol: 'MTK', supply: 1000000 },
      });
      expect(result).toEqual(mockResponse);
    });

    it('should create smart contract with description', async () => {
      const mockResponse = { contract_id: 'contract_789' };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      await aiClient.createContract({
        contractType: 'nft',
        parameters: { name: 'MyNFT', symbol: 'MNFT' },
        description: 'A custom NFT collection',
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/personal-ai/smart-contract/create', {
        contract_type: 'nft',
        parameters: { name: 'MyNFT', symbol: 'MNFT' },
        description: 'A custom NFT collection',
      });
    });

    it('should wrap errors in AIError', async () => {
      mockHttpClient.post = jest.fn().mockRejectedValue(new Error('Invalid contract type'));

      await expect(
        aiClient.createContract({
          contractType: 'invalid',
          parameters: {},
        })
      ).rejects.toThrow(AIError);
      await expect(
        aiClient.createContract({
          contractType: 'invalid',
          parameters: {},
        })
      ).rejects.toThrow('Contract creation failed');
    });
  });

  describe('deployContract', () => {
    it('should deploy contract with required fields', async () => {
      const mockResponse = {
        address: '0xdeployed123',
        transaction_hash: '0xtxhash',
        gas_used: '1500000',
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await aiClient.deployContract({
        contractCode: '0x608060405...',
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/personal-ai/smart-contract/deploy', {
        contract_code: '0x608060405...',
      });
      expect(result).toEqual(mockResponse);
    });

    it('should deploy contract with all options', async () => {
      const mockResponse = {
        address: '0xdeployed456',
        transaction_hash: '0xtxhash2',
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      await aiClient.deployContract({
        contractCode: '0x608060405...',
        constructorArgs: ['MyToken', 'MTK', 1000000],
        gasLimit: 3000000,
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/personal-ai/smart-contract/deploy', {
        contract_code: '0x608060405...',
        constructor_args: ['MyToken', 'MTK', 1000000],
        gas_limit: 3000000,
      });
    });

    it('should wrap errors in AIError', async () => {
      mockHttpClient.post = jest.fn().mockRejectedValue(new Error('Out of gas'));

      await expect(
        aiClient.deployContract({ contractCode: '0x...' })
      ).rejects.toThrow(AIError);
      await expect(
        aiClient.deployContract({ contractCode: '0x...' })
      ).rejects.toThrow('Contract deployment failed');
    });
  });

  describe('optimizeTransaction', () => {
    it('should optimize transaction', async () => {
      const mockResponse = {
        optimized_transaction: {
          to: '0x...',
          value: '1000',
          gas_limit: '21000',
          gas_price: '1000000000',
        },
        savings: '15%',
        estimated_time: '2 minutes',
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await aiClient.optimizeTransaction({
        transaction: { to: '0x...', value: '1000' },
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/personal-ai/transaction/optimize', {
        transaction: { to: '0x...', value: '1000' },
      });
      expect(result).toEqual(mockResponse);
    });

    it('should optimize transaction with goals', async () => {
      const mockResponse = { optimized: true };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      await aiClient.optimizeTransaction({
        transaction: { to: '0x...', value: '1000' },
        optimizationGoals: ['low_fee', 'fast_confirmation'],
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/personal-ai/transaction/optimize', {
        transaction: { to: '0x...', value: '1000' },
        optimization_goals: ['low_fee', 'fast_confirmation'],
      });
    });

    it('should wrap errors in AIError', async () => {
      mockHttpClient.post = jest.fn().mockRejectedValue(new Error('Invalid transaction'));

      await expect(
        aiClient.optimizeTransaction({ transaction: {} })
      ).rejects.toThrow(AIError);
      await expect(
        aiClient.optimizeTransaction({ transaction: {} })
      ).rejects.toThrow('Transaction optimization failed');
    });
  });

  describe('analyzeBlockchain', () => {
    it('should analyze blockchain with query', async () => {
      const mockResponse = {
        analysis: 'Top 10 active addresses...',
        data: [
          { address: '0x1', transactions: 1000 },
          { address: '0x2', transactions: 800 },
        ],
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await aiClient.analyzeBlockchain({
        query: 'What are the most active addresses?',
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/personal-ai/analyze', {
        query: 'What are the most active addresses?',
      });
      expect(result).toEqual(mockResponse);
    });

    it('should analyze blockchain with context', async () => {
      const mockResponse = { analysis: 'Analysis results...' };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      await aiClient.analyzeBlockchain({
        query: 'Analyze token transfers',
        context: { token: '0xtokenaddress', timeframe: '24h' },
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/personal-ai/analyze', {
        query: 'Analyze token transfers',
        context: { token: '0xtokenaddress', timeframe: '24h' },
      });
    });

    it('should wrap errors in AIError', async () => {
      mockHttpClient.post = jest.fn().mockRejectedValue(new Error('Analysis failed'));

      await expect(
        aiClient.analyzeBlockchain({ query: 'test' })
      ).rejects.toThrow(AIError);
      await expect(
        aiClient.analyzeBlockchain({ query: 'test' })
      ).rejects.toThrow('Blockchain analysis failed');
    });
  });

  describe('analyzeWallet', () => {
    it('should analyze wallet by address', async () => {
      const mockResponse = {
        riskScore: 25,
        riskLevel: 'low',
        transactionPatterns: ['regular_transfers', 'dex_swaps'],
        recommendations: ['Consider diversifying holdings'],
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await aiClient.analyzeWallet('XAI1abc...');

      expect(mockHttpClient.post).toHaveBeenCalledWith('/personal-ai/wallet/analyze', {
        address: 'XAI1abc...',
      });
      expect(result).toEqual(mockResponse);
    });

    it('should wrap errors in AIError', async () => {
      mockHttpClient.post = jest.fn().mockRejectedValue(new Error('Wallet not found'));

      await expect(aiClient.analyzeWallet('invalid')).rejects.toThrow(AIError);
      await expect(aiClient.analyzeWallet('invalid')).rejects.toThrow('Wallet analysis failed');
    });
  });

  describe('walletRecoveryAdvice', () => {
    it('should get wallet recovery advice', async () => {
      const mockResponse = {
        recoveryPossible: true,
        steps: [
          'Verify partial mnemonic words',
          'Check common word substitutions',
          'Use recovery tool',
        ],
        estimatedTime: '2-4 hours',
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await aiClient.walletRecoveryAdvice({
        mnemonicWords: ['apple', 'banana', 'cherry'],
        creationDate: '2024-01-01',
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/personal-ai/wallet/recovery', {
        mnemonicWords: ['apple', 'banana', 'cherry'],
        creationDate: '2024-01-01',
      });
      expect(result).toEqual(mockResponse);
    });

    it('should wrap errors in AIError', async () => {
      mockHttpClient.post = jest.fn().mockRejectedValue(new Error('Recovery not possible'));

      await expect(
        aiClient.walletRecoveryAdvice({ partial: 'data' })
      ).rejects.toThrow(AIError);
      await expect(
        aiClient.walletRecoveryAdvice({ partial: 'data' })
      ).rejects.toThrow('Wallet recovery advice failed');
    });
  });

  describe('nodeSetupRecommendations', () => {
    it('should get node setup recommendations without params', async () => {
      const mockResponse = {
        recommendations: ['Use SSD storage', 'Ensure stable internet'],
        minimumRequirements: { ram: '8GB', storage: '200GB' },
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await aiClient.nodeSetupRecommendations();

      expect(mockHttpClient.post).toHaveBeenCalledWith('/personal-ai/node/setup', {});
      expect(result).toEqual(mockResponse);
    });

    it('should get node setup recommendations with hardware specs', async () => {
      const mockResponse = {
        suitability: 'excellent',
        recommendations: ['Current setup is optimal'],
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      await aiClient.nodeSetupRecommendations(
        { ram: '16GB', cpu: '4 cores', storage: '500GB SSD' }
      );

      expect(mockHttpClient.post).toHaveBeenCalledWith('/personal-ai/node/setup', {
        hardware_specs: { ram: '16GB', cpu: '4 cores', storage: '500GB SSD' },
      });
    });

    it('should get node setup recommendations with use case', async () => {
      const mockResponse = {
        recommendations: ['Validator requires higher specs'],
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      await aiClient.nodeSetupRecommendations(undefined, 'validator');

      expect(mockHttpClient.post).toHaveBeenCalledWith('/personal-ai/node/setup', {
        use_case: 'validator',
      });
    });

    it('should get node setup recommendations with all params', async () => {
      const mockResponse = { recommendations: ['Good setup for validator'] };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      await aiClient.nodeSetupRecommendations(
        { ram: '32GB' },
        'validator'
      );

      expect(mockHttpClient.post).toHaveBeenCalledWith('/personal-ai/node/setup', {
        hardware_specs: { ram: '32GB' },
        use_case: 'validator',
      });
    });

    it('should wrap errors in AIError', async () => {
      mockHttpClient.post = jest.fn().mockRejectedValue(new Error('Service unavailable'));

      await expect(aiClient.nodeSetupRecommendations()).rejects.toThrow(AIError);
      await expect(aiClient.nodeSetupRecommendations()).rejects.toThrow(
        'Node setup recommendations failed'
      );
    });
  });

  describe('liquidityAlert', () => {
    it('should set up liquidity alert', async () => {
      const mockResponse = {
        alert_id: 'alert_123',
        status: 'active',
        notifications: ['email', 'webhook'],
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await aiClient.liquidityAlert({
        poolId: 'XAI-USDC',
        alertType: 'impermanent_loss',
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/personal-ai/liquidity/alert', {
        pool_id: 'XAI-USDC',
        alert_type: 'impermanent_loss',
      });
      expect(result).toEqual(mockResponse);
    });

    it('should set up liquidity alert with threshold', async () => {
      const mockResponse = { alert_id: 'alert_456' };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      await aiClient.liquidityAlert({
        poolId: 'XAI-ETH',
        alertType: 'price_change',
        threshold: 5.0,
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/personal-ai/liquidity/alert', {
        pool_id: 'XAI-ETH',
        alert_type: 'price_change',
        threshold: 5.0,
      });
    });

    it('should handle threshold of 0', async () => {
      const mockResponse = { alert_id: 'alert_789' };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      await aiClient.liquidityAlert({
        poolId: 'XAI-USDT',
        alertType: 'any_change',
        threshold: 0,
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/personal-ai/liquidity/alert', {
        pool_id: 'XAI-USDT',
        alert_type: 'any_change',
        threshold: 0,
      });
    });

    it('should wrap errors in AIError', async () => {
      mockHttpClient.post = jest.fn().mockRejectedValue(new Error('Pool not found'));

      await expect(
        aiClient.liquidityAlert({ poolId: 'invalid', alertType: 'test' })
      ).rejects.toThrow(AIError);
      await expect(
        aiClient.liquidityAlert({ poolId: 'invalid', alertType: 'test' })
      ).rejects.toThrow('Liquidity alert setup failed');
    });
  });

  describe('listAssistants', () => {
    it('should list available AI assistants', async () => {
      const mockResponse = {
        assistants: [
          {
            id: 'trading-assistant',
            name: 'Trading Assistant',
            description: 'Helps with trading decisions',
            capabilities: ['market_analysis', 'trade_execution'],
          },
          {
            id: 'security-assistant',
            name: 'Security Assistant',
            description: 'Helps with security analysis',
            capabilities: ['vulnerability_scan', 'audit_review'],
          },
        ],
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await aiClient.listAssistants();

      expect(mockHttpClient.get).toHaveBeenCalledWith('/personal-ai/assistants');
      expect(result).toHaveLength(2);
      expect(result[0].id).toBe('trading-assistant');
    });

    it('should handle empty assistants list', async () => {
      const mockResponse = { assistants: null };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await aiClient.listAssistants();

      expect(result).toEqual([]);
    });

    it('should wrap errors in AIError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Service down'));

      await expect(aiClient.listAssistants()).rejects.toThrow(AIError);
      await expect(aiClient.listAssistants()).rejects.toThrow('Failed to list assistants');
    });
  });
});
