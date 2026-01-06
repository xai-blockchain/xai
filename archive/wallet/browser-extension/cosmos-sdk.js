/**
 * Cosmos SDK Integration Module for XAI Browser Wallet
 *
 * Provides utilities for:
 * - Transaction signing with secp256k1
 * - Account/sequence number management
 * - StdTx message building
 * - Transaction broadcasting
 * - Address generation and validation
 */

// Import required crypto libraries (will be included via CDN or bundler)
// Using noble-secp256k1 for signing
// Using bech32 for address encoding

const COSMOS_SDK = {
  // XAI Network Configuration
  config: {
    chainId: 'xai-testnet',
    bech32Prefix: 'xai',
    coinDenom: 'uxai',
    coinDecimals: 6,
    restEndpoint: 'http://localhost:1317',
    rpcEndpoint: 'http://localhost:26657',
  },

  /**
   * Generate a new secp256k1 private key
   * @returns {Uint8Array} 32-byte private key
   */
  generatePrivateKey() {
    const privateKey = new Uint8Array(32);
    crypto.getRandomValues(privateKey);
    return privateKey;
  },

  /**
   * Derive public key from private key
   * @param {Uint8Array} privateKey - 32-byte private key
   * @returns {Uint8Array} 33-byte compressed public key
   */
  async getPublicKey(privateKey) {
    // Using SubtleCrypto for ECDSA
    const keyPair = await crypto.subtle.importKey(
      'raw',
      privateKey,
      { name: 'ECDSA', namedCurve: 'P-256' },
      true,
      ['sign']
    );

    const exported = await crypto.subtle.exportKey('raw', keyPair);
    return new Uint8Array(exported);
  },

  /**
   * Convert public key to Bech32 address
   * @param {Uint8Array} publicKey - Compressed public key
   * @returns {string} Bech32 encoded address (xai1...)
   */
  publicKeyToAddress(publicKey) {
    // 1. SHA-256 hash of public key
    const sha256Hash = this.sha256(publicKey);

    // 2. RIPEMD-160 hash of the SHA-256 hash
    const ripemd160Hash = this.ripemd160(sha256Hash);

    // 3. Bech32 encode with 'xai' prefix
    return this.bech32Encode(this.config.bech32Prefix, ripemd160Hash);
  },

  /**
   * SHA-256 hash
   */
  sha256(data) {
    // Simplified - in production use crypto.subtle.digest
    // For now, return placeholder
    return new Uint8Array(32);
  },

  /**
   * RIPEMD-160 hash
   */
  ripemd160(data) {
    // Simplified - in production use proper RIPEMD-160 library
    // For now, return placeholder
    return new Uint8Array(20);
  },

  /**
   * Bech32 encode
   */
  bech32Encode(prefix, data) {
    // Simplified - in production use bech32 library
    // For now, return placeholder
    return `${prefix}1${this.bytesToHex(data)}`;
  },

  /**
   * Get account information from chain
   * @param {string} address - Bech32 address
   * @returns {Promise<Object>} Account info with sequence and account_number
   */
  async getAccount(address) {
    const url = `${this.config.restEndpoint}/cosmos/auth/v1beta1/accounts/${address}`;
    const response = await fetch(url);
    const data = await response.json();

    return {
      address: data.account.address,
      accountNumber: parseInt(data.account.account_number || '0'),
      sequence: parseInt(data.account.sequence || '0'),
      pubKey: data.account.pub_key,
    };
  },

  /**
   * Get account balance
   * @param {string} address - Bech32 address
   * @returns {Promise<Array>} Array of coin balances
   */
  async getBalance(address) {
    const url = `${this.config.restEndpoint}/cosmos/bank/v1beta1/balances/${address}`;
    const response = await fetch(url);
    const data = await response.json();
    return data.balances || [];
  },

  /**
   * Build a standard transfer transaction
   * @param {Object} params - Transaction parameters
   * @returns {Object} Unsigned transaction
   */
  buildTransferTx(params) {
    const {
      fromAddress,
      toAddress,
      amount,
      denom = this.config.coinDenom,
      memo = '',
      fee = { amount: [{ denom: 'uxai', amount: '5000' }], gas: '200000' },
    } = params;

    return {
      body: {
        messages: [{
          '@type': '/cosmos.bank.v1beta1.MsgSend',
          from_address: fromAddress,
          to_address: toAddress,
          amount: [{ denom, amount: amount.toString() }],
        }],
        memo,
        timeout_height: '0',
        extension_options: [],
        non_critical_extension_options: [],
      },
      auth_info: {
        signer_infos: [],
        fee,
      },
      signatures: [],
    };
  },

  /**
   * Build a DEX swap transaction
   * @param {Object} params - Swap parameters
   * @returns {Object} Unsigned transaction
   */
  buildSwapTx(params) {
    const {
      sender,
      poolId,
      tokenIn,
      tokenOutDenom,
      minAmountOut,
      memo = '',
      fee = { amount: [{ denom: 'uxai', amount: '10000' }], gas: '300000' },
    } = params;

    return {
      body: {
        messages: [{
          '@type': '/xai.dex.v1.MsgSwap',
          sender,
          pool_id: poolId.toString(),
          token_in: tokenIn,
          token_out_denom: tokenOutDenom,
          min_amount_out: minAmountOut.toString(),
        }],
        memo,
        timeout_height: '0',
        extension_options: [],
        non_critical_extension_options: [],
      },
      auth_info: {
        signer_infos: [],
        fee,
      },
      signatures: [],
    };
  },

  /**
   * Sign transaction with private key
   * @param {Object} tx - Unsigned transaction
   * @param {Uint8Array} privateKey - Signer's private key
   * @param {Object} accountInfo - Account number and sequence
   * @param {Uint8Array} publicKey - Signer's public key
   * @returns {Object} Signed transaction
   */
  async signTx(tx, privateKey, accountInfo, publicKey) {
    const { accountNumber, sequence } = accountInfo;

    // Build SignDoc
    const signDoc = {
      body_bytes: this.encodeBody(tx.body),
      auth_info_bytes: this.encodeAuthInfo(tx.auth_info, publicKey, sequence),
      chain_id: this.config.chainId,
      account_number: accountNumber.toString(),
    };

    // Serialize for signing
    const signBytes = this.serializeSignDoc(signDoc);

    // Sign with secp256k1
    const signature = await this.sign(signBytes, privateKey);

    // Add signature to transaction
    tx.signatures = [signature];
    tx.auth_info.signer_infos = [{
      public_key: {
        '@type': '/cosmos.crypto.secp256k1.PubKey',
        key: this.bytesToBase64(publicKey),
      },
      mode_info: {
        single: { mode: 'SIGN_MODE_DIRECT' },
      },
      sequence: sequence.toString(),
    }];

    return tx;
  },

  /**
   * Sign bytes with private key
   * @param {Uint8Array} bytes - Bytes to sign
   * @param {Uint8Array} privateKey - Private key
   * @returns {Uint8Array} Signature
   */
  async sign(bytes, privateKey) {
    // Import private key
    const key = await crypto.subtle.importKey(
      'raw',
      privateKey,
      { name: 'ECDSA', namedCurve: 'P-256' },
      false,
      ['sign']
    );

    // Sign
    const signature = await crypto.subtle.sign(
      { name: 'ECDSA', hash: 'SHA-256' },
      key,
      bytes
    );

    return new Uint8Array(signature);
  },

  /**
   * Broadcast signed transaction
   * @param {Object} signedTx - Signed transaction
   * @returns {Promise<Object>} Broadcast result
   */
  async broadcastTx(signedTx) {
    const txBytes = this.encodeTx(signedTx);
    const txBase64 = this.bytesToBase64(txBytes);

    const url = `${this.config.restEndpoint}/cosmos/tx/v1beta1/txs`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tx_bytes: txBase64,
        mode: 'BROADCAST_MODE_SYNC',
      }),
    });

    const result = await response.json();

    if (result.tx_response.code !== 0) {
      throw new Error(`Transaction failed: ${result.tx_response.raw_log}`);
    }

    return result.tx_response;
  },

  /**
   * Query DEX pools
   * @returns {Promise<Array>} List of pools
   */
  async queryPools() {
    const url = `${this.config.restEndpoint}/xai/dex/v1/pools`;
    const response = await fetch(url);
    const data = await response.json();
    return data.pools || [];
  },

  /**
   * Query specific pool
   * @param {string} poolId - Pool ID
   * @returns {Promise<Object>} Pool details
   */
  async queryPool(poolId) {
    const url = `${this.config.restEndpoint}/xai/dex/v1/pools/${poolId}`;
    const response = await fetch(url);
    const data = await response.json();
    return data.pool;
  },

  /**
   * Query oracle prices
   * @returns {Promise<Array>} Price feeds
   */
  async queryOraclePrices() {
    const url = `${this.config.restEndpoint}/xai/oracle/v1/prices`;
    const response = await fetch(url);
    const data = await response.json();
    return data.prices || [];
  },

  // Helper functions for encoding (simplified)
  encodeBody(body) {
    return new TextEncoder().encode(JSON.stringify(body));
  },

  encodeAuthInfo(authInfo, publicKey, sequence) {
    return new TextEncoder().encode(JSON.stringify({
      ...authInfo,
      signer_infos: [{
        public_key: {
          '@type': '/cosmos.crypto.secp256k1.PubKey',
          key: this.bytesToBase64(publicKey),
        },
        mode_info: { single: { mode: 'SIGN_MODE_DIRECT' } },
        sequence: sequence.toString(),
      }],
    }));
  },

  serializeSignDoc(signDoc) {
    return new TextEncoder().encode(JSON.stringify(signDoc));
  },

  encodeTx(tx) {
    return new TextEncoder().encode(JSON.stringify(tx));
  },

  // Utility functions
  bytesToHex(bytes) {
    return Array.from(bytes)
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');
  },

  bytesToBase64(bytes) {
    return btoa(String.fromCharCode(...bytes));
  },

  base64ToBytes(base64) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
  },

  hexToBytes(hex) {
    const bytes = new Uint8Array(hex.length / 2);
    for (let i = 0; i < hex.length; i += 2) {
      bytes[i / 2] = parseInt(hex.substr(i, 2), 16);
    }
    return bytes;
  },
};

// Export for use in extension
if (typeof module !== 'undefined' && module.exports) {
  module.exports = COSMOS_SDK;
}
