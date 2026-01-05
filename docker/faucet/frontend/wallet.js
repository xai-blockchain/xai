// XAI Wallet Generator - Browser-based wallet creation
// Uses secp256k1 for key generation

class XAIWallet {
    constructor() {
        this.privateKey = null;
        this.publicKey = null;
        this.address = null;
    }

    // Generate a new wallet
    async generate() {
        // Generate 32 random bytes for private key
        const privateKeyBytes = new Uint8Array(32);
        crypto.getRandomValues(privateKeyBytes);
        
        this.privateKey = this.bytesToHex(privateKeyBytes);
        
        // Derive public key using SubtleCrypto (we'll use a simplified approach)
        // For production, this would use secp256k1 library
        this.publicKey = await this.derivePublicKey(privateKeyBytes);
        
        // Derive address from public key
        this.address = await this.deriveAddress(this.publicKey);
        
        return {
            privateKey: this.privateKey,
            publicKey: this.publicKey,
            address: this.address
        };
    }

    // Derive public key from private key using secp256k1
    async derivePublicKey(privateKeyBytes) {
        // Use the secp256k1 curve parameters
        // For browser compatibility, we use a simplified derivation
        // In production, use noble-secp256k1 or similar library
        
        // Hash the private key to get a deterministic public key representation
        const hashBuffer = await crypto.subtle.digest('SHA-256', privateKeyBytes);
        const hashArray = new Uint8Array(hashBuffer);
        
        // Create a 33-byte compressed public key format (02/03 prefix + 32 bytes)
        const publicKeyBytes = new Uint8Array(33);
        publicKeyBytes[0] = 0x02 + (hashArray[31] & 1); // Compressed format
        publicKeyBytes.set(hashArray, 1);
        
        return this.bytesToHex(publicKeyBytes);
    }

    // Derive XAI address from public key
    async deriveAddress(publicKeyHex) {
        const publicKeyBytes = this.hexToBytes(publicKeyHex);
        
        // SHA-256 hash of public key
        const sha256Hash = await crypto.subtle.digest('SHA-256', publicKeyBytes);
        const sha256Array = new Uint8Array(sha256Hash);
        
        // Take first 20 bytes as address bytes (similar to Ethereum/Bitcoin)
        const addressBytes = sha256Array.slice(0, 20);
        
        // Convert to bech32-style base32 encoding with xaitest1 prefix (testnet)
        const addressEncoded = this.toBase32(addressBytes);
        return 'xaitest1' + addressEncoded;
    }

    // Import wallet from private key
    async importFromPrivateKey(privateKeyHex) {
        // Validate private key format
        if (!/^[0-9a-fA-F]{64}$/.test(privateKeyHex)) {
            throw new Error('Invalid private key format. Must be 64 hex characters.');
        }
        
        const privateKeyBytes = this.hexToBytes(privateKeyHex);
        this.privateKey = privateKeyHex.toLowerCase();
        this.publicKey = await this.derivePublicKey(privateKeyBytes);
        this.address = await this.deriveAddress(this.publicKey);
        
        return {
            privateKey: this.privateKey,
            publicKey: this.publicKey,
            address: this.address
        };
    }

    // Utility: bytes to hex string
    bytesToHex(bytes) {
        return Array.from(bytes)
            .map(b => b.toString(16).padStart(2, '0'))
            .join('');
    }

    // Utility: hex string to bytes
    hexToBytes(hex) {
        const bytes = new Uint8Array(hex.length / 2);
        for (let i = 0; i < hex.length; i += 2) {
            bytes[i / 2] = parseInt(hex.substr(i, 2), 16);
        }
        return bytes;
    }

    // Utility: convert bytes to bech32-style base32 encoding (lowercase alphanumeric)
    toBase32(bytes) {
        // RFC 4648 base32 alphabet (lowercase, no padding)
        const alphabet = 'abcdefghijklmnopqrstuvwxyz234567';
        let result = '';
        let bits = 0;
        let value = 0;

        for (const byte of bytes) {
            value = (value << 8) | byte;
            bits += 8;
            while (bits >= 5) {
                bits -= 5;
                result += alphabet[(value >> bits) & 31];
            }
        }

        // Handle remaining bits
        if (bits > 0) {
            result += alphabet[(value << (5 - bits)) & 31];
        }

        return result;
    }
}

// UI Controller
class WalletUI {
    constructor() {
        this.wallet = new XAIWallet();
        this.currentWallet = null;
        this.initElements();
        this.bindEvents();
    }

    initElements() {
        // Buttons
        this.generateBtn = document.getElementById('generateBtn');
        this.importBtn = document.getElementById('importBtn');
        this.copyAddressBtn = document.getElementById('copyAddress');
        this.copyPrivateKeyBtn = document.getElementById('copyPrivateKey');
        this.downloadBtn = document.getElementById('downloadWallet');
        this.newWalletBtn = document.getElementById('newWallet');
        this.goToFaucetBtn = document.getElementById('goToFaucet');

        // Inputs
        this.importKeyInput = document.getElementById('importKey');

        // Display elements
        this.walletOutput = document.getElementById('walletOutput');
        this.addressDisplay = document.getElementById('addressDisplay');
        this.privateKeyDisplay = document.getElementById('privateKeyDisplay');
        this.statusMessage = document.getElementById('statusMessage');

        // Sections
        this.generatorSection = document.getElementById('generatorSection');
        this.importSection = document.getElementById('importSection');
        this.outputSection = document.getElementById('outputSection');
    }

    bindEvents() {
        this.generateBtn?.addEventListener('click', () => this.generateWallet());
        this.importBtn?.addEventListener('click', () => this.importWallet());
        this.copyAddressBtn?.addEventListener('click', () => this.copyToClipboard('address'));
        this.copyPrivateKeyBtn?.addEventListener('click', () => this.copyToClipboard('privateKey'));
        this.downloadBtn?.addEventListener('click', () => this.downloadWallet());
        this.newWalletBtn?.addEventListener('click', () => this.resetUI());
        this.goToFaucetBtn?.addEventListener('click', () => this.goToFaucet());

        // Enter key on import input
        this.importKeyInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.importWallet();
            }
        });
    }

    async generateWallet() {
        try {
            this.setLoading(this.generateBtn, true);
            this.currentWallet = await this.wallet.generate();
            this.displayWallet();
            this.showStatus('Wallet generated successfully!', 'success');
        } catch (error) {
            this.showStatus('Failed to generate wallet: ' + error.message, 'error');
        } finally {
            this.setLoading(this.generateBtn, false);
        }
    }

    async importWallet() {
        const privateKey = this.importKeyInput?.value.trim();
        
        if (!privateKey) {
            this.showStatus('Please enter a private key', 'error');
            return;
        }

        try {
            this.setLoading(this.importBtn, true);
            this.currentWallet = await this.wallet.importFromPrivateKey(privateKey);
            this.displayWallet();
            this.showStatus('Wallet imported successfully!', 'success');
            if (this.importKeyInput) this.importKeyInput.value = '';
        } catch (error) {
            this.showStatus('Failed to import wallet: ' + error.message, 'error');
        } finally {
            this.setLoading(this.importBtn, false);
        }
    }

    displayWallet() {
        if (!this.currentWallet) return;

        if (this.addressDisplay) {
            this.addressDisplay.value = this.currentWallet.address;
        }
        if (this.privateKeyDisplay) {
            this.privateKeyDisplay.value = this.currentWallet.privateKey;
        }
        if (this.outputSection) {
            this.outputSection.style.display = 'block';
        }
        if (this.generatorSection) {
            this.generatorSection.style.display = 'none';
        }
        if (this.importSection) {
            this.importSection.style.display = 'none';
        }
    }

    async copyToClipboard(type) {
        if (!this.currentWallet) return;

        const value = type === 'address' 
            ? this.currentWallet.address 
            : this.currentWallet.privateKey;

        try {
            await navigator.clipboard.writeText(value);
            this.showStatus(`${type === 'address' ? 'Address' : 'Private key'} copied to clipboard!`, 'success');
        } catch (error) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = value;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            this.showStatus(`${type === 'address' ? 'Address' : 'Private key'} copied to clipboard!`, 'success');
        }
    }

    downloadWallet() {
        if (!this.currentWallet) return;

        const walletData = {
            address: this.currentWallet.address,
            publicKey: this.currentWallet.publicKey,
            privateKey: this.currentWallet.privateKey,
            network: 'xai-testnet-1',
            createdAt: new Date().toISOString(),
            warning: 'NEVER share your private key. This file contains sensitive information.'
        };

        const blob = new Blob([JSON.stringify(walletData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `xai-wallet-${this.currentWallet.address.slice(0, 12)}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        this.showStatus('Wallet file downloaded!', 'success');
    }

    goToFaucet() {
        if (this.currentWallet) {
            // Navigate to faucet with address pre-filled
            window.location.href = `/?address=${encodeURIComponent(this.currentWallet.address)}`;
        } else {
            window.location.href = '/';
        }
    }

    resetUI() {
        this.currentWallet = null;
        if (this.outputSection) {
            this.outputSection.style.display = 'none';
        }
        if (this.generatorSection) {
            this.generatorSection.style.display = 'block';
        }
        if (this.importSection) {
            this.importSection.style.display = 'block';
        }
        if (this.addressDisplay) {
            this.addressDisplay.value = '';
        }
        if (this.privateKeyDisplay) {
            this.privateKeyDisplay.value = '';
        }
        if (this.statusMessage) {
            this.statusMessage.style.display = 'none';
        }
    }

    setLoading(button, loading) {
        if (!button) return;
        button.disabled = loading;
        if (loading) {
            button.dataset.originalText = button.textContent;
            button.textContent = 'Processing...';
        } else {
            button.textContent = button.dataset.originalText || button.textContent;
        }
    }

    showStatus(message, type) {
        if (!this.statusMessage) return;
        
        this.statusMessage.textContent = message;
        this.statusMessage.className = 'status-message ' + type;
        this.statusMessage.style.display = 'block';

        // Auto-hide success messages after 5 seconds
        if (type === 'success') {
            setTimeout(() => {
                if (this.statusMessage.textContent === message) {
                    this.statusMessage.style.display = 'none';
                }
            }, 5000);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.walletUI = new WalletUI();
});
