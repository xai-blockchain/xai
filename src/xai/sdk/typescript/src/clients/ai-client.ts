/**
 * AI Client for XAI SDK
 *
 * Handles all AI-related operations including:
 * - Personal AI assistant operations
 * - Smart contract creation and deployment
 * - Transaction optimization
 * - Blockchain and wallet analysis
 * - Node setup recommendations
 */

import { HTTPClient } from '../utils/http-client';
import { AIError } from '../errors';

/**
 * AI atomic swap parameters
 */
export interface AtomicSwapParams {
  fromCurrency: string;
  toCurrency: string;
  amount: number;
  recipientAddress: string;
}

/**
 * Smart contract creation parameters
 */
export interface CreateContractParams {
  contractType: string;
  parameters: Record<string, unknown>;
  description?: string;
}

/**
 * Smart contract deployment parameters
 */
export interface DeployContractParams {
  contractCode: string;
  constructorArgs?: unknown[];
  gasLimit?: number;
}

/**
 * Transaction optimization parameters
 */
export interface OptimizeTransactionParams {
  transaction: Record<string, unknown>;
  optimizationGoals?: string[];
}

/**
 * Blockchain analysis parameters
 */
export interface AnalyzeBlockchainParams {
  query: string;
  context?: Record<string, unknown>;
}

/**
 * Liquidity alert parameters
 */
export interface LiquidityAlertParams {
  poolId: string;
  alertType: string;
  threshold?: number;
}

/**
 * AI stream parameters
 */
export interface StreamParams {
  prompt: string;
  assistantId?: string;
  context?: Record<string, unknown>;
}

/**
 * AI assistant information
 */
export interface AIAssistant {
  id: string;
  name: string;
  description: string;
  capabilities: string[];
}

/**
 * Client for AI operations on XAI blockchain
 */
export class AIClient {
  constructor(private httpClient: HTTPClient) {}

  /**
   * Execute atomic swap with AI assistance
   *
   * @param params - Swap parameters
   * @returns Swap execution result
   *
   * @example
   * ```typescript
   * const result = await client.ai.atomicSwap({
   *   fromCurrency: 'XAI',
   *   toCurrency: 'BTC',
   *   amount: 100,
   *   recipientAddress: 'bc1q...'
   * });
   * ```
   */
  async atomicSwap(params: AtomicSwapParams): Promise<Record<string, unknown>> {
    try {
      return await this.httpClient.post('/personal-ai/atomic-swap', {
        from_currency: params.fromCurrency,
        to_currency: params.toCurrency,
        amount: params.amount,
        recipient_address: params.recipientAddress,
      });
    } catch (error) {
      throw new AIError(`Atomic swap failed: ${error}`);
    }
  }

  /**
   * Create smart contract with AI assistance
   *
   * @param params - Contract creation parameters
   * @returns Created contract details
   *
   * @example
   * ```typescript
   * const contract = await client.ai.createContract({
   *   contractType: 'token',
   *   parameters: { name: 'MyToken', symbol: 'MTK', supply: 1000000 },
   *   description: 'A custom ERC20 token'
   * });
   * ```
   */
  async createContract(params: CreateContractParams): Promise<Record<string, unknown>> {
    try {
      const payload: Record<string, unknown> = {
        contract_type: params.contractType,
        parameters: params.parameters,
      };
      if (params.description) {
        payload.description = params.description;
      }
      return await this.httpClient.post('/personal-ai/smart-contract/create', payload);
    } catch (error) {
      throw new AIError(`Contract creation failed: ${error}`);
    }
  }

  /**
   * Deploy smart contract with AI optimization
   *
   * @param params - Deployment parameters
   * @returns Deployment result with contract address
   *
   * @example
   * ```typescript
   * const deployment = await client.ai.deployContract({
   *   contractCode: '0x608060...',
   *   constructorArgs: ['MyToken', 'MTK'],
   *   gasLimit: 3000000
   * });
   * console.log('Contract deployed at:', deployment.address);
   * ```
   */
  async deployContract(params: DeployContractParams): Promise<Record<string, unknown>> {
    try {
      const payload: Record<string, unknown> = {
        contract_code: params.contractCode,
      };
      if (params.constructorArgs) {
        payload.constructor_args = params.constructorArgs;
      }
      if (params.gasLimit) {
        payload.gas_limit = params.gasLimit;
      }
      return await this.httpClient.post('/personal-ai/smart-contract/deploy', payload);
    } catch (error) {
      throw new AIError(`Contract deployment failed: ${error}`);
    }
  }

  /**
   * Optimize transaction with AI
   *
   * @param params - Optimization parameters
   * @returns Optimized transaction details
   *
   * @example
   * ```typescript
   * const optimized = await client.ai.optimizeTransaction({
   *   transaction: { to: '0x...', value: '1000' },
   *   optimizationGoals: ['low_fee', 'fast_confirmation']
   * });
   * ```
   */
  async optimizeTransaction(params: OptimizeTransactionParams): Promise<Record<string, unknown>> {
    try {
      const payload: Record<string, unknown> = {
        transaction: params.transaction,
      };
      if (params.optimizationGoals) {
        payload.optimization_goals = params.optimizationGoals;
      }
      return await this.httpClient.post('/personal-ai/transaction/optimize', payload);
    } catch (error) {
      throw new AIError(`Transaction optimization failed: ${error}`);
    }
  }

  /**
   * Analyze blockchain with AI
   *
   * @param params - Analysis parameters
   * @returns Analysis results
   *
   * @example
   * ```typescript
   * const analysis = await client.ai.analyzeBlockchain({
   *   query: 'What are the most active addresses in the last 24 hours?'
   * });
   * ```
   */
  async analyzeBlockchain(params: AnalyzeBlockchainParams): Promise<Record<string, unknown>> {
    try {
      const payload: Record<string, unknown> = { query: params.query };
      if (params.context) {
        payload.context = params.context;
      }
      return await this.httpClient.post('/personal-ai/analyze', payload);
    } catch (error) {
      throw new AIError(`Blockchain analysis failed: ${error}`);
    }
  }

  /**
   * Analyze wallet with AI
   *
   * @param address - Wallet address to analyze
   * @returns Wallet analysis results
   *
   * @example
   * ```typescript
   * const analysis = await client.ai.analyzeWallet('XAI1abc...');
   * console.log('Risk score:', analysis.riskScore);
   * ```
   */
  async analyzeWallet(address: string): Promise<Record<string, unknown>> {
    try {
      return await this.httpClient.post('/personal-ai/wallet/analyze', { address });
    } catch (error) {
      throw new AIError(`Wallet analysis failed: ${error}`);
    }
  }

  /**
   * Get wallet recovery advice from AI
   *
   * @param partialInfo - Partial wallet information
   * @returns Recovery recommendations
   *
   * @example
   * ```typescript
   * const advice = await client.ai.walletRecoveryAdvice({
   *   mnemonicWords: ['apple', 'banana', '...'],
   *   creationDate: '2024-01-01'
   * });
   * ```
   */
  async walletRecoveryAdvice(partialInfo: Record<string, unknown>): Promise<Record<string, unknown>> {
    try {
      return await this.httpClient.post('/personal-ai/wallet/recovery', partialInfo);
    } catch (error) {
      throw new AIError(`Wallet recovery advice failed: ${error}`);
    }
  }

  /**
   * Get node setup recommendations from AI
   *
   * @param hardwareSpecs - Optional hardware specifications
   * @param useCase - Optional use case
   * @returns Setup recommendations
   *
   * @example
   * ```typescript
   * const recommendations = await client.ai.nodeSetupRecommendations(
   *   { ram: '16GB', cpu: '4 cores', storage: '500GB SSD' },
   *   'validator'
   * );
   * ```
   */
  async nodeSetupRecommendations(
    hardwareSpecs?: Record<string, unknown>,
    useCase?: string
  ): Promise<Record<string, unknown>> {
    try {
      const payload: Record<string, unknown> = {};
      if (hardwareSpecs) {
        payload.hardware_specs = hardwareSpecs;
      }
      if (useCase) {
        payload.use_case = useCase;
      }
      return await this.httpClient.post('/personal-ai/node/setup', payload);
    } catch (error) {
      throw new AIError(`Node setup recommendations failed: ${error}`);
    }
  }

  /**
   * Set up liquidity pool alert with AI monitoring
   *
   * @param params - Alert parameters
   * @returns Alert configuration result
   *
   * @example
   * ```typescript
   * const alert = await client.ai.liquidityAlert({
   *   poolId: 'XAI-USDC',
   *   alertType: 'impermanent_loss',
   *   threshold: 5.0
   * });
   * ```
   */
  async liquidityAlert(params: LiquidityAlertParams): Promise<Record<string, unknown>> {
    try {
      const payload: Record<string, unknown> = {
        pool_id: params.poolId,
        alert_type: params.alertType,
      };
      if (params.threshold !== undefined) {
        payload.threshold = params.threshold;
      }
      return await this.httpClient.post('/personal-ai/liquidity/alert', payload);
    } catch (error) {
      throw new AIError(`Liquidity alert setup failed: ${error}`);
    }
  }

  /**
   * List available AI assistants
   *
   * @returns List of available AI assistants
   *
   * @example
   * ```typescript
   * const assistants = await client.ai.listAssistants();
   * assistants.forEach(a => console.log(a.name, a.capabilities));
   * ```
   */
  async listAssistants(): Promise<AIAssistant[]> {
    try {
      const response = await this.httpClient.get<{ assistants: AIAssistant[] }>('/personal-ai/assistants');
      return response.assistants || [];
    } catch (error) {
      throw new AIError(`Failed to list assistants: ${error}`);
    }
  }
}
