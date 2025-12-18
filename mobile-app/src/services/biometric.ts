import ReactNativeBiometrics from 'react-native-biometrics';
import { BIOMETRIC_PROMPT } from '@/constants';

class BiometricService {
  private rnBiometrics: ReactNativeBiometrics;

  constructor() {
    this.rnBiometrics = new ReactNativeBiometrics();
  }

  /**
   * Check if biometric authentication is available
   */
  async isAvailable(): Promise<{
    available: boolean;
    biometryType?: 'TouchID' | 'FaceID' | 'Fingerprint';
  }> {
    try {
      const { available, biometryType } = await this.rnBiometrics.isSensorAvailable();
      return {
        available,
        biometryType: biometryType as 'TouchID' | 'FaceID' | 'Fingerprint' | undefined,
      };
    } catch (error) {
      console.error('Biometric check failed:', error);
      return { available: false };
    }
  }

  /**
   * Authenticate using biometrics
   */
  async authenticate(promptMessage?: string): Promise<boolean> {
    try {
      const { success } = await this.rnBiometrics.simplePrompt({
        promptMessage: promptMessage || BIOMETRIC_PROMPT.subtitle,
        cancelButtonText: BIOMETRIC_PROMPT.cancelButton,
      });
      return success;
    } catch (error) {
      console.error('Biometric authentication failed:', error);
      return false;
    }
  }

  /**
   * Create biometric keys
   */
  async createKeys(): Promise<boolean> {
    try {
      const { publicKey } = await this.rnBiometrics.createKeys();
      return !!publicKey;
    } catch (error) {
      console.error('Failed to create biometric keys:', error);
      return false;
    }
  }

  /**
   * Delete biometric keys
   */
  async deleteKeys(): Promise<boolean> {
    try {
      const { keysDeleted } = await this.rnBiometrics.deleteKeys();
      return keysDeleted;
    } catch (error) {
      console.error('Failed to delete biometric keys:', error);
      return false;
    }
  }

  /**
   * Create signature with biometric authentication
   */
  async createSignature(payload: string): Promise<{ signature: string } | null> {
    try {
      const { success, signature } = await this.rnBiometrics.createSignature({
        promptMessage: BIOMETRIC_PROMPT.subtitle,
        payload,
      });
      return success && signature ? { signature } : null;
    } catch (error) {
      console.error('Failed to create signature:', error);
      return null;
    }
  }
}

export default new BiometricService();
