/**
 * Example usage of Trezor Hardware Wallet Integration
 *
 * This file demonstrates how to use the trezor-hw module in the XAI browser extension.
 *
 * IMPORTANT: This is example code. In production, ensure:
 * 1. Trezor Connect library is loaded via manifest.json CSP
 * 2. Proper error handling for all user-facing operations
 * 3. UI feedback for long-running operations
 * 4. Secure storage of session data
 */

import {
  isTrezorSupported,
  initTrezorConnect,
  connectTrezor,
  getTrezorAddress,
  signWithTrezor,
  verifyAddressOnDevice,
  disconnectTrezor,
  TrezorError,
  TrezorErrorCode,
  XAI_DEFAULT_PATH,
  XAI_COIN_TYPE,
} from './trezor-hw.js';

/**
 * Example 1: Check Trezor support and initialize
 */
async function example1_InitializeTrezor() {
  console.log('=== Example 1: Initialize Trezor ===');

  // Check if Trezor is supported in this browser
  if (!isTrezorSupported()) {
    console.error('Trezor not supported in this browser');
    return;
  }

  try {
    // Initialize Trezor Connect
    const result = await initTrezorConnect({
      debug: true, // Enable debug logging for development
    });

    console.log('Trezor initialized successfully');
    console.log('Version:', result.version);
    console.log('Manifest:', result.manifest);
  } catch (error) {
    if (error instanceof TrezorError) {
      console.error('Trezor initialization failed:', error.message);
      console.error('Error code:', error.code);
    } else {
      console.error('Unexpected error:', error);
    }
  }
}

/**
 * Example 2: Connect to device and get device info
 */
async function example2_ConnectDevice() {
  console.log('=== Example 2: Connect to Trezor Device ===');

  try {
    const device = await connectTrezor();

    console.log('Connected to Trezor device:');
    console.log('  Device ID:', device.device.id);
    console.log('  Label:', device.device.label);
    console.log('  Model:', device.device.model);
    console.log('  Firmware:', device.device.firmwareVersion);
    console.log('  PIN Protection:', device.device.pinProtection);
    console.log('  Passphrase Protection:', device.device.passphraseProtection);
  } catch (error) {
    if (error instanceof TrezorError) {
      if (error.code === TrezorErrorCode.USER_CANCELLED) {
        console.log('User cancelled device selection');
      } else if (error.code === TrezorErrorCode.DEVICE_NOT_CONNECTED) {
        console.error('No Trezor device connected. Please connect your device.');
      } else {
        console.error('Connection error:', error.message);
      }
    } else {
      console.error('Unexpected error:', error);
    }
  }
}

/**
 * Example 3: Get XAI address from Trezor
 */
async function example3_GetAddress() {
  console.log('=== Example 3: Get XAI Address ===');

  try {
    // Get address using default path
    const result = await getTrezorAddress();

    console.log('XAI Address:', result.address);
    console.log('Public Key:', result.publicKey);
    console.log('Derivation Path:', result.path);
  } catch (error) {
    if (error instanceof TrezorError) {
      console.error('Failed to get address:', error.message);
    } else {
      console.error('Unexpected error:', error);
    }
  }
}

/**
 * Example 4: Get address with on-device verification
 */
async function example4_VerifyAddress() {
  console.log('=== Example 4: Verify Address on Device ===');

  try {
    // Get address and display it on device screen for user verification
    const result = await getTrezorAddress(XAI_DEFAULT_PATH, {
      showOnDevice: true,
    });

    console.log('Address displayed on device:', result.address);
    console.log('Please verify the address matches on your Trezor screen');
  } catch (error) {
    if (error instanceof TrezorError) {
      if (error.code === TrezorErrorCode.USER_CANCELLED) {
        console.log('User cancelled address verification');
      } else {
        console.error('Verification failed:', error.message);
      }
    } else {
      console.error('Unexpected error:', error);
    }
  }
}

/**
 * Example 5: Sign a transaction
 */
async function example5_SignTransaction() {
  console.log('=== Example 5: Sign Transaction ===');

  try {
    // Build transaction payload
    const txPayload = {
      from: 'XAI1234567890abcdef1234567890abcdef123456',
      to: 'XAIabcdef1234567890abcdef1234567890abcdef',
      amount: 100,
      fee: 1,
      nonce: 42,
      timestamp: Date.now(),
    };

    console.log('Transaction to sign:', txPayload);
    console.log('Waiting for user confirmation on device...');

    // Sign transaction on Trezor device
    const result = await signWithTrezor(XAI_DEFAULT_PATH, txPayload);

    console.log('Transaction signed successfully!');
    console.log('Signature:', result.signature);
    console.log('Message Hash:', result.messageHash);
    console.log('Recovery ID (v):', result.signatureV);

    // Now submit the signed transaction to XAI network
    // await submitTransaction(txPayload, result.signature);
  } catch (error) {
    if (error instanceof TrezorError) {
      if (error.code === TrezorErrorCode.USER_CANCELLED) {
        console.log('User rejected transaction on device');
      } else if (error.code === TrezorErrorCode.SIGNING_FAILED) {
        console.error('Signing failed:', error.message);
      } else {
        console.error('Transaction signing error:', error.message);
      }
    } else {
      console.error('Unexpected error:', error);
    }
  }
}

/**
 * Example 6: Use custom derivation path for multiple accounts
 */
async function example6_MultipleAccounts() {
  console.log('=== Example 6: Multiple Accounts ===');

  try {
    // Get addresses for first 3 accounts
    for (let accountIndex = 0; accountIndex < 3; accountIndex++) {
      const path = `m/44'/${XAI_COIN_TYPE}'/${accountIndex}'/0/0`;
      const result = await getTrezorAddress(path);

      console.log(`Account ${accountIndex}:`);
      console.log('  Path:', path);
      console.log('  Address:', result.address);
    }
  } catch (error) {
    console.error('Failed to get addresses:', error.message);
  }
}

/**
 * Example 7: Complete workflow - Initialize, Connect, Sign, Disconnect
 */
async function example7_CompleteWorkflow() {
  console.log('=== Example 7: Complete Workflow ===');

  try {
    // Step 1: Check support
    if (!isTrezorSupported()) {
      throw new Error('Trezor not supported');
    }

    // Step 2: Initialize
    console.log('Initializing Trezor Connect...');
    await initTrezorConnect();

    // Step 3: Connect to device
    console.log('Connecting to device...');
    const device = await connectTrezor();
    console.log(`Connected to ${device.device.label} (${device.device.model})`);

    // Step 4: Get address
    console.log('Getting XAI address...');
    const addressResult = await getTrezorAddress();
    console.log('Address:', addressResult.address);

    // Step 5: Verify address on device
    console.log('Verifying address on device...');
    await verifyAddressOnDevice();

    // Step 6: Sign a transaction
    console.log('Preparing transaction...');
    const txPayload = {
      from: addressResult.address,
      to: 'XAIabcdef1234567890abcdef1234567890abcdef',
      amount: 50,
      fee: 1,
      nonce: 1,
    };

    console.log('Signing transaction (confirm on device)...');
    const signResult = await signWithTrezor(XAI_DEFAULT_PATH, txPayload);
    console.log('Transaction signed! Signature:', signResult.signature);

    // Step 7: Disconnect
    console.log('Disconnecting...');
    await disconnectTrezor();
    console.log('Workflow complete!');
  } catch (error) {
    if (error instanceof TrezorError) {
      console.error('Trezor error:', error.code, '-', error.message);
    } else {
      console.error('Error:', error.message);
    }

    // Cleanup on error
    await disconnectTrezor();
  }
}

/**
 * Example 8: Error handling patterns
 */
async function example8_ErrorHandling() {
  console.log('=== Example 8: Error Handling ===');

  try {
    const result = await getTrezorAddress();
    console.log('Address:', result.address);
  } catch (error) {
    if (error instanceof TrezorError) {
      // Handle specific error types
      switch (error.code) {
        case TrezorErrorCode.NOT_INITIALIZED:
          console.error('Please initialize Trezor Connect first');
          // Attempt to initialize
          await initTrezorConnect();
          break;

        case TrezorErrorCode.DEVICE_NOT_CONNECTED:
          console.error('Please connect your Trezor device');
          // Show UI prompt to connect device
          break;

        case TrezorErrorCode.USER_CANCELLED:
          console.log('Operation cancelled by user');
          // Don't show error - user action was intentional
          break;

        case TrezorErrorCode.POPUP_BLOCKED:
          console.error('Popup blocked. Please allow popups for this site.');
          // Show UI instruction to enable popups
          break;

        case TrezorErrorCode.FIRMWARE_OUTDATED:
          console.error('Firmware outdated. Please update your Trezor.');
          // Show link to Trezor firmware update
          break;

        case TrezorErrorCode.WRONG_PASSPHRASE:
          console.error('Incorrect passphrase. Please try again.');
          // Allow retry
          break;

        default:
          console.error('Trezor error:', error.message);
      }
    } else {
      console.error('Unexpected error:', error);
    }
  }
}

// Export examples for use in extension
export {
  example1_InitializeTrezor,
  example2_ConnectDevice,
  example3_GetAddress,
  example4_VerifyAddress,
  example5_SignTransaction,
  example6_MultipleAccounts,
  example7_CompleteWorkflow,
  example8_ErrorHandling,
};

// For testing in browser console
if (typeof window !== 'undefined') {
  window.TrezorExamples = {
    example1_InitializeTrezor,
    example2_ConnectDevice,
    example3_GetAddress,
    example4_VerifyAddress,
    example5_SignTransaction,
    example6_MultipleAccounts,
    example7_CompleteWorkflow,
    example8_ErrorHandling,
  };

  console.log('Trezor examples loaded. Run examples with:');
  console.log('  TrezorExamples.example1_InitializeTrezor()');
  console.log('  TrezorExamples.example7_CompleteWorkflow()');
}
