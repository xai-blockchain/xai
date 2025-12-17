/**
 * XAI Hardware Wallet Manager
 *
 * Unified interface for managing Ledger and Trezor hardware wallets in the XAI browser extension.
 * Provides wallet detection, connection management, transaction signing, and event notifications.
 *
 * Features:
 * - Automatic wallet type detection
 * - Unified API for both Ledger and Trezor
 * - Connection state management with reconnection
 * - Event-driven architecture for UI updates
 * - Transaction formatting and signature handling
 * - BIP32 path configuration
 * - Graceful error handling with user-friendly messages
 *
 * @module hw-manager
 */

/**
 * Hardware wallet connection information.
 *
 * @typedef {Object} WalletInfo
 * @property {string} type - Wallet type ('ledger' or 'trezor')
 * @property {string} address - XAI address derived from wallet
 * @property {string} publicKey - Public key (hex, 64 bytes)
 * @property {string} bip32Path - BIP32 derivation path used
 * @property {number} connectedAt - Connection timestamp (ms)
 */

/**
 * Transaction payload for signing.
 *
 * @typedef {Object} TransactionPayload
 * @property {string} sender - Sender XAI address
 * @property {string} recipient - Recipient XAI address
 * @property {number|string} amount - Amount to send (XAI)
 * @property {number|string} fee - Transaction fee (XAI)
 * @property {number} nonce - Transaction nonce
 * @property {string} [memo] - Optional transaction memo
 * @property {string} [network] - Network name (mainnet/testnet)
 * @property {number} [chainId] - Chain ID (default: 22593)
 */

/**
 * Unsigned transaction object (XAI format).
 *
 * @typedef {Object} UnsignedTransaction
 * @property {string} version - Format version
 * @property {string} tx_type - Transaction type
 * @property {string} sender - Sender address
 * @property {string} recipient - Recipient address
 * @property {number} amount - Transfer amount
 * @property {number} fee - Transaction fee
 * @property {number} nonce - Transaction nonce
 * @property {string} memo - Memo/note
 * @property {string} network - Network identifier
 * @property {number} created_at - Creation timestamp
 */

/**
 * Signed transaction object with signature.
 *
 * @typedef {Object} SignedTransaction
 * @property {UnsignedTransaction} transaction - Original unsigned transaction
 * @property {string} signature - Signature hex string (128 chars = 64 bytes)
 * @property {string} publicKey - Signer's public key
 * @property {string} payloadHash - Hash of signed payload
 * @property {number} signedAt - Signature timestamp
 */

/**
 * Unified Hardware Wallet Manager.
 * Manages connection, signing, and events for both Ledger and Trezor devices.
 *
 * @class HardwareWalletManager
 */
class HardwareWalletManager {
    /**
     * Create a hardware wallet manager instance.
     *
     * @param {Object} [options] - Configuration options
     * @param {string} [options.bip32Path="m/44'/22593'/0'/0/0"] - Default BIP32 derivation path
     * @param {boolean} [options.autoReconnect=false] - Attempt to reconnect on disconnect
     * @param {number} [options.reconnectDelay=3000] - Delay between reconnection attempts (ms)
     */
    constructor(options = {}) {
        this.bip32Path = options.bip32Path || "m/44'/22593'/0'/0/0";
        this.autoReconnect = options.autoReconnect || false;
        this.reconnectDelay = options.reconnectDelay || 3000;

        this.currentWallet = null;
        this.currentWalletType = null;
        this.walletInfo = null;
        this.eventListeners = {};
        this.reconnectTimer = null;
    }

    /**
     * Detect which hardware wallet types are supported in this browser.
     *
     * @static
     * @returns {string[]} Array of supported wallet types ('ledger', 'trezor')
     */
    static getSupportedWallets() {
        const supported = [];

        // Check for Ledger support (WebHID or WebUSB)
        if (typeof navigator !== 'undefined') {
            if ('hid' in navigator || 'usb' in navigator) {
                supported.push('ledger');
            }

            // Trezor works via Trezor Connect (always available)
            supported.push('trezor');
        }

        return supported;
    }

    /**
     * Get user-friendly name for wallet type.
     *
     * @static
     * @param {string} type - Wallet type ('ledger' or 'trezor')
     * @returns {string} Human-readable name
     */
    static getWalletName(type) {
        const names = {
            ledger: 'Ledger',
            trezor: 'Trezor',
        };
        return names[type] || type;
    }

    /**
     * Connect to a hardware wallet.
     *
     * @param {string} walletType - Wallet type ('ledger' or 'trezor')
     * @param {Object} [options] - Connection options
     * @param {string} [options.bip32Path] - Override default BIP32 path
     * @returns {Promise<WalletInfo>} Wallet connection information
     * @throws {Error} If connection fails or wallet type unsupported
     */
    async connect(walletType, options = {}) {
        // Validate wallet type
        const supportedWallets = HardwareWalletManager.getSupportedWallets();
        if (!supportedWallets.includes(walletType)) {
            throw new Error(
                `Wallet type '${walletType}' not supported. ` +
                `Available: ${supportedWallets.join(', ')}`
            );
        }

        // Disconnect existing wallet if any
        if (this.currentWallet) {
            await this.disconnect();
        }

        const bip32Path = options.bip32Path || this.bip32Path;

        try {
            this._emit('connecting', { type: walletType });

            // Create wallet instance
            if (walletType === 'ledger') {
                // Import Ledger module
                if (typeof LedgerHardwareWallet === 'undefined') {
                    throw new Error('Ledger module not loaded. Include ledger-hw.js first.');
                }
                this.currentWallet = new LedgerHardwareWallet({ bip32Path });
            } else if (walletType === 'trezor') {
                // Import Trezor module
                if (typeof TrezorHardwareWallet === 'undefined') {
                    throw new Error('Trezor module not loaded. Include trezor-hw.js first.');
                }
                this.currentWallet = new TrezorHardwareWallet({ bip32Path });
            } else {
                throw new Error(`Unknown wallet type: ${walletType}`);
            }

            // Connect to device
            await this.currentWallet.connect();

            // Get address and public key
            const publicKey = await this.currentWallet.getPublicKey(false);
            const address = await this.currentWallet.getAddress(false);

            // Store wallet info
            this.currentWalletType = walletType;
            this.walletInfo = {
                type: walletType,
                address: address,
                publicKey: publicKey,
                bip32Path: bip32Path,
                connectedAt: Date.now(),
            };

            this._emit('connected', this.walletInfo);

            return this.walletInfo;
        } catch (err) {
            this.currentWallet = null;
            this.currentWalletType = null;
            this.walletInfo = null;

            const error = this._formatError(err, walletType);
            this._emit('error', { error: error.message, walletType });

            throw error;
        }
    }

    /**
     * Disconnect from the current hardware wallet.
     *
     * @returns {Promise<void>}
     */
    async disconnect() {
        // Clear reconnect timer
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }

        if (!this.currentWallet) {
            return;
        }

        try {
            await this.currentWallet.disconnect();
        } catch (err) {
            console.warn('Error disconnecting wallet:', err);
        } finally {
            const walletType = this.currentWalletType;

            this.currentWallet = null;
            this.currentWalletType = null;
            this.walletInfo = null;

            this._emit('disconnected', { type: walletType });
        }
    }

    /**
     * Check if a hardware wallet is currently connected.
     *
     * @returns {boolean} True if connected
     */
    isConnected() {
        return this.currentWallet !== null && this.currentWallet.isConnected();
    }

    /**
     * Get information about the currently connected wallet.
     *
     * @returns {WalletInfo|null} Wallet info or null if not connected
     */
    getConnectedWallet() {
        return this.walletInfo;
    }

    /**
     * Get the XAI address from the connected wallet.
     *
     * @param {boolean} [showOnDevice=false] - Display address on device for verification
     * @returns {Promise<string>} XAI address
     * @throws {Error} If not connected
     */
    async getAddress(showOnDevice = false) {
        this._requireConnection();

        try {
            const address = await this.currentWallet.getAddress(showOnDevice);

            if (this.walletInfo) {
                this.walletInfo.address = address;
            }

            return address;
        } catch (err) {
            throw this._formatError(err, this.currentWalletType);
        }
    }

    /**
     * Sign a transaction with the connected hardware wallet.
     *
     * @param {TransactionPayload} txPayload - Transaction data to sign
     * @returns {Promise<SignedTransaction>} Signed transaction with signature
     * @throws {Error} If not connected or signing fails
     */
    async signTransaction(txPayload) {
        this._requireConnection();

        this._emit('signing', { type: 'transaction', payload: txPayload });

        try {
            // Build unsigned transaction
            const unsignedTx = this.buildUnsignedTransaction(txPayload);

            // Get payload bytes for signing
            const payloadBytes = unsignedTx.payloadBytes;

            // Sign with hardware wallet
            let signature;

            if (this.currentWalletType === 'ledger') {
                // Ledger returns Uint8Array directly
                signature = await this.currentWallet.signTransaction(payloadBytes);
            } else if (this.currentWalletType === 'trezor') {
                // Trezor may need EIP-155 formatted transaction
                // For raw payload, use signMessage or adapt to Ethereum format
                const ethTx = this._convertToEthereumTx(txPayload);
                const result = await this.currentWallet.signTransaction(ethTx);
                signature = result.signature;
            } else {
                throw new Error('Unknown wallet type');
            }

            // Convert signature to hex string
            const signatureHex = Array.from(signature)
                .map(b => b.toString(16).padStart(2, '0'))
                .join('');

            // Create signed transaction
            const signedTx = await this.combineSignature(
                unsignedTx,
                signatureHex,
                this.walletInfo.publicKey
            );

            this._emit('signed', { type: 'transaction', signature: signatureHex });

            return signedTx;
        } catch (err) {
            const error = this._formatError(err, this.currentWalletType);
            this._emit('error', { error: error.message, operation: 'sign_transaction' });
            throw error;
        }
    }

    /**
     * Sign an arbitrary message with the connected hardware wallet.
     *
     * @param {string|Uint8Array} message - Message to sign
     * @returns {Promise<string>} Signature as hex string
     * @throws {Error} If not connected or signing fails
     */
    async signMessage(message) {
        this._requireConnection();

        this._emit('signing', { type: 'message', message });

        try {
            // Convert message to bytes if string
            const messageBytes = typeof message === 'string'
                ? new TextEncoder().encode(message)
                : message;

            // Sign with hardware wallet
            const signature = await this.currentWallet.signMessage(messageBytes);

            // Convert to hex string
            const signatureHex = Array.from(signature)
                .map(b => b.toString(16).padStart(2, '0'))
                .join('');

            this._emit('signed', { type: 'message', signature: signatureHex });

            return signatureHex;
        } catch (err) {
            const error = this._formatError(err, this.currentWalletType);
            this._emit('error', { error: error.message, operation: 'sign_message' });
            throw error;
        }
    }

    /**
     * Build an unsigned transaction from transaction payload.
     *
     * @param {TransactionPayload} payload - Transaction data
     * @returns {Object} Unsigned transaction with payload bytes and hash
     */
    buildUnsignedTransaction(payload) {
        // Validate required fields
        if (!payload.sender) throw new Error('Transaction sender is required');
        if (!payload.recipient) throw new Error('Transaction recipient is required');
        if (payload.amount == null) throw new Error('Transaction amount is required');
        if (payload.fee == null) throw new Error('Transaction fee is required');
        if (payload.nonce == null) throw new Error('Transaction nonce is required');

        // Create unsigned transaction object (XAI format)
        const unsignedTx = {
            version: '1.0',
            tx_type: 'transfer',
            sender: payload.sender,
            recipient: payload.recipient,
            amount: parseFloat(payload.amount),
            fee: parseFloat(payload.fee),
            nonce: parseInt(payload.nonce, 10),
            memo: payload.memo || '',
            network: payload.network || 'mainnet',
            created_at: Math.floor(Date.now() / 1000),
        };

        // Compute canonical payload for signing
        const canonical = JSON.stringify(unsignedTx, Object.keys(unsignedTx).sort());
        const payloadBytes = new TextEncoder().encode(canonical);

        // Compute payload hash (SHA-256)
        const payloadHashPromise = crypto.subtle.digest('SHA-256', payloadBytes);

        return {
            transaction: unsignedTx,
            payloadBytes: payloadBytes,
            payloadHashPromise: payloadHashPromise,

            // Synchronous access to hash (requires await)
            async getPayloadHash() {
                const hashBuffer = await this.payloadHashPromise;
                const hashArray = Array.from(new Uint8Array(hashBuffer));
                return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
            },
        };
    }

    /**
     * Combine unsigned transaction with signature to create signed transaction.
     *
     * @param {Object} unsignedTx - Unsigned transaction from buildUnsignedTransaction
     * @param {string} signature - Signature hex string (128 chars = 64 bytes)
     * @param {string} publicKey - Signer's public key hex string
     * @returns {Promise<SignedTransaction>} Complete signed transaction
     */
    async combineSignature(unsignedTx, signature, publicKey) {
        // Get payload hash
        const payloadHash = await unsignedTx.getPayloadHash();

        return {
            transaction: unsignedTx.transaction,
            signature: signature,
            publicKey: publicKey,
            payloadHash: payloadHash,
            signedAt: Math.floor(Date.now() / 1000),
        };
    }

    /**
     * Register an event listener.
     *
     * Supported events:
     * - 'connecting': Wallet connection started
     * - 'connected': Wallet successfully connected
     * - 'disconnected': Wallet disconnected
     * - 'signing': Signature operation started
     * - 'signed': Signature completed successfully
     * - 'error': Error occurred
     *
     * @param {string} event - Event name
     * @param {Function} callback - Event callback function
     */
    on(event, callback) {
        if (typeof callback !== 'function') {
            throw new Error('Event callback must be a function');
        }

        if (!this.eventListeners[event]) {
            this.eventListeners[event] = [];
        }

        this.eventListeners[event].push(callback);
    }

    /**
     * Unregister an event listener.
     *
     * @param {string} event - Event name
     * @param {Function} callback - Event callback to remove
     */
    off(event, callback) {
        if (!this.eventListeners[event]) {
            return;
        }

        this.eventListeners[event] = this.eventListeners[event].filter(
            cb => cb !== callback
        );
    }

    /**
     * Emit an event to all registered listeners.
     *
     * @private
     * @param {string} event - Event name
     * @param {*} data - Event data
     */
    _emit(event, data) {
        const listeners = this.eventListeners[event] || [];

        for (const callback of listeners) {
            try {
                callback(data);
            } catch (err) {
                console.error(`Error in ${event} event listener:`, err);
            }
        }
    }

    /**
     * Require an active connection, throw error if not connected.
     *
     * @private
     * @throws {Error} If not connected
     */
    _requireConnection() {
        if (!this.isConnected()) {
            throw new Error('No hardware wallet connected. Call connect() first.');
        }
    }

    /**
     * Format error messages to be user-friendly.
     *
     * @private
     * @param {Error} err - Original error
     * @param {string} walletType - Wallet type ('ledger' or 'trezor')
     * @returns {Error} Formatted error
     */
    _formatError(err, walletType) {
        const message = err.message || String(err);

        // User-friendly error messages
        const friendlyErrors = {
            'User rejected': 'Transaction was rejected on the device.',
            'user rejected': 'Transaction was rejected on the device.',
            'User cancelled': 'Transaction was cancelled on the device.',
            'User denied': 'Action was denied on the device.',
            'device not found': `${HardwareWalletManager.getWalletName(walletType)} device not found. Please connect it and unlock.`,
            'Device not connected': `${HardwareWalletManager.getWalletName(walletType)} not connected. Please connect your device.`,
            'app not open': `Please open the XAI (or Ethereum) app on your ${HardwareWalletManager.getWalletName(walletType)}.`,
            'wrong app': `Wrong app open on ${HardwareWalletManager.getWalletName(walletType)}. Please open the XAI or Ethereum app.`,
            'Timeout': 'Request timed out. Please try again.',
        };

        // Check for known error patterns
        for (const [pattern, friendlyMessage] of Object.entries(friendlyErrors)) {
            if (message.toLowerCase().includes(pattern.toLowerCase())) {
                return new Error(friendlyMessage);
            }
        }

        // Return original error if no match
        return err;
    }

    /**
     * Convert XAI transaction payload to Ethereum transaction format for Trezor.
     *
     * @private
     * @param {TransactionPayload} txPayload - XAI transaction payload
     * @returns {Object} Ethereum-formatted transaction
     */
    _convertToEthereumTx(txPayload) {
        // Convert XAI amounts to wei (assuming 18 decimals)
        const amountWei = Math.floor(parseFloat(txPayload.amount) * 1e18);
        const gasPriceWei = Math.floor(parseFloat(txPayload.fee) * 1e9); // Fee in Gwei

        return {
            to: txPayload.recipient,
            value: '0x' + amountWei.toString(16),
            gasPrice: '0x' + gasPriceWei.toString(16),
            gasLimit: '0x5208', // 21000 in hex (standard transfer)
            nonce: '0x' + parseInt(txPayload.nonce, 10).toString(16),
            data: txPayload.memo ? '0x' + Buffer.from(txPayload.memo).toString('hex') : '0x',
            chainId: txPayload.chainId || 22593, // XAI chain ID
        };
    }

    /**
     * Attempt to reconnect to the last connected wallet.
     *
     * @private
     * @returns {Promise<void>}
     */
    async _attemptReconnect() {
        if (!this.autoReconnect || !this.currentWalletType) {
            return;
        }

        try {
            await this.connect(this.currentWalletType);
        } catch (err) {
            // Schedule next reconnection attempt
            this.reconnectTimer = setTimeout(() => {
                this._attemptReconnect();
            }, this.reconnectDelay);
        }
    }
}

// Transaction builder helper functions

/**
 * Build an unsigned transaction from basic parameters.
 *
 * @param {string} from - Sender XAI address
 * @param {string} to - Recipient XAI address
 * @param {number|string} amount - Amount to send
 * @param {number|string} fee - Transaction fee
 * @param {number} nonce - Transaction nonce
 * @param {Object} [options] - Optional parameters
 * @param {string} [options.memo] - Transaction memo
 * @param {string} [options.network] - Network (mainnet/testnet)
 * @returns {Object} Unsigned transaction object
 */
function buildUnsignedTransaction(from, to, amount, fee, nonce, options = {}) {
    const payload = {
        sender: from,
        recipient: to,
        amount: amount,
        fee: fee,
        nonce: nonce,
        memo: options.memo || '',
        network: options.network || 'mainnet',
    };

    const manager = new HardwareWalletManager();
    return manager.buildUnsignedTransaction(payload);
}

/**
 * Combine an unsigned transaction with a signature to create a complete signed transaction.
 *
 * @param {Object} unsignedTx - Unsigned transaction from buildUnsignedTransaction
 * @param {string} signature - Signature hex string (128 chars)
 * @param {string} publicKey - Signer's public key hex string (128 chars)
 * @returns {Promise<Object>} Signed transaction ready for broadcast
 */
async function combineSignature(unsignedTx, signature, publicKey) {
    const manager = new HardwareWalletManager();
    return await manager.combineSignature(unsignedTx, signature, publicKey);
}

// Export for ES6 modules and browser globals
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        HardwareWalletManager,
        buildUnsignedTransaction,
        combineSignature,
    };
} else if (typeof window !== 'undefined') {
    window.HardwareWalletManager = HardwareWalletManager;
    window.buildUnsignedTransaction = buildUnsignedTransaction;
    window.combineSignature = combineSignature;
}
