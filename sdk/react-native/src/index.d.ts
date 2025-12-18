/**
 * XAI React Native SDK Type Definitions
 * TypeScript definitions for external consumers
 */

declare module '@xai/react-native-sdk' {
  // Re-export all types and interfaces
  export * from './types';
  export * from './clients/XAIClient';
  export * from './clients/XAIWallet';
  export * from './clients/BiometricAuth';
  export * from './clients/SecureStorage';
  export * from './clients/PushNotifications';
  export * from './hooks';
  export * from './utils/crypto';
}
