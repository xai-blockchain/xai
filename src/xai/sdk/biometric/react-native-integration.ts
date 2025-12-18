/**
 * React Native Biometric Authentication Integration
 *
 * Provides a consistent biometric authentication API across iOS and Android
 * using react-native-biometrics as the underlying implementation.
 *
 * Installation:
 *   npm install react-native-biometrics
 *   cd ios && pod install
 *
 * iOS Setup (Info.plist):
 *   <key>NSFaceIDUsageDescription</key>
 *   <string>We use Face ID to secure your wallet</string>
 *
 * Android Setup (AndroidManifest.xml):
 *   <uses-permission android:name="android.permission.USE_BIOMETRIC" />
 */

import ReactNativeBiometrics, { BiometryType } from 'react-native-biometrics';
import {
  BiometricType,
  BiometricError,
  BiometricCapability,
  BiometricConfig,
  BiometricResult,
  IBiometricAuthProvider,
  SecureKeyConfig,
  EncryptedData,
  PlatformBiometricInfo,
} from './types';
import { Platform } from 'react-native';

/**
 * React Native implementation of biometric authentication
 */
export class ReactNativeBiometricProvider implements IBiometricAuthProvider {
  private rnBiometrics: ReactNativeBiometrics;

  constructor() {
    this.rnBiometrics = new ReactNativeBiometrics({
      allowDeviceCredentials: false, // We'll handle this per-call
    });
  }

  /**
   * Check if biometric authentication is available
   */
  async isAvailable(): Promise<BiometricCapability> {
    try {
      const { available, biometryType } = await this.rnBiometrics.isSensorAvailable();

      if (!available) {
        return {
          available: false,
          enrolled: false,
          biometricTypes: [BiometricType.NONE],
          hardwareDetected: false,
          securityLevel: 'none',
        };
      }

      const mappedType = this.mapBiometryType(biometryType);
      const securityLevel = this.determineSecurityLevel(mappedType);

      return {
        available: true,
        enrolled: true, // If sensor is available, we assume enrolled
        biometricTypes: [mappedType],
        hardwareDetected: true,
        securityLevel,
      };
    } catch (error) {
      console.error('Error checking biometric availability:', error);
      return {
        available: false,
        enrolled: false,
        biometricTypes: [BiometricType.NONE],
        hardwareDetected: false,
        securityLevel: 'none',
      };
    }
  }

  /**
   * Authenticate user with biometrics
   */
  async authenticate(config: BiometricConfig): Promise<BiometricResult> {
    const timestamp = Math.floor(Date.now() / 1000);

    try {
      const { success } = await this.rnBiometrics.simplePrompt({
        promptMessage: config.promptMessage,
        cancelButtonText: config.cancelButtonText,
        fallbackPromptMessage: config.fallbackToPasscode
          ? 'Use device passcode'
          : undefined,
      });

      if (!success) {
        return {
          success: false,
          biometricType: await this.getAuthType(),
          errorCode: BiometricError.AUTHENTICATION_FAILED,
          errorMessage: 'Biometric authentication failed',
          timestamp,
        };
      }

      return {
        success: true,
        biometricType: await this.getAuthType(),
        timestamp,
      };
    } catch (error: any) {
      return this.handleAuthError(error, timestamp);
    }
  }

  /**
   * Get the primary biometric type available
   */
  async getAuthType(): Promise<BiometricType> {
    try {
      const { biometryType } = await this.rnBiometrics.isSensorAvailable();
      return this.mapBiometryType(biometryType);
    } catch (error) {
      return BiometricType.NONE;
    }
  }

  /**
   * Invalidate current authentication session
   */
  async invalidateAuthentication(): Promise<boolean> {
    // react-native-biometrics doesn't maintain session state
    // Each authentication is independent
    return true;
  }

  /**
   * Store data encrypted with biometric-protected key
   */
  async storeSecure(
    data: string,
    config: SecureKeyConfig
  ): Promise<EncryptedData> {
    try {
      // Create a key pair bound to biometric authentication
      const { publicKey } = await this.rnBiometrics.createKeys({
        keyAlias: config.keyAlias,
        requireBiometric: config.requireBiometric,
      });

      // For actual encryption, we need to use platform-specific crypto
      // This is a simplified implementation
      const encrypted = await this.encryptWithPublicKey(data, publicKey);

      return {
        ciphertext: encrypted.ciphertext,
        iv: encrypted.iv,
        tag: encrypted.tag,
        algorithm: 'RSA-OAEP',
        keyAlias: config.keyAlias,
      };
    } catch (error) {
      throw new Error(`Failed to store secure data: ${error}`);
    }
  }

  /**
   * Retrieve and decrypt data with biometric authentication
   */
  async retrieveSecure(
    encrypted: EncryptedData,
    promptConfig: BiometricConfig
  ): Promise<string | null> {
    try {
      // First authenticate with biometrics
      const authResult = await this.authenticate(promptConfig);

      if (!authResult.success) {
        return null;
      }

      // Create signature to prove biometric authentication
      const { success, signature } = await this.rnBiometrics.createSignature({
        promptMessage: promptConfig.promptMessage,
        payload: encrypted.ciphertext,
        cancelButtonText: promptConfig.cancelButtonText,
      });

      if (!success || !signature) {
        return null;
      }

      // Decrypt using the signature as proof of authentication
      const decrypted = await this.decryptWithSignature(
        encrypted,
        signature
      );

      return decrypted;
    } catch (error) {
      console.error('Error retrieving secure data:', error);
      return null;
    }
  }

  /**
   * Delete securely stored data
   */
  async deleteSecure(keyAlias: string): Promise<boolean> {
    try {
      const { keysDeleted } = await this.rnBiometrics.deleteKeys();
      return keysDeleted;
    } catch (error) {
      console.error('Error deleting secure key:', error);
      return false;
    }
  }

  /**
   * Get platform-specific biometric information
   */
  async getPlatformInfo(): Promise<PlatformBiometricInfo> {
    const capability = await this.isAvailable();

    return {
      platform: Platform.OS === 'ios' ? 'ios' : Platform.OS === 'android' ? 'android' : 'unknown',
      osVersion: Platform.Version.toString(),
      availableTypes: capability.biometricTypes,
      supportsStrongAuth: capability.securityLevel === 'strong',
      supportsCryptoOperations: capability.available,
    };
  }

  /**
   * Create a biometric-protected key pair for wallet encryption
   */
  async createWalletKey(walletId: string): Promise<{ publicKey: string }> {
    try {
      const { publicKey } = await this.rnBiometrics.createKeys({
        keyAlias: `wallet_${walletId}`,
        requireBiometric: true,
      });

      return { publicKey };
    } catch (error) {
      throw new Error(`Failed to create wallet key: ${error}`);
    }
  }

  /**
   * Sign wallet transaction with biometric authentication
   */
  async signWithBiometric(
    payload: string,
    walletId: string,
    promptMessage: string = 'Authenticate to sign transaction'
  ): Promise<{ signature: string } | null> {
    try {
      const { success, signature } = await this.rnBiometrics.createSignature({
        promptMessage,
        payload,
        cancelButtonText: 'Cancel',
      });

      if (!success || !signature) {
        return null;
      }

      return { signature };
    } catch (error) {
      console.error('Error signing with biometric:', error);
      return null;
    }
  }

  // Private helper methods

  private mapBiometryType(biometryType: string | undefined): BiometricType {
    switch (biometryType) {
      case BiometryType.FaceID:
        return BiometricType.FACE_ID;
      case BiometryType.TouchID:
        return BiometricType.TOUCH_ID;
      case BiometryType.Biometrics:
        return Platform.OS === 'android'
          ? BiometricType.FINGERPRINT
          : BiometricType.NONE;
      default:
        return BiometricType.NONE;
    }
  }

  private determineSecurityLevel(
    biometricType: BiometricType
  ): 'strong' | 'weak' | 'none' {
    switch (biometricType) {
      case BiometricType.FACE_ID:
      case BiometricType.IRIS:
        return 'strong';
      case BiometricType.TOUCH_ID:
      case BiometricType.FINGERPRINT:
        return 'strong'; // Modern implementations are strong
      case BiometricType.VOICE:
        return 'weak';
      default:
        return 'none';
    }
  }

  private handleAuthError(error: any, timestamp: number): BiometricResult {
    let errorCode = BiometricError.UNKNOWN;
    let errorMessage = 'Unknown error occurred';

    if (error.name === 'UserCancel') {
      errorCode = BiometricError.USER_CANCEL;
      errorMessage = 'User cancelled authentication';
    } else if (error.name === 'AuthenticationFailed') {
      errorCode = BiometricError.AUTHENTICATION_FAILED;
      errorMessage = 'Authentication failed';
    } else if (error.name === 'UserFallback') {
      errorCode = BiometricError.USER_CANCEL;
      errorMessage = 'User chose fallback';
    } else if (error.name === 'SystemCancel') {
      errorCode = BiometricError.TIMEOUT;
      errorMessage = 'System cancelled authentication';
    } else if (error.name === 'PasscodeNotSet') {
      errorCode = BiometricError.NOT_AVAILABLE;
      errorMessage = 'Passcode not set on device';
    } else if (error.name === 'BiometryNotAvailable') {
      errorCode = BiometricError.NOT_AVAILABLE;
      errorMessage = 'Biometry not available';
    } else if (error.name === 'BiometryNotEnrolled') {
      errorCode = BiometricError.NOT_ENROLLED;
      errorMessage = 'No biometrics enrolled';
    } else if (error.name === 'BiometryLockout') {
      errorCode = BiometricError.LOCKOUT;
      errorMessage = 'Biometry locked out';
    }

    return {
      success: false,
      biometricType: BiometricType.NONE,
      errorCode,
      errorMessage,
      timestamp,
    };
  }

  // Placeholder encryption methods - implement with platform-specific crypto
  private async encryptWithPublicKey(
    data: string,
    publicKey: string
  ): Promise<{ ciphertext: string; iv: string; tag: string }> {
    // TODO: Implement actual RSA encryption using platform crypto libraries
    // iOS: Security framework
    // Android: KeyStore + Cipher
    throw new Error('encryptWithPublicKey not fully implemented - use platform-specific crypto');
  }

  private async decryptWithSignature(
    encrypted: EncryptedData,
    signature: string
  ): Promise<string> {
    // TODO: Implement actual decryption using signature as proof
    throw new Error('decryptWithSignature not fully implemented - use platform-specific crypto');
  }
}

/**
 * Singleton instance for convenience
 */
export const biometricAuth = new ReactNativeBiometricProvider();

/**
 * Example usage:
 *
 * // Check availability
 * const capability = await biometricAuth.isAvailable();
 * if (!capability.available) {
 *   console.log('Biometrics not available');
 *   return;
 * }
 *
 * // Authenticate
 * const result = await biometricAuth.authenticate({
 *   promptMessage: 'Authenticate to access your wallet',
 *   cancelButtonText: 'Cancel',
 *   fallbackToPasscode: true,
 * });
 *
 * if (result.success) {
 *   console.log('Authenticated with', result.biometricType);
 *   // Access wallet private key
 * } else {
 *   console.error('Auth failed:', result.errorMessage);
 * }
 *
 * // Create wallet key
 * const { publicKey } = await biometricAuth.createWalletKey('wallet_001');
 *
 * // Sign transaction
 * const signature = await biometricAuth.signWithBiometric(
 *   transactionHash,
 *   'wallet_001',
 *   'Sign transaction'
 * );
 */
