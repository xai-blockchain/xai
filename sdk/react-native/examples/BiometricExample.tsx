/**
 * Biometric Authentication Example
 * Demonstrates Face ID / Touch ID integration for secure wallet operations
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  Button,
  Alert,
  StyleSheet,
  Switch,
} from 'react-native';
import {
  getBiometricAuth,
  getXAIWallet,
  BiometricError,
} from '@xai/react-native-sdk';

export default function BiometricExample() {
  const [biometricAvailable, setBiometricAvailable] = useState(false);
  const [biometricType, setBiometricType] = useState('None');
  const [biometricEnabled, setBiometricEnabled] = useState(false);
  const [hasWallet, setHasWallet] = useState(false);

  const biometric = getBiometricAuth();
  const wallet = getXAIWallet();

  useEffect(() => {
    checkBiometricAvailability();
    checkWalletStatus();
  }, []);

  const checkBiometricAvailability = async () => {
    const available = await biometric.isAvailable();
    setBiometricAvailable(available);

    if (available) {
      const type = await biometric.getBiometricTypeName();
      setBiometricType(type);
    }
  };

  const checkWalletStatus = async () => {
    await wallet.initialize();
    const exists = await wallet.hasWallet();
    setHasWallet(exists);

    if (exists) {
      const enabled = await wallet.isBiometricEnabled();
      setBiometricEnabled(enabled);
    }
  };

  const handleCreateWallet = async () => {
    try {
      const newWallet = await wallet.createWallet(biometricAvailable);

      Alert.alert(
        'Wallet Created',
        `Address: ${newWallet.address}\n\n${
          biometricAvailable
            ? `${biometricType} authentication enabled`
            : 'Biometric authentication not available'
        }`
      );

      await checkWalletStatus();
    } catch (error: any) {
      Alert.alert('Error', error.message);
    }
  };

  const handleToggleBiometric = async (enabled: boolean) => {
    try {
      await wallet.setBiometricEnabled(enabled, {
        title: 'Enable Biometric',
        description: `Use ${biometricType} to secure your wallet`,
      });

      setBiometricEnabled(enabled);

      Alert.alert(
        'Success',
        `${biometricType} ${enabled ? 'enabled' : 'disabled'}`
      );
    } catch (error: any) {
      if (error instanceof BiometricError) {
        Alert.alert('Biometric Error', error.message);
      } else {
        Alert.alert('Error', error.message);
      }
    }
  };

  const handleTestAuthentication = async () => {
    try {
      const authenticated = await biometric.authenticate({
        title: 'Test Authentication',
        description: `Authenticate with ${biometricType}`,
        cancelText: 'Cancel',
      });

      if (authenticated) {
        Alert.alert('Success', 'Authentication successful!');
      }
    } catch (error: any) {
      if (error instanceof BiometricError) {
        Alert.alert('Authentication Failed', error.message);
      } else {
        Alert.alert('Error', error.message);
      }
    }
  };

  const handleSignMessage = async () => {
    if (!hasWallet) {
      Alert.alert('Error', 'No wallet found');
      return;
    }

    try {
      const message = 'Hello, XAI Blockchain!';

      const signature = await wallet.signMessage(message, {
        title: 'Sign Message',
        description: `Authenticate to sign:\n"${message}"`,
      });

      Alert.alert(
        'Message Signed',
        `Signature:\n${signature.substring(0, 32)}...`
      );
    } catch (error: any) {
      if (error instanceof BiometricError) {
        Alert.alert('Authentication Failed', error.message);
      } else {
        Alert.alert('Error', error.message);
      }
    }
  };

  const handleExportMnemonic = async () => {
    if (!hasWallet) {
      Alert.alert('Error', 'No wallet found');
      return;
    }

    try {
      const mnemonic = await wallet.exportMnemonic({
        title: 'Export Mnemonic',
        description: 'Authenticate to view your recovery phrase',
      });

      Alert.alert(
        'Mnemonic Phrase',
        mnemonic,
        [{ text: 'OK', style: 'default' }],
        { cancelable: false }
      );
    } catch (error: any) {
      if (error instanceof BiometricError) {
        Alert.alert('Authentication Failed', error.message);
      } else {
        Alert.alert('Error', error.message);
      }
    }
  };

  const handleGetPrivateKey = async () => {
    if (!hasWallet) {
      Alert.alert('Error', 'No wallet found');
      return;
    }

    Alert.alert(
      'Warning',
      'Exporting your private key is dangerous. Only do this if you know what you are doing.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Continue',
          style: 'destructive',
          onPress: async () => {
            try {
              const privateKey = await wallet.getPrivateKey({
                title: 'Export Private Key',
                description: 'Authenticate to view your private key',
              });

              Alert.alert(
                'Private Key',
                `${privateKey.substring(0, 16)}...`,
                [{ text: 'OK' }],
                { cancelable: false }
              );
            } catch (error: any) {
              if (error instanceof BiometricError) {
                Alert.alert('Authentication Failed', error.message);
              } else {
                Alert.alert('Error', error.message);
              }
            }
          },
        },
      ]
    );
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Biometric Authentication</Text>

      {/* Biometric Status */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Biometric Status</Text>
        <Text>
          Available: {biometricAvailable ? 'Yes' : 'No'}
        </Text>
        <Text>Type: {biometricType}</Text>
      </View>

      {/* Wallet Status */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Wallet Status</Text>
        <Text>
          Wallet Exists: {hasWallet ? 'Yes' : 'No'}
        </Text>
        {hasWallet && (
          <View style={styles.switchRow}>
            <Text>Biometric Enabled:</Text>
            <Switch
              value={biometricEnabled}
              onValueChange={handleToggleBiometric}
              disabled={!biometricAvailable}
            />
          </View>
        )}
      </View>

      {/* Actions */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Actions</Text>

        {!hasWallet && (
          <Button
            title="Create Wallet"
            onPress={handleCreateWallet}
          />
        )}

        {biometricAvailable && (
          <View style={styles.buttonSpacing}>
            <Button
              title="Test Authentication"
              onPress={handleTestAuthentication}
            />
          </View>
        )}

        {hasWallet && (
          <>
            <View style={styles.buttonSpacing}>
              <Button
                title="Sign Message"
                onPress={handleSignMessage}
              />
            </View>

            <View style={styles.buttonSpacing}>
              <Button
                title="Export Mnemonic"
                onPress={handleExportMnemonic}
              />
            </View>

            <View style={styles.buttonSpacing}>
              <Button
                title="View Private Key"
                onPress={handleGetPrivateKey}
                color="#ff6b6b"
              />
            </View>
          </>
        )}
      </View>

      {/* Information */}
      <View style={styles.infoSection}>
        <Text style={styles.infoTitle}>How It Works</Text>
        <Text style={styles.infoText}>
          • Biometric authentication provides an extra layer of security
        </Text>
        <Text style={styles.infoText}>
          • Your private key is encrypted and stored in the device keychain
        </Text>
        <Text style={styles.infoText}>
          • {biometricType} is required for sensitive operations
        </Text>
        <Text style={styles.infoText}>
          • Keys never leave your device
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
  },
  section: {
    backgroundColor: 'white',
    padding: 15,
    marginBottom: 15,
    borderRadius: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 10,
  },
  buttonSpacing: {
    marginTop: 10,
  },
  infoSection: {
    backgroundColor: '#e3f2fd',
    padding: 15,
    borderRadius: 8,
    marginTop: 10,
  },
  infoTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#1976d2',
  },
  infoText: {
    fontSize: 14,
    marginBottom: 5,
    color: '#424242',
  },
});
