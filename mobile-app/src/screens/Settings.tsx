import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  ScrollView,
  Switch,
  Alert,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { useWalletStore } from '@/store/wallet';
import { useAppStore } from '@/store/app';
import { formatAddress } from '@/utils/format';
import { COLORS } from '@/constants';

const Settings: React.FC = () => {
  const { wallet, deleteWallet } = useWalletStore();
  const { settings, updateSettings, biometricConfig, enableBiometric, disableBiometric } = useAppStore();

  const handleBiometricToggle = async (value: boolean) => {
    if (value) {
      const result = await enableBiometric();
      if (!result.success) {
        Alert.alert('Error', result.error || 'Failed to enable biometric');
      }
    } else {
      await disableBiometric();
    }
  };

  const handleDeleteWallet = () => {
    Alert.alert(
      'Delete Wallet',
      'Are you sure you want to delete your wallet? This action cannot be undone. Make sure you have backed up your recovery phrase.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            await deleteWallet();
          },
        },
      ],
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollView}>
        {/* Wallet Info */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Wallet</Text>
          <View style={styles.card}>
            <View style={styles.walletInfo}>
              <Text style={styles.walletLabel}>Address</Text>
              <Text style={styles.walletAddress}>{formatAddress(wallet?.address || '', 12)}</Text>
            </View>
          </View>
        </View>

        {/* Security */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Security</Text>

          <SettingItem
            icon="fingerprint"
            title="Biometric Authentication"
            subtitle={biometricConfig.biometryType || 'Face ID / Touch ID'}
            rightComponent={
              <Switch
                value={settings.biometricEnabled}
                onValueChange={handleBiometricToggle}
                trackColor={{ false: COLORS.border, true: COLORS.primary }}
              />
            }
          />

          <SettingItem
            icon="lock-clock"
            title="Auto-Lock"
            subtitle="Lock app when inactive"
            rightComponent={
              <Switch
                value={settings.autoLockEnabled}
                onValueChange={value => updateSettings({ autoLockEnabled: value })}
                trackColor={{ false: COLORS.border, true: COLORS.primary }}
              />
            }
          />

          <SettingItem
            icon="key-variant"
            title="Show Recovery Phrase"
            subtitle="View your backup phrase"
            onPress={() => Alert.alert('Info', 'Recovery phrase viewing will be implemented')}
          />
        </View>

        {/* Network */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Network</Text>

          <SettingItem
            icon="cloud-outline"
            title="Light Client Mode"
            subtitle="Reduce bandwidth usage"
            rightComponent={
              <Switch
                value={settings.lightClientMode}
                onValueChange={value => updateSettings({ lightClientMode: value })}
                trackColor={{ false: COLORS.border, true: COLORS.primary }}
              />
            }
          />

          <SettingItem
            icon="server"
            title="Node Endpoint"
            subtitle={settings.apiEndpoint}
            onPress={() => Alert.alert('Info', 'Node endpoint configuration will be implemented')}
          />
        </View>

        {/* Notifications */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Notifications</Text>

          <SettingItem
            icon="bell-outline"
            title="Push Notifications"
            subtitle="Receive transaction alerts"
            rightComponent={
              <Switch
                value={settings.pushNotificationsEnabled}
                onValueChange={value => updateSettings({ pushNotificationsEnabled: value })}
                trackColor={{ false: COLORS.border, true: COLORS.primary }}
              />
            }
          />
        </View>

        {/* About */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>About</Text>

          <SettingItem
            icon="information-outline"
            title="About XAI Wallet"
            subtitle="Version 1.0.0"
            onPress={() => Alert.alert('XAI Wallet', 'Version 1.0.0\n\nAI-Powered Blockchain Wallet')}
          />

          <SettingItem
            icon="book-open-outline"
            title="Terms of Service"
            onPress={() => Alert.alert('Info', 'Terms of service will be shown')}
          />

          <SettingItem
            icon="shield-check-outline"
            title="Privacy Policy"
            onPress={() => Alert.alert('Info', 'Privacy policy will be shown')}
          />
        </View>

        {/* Danger Zone */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Danger Zone</Text>

          <TouchableOpacity style={styles.dangerButton} onPress={handleDeleteWallet}>
            <Icon name="delete-outline" size={24} color={COLORS.error} />
            <Text style={styles.dangerButtonText}>Delete Wallet</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const SettingItem: React.FC<{
  icon: string;
  title: string;
  subtitle?: string;
  rightComponent?: React.ReactNode;
  onPress?: () => void;
}> = ({ icon, title, subtitle, rightComponent, onPress }) => (
  <TouchableOpacity
    style={styles.settingItem}
    onPress={onPress}
    disabled={!onPress && !rightComponent}>
    <Icon name={icon} size={24} color={COLORS.text} style={styles.settingIcon} />
    <View style={styles.settingContent}>
      <Text style={styles.settingTitle}>{title}</Text>
      {subtitle && <Text style={styles.settingSubtitle}>{subtitle}</Text>}
    </View>
    {rightComponent || (onPress && <Icon name="chevron-right" size={24} color={COLORS.text} />)}
  </TouchableOpacity>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  scrollView: {
    flex: 1,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.text,
    opacity: 0.6,
    textTransform: 'uppercase',
    marginLeft: 16,
    marginBottom: 8,
    marginTop: 16,
  },
  card: {
    backgroundColor: COLORS.card,
    marginHorizontal: 16,
    padding: 16,
    borderRadius: 12,
  },
  walletInfo: {
    gap: 4,
  },
  walletLabel: {
    fontSize: 12,
    color: COLORS.text,
    opacity: 0.6,
  },
  walletAddress: {
    fontSize: 14,
    fontWeight: '500',
    color: COLORS.text,
    fontFamily: 'monospace',
  },
  settingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.card,
    marginHorizontal: 16,
    padding: 16,
    borderRadius: 12,
    marginBottom: 8,
  },
  settingIcon: {
    marginRight: 12,
  },
  settingContent: {
    flex: 1,
  },
  settingTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: COLORS.text,
    marginBottom: 2,
  },
  settingSubtitle: {
    fontSize: 12,
    color: COLORS.text,
    opacity: 0.6,
  },
  dangerButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: COLORS.error + '10',
    marginHorizontal: 16,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: COLORS.error,
    gap: 8,
  },
  dangerButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.error,
  },
});

export default Settings;
