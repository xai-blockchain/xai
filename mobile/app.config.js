/**
 * XAI Wallet - Dynamic Expo Configuration
 *
 * This file provides environment-aware configuration for the XAI mobile app.
 * It extends app.json with dynamic values and environment variables.
 */

const IS_DEV = process.env.EXPO_PUBLIC_ENV === 'development';
const IS_PREVIEW = process.env.EXPO_PUBLIC_ENV === 'preview';
const IS_STAGING = process.env.EXPO_PUBLIC_ENV === 'staging';
const IS_PROD = process.env.EXPO_PUBLIC_ENV === 'production';

// Environment-specific configuration
const ENV_CONFIG = {
  development: {
    name: 'XAI Wallet (Dev)',
    scheme: 'xaiwallet-dev',
    apiUrl: process.env.EXPO_PUBLIC_API_URL || 'http://localhost:12001',
    enableDebug: true,
    enableMockData: true,
    sentryDsn: null,
    analyticsEnabled: false,
  },
  preview: {
    name: 'XAI Wallet (Preview)',
    scheme: 'xaiwallet-preview',
    apiUrl: process.env.EXPO_PUBLIC_API_URL || 'https://testnet.xai.network:12001',
    enableDebug: true,
    enableMockData: false,
    sentryDsn: process.env.SENTRY_DSN,
    analyticsEnabled: false,
  },
  staging: {
    name: 'XAI Wallet (Staging)',
    scheme: 'xaiwallet-staging',
    apiUrl: process.env.EXPO_PUBLIC_API_URL || 'https://staging.xai.network:12001',
    enableDebug: false,
    enableMockData: false,
    sentryDsn: process.env.SENTRY_DSN,
    analyticsEnabled: true,
  },
  production: {
    name: 'XAI Wallet',
    scheme: 'xaiwallet',
    apiUrl: process.env.EXPO_PUBLIC_API_URL || 'https://api.xai.network',
    enableDebug: false,
    enableMockData: false,
    sentryDsn: process.env.SENTRY_DSN,
    analyticsEnabled: true,
  },
};

const getEnvConfig = () => {
  if (IS_DEV) return ENV_CONFIG.development;
  if (IS_PREVIEW) return ENV_CONFIG.preview;
  if (IS_STAGING) return ENV_CONFIG.staging;
  if (IS_PROD) return ENV_CONFIG.production;
  return ENV_CONFIG.development; // Default to development
};

const envConfig = getEnvConfig();

module.exports = ({ config }) => {
  return {
    ...config,
    name: envConfig.name,
    scheme: envConfig.scheme,
    extra: {
      ...config.extra,
      // Environment information
      env: process.env.EXPO_PUBLIC_ENV || 'development',

      // API Configuration
      apiUrl: envConfig.apiUrl,
      wsUrl: envConfig.apiUrl.replace(/^http/, 'ws'),

      // Feature flags
      enableDebug: envConfig.enableDebug,
      enableMockData: envConfig.enableMockData,
      analyticsEnabled: envConfig.analyticsEnabled,

      // Third-party services
      sentryDsn: envConfig.sentryDsn,

      // Build information
      buildDate: new Date().toISOString(),
      buildNumber: process.env.EAS_BUILD_NUMBER || '1',
      gitCommit: process.env.EAS_BUILD_GIT_COMMIT_HASH || 'local',

      // XAI Network configuration
      network: {
        name: IS_PROD ? 'mainnet' : 'testnet',
        chainId: IS_PROD ? 'xai-1' : 'xai-testnet-1',
        explorerUrl: IS_PROD
          ? 'https://explorer.xai.network'
          : 'https://testnet-explorer.xai.network',
        faucetEnabled: !IS_PROD,
      },

      // Security configuration
      security: {
        biometricsRequired: IS_PROD,
        pinRequired: true,
        sessionTimeout: IS_PROD ? 300000 : 3600000, // 5 min prod, 1 hour dev
        maxPinAttempts: 5,
      },

      // EAS configuration
      eas: {
        projectId: process.env.EAS_PROJECT_ID || config.extra?.eas?.projectId,
      },
    },

    // Update configuration based on environment
    updates: IS_PROD
      ? {
          enabled: true,
          fallbackToCacheTimeout: 30000,
          checkAutomatically: 'ON_LOAD',
          url: `https://u.expo.dev/${process.env.EAS_PROJECT_ID}`,
        }
      : {
          enabled: false,
        },

    // iOS specific overrides
    ios: {
      ...config.ios,
      bundleIdentifier: IS_PROD
        ? 'com.xai.wallet'
        : `com.xai.wallet.${process.env.EXPO_PUBLIC_ENV || 'dev'}`,
    },

    // Android specific overrides
    android: {
      ...config.android,
      package: IS_PROD
        ? 'com.xai.wallet'
        : `com.xai.wallet.${process.env.EXPO_PUBLIC_ENV || 'dev'}`,
    },

    // Plugins with environment-specific configuration
    plugins: [
      ...(config.plugins || []),
      // Add Sentry for non-dev environments
      ...(envConfig.sentryDsn
        ? [
            [
              '@sentry/react-native/expo',
              {
                organization: process.env.SENTRY_ORG || 'xai-network',
                project: process.env.SENTRY_PROJECT || 'xai-wallet-mobile',
              },
            ],
          ]
        : []),
    ],
  };
};
