/**
 * Biometric Authentication Client
 * Face ID / Touch ID wrapper for secure wallet access
 */

import ReactNativeBiometrics, { BiometryTypes } from 'react-native-biometrics';
import { BiometricError, BiometricConfig } from '../types';

export class BiometricAuth {
  private rnBiometrics: ReactNativeBiometrics;
  private defaultConfig: BiometricConfig = {
    title: 'Authenticate',
    subtitle: 'Verify your identity',
    description: 'Use biometric authentication to continue',
    cancelText: 'Cancel',
    fallbackEnabled: false,
  };

  constructor() {
    this.rnBiometrics = new ReactNativeBiometrics({
      allowDeviceCredentials: false,
    });
  }

  /**
   * Check if biometric authentication is available on the device
   */
  async isAvailable(): Promise<boolean> {
    try {
      const { available } = await this.rnBiometrics.isSensorAvailable();
      return available;
    } catch (error) {
      return false;
    }
  }

  /**
   * Get the type of biometric authentication available
   */
  async getBiometricType(): Promise<BiometryTypes | null> {
    try {
      const { available, biometryType } =
        await this.rnBiometrics.isSensorAvailable();

      if (!available) {
        return null;
      }

      return biometryType || null;
    } catch (error) {
      return null;
    }
  }

  /**
   * Authenticate using biometrics
   */
  async authenticate(config?: BiometricConfig): Promise<boolean> {
    try {
      const isAvailable = await this.isAvailable();
      if (!isAvailable) {
        throw new BiometricError('Biometric authentication not available');
      }

      const promptConfig = { ...this.defaultConfig, ...config };

      const { success } = await this.rnBiometrics.simplePrompt({
        promptMessage: promptConfig.description!,
        cancelButtonText: promptConfig.cancelText,
      });

      return success;
    } catch (error: any) {
      if (error.message?.includes('cancelled')) {
        throw new BiometricError('Authentication cancelled by user');
      }
      throw new BiometricError('Biometric authentication failed', error);
    }
  }

  /**
   * Create a signature using biometric authentication
   * This creates a cryptographic signature that proves biometric auth occurred
   */
  async createSignature(
    payload: string,
    config?: BiometricConfig
  ): Promise<string> {
    try {
      const isAvailable = await this.isAvailable();
      if (!isAvailable) {
        throw new BiometricError('Biometric authentication not available');
      }

      // Check if keys exist
      const { keysExist } = await this.rnBiometrics.biometricKeysExist();

      if (!keysExist) {
        // Create biometric keys
        await this.rnBiometrics.createKeys();
      }

      const promptConfig = { ...this.defaultConfig, ...config };

      const { success, signature } = await this.rnBiometrics.createSignature({
        promptMessage: promptConfig.description!,
        payload: payload,
        cancelButtonText: promptConfig.cancelText,
      });

      if (!success || !signature) {
        throw new BiometricError('Failed to create biometric signature');
      }

      return signature;
    } catch (error: any) {
      if (error.message?.includes('cancelled')) {
        throw new BiometricError('Authentication cancelled by user');
      }
      throw new BiometricError('Failed to create signature', error);
    }
  }

  /**
   * Delete biometric keys
   */
  async deleteKeys(): Promise<void> {
    try {
      const { keysDeleted } = await this.rnBiometrics.deleteKeys();
      if (!keysDeleted) {
        throw new BiometricError('Failed to delete biometric keys');
      }
    } catch (error) {
      throw new BiometricError('Failed to delete keys', error);
    }
  }

  /**
   * Check if biometric keys exist
   */
  async hasKeys(): Promise<boolean> {
    try {
      const { keysExist } = await this.rnBiometrics.biometricKeysExist();
      return keysExist;
    } catch (error) {
      return false;
    }
  }

  /**
   * Get user-friendly biometric type name
   */
  async getBiometricTypeName(): Promise<string> {
    const biometryType = await this.getBiometricType();

    switch (biometryType) {
      case BiometryTypes.FaceID:
        return 'Face ID';
      case BiometryTypes.TouchID:
        return 'Touch ID';
      case BiometryTypes.Biometrics:
        return 'Biometrics';
      default:
        return 'None';
    }
  }

  /**
   * Authenticate and execute a callback on success
   */
  async authenticateAndExecute<T>(
    callback: () => Promise<T>,
    config?: BiometricConfig
  ): Promise<T> {
    const authenticated = await this.authenticate(config);

    if (!authenticated) {
      throw new BiometricError('Authentication required');
    }

    return await callback();
  }
}

// Singleton instance
let biometricInstance: BiometricAuth | null = null;

export function getBiometricAuth(): BiometricAuth {
  if (!biometricInstance) {
    biometricInstance = new BiometricAuth();
  }
  return biometricInstance;
}
