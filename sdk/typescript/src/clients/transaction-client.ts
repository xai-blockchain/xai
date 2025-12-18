/**
 * Transaction Client
 * Handles transaction building, signing, and broadcasting
 */

import { HTTPClient } from '../utils/http-client';
import { Wallet } from './wallet-client';
import { hash256 } from '../utils/crypto';
import { TransactionError } from '../errors';
import {
  Transaction,
  UnsignedTransaction,
  SignedTransaction,
  BroadcastResult,
  FeeEstimate,
} from '../types';

export class TransactionBuilder {
  private tx: UnsignedTransaction;

  constructor(sender: string, recipient: string, amount: number) {
    this.tx = {
      sender,
      recipient,
      amount,
      fee: 0,
      tx_type: 'normal',
    };
  }

  public setFee(fee: number): this {
    if (fee < 0) {
      throw new TransactionError('Fee must be non-negative');
    }
    this.tx.fee = fee;
    return this;
  }

  public setNonce(nonce: number): this {
    if (nonce < 0) {
      throw new TransactionError('Nonce must be non-negative');
    }
    this.tx.nonce = nonce;
    return this;
  }

  public setType(type: string): this {
    this.tx.tx_type = type;
    return this;
  }

  public setMetadata(metadata: Record<string, any>): this {
    this.tx.metadata = metadata;
    return this;
  }

  public enableRBF(replacesTxid?: string): this {
    this.tx.rbf_enabled = true;
    if (replacesTxid) {
      this.tx.replaces_txid = replacesTxid;
    }
    return this;
  }

  public setGasSponsor(sponsor: string): this {
    this.tx.gas_sponsor = sponsor;
    return this;
  }

  public async sign(wallet: Wallet): Promise<SignedTransaction> {
    const timestamp = Date.now() / 1000;
    
    // Calculate transaction hash
    const txData = {
      chain_context: 'mainnet',
      sender: this.tx.sender,
      recipient: this.tx.recipient,
      amount: this.tx.amount,
      fee: this.tx.fee,
      timestamp,
      nonce: this.tx.nonce,
      inputs: this.tx.inputs || [],
      outputs: this.tx.outputs || [],
    };

    const txHash = hash256(JSON.stringify(txData));
    const signature = await wallet.sign(txHash);

    return {
      ...this.tx,
      txid: txHash,
      timestamp,
      signature,
      public_key: wallet.publicKey,
    } as SignedTransaction;
  }

  public build(): UnsignedTransaction {
    return { ...this.tx };
  }
}

export class TransactionClient {
  constructor(private httpClient: HTTPClient) {}

  /**
   * Create a new transaction builder
   */
  public build(sender: string, recipient: string, amount: number): TransactionBuilder {
    return new TransactionBuilder(sender, recipient, amount);
  }

  /**
   * Get a transaction by ID
   */
  public async getTransaction(txid: string): Promise<Transaction> {
    return this.httpClient.get<Transaction>(`/transaction/${txid}`);
  }

  /**
   * Get pending transactions
   */
  public async getPending(limit: number = 50, offset: number = 0): Promise<{
    count: number;
    limit: number;
    offset: number;
    transactions: Transaction[];
  }> {
    return this.httpClient.get('/transactions', {
      params: { limit, offset },
    });
  }

  /**
   * Broadcast a signed transaction
   */
  public async broadcast(transaction: SignedTransaction): Promise<BroadcastResult> {
    try {
      const response = await this.httpClient.post<{ txid: string; message?: string }>(
        '/transaction/send',
        {
          sender: transaction.sender,
          recipient: transaction.recipient,
          amount: transaction.amount,
          fee: transaction.fee,
          signature: transaction.signature,
          public_key: transaction.public_key,
          nonce: transaction.nonce,
          tx_type: transaction.tx_type,
          metadata: transaction.metadata,
          rbf_enabled: transaction.rbf_enabled,
          replaces_txid: transaction.replaces_txid,
          gas_sponsor: transaction.gas_sponsor,
        }
      );

      return {
        success: true,
        txid: response.txid,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Estimate transaction fee
   */
  public async estimateFee(): Promise<FeeEstimate> {
    return this.httpClient.get<FeeEstimate>('/fee/estimate');
  }

  /**
   * Send a transaction (build, sign, and broadcast)
   */
  public async send(
    wallet: Wallet,
    recipient: string,
    amount: number,
    options?: {
      fee?: number;
      nonce?: number;
      metadata?: Record<string, any>;
    }
  ): Promise<BroadcastResult> {
    // Get nonce if not provided
    let nonce = options?.nonce;
    if (nonce === undefined) {
      const nonceInfo = await this.httpClient.get<{ next_nonce: number }>(
        `/address/${wallet.address}/nonce`
      );
      nonce = nonceInfo.next_nonce;
    }

    // Get fee estimate if not provided
    let fee = options?.fee;
    if (fee === undefined) {
      const feeEstimate = await this.estimateFee();
      fee = feeEstimate.recommended;
    }

    // Build and sign transaction
    const builder = this.build(wallet.address, recipient, amount)
      .setFee(fee)
      .setNonce(nonce);

    if (options?.metadata) {
      builder.setMetadata(options.metadata);
    }

    const signedTx = await builder.sign(wallet);

    // Broadcast
    return this.broadcast(signedTx);
  }
}
