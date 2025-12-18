/**
 * TypeScript Type Definitions for XAI Biometric Authentication
 *
 * Use these types across mobile SDKs (React Native, iOS, Android)
 * to ensure consistent biometric authentication interfaces.
 */

/**
 * Types of biometric authentication supported across platforms
 */
export enum BiometricType {
  FACE_ID = 'face_id',           // iOS Face ID
  TOUCH_ID = 'touch_id',         // iOS Touch ID
  FINGERPRINT = 'fingerprint',   // Android fingerprint
  IRIS = 'iris',                 // Samsung iris scanner
  VOICE = 'voice',               // Voice recognition
  NONE = 'none'                  // No biometrics available
}

/**
 * Biometric authentication error codes
 */
export enum BiometricError {
  NOT_AVAILABLE = 'not_available',
  NOT_ENROLLED = 'not_enrolled',
  USER_CANCEL = 'user_cancel',
  AUTHENTICATION_FAILED = 'authentication_failed',
  LOCKOUT = 'lockout',
  PERMANENT_LOCKOUT = 'permanent_lockout',
  HARDWARE_ERROR = 'hardware_error',
  TIMEOUT = 'timeout',
  UNKNOWN = 'unknown'
}

/**
 * Security level of biometric authentication
 */
export type BiometricSecurityLevel = 'strong' | 'weak' | 'none';

/**
 * Device biometric capabilities
 */
export interface BiometricCapability {
  /** Whether biometric authentication is available */
  available: boolean;

  /** Whether user has enrolled biometrics */
  enrolled: boolean;

  /** List of available biometric types */
  biometricTypes: BiometricType[];

  /** Whether biometric hardware is detected */
  hardwareDetected: boolean;

  /** Security level of available biometrics */
  securityLevel: BiometricSecurityLevel;
}

/**
 * Configuration for biometric authentication prompt
 */
export interface BiometricConfig {
  /** Message to display in authentication prompt */
  promptMessage: string;

  /** Text for cancel button */
  cancelButtonText: string;

  /** Allow fallback to device passcode */
  fallbackToPasscode: boolean;

  /** Authentication timeout in seconds */
  timeoutSeconds?: number;

  /** Subtitle text (Android only) */
  subtitle?: string;

  /** Description text (Android only) */
  description?: string;

  /** Negative button text (Android only) */
  negativeButtonText?: string;
}

/**
 * Result of biometric authentication attempt
 */
export interface BiometricResult {
  /** Whether authentication was successful */
  success: boolean;

  /** Type of biometric used */
  biometricType: BiometricType;

  /** Error code if authentication failed */
  errorCode?: BiometricError;

  /** Human-readable error message */
  errorMessage?: string;

  /** Unix timestamp of authentication attempt */
  timestamp?: number;
}

/**
 * Configuration for secure key storage
 */
export interface SecureKeyConfig {
  /** Alias/identifier for the key */
  keyAlias: string;

  /** Require biometric authentication to access key */
  requireBiometric: boolean;

  /** Invalidate key when new biometrics are enrolled */
  invalidateOnEnrollment: boolean;

  /** User authentication validity duration in seconds */
  authValidityDuration?: number;
}

/**
 * Options for key derivation from biometric
 */
export interface KeyDerivationOptions {
  /** Salt for key derivation (hex string) */
  salt: string;

  /** Number of PBKDF2 iterations */
  iterations: number;

  /** Derived key length in bytes */
  keyLength: number;

  /** Hash algorithm (default: 'SHA-256') */
  algorithm?: 'SHA-256' | 'SHA-512';
}

/**
 * Encrypted data container
 */
export interface EncryptedData {
  /** Encrypted data (base64) */
  ciphertext: string;

  /** Initialization vector (base64) */
  iv: string;

  /** Authentication tag for AEAD (base64) */
  tag?: string;

  /** Encryption algorithm used */
  algorithm: string;

  /** Key alias used for encryption */
  keyAlias: string;
}

/**
 * Biometric authentication provider interface
 */
export interface IBiometricAuthProvider {
  /**
   * Check if biometric authentication is available
   */
  isAvailable(): Promise<BiometricCapability>;

  /**
   * Authenticate user with biometrics
   */
  authenticate(config: BiometricConfig): Promise<BiometricResult>;

  /**
   * Get the primary biometric type available
   */
  getAuthType(): Promise<BiometricType>;

  /**
   * Invalidate current authentication session
   */
  invalidateAuthentication(): Promise<boolean>;

  /**
   * Store data encrypted with biometric-protected key
   */
  storeSecure(
    data: string,
    config: SecureKeyConfig
  ): Promise<EncryptedData>;

  /**
   * Retrieve and decrypt data with biometric authentication
   */
  retrieveSecure(
    encrypted: EncryptedData,
    promptConfig: BiometricConfig
  ): Promise<string | null>;

  /**
   * Delete securely stored data
   */
  deleteSecure(keyAlias: string): Promise<boolean>;
}

/**
 * Wallet key storage configuration
 */
export interface WalletKeyConfig {
  /** Wallet address/identifier */
  walletId: string;

  /** Require biometric to access private key */
  requireBiometric: boolean;

  /** Backup encryption password (optional) */
  backupPassword?: string;

  /** Number of failed attempts before lockout */
  maxAttempts?: number;
}

/**
 * Platform-specific biometric info
 */
export interface PlatformBiometricInfo {
  /** Platform name */
  platform: 'ios' | 'android' | 'unknown';

  /** OS version */
  osVersion: string;

  /** Available biometric types */
  availableTypes: BiometricType[];

  /** Whether strong biometrics are supported */
  supportsStrongAuth: boolean;

  /** Whether crypto operations are supported */
  supportsCryptoOperations: boolean;
}
