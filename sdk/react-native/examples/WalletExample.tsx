/**
 * Complete Wallet Example
 * Demonstrates wallet creation, import, and transaction sending with biometric authentication
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  Button,
  Alert,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import {
  XAIClient,
  useWallet,
  useTransactions,
  useBlockchain,
  getBiometricAuth,
} from '@xai/react-native-sdk';

// Initialize client
const client = new XAIClient({
  baseUrl: 'http://localhost:5000',
  timeout: 30000,
});

export default function WalletExample() {
  const {
    wallet,
    balance,
    loading: walletLoading,
    error: walletError,
    createWallet,
    importWallet,
    deleteWallet,
    refreshBalance,
  } = useWallet({
    client,
    autoRefreshBalance: true,
    refreshInterval: 30000,
  });

  const {
    transactions,
    sendTransaction,
    loading: txLoading,
    error: txError,
  } = useTransactions({
    client,
    address: wallet?.address || null,
    autoRefresh: true,
    refreshInterval: 15000,
  });

  const { info, latestBlock } = useBlockchain({
    client,
    autoRefresh: true,
    refreshInterval: 10000,
  });

  const [mnemonic, setMnemonic] = useState('');
  const [recipient, setRecipient] = useState('');
  const [amount, setAmount] = useState('');
  const [showMnemonic, setShowMnemonic] = useState(false);

  const handleCreateWallet = async () => {
    try {
      const biometric = getBiometricAuth();
      const available = await biometric.isAvailable();

      const newWallet = await createWallet(available);

      if (newWallet.mnemonic) {
        setMnemonic(newWallet.mnemonic);
        setShowMnemonic(true);
      }

      Alert.alert(
        'Wallet Created',
        `Address: ${newWallet.address}\n\nPlease save your mnemonic phrase!`
      );
    } catch (error: any) {
      Alert.alert('Error', error.message);
    }
  };

  const handleImportWallet = async () => {
    if (!mnemonic.trim()) {
      Alert.alert('Error', 'Please enter a mnemonic phrase');
      return;
    }

    try {
      const biometric = getBiometricAuth();
      const available = await biometric.isAvailable();

      const importedWallet = await importWallet(mnemonic.trim(), available);

      Alert.alert(
        'Wallet Imported',
        `Address: ${importedWallet.address}`
      );
      setMnemonic('');
      setShowMnemonic(false);
    } catch (error: any) {
      Alert.alert('Error', error.message);
    }
  };

  const handleDeleteWallet = async () => {
    Alert.alert(
      'Delete Wallet',
      'Are you sure? This action cannot be undone!',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteWallet();
              Alert.alert('Success', 'Wallet deleted');
            } catch (error: any) {
              Alert.alert('Error', error.message);
            }
          },
        },
      ]
    );
  };

  const handleSendTransaction = async () => {
    if (!wallet) return;
    if (!recipient.trim() || !amount.trim()) {
      Alert.alert('Error', 'Please enter recipient and amount');
      return;
    }

    try {
      const { fee } = await client.estimateFee({
        from: wallet.address,
        to: recipient.trim(),
        value: amount,
      });

      Alert.alert(
        'Confirm Transaction',
        `Send ${amount} XAI to ${recipient.substring(0, 10)}...?\n\nFee: ${fee} XAI`,
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Send',
            onPress: async () => {
              try {
                const tx = await sendTransaction({
                  from: wallet.address,
                  to: recipient.trim(),
                  value: amount,
                });

                Alert.alert(
                  'Success',
                  `Transaction sent!\n\nHash: ${tx.hash}`
                );
                setRecipient('');
                setAmount('');
              } catch (error: any) {
                Alert.alert('Error', error.message);
              }
            },
          },
        ]
      );
    } catch (error: any) {
      Alert.alert('Error', error.message);
    }
  };

  if (walletLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
        <Text>Loading wallet...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      {/* Blockchain Info */}
      {info && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Blockchain Info</Text>
          <Text>Height: {info.height}</Text>
          <Text>Latest Block: {latestBlock?.number}</Text>
          <Text>Difficulty: {info.difficulty}</Text>
        </View>
      )}

      {/* Wallet Section */}
      {!wallet ? (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Create or Import Wallet</Text>

          <Button title="Create New Wallet" onPress={handleCreateWallet} />

          <Text style={styles.divider}>OR</Text>

          <TextInput
            style={styles.input}
            placeholder="Enter mnemonic phrase"
            value={mnemonic}
            onChangeText={setMnemonic}
            multiline
            numberOfLines={3}
          />
          <Button title="Import Wallet" onPress={handleImportWallet} />
        </View>
      ) : (
        <>
          {/* Wallet Info */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Wallet</Text>
            <Text style={styles.label}>Address:</Text>
            <Text style={styles.value}>{wallet.address}</Text>

            <Text style={styles.label}>Balance:</Text>
            <Text style={styles.balance}>{balance || '0'} XAI</Text>

            <View style={styles.buttonRow}>
              <Button title="Refresh" onPress={refreshBalance} />
              <Button
                title="Delete Wallet"
                onPress={handleDeleteWallet}
                color="#ff4444"
              />
            </View>
          </View>

          {/* Send Transaction */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Send Transaction</Text>

            <TextInput
              style={styles.input}
              placeholder="Recipient Address"
              value={recipient}
              onChangeText={setRecipient}
            />

            <TextInput
              style={styles.input}
              placeholder="Amount (XAI)"
              value={amount}
              onChangeText={setAmount}
              keyboardType="numeric"
            />

            <Button
              title={txLoading ? 'Sending...' : 'Send'}
              onPress={handleSendTransaction}
              disabled={txLoading}
            />
          </View>

          {/* Transaction History */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>
              Recent Transactions ({transactions.length})
            </Text>

            {transactions.slice(0, 5).map((tx) => (
              <View key={tx.hash} style={styles.transaction}>
                <Text style={styles.txHash}>
                  {tx.hash.substring(0, 16)}...
                </Text>
                <Text>
                  {tx.from === wallet.address ? 'Sent' : 'Received'}{' '}
                  {tx.value} XAI
                </Text>
                <Text style={styles.txStatus}>{tx.status}</Text>
              </View>
            ))}
          </View>
        </>
      )}

      {/* Mnemonic Display */}
      {showMnemonic && mnemonic && (
        <View style={[styles.section, styles.mnemonicSection]}>
          <Text style={styles.warning}>⚠️ SAVE THIS MNEMONIC PHRASE</Text>
          <Text style={styles.mnemonic}>{mnemonic}</Text>
          <Button
            title="I've Saved It"
            onPress={() => {
              setShowMnemonic(false);
              setMnemonic('');
            }}
          />
        </View>
      )}

      {/* Errors */}
      {(walletError || txError) && (
        <View style={styles.errorSection}>
          <Text style={styles.error}>
            {walletError?.message || txError?.message}
          </Text>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
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
  label: {
    fontSize: 12,
    color: '#666',
    marginTop: 10,
  },
  value: {
    fontSize: 14,
    marginBottom: 5,
  },
  balance: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#4CAF50',
    marginBottom: 10,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 4,
    padding: 10,
    marginBottom: 10,
  },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 10,
  },
  divider: {
    textAlign: 'center',
    marginVertical: 15,
    color: '#999',
  },
  transaction: {
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
    paddingVertical: 10,
  },
  txHash: {
    fontFamily: 'monospace',
    fontSize: 12,
    color: '#666',
  },
  txStatus: {
    fontSize: 12,
    color: '#4CAF50',
    marginTop: 5,
  },
  mnemonicSection: {
    backgroundColor: '#fff3cd',
    borderColor: '#ffc107',
    borderWidth: 2,
  },
  warning: {
    color: '#ff6b6b',
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 10,
  },
  mnemonic: {
    fontFamily: 'monospace',
    fontSize: 14,
    padding: 10,
    backgroundColor: '#f8f9fa',
    borderRadius: 4,
    marginBottom: 10,
  },
  errorSection: {
    backgroundColor: '#ffebee',
    padding: 15,
    marginBottom: 15,
    borderRadius: 8,
  },
  error: {
    color: '#c62828',
  },
});
