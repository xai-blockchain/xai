/**
 * Hardware Wallet UI Controller for XAI Browser Extension
 *
 * Manages the user interface for hardware wallet interactions including:
 * - Device connection modal
 * - Connection status display
 * - Transaction signing flow
 * - Error handling and user guidance
 */

class HardwareWalletUI {
  constructor(hwManager) {
    this.hwManager = hwManager;
    this.isInitialized = false;
  }

  /**
   * Initialize the hardware wallet UI
   * Should be called after DOM is loaded
   */
  initialize() {
    if (this.isInitialized) return;

    // Bind event listeners
    this.bindEventListeners();

    // Update UI based on current state
    this.updateUI();

    this.isInitialized = true;
  }

  /**
   * Bind all event listeners for hardware wallet UI
   */
  bindEventListeners() {
    // Connect button
    const connectBtn = document.getElementById('hwConnectBtn');
    if (connectBtn) {
      connectBtn.addEventListener('click', () => this.showConnectionModal());
    }

    // Disconnect button
    const disconnectBtn = document.getElementById('hwDisconnectBtn');
    if (disconnectBtn) {
      disconnectBtn.addEventListener('click', () => this.handleDisconnect());
    }

    // Device selection buttons
    const ledgerBtn = document.getElementById('hwSelectLedger');
    if (ledgerBtn) {
      ledgerBtn.addEventListener('click', () => this.handleDeviceSelection('ledger'));
    }

    const trezorBtn = document.getElementById('hwSelectTrezor');
    if (trezorBtn) {
      trezorBtn.addEventListener('click', () => this.handleDeviceSelection('trezor'));
    }

    // Modal close buttons
    const closeModalBtn = document.getElementById('hwModalClose');
    if (closeModalBtn) {
      closeModalBtn.addEventListener('click', () => this.hideConnectionModal());
    }

    // Close modal on background click
    const modal = document.getElementById('hwConnectionModal');
    if (modal) {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) {
          this.hideConnectionModal();
        }
      });
    }

    // ESC key to close modal
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.hideConnectionModal();
        this.hideSigningPrompt();
      }
    });
  }

  /**
   * Update UI elements based on current hardware wallet state
   */
  updateUI() {
    const state = this.hwManager.getState();
    const statusEl = document.getElementById('hwStatus');
    const connectBtn = document.getElementById('hwConnectBtn');
    const disconnectBtn = document.getElementById('hwDisconnectBtn');
    const addressEl = document.getElementById('hwAddressDisplay');

    if (state.connected) {
      // Connected state
      if (statusEl) {
        statusEl.className = 'hw-status hw-status--connected';
        statusEl.textContent = `${HardwareWalletManager.getDeviceName(state.deviceType)} Connected`;
      }

      if (connectBtn) connectBtn.classList.add('hidden');
      if (disconnectBtn) disconnectBtn.classList.remove('hidden');

      if (addressEl) {
        addressEl.textContent = HardwareWalletManager.formatAddress(state.address);
        addressEl.classList.remove('hidden');
      }

      // Auto-populate wallet address field
      const walletAddressInput = document.getElementById('walletAddress');
      if (walletAddressInput && state.address) {
        walletAddressInput.value = state.address;
        // Trigger change event to ensure session is registered
        walletAddressInput.dispatchEvent(new Event('change'));
      }
    } else {
      // Disconnected state
      if (statusEl) {
        statusEl.className = 'hw-status hw-status--disconnected';
        statusEl.textContent = 'No Hardware Wallet';
      }

      if (connectBtn) connectBtn.classList.remove('hidden');
      if (disconnectBtn) disconnectBtn.classList.add('hidden');

      if (addressEl) {
        addressEl.classList.add('hidden');
      }
    }
  }

  /**
   * Show the device connection modal
   */
  showConnectionModal() {
    const modal = document.getElementById('hwConnectionModal');
    if (modal) {
      modal.classList.remove('hidden');
      modal.setAttribute('aria-hidden', 'false');

      // Reset modal state
      this.setModalState('select');
    }
  }

  /**
   * Hide the device connection modal
   */
  hideConnectionModal() {
    const modal = document.getElementById('hwConnectionModal');
    if (modal) {
      modal.classList.add('hidden');
      modal.setAttribute('aria-hidden', 'true');

      // Reset any error messages
      this.clearModalError();
    }
  }

  /**
   * Set modal state (select, connecting, success, error)
   */
  setModalState(state) {
    const selectView = document.getElementById('hwModalSelectView');
    const connectingView = document.getElementById('hwModalConnectingView');
    const deviceTypeEl = document.getElementById('hwConnectingDevice');

    // Hide all views
    if (selectView) selectView.classList.add('hidden');
    if (connectingView) connectingView.classList.add('hidden');

    // Show appropriate view
    switch (state) {
      case 'select':
        if (selectView) selectView.classList.remove('hidden');
        break;
      case 'connecting':
        if (connectingView) {
          connectingView.classList.remove('hidden');
          if (deviceTypeEl) {
            deviceTypeEl.textContent = 'device';
          }
        }
        break;
    }
  }

  /**
   * Show error message in modal
   */
  showModalError(message) {
    const errorEl = document.getElementById('hwModalError');
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.classList.remove('hidden');
    }
  }

  /**
   * Clear error message in modal
   */
  clearModalError() {
    const errorEl = document.getElementById('hwModalError');
    if (errorEl) {
      errorEl.textContent = '';
      errorEl.classList.add('hidden');
    }
  }

  /**
   * Handle device selection and connection
   */
  async handleDeviceSelection(deviceType) {
    this.clearModalError();
    this.setModalState('connecting');

    const deviceTypeEl = document.getElementById('hwConnectingDevice');
    if (deviceTypeEl) {
      deviceTypeEl.textContent = HardwareWalletManager.getDeviceName(deviceType);
    }

    try {
      const result = await this.hwManager.connect(deviceType);

      if (result.success) {
        // Show success briefly, then close
        this.showModalSuccess(`Connected to ${HardwareWalletManager.getDeviceName(deviceType)}`);

        setTimeout(() => {
          this.hideConnectionModal();
          this.updateUI();
        }, 1500);
      } else {
        throw new Error('Connection failed');
      }
    } catch (error) {
      console.error('Hardware wallet connection error:', error);

      // Show user-friendly error
      let errorMessage = this.getFriendlyErrorMessage(error.message, deviceType);
      this.showModalError(errorMessage);

      // Return to device selection
      setTimeout(() => {
        this.setModalState('select');
      }, 3000);
    }
  }

  /**
   * Convert technical error messages to user-friendly guidance
   */
  getFriendlyErrorMessage(error, deviceType) {
    const deviceName = HardwareWalletManager.getDeviceName(deviceType);

    if (error.includes('not found') || error.includes('No device')) {
      return `${deviceName} not detected. Please connect your device and unlock it.`;
    }

    if (error.includes('locked') || error.includes('unlock')) {
      return `${deviceName} is locked. Please unlock your device and try again.`;
    }

    if (error.includes('app') || error.includes('application')) {
      return `Please open the XAI app on your ${deviceName} device.`;
    }

    if (error.includes('rejected') || error.includes('denied')) {
      return `Connection was rejected on the device.`;
    }

    if (error.includes('timeout')) {
      return `Connection timed out. Please ensure your ${deviceName} is connected and unlocked.`;
    }

    // Generic fallback
    return `Failed to connect to ${deviceName}. ${error}`;
  }

  /**
   * Show success message in modal
   */
  showModalSuccess(message) {
    const successEl = document.getElementById('hwModalSuccess');
    if (successEl) {
      successEl.textContent = message;
      successEl.classList.remove('hidden');

      setTimeout(() => {
        successEl.classList.add('hidden');
      }, 2000);
    }
  }

  /**
   * Handle disconnect request
   */
  async handleDisconnect() {
    await this.hwManager.disconnect();
    this.updateUI();
  }

  /**
   * Show signing prompt when using hardware wallet
   */
  showSigningPrompt(deviceType, payload) {
    const prompt = document.getElementById('hwSigningPrompt');
    if (!prompt) return;

    const deviceEl = document.getElementById('hwSigningDevice');
    if (deviceEl) {
      deviceEl.textContent = HardwareWalletManager.getDeviceName(deviceType);
    }

    const payloadEl = document.getElementById('hwSigningPayload');
    if (payloadEl) {
      payloadEl.textContent = JSON.stringify(payload, null, 2);
    }

    prompt.classList.remove('hidden');
    prompt.setAttribute('aria-hidden', 'false');
  }

  /**
   * Hide signing prompt
   */
  hideSigningPrompt() {
    const prompt = document.getElementById('hwSigningPrompt');
    if (prompt) {
      prompt.classList.add('hidden');
      prompt.setAttribute('aria-hidden', 'true');
    }
  }

  /**
   * Update signing prompt status
   */
  updateSigningStatus(status, message) {
    const statusEl = document.getElementById('hwSigningStatus');
    if (statusEl) {
      statusEl.className = `hw-signing-status hw-signing-status--${status}`;
      statusEl.textContent = message;
    }
  }

  /**
   * Sign a transaction using the hardware wallet
   * Shows UI prompts and handles the complete signing flow
   */
  async signTransactionWithUI(payload) {
    if (!this.hwManager.connected) {
      throw new Error('No hardware wallet connected. Please connect your device first.');
    }

    const state = this.hwManager.getState();

    try {
      // Show signing prompt
      this.showSigningPrompt(state.deviceType, payload);
      this.updateSigningStatus('waiting', `Please confirm on your ${HardwareWalletManager.getDeviceName(state.deviceType)} device...`);

      // Request signature
      const signature = await this.hwManager.signTransaction(payload);

      // Success
      this.updateSigningStatus('success', 'Transaction signed successfully!');

      // Hide prompt after brief delay
      setTimeout(() => {
        this.hideSigningPrompt();
      }, 1500);

      return signature;
    } catch (error) {
      console.error('Signing error:', error);

      // Show error in prompt
      const friendlyError = this.getFriendlyErrorMessage(error.message, state.deviceType);
      this.updateSigningStatus('error', friendlyError);

      // Keep prompt visible for user to read error
      setTimeout(() => {
        this.hideSigningPrompt();
      }, 4000);

      throw error;
    }
  }

  /**
   * Check if hardware wallet should be used for signing
   */
  shouldUseHardwareWallet() {
    return this.hwManager.connected;
  }

  /**
   * Get hardware wallet address (if connected)
   */
  getAddress() {
    const state = this.hwManager.getState();
    return state.connected ? state.address : null;
  }

  /**
   * Get hardware wallet public key (if connected)
   */
  getPublicKey() {
    const state = this.hwManager.getState();
    return state.connected ? state.publicKey : null;
  }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = HardwareWalletUI;
}
