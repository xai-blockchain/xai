/**
 * Settings Screen - App configuration and preferences
 *
 * Production-ready features:
 * - Node URL configuration
 * - Theme toggle (dark/light)
 * - Currency selection
 * - Security settings (biometrics, PIN, auto-lock)
 * - About section with version
 * - Clear cache option
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Switch,
  Alert,
  Linking,
  Platform,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import * as Application from 'expo-application';
import * as LocalAuthentication from 'expo-local-authentication';
import { Card, Button, Input, Icon } from '../components';
import { useTheme } from '../theme';
import { triggerHaptic } from '../hooks/useHaptics';
import {
  loadSettings,
  saveSettings,
  clearCache,
  resetSettings,
} from '../utils/storage';
import { xaiApi } from '../services/api';
import { AppSettings, SecuritySettings } from '../types';
import { spacing, borderRadius } from '../theme/spacing';

// Currency options
const CURRENCIES = [
  { code: 'USD', symbol: '$', name: 'US Dollar' },
  { code: 'EUR', symbol: '\u20AC', name: 'Euro' },
  { code: 'GBP', symbol: '\u00A3', name: 'British Pound' },
  { code: 'JPY', symbol: '\u00A5', name: 'Japanese Yen' },
  { code: 'BTC', symbol: '\u20BF', name: 'Bitcoin' },
  { code: 'ETH', symbol: '\u039E', name: 'Ethereum' },
];

// Auto-lock timeout options (in minutes)
const AUTO_LOCK_OPTIONS = [
  { value: 0, label: 'Never' },
  { value: 1, label: '1 minute' },
  { value: 5, label: '5 minutes' },
  { value: 15, label: '15 minutes' },
  { value: 30, label: '30 minutes' },
];

type SettingsSection = 'network' | 'display' | 'security' | 'about' | 'data';

interface SettingRowProps {
  label: string;
  value?: string;
  onPress?: () => void;
  rightElement?: React.ReactNode;
  leftIcon?: string;
  isLast?: boolean;
  subtitle?: string;
}

function SettingRow({
  label,
  value,
  onPress,
  rightElement,
  leftIcon,
  isLast = false,
  subtitle,
}: SettingRowProps) {
  const theme = useTheme();

  const content = (
    <View
      style={[
        styles.settingRow,
        !isLast && { borderBottomWidth: 1, borderBottomColor: theme.colors.border },
      ]}
    >
      {leftIcon && (
        <View style={[styles.iconContainer, { backgroundColor: theme.colors.brand.primaryMuted }]}>
          <Icon name={leftIcon as any} size={18} color={theme.colors.brand.primary} />
        </View>
      )}
      <View style={styles.settingContent}>
        <Text style={[styles.settingLabel, { color: theme.colors.text }]}>{label}</Text>
        {subtitle && (
          <Text style={[styles.settingSubtitle, { color: theme.colors.textMuted }]}>
            {subtitle}
          </Text>
        )}
      </View>
      {value && (
        <Text style={[styles.settingValue, { color: theme.colors.textMuted }]}>{value}</Text>
      )}
      {rightElement}
      {onPress && !rightElement && (
        <Icon name="chevron-right" size={20} color={theme.colors.textMuted} />
      )}
    </View>
  );

  if (onPress) {
    return (
      <Button
        variant="ghost"
        onPress={() => {
          triggerHaptic('selection');
          onPress();
        }}
        style={styles.settingButton}
      >
        {content}
      </Button>
    );
  }

  return content;
}

export function SettingsScreen() {
  const theme = useTheme();
  const navigation = useNavigation();

  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [nodeUrl, setNodeUrl] = useState('');
  const [editingNodeUrl, setEditingNodeUrl] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [hasBiometrics, setHasBiometrics] = useState(false);
  const [clearingCache, setClearingCache] = useState(false);
  const [showCurrencyPicker, setShowCurrencyPicker] = useState(false);
  const [showAutoLockPicker, setShowAutoLockPicker] = useState(false);

  // Get app version
  const appVersion = Application.nativeApplicationVersion || '1.0.0';
  const buildNumber = Application.nativeBuildVersion || '1';

  // Load settings and check biometrics
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const loadedSettings = await loadSettings();
      setSettings(loadedSettings);
      setNodeUrl(loadedSettings.nodeUrl);

      // Check if device has biometrics
      const compatible = await LocalAuthentication.hasHardwareAsync();
      const enrolled = await LocalAuthentication.isEnrolledAsync();
      setHasBiometrics(compatible && enrolled);
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  };

  // Update a specific setting
  const updateSetting = useCallback(
    async <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
      if (!settings) return;

      const newSettings = { ...settings, [key]: value };
      setSettings(newSettings);
      await saveSettings({ [key]: value });
      triggerHaptic('selection');
    },
    [settings]
  );

  // Update security settings
  const updateSecuritySetting = useCallback(
    async <K extends keyof SecuritySettings>(key: K, value: SecuritySettings[K]) => {
      if (!settings) return;

      const newSecurity = { ...settings.security, [key]: value };
      const newSettings = { ...settings, security: newSecurity };
      setSettings(newSettings);
      await saveSettings({ security: newSecurity });
      triggerHaptic('selection');
    },
    [settings]
  );

  // Test node connection
  const testNodeConnection = async () => {
    if (!nodeUrl.trim()) {
      Alert.alert('Error', 'Please enter a node URL');
      return;
    }

    setTestingConnection(true);
    try {
      // Temporarily configure API with new URL
      const originalUrl = xaiApi.getBaseUrl();
      xaiApi.configure({ baseUrl: nodeUrl.trim() });

      const result = await xaiApi.getHealth();

      if (result.success) {
        Alert.alert('Success', 'Connected to node successfully!');
        await updateSetting('nodeUrl', nodeUrl.trim());
        setEditingNodeUrl(false);
      } else {
        // Restore original URL on failure
        xaiApi.configure({ baseUrl: originalUrl });
        Alert.alert('Connection Failed', result.error || 'Could not connect to node');
      }
    } catch (error) {
      Alert.alert('Connection Failed', 'Could not connect to the specified node');
    } finally {
      setTestingConnection(false);
    }
  };

  // Toggle biometrics
  const toggleBiometrics = async (enabled: boolean) => {
    if (enabled) {
      try {
        const result = await LocalAuthentication.authenticateAsync({
          promptMessage: 'Authenticate to enable biometric security',
          cancelLabel: 'Cancel',
        });

        if (result.success) {
          await updateSecuritySetting('biometricEnabled', true);
        }
      } catch (error) {
        Alert.alert('Error', 'Failed to enable biometric authentication');
      }
    } else {
      await updateSecuritySetting('biometricEnabled', false);
    }
  };

  // Clear app cache
  const handleClearCache = async () => {
    Alert.alert(
      'Clear Cache',
      'This will clear cached data including balances and transaction history. You will need to refresh to reload data.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: async () => {
            setClearingCache(true);
            try {
              await clearCache();
              triggerHaptic('success');
              Alert.alert('Success', 'Cache cleared successfully');
            } catch (error) {
              Alert.alert('Error', 'Failed to clear cache');
            } finally {
              setClearingCache(false);
            }
          },
        },
      ]
    );
  };

  // Reset all settings
  const handleResetSettings = () => {
    Alert.alert(
      'Reset Settings',
      'This will reset all settings to their default values. This does not affect your wallets.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset',
          style: 'destructive',
          onPress: async () => {
            try {
              await resetSettings();
              await loadInitialData();
              triggerHaptic('success');
              Alert.alert('Success', 'Settings reset to defaults');
            } catch (error) {
              Alert.alert('Error', 'Failed to reset settings');
            }
          },
        },
      ]
    );
  };

  if (!settings) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <View style={styles.loadingContainer}>
          <Text style={[styles.loadingText, { color: theme.colors.textMuted }]}>
            Loading settings...
          </Text>
        </View>
      </View>
    );
  }

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: theme.colors.background }]}
      contentContainerStyle={styles.content}
    >
      {/* Network Settings */}
      <Card title="Network">
        {editingNodeUrl ? (
          <View>
            <Input
              label="Node URL"
              value={nodeUrl}
              onChangeText={setNodeUrl}
              placeholder="http://localhost:12001"
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
            />
            <View style={styles.nodeButtonsRow}>
              <Button
                title="Cancel"
                variant="outline"
                size="small"
                onPress={() => {
                  setNodeUrl(settings.nodeUrl);
                  setEditingNodeUrl(false);
                }}
                style={styles.nodeButton}
              />
              <Button
                title="Test & Save"
                size="small"
                loading={testingConnection}
                onPress={testNodeConnection}
                style={styles.nodeButton}
              />
            </View>
          </View>
        ) : (
          <SettingRow
            label="Node URL"
            value={settings.nodeUrl}
            leftIcon="server"
            onPress={() => setEditingNodeUrl(true)}
            isLast
          />
        )}
      </Card>

      {/* Display Settings */}
      <Card title="Display">
        <SettingRow
          label="Theme"
          leftIcon="moon"
          rightElement={
            <View style={styles.themeButtons}>
              {(['dark', 'light', 'system'] as const).map((themeOption) => (
                <Button
                  key={themeOption}
                  title={themeOption.charAt(0).toUpperCase() + themeOption.slice(1)}
                  variant={settings.theme === themeOption ? 'primary' : 'secondary'}
                  size="small"
                  onPress={() => updateSetting('theme', themeOption)}
                  style={styles.themeButton}
                />
              ))}
            </View>
          }
        />
        <SettingRow
          label="Currency"
          value={settings.currency}
          leftIcon="dollar"
          onPress={() => setShowCurrencyPicker(true)}
        />
        <SettingRow
          label="Show Fiat Values"
          leftIcon="chart"
          rightElement={
            <Switch
              value={settings.display.showFiatValue}
              onValueChange={(value) =>
                updateSetting('display', { ...settings.display, showFiatValue: value })
              }
              trackColor={{
                false: theme.colors.surfaceOverlay,
                true: theme.colors.brand.primaryMuted,
              }}
              thumbColor={
                settings.display.showFiatValue
                  ? theme.colors.brand.primary
                  : theme.colors.textMuted
              }
            />
          }
        />
        <SettingRow
          label="Hide Balance"
          leftIcon="eye-off"
          subtitle="Hide balance on home screen"
          rightElement={
            <Switch
              value={settings.security.hideBalance}
              onValueChange={(value) => updateSecuritySetting('hideBalance', value)}
              trackColor={{
                false: theme.colors.surfaceOverlay,
                true: theme.colors.brand.primaryMuted,
              }}
              thumbColor={
                settings.security.hideBalance
                  ? theme.colors.brand.primary
                  : theme.colors.textMuted
              }
            />
          }
          isLast
        />
      </Card>

      {/* Security Settings */}
      <Card title="Security">
        {hasBiometrics && (
          <SettingRow
            label="Biometric Authentication"
            leftIcon="fingerprint"
            subtitle={Platform.OS === 'ios' ? 'Face ID / Touch ID' : 'Fingerprint'}
            rightElement={
              <Switch
                value={settings.security.biometricEnabled}
                onValueChange={toggleBiometrics}
                trackColor={{
                  false: theme.colors.surfaceOverlay,
                  true: theme.colors.brand.primaryMuted,
                }}
                thumbColor={
                  settings.security.biometricEnabled
                    ? theme.colors.brand.primary
                    : theme.colors.textMuted
                }
              />
            }
          />
        )}
        <SettingRow
          label="Require Auth for Sending"
          leftIcon="lock"
          subtitle="Authenticate before sending transactions"
          rightElement={
            <Switch
              value={settings.security.requireAuthForSend}
              onValueChange={(value) => updateSecuritySetting('requireAuthForSend', value)}
              trackColor={{
                false: theme.colors.surfaceOverlay,
                true: theme.colors.brand.primaryMuted,
              }}
              thumbColor={
                settings.security.requireAuthForSend
                  ? theme.colors.brand.primary
                  : theme.colors.textMuted
              }
            />
          }
        />
        <SettingRow
          label="Auto-Lock Timeout"
          value={
            AUTO_LOCK_OPTIONS.find((opt) => opt.value === settings.security.autoLockTimeout)
              ?.label || '5 minutes'
          }
          leftIcon="clock"
          onPress={() => setShowAutoLockPicker(true)}
          isLast
        />
      </Card>

      {/* Data Management */}
      <Card title="Data">
        <SettingRow
          label="Clear Cache"
          leftIcon="trash"
          subtitle="Clear cached balances and history"
          onPress={handleClearCache}
        />
        <SettingRow
          label="Reset Settings"
          leftIcon="refresh"
          subtitle="Reset all settings to defaults"
          onPress={handleResetSettings}
          isLast
        />
      </Card>

      {/* About */}
      <Card title="About">
        <SettingRow label="Version" value={`${appVersion} (${buildNumber})`} leftIcon="info" />
        <SettingRow
          label="Website"
          value="xai.network"
          leftIcon="globe"
          onPress={() => Linking.openURL('https://xai.network')}
        />
        <SettingRow
          label="GitHub"
          value="github.com/xai"
          leftIcon="github"
          onPress={() => Linking.openURL('https://github.com/xai')}
        />
        <SettingRow
          label="Terms of Service"
          leftIcon="file-text"
          onPress={() => Linking.openURL('https://xai.network/terms')}
        />
        <SettingRow
          label="Privacy Policy"
          leftIcon="shield"
          onPress={() => Linking.openURL('https://xai.network/privacy')}
          isLast
        />
      </Card>

      {/* Currency Picker Modal */}
      {showCurrencyPicker && (
        <View style={[styles.pickerOverlay, { backgroundColor: theme.colors.overlay }]}>
          <View style={[styles.pickerContainer, { backgroundColor: theme.colors.surface }]}>
            <View style={styles.pickerHeader}>
              <Text style={[styles.pickerTitle, { color: theme.colors.text }]}>
                Select Currency
              </Text>
              <Button
                title="Done"
                variant="ghost"
                size="small"
                onPress={() => setShowCurrencyPicker(false)}
              />
            </View>
            <ScrollView style={styles.pickerList}>
              {CURRENCIES.map((currency) => (
                <Button
                  key={currency.code}
                  variant="ghost"
                  onPress={() => {
                    updateSetting('currency', currency.code);
                    setShowCurrencyPicker(false);
                  }}
                  style={[
                    styles.pickerOption,
                    settings.currency === currency.code && {
                      backgroundColor: theme.colors.brand.primaryMuted,
                    },
                  ]}
                >
                  <View style={styles.pickerOptionContent}>
                    <Text style={[styles.currencySymbol, { color: theme.colors.text }]}>
                      {currency.symbol}
                    </Text>
                    <View style={styles.currencyInfo}>
                      <Text style={[styles.currencyCode, { color: theme.colors.text }]}>
                        {currency.code}
                      </Text>
                      <Text style={[styles.currencyName, { color: theme.colors.textMuted }]}>
                        {currency.name}
                      </Text>
                    </View>
                    {settings.currency === currency.code && (
                      <Icon name="check" size={20} color={theme.colors.brand.primary} />
                    )}
                  </View>
                </Button>
              ))}
            </ScrollView>
          </View>
        </View>
      )}

      {/* Auto-Lock Picker Modal */}
      {showAutoLockPicker && (
        <View style={[styles.pickerOverlay, { backgroundColor: theme.colors.overlay }]}>
          <View style={[styles.pickerContainer, { backgroundColor: theme.colors.surface }]}>
            <View style={styles.pickerHeader}>
              <Text style={[styles.pickerTitle, { color: theme.colors.text }]}>
                Auto-Lock Timeout
              </Text>
              <Button
                title="Done"
                variant="ghost"
                size="small"
                onPress={() => setShowAutoLockPicker(false)}
              />
            </View>
            <ScrollView style={styles.pickerList}>
              {AUTO_LOCK_OPTIONS.map((option) => (
                <Button
                  key={option.value}
                  variant="ghost"
                  onPress={() => {
                    updateSecuritySetting('autoLockTimeout', option.value);
                    setShowAutoLockPicker(false);
                  }}
                  style={[
                    styles.pickerOption,
                    settings.security.autoLockTimeout === option.value && {
                      backgroundColor: theme.colors.brand.primaryMuted,
                    },
                  ]}
                >
                  <View style={styles.pickerOptionContent}>
                    <Text style={[styles.optionLabel, { color: theme.colors.text }]}>
                      {option.label}
                    </Text>
                    {settings.security.autoLockTimeout === option.value && (
                      <Icon name="check" size={20} color={theme.colors.brand.primary} />
                    )}
                  </View>
                </Button>
              ))}
            </ScrollView>
          </View>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    padding: spacing['4'],
    paddingBottom: spacing['8'],
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    fontSize: 16,
  },
  settingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing['3'],
    paddingHorizontal: spacing['2'],
  },
  settingButton: {
    padding: 0,
    margin: 0,
  },
  iconContainer: {
    width: 32,
    height: 32,
    borderRadius: borderRadius.md,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: spacing['3'],
  },
  settingContent: {
    flex: 1,
  },
  settingLabel: {
    fontSize: 16,
    fontWeight: '500',
  },
  settingSubtitle: {
    fontSize: 12,
    marginTop: 2,
  },
  settingValue: {
    fontSize: 14,
    marginRight: spacing['2'],
  },
  themeButtons: {
    flexDirection: 'row',
    gap: spacing['2'],
  },
  themeButton: {
    minWidth: 60,
  },
  nodeButtonsRow: {
    flexDirection: 'row',
    gap: spacing['2'],
    marginTop: spacing['2'],
  },
  nodeButton: {
    flex: 1,
  },
  // Picker modal
  pickerOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'flex-end',
  },
  pickerContainer: {
    borderTopLeftRadius: borderRadius.xl,
    borderTopRightRadius: borderRadius.xl,
    maxHeight: '60%',
    paddingBottom: spacing['6'],
  },
  pickerHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: spacing['4'],
    borderBottomWidth: 1,
  },
  pickerTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  pickerList: {
    padding: spacing['2'],
  },
  pickerOption: {
    padding: spacing['3'],
    borderRadius: borderRadius.md,
    marginBottom: spacing['1'],
  },
  pickerOptionContent: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  currencySymbol: {
    fontSize: 20,
    fontWeight: '600',
    width: 32,
    textAlign: 'center',
  },
  currencyInfo: {
    flex: 1,
    marginLeft: spacing['3'],
  },
  currencyCode: {
    fontSize: 16,
    fontWeight: '600',
  },
  currencyName: {
    fontSize: 12,
    marginTop: 2,
  },
  optionLabel: {
    fontSize: 16,
    flex: 1,
  },
});
