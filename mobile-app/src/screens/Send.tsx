import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  SafeAreaView,
  Alert,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import { useWalletStore } from '@/store/wallet';
import { useAppStore } from '@/store/app';
import { signMessage } from '@/utils/crypto';
import { isValidAddress } from '@/utils/crypto';
import { parseAmount, formatBalance } from '@/utils/format';
import APIService from '@/services/api';
import { COLORS, WALLET, ERROR_MESSAGES } from '@/constants';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

const Send: React.FC = () => {
  const { wallet, balance, refreshBalance, addPendingTransaction } = useWalletStore();
  const { updateActivity, settings } = useAppStore();
  const [recipient, setRecipient] = useState('');
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [sending, setSending] = useState(false);

  const handleSend = async () => {
    updateActivity();

    // Validation
    if (!recipient.trim()) {
      Alert.alert('Error', 'Please enter recipient address');
      return;
    }

    if (!isValidAddress(recipient)) {
      Alert.alert('Error', ERROR_MESSAGES.INVALID_ADDRESS);
      return;
    }

    const parsedAmount = parseAmount(amount);
    if (!parsedAmount || parsedAmount <= 0) {
      Alert.alert('Error', 'Please enter valid amount');
      return;
    }

    if (parsedAmount < WALLET.MIN_TRANSACTION_AMOUNT) {
      Alert.alert('Error', `Minimum amount is ${WALLET.MIN_TRANSACTION_AMOUNT} XAI`);
      return;
    }

    if (parsedAmount > balance) {
      Alert.alert('Error', ERROR_MESSAGES.INSUFFICIENT_BALANCE);
      return;
    }

    if (!wallet?.privateKey) {
      Alert.alert('Error', 'Private key not available');
      return;
    }

    // Confirm transaction
    Alert.alert(
      'Confirm Transaction',
      `Send ${formatBalance(parsedAmount)} XAI to ${recipient}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Send', onPress: () => executeSend(parsedAmount) },
      ],
    );
  };

  const executeSend = async (parsedAmount: number) => {
    if (!wallet?.privateKey) return;

    setSending(true);

    try {
      // Get nonce
      const nonceData = await APIService.getNonce(wallet.address);
      const nonce = nonceData.next_nonce;

      // Create transaction
      const timestamp = Math.floor(Date.now() / 1000);
      const txData = {
        sender: wallet.address,
        recipient,
        amount: parsedAmount,
        timestamp,
        nonce,
        data: note || undefined,
      };

      // Sign transaction
      const message = JSON.stringify(txData);
      const signature = await signMessage(message, wallet.privateKey);

      // Send transaction
      const result = await APIService.sendTransaction({
        ...txData,
        signature,
      });

      if (result.success && result.txid) {
        // Add to pending transactions
        await addPendingTransaction({
          transaction: {
            txid: result.txid,
            ...txData,
            signature,
            fee: 0,
            status: 'pending',
          },
          signedData: signature,
          timestamp: Date.now(),
          retryCount: 0,
        });

        Alert.alert('Success', 'Transaction sent successfully!', [
          { text: 'OK', onPress: () => resetForm() },
        ]);

        // Refresh balance
        await refreshBalance();
      } else {
        Alert.alert('Error', result.error || ERROR_MESSAGES.TRANSACTION_FAILED);
      }
    } catch (error) {
      console.error('Send transaction error:', error);
      Alert.alert('Error', ERROR_MESSAGES.TRANSACTION_FAILED);
    } finally {
      setSending(false);
    }
  };

  const resetForm = () => {
    setRecipient('');
    setAmount('');
    setNote('');
  };

  const handleScanQR = () => {
    // Navigate to QR scanner
    // navigation.navigate('QRScanner', { onScan: setRecipient });
    Alert.alert('QR Scanner', 'QR scanner will be implemented');
  };

  const handleMaxAmount = () => {
    setAmount(balance.toString());
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.content}>
        <View style={styles.balanceInfo}>
          <Text style={styles.balanceLabel}>Available Balance</Text>
          <Text style={styles.balanceAmount}>{formatBalance(balance)} XAI</Text>
        </View>

        <View style={styles.form}>
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Recipient Address</Text>
            <View style={styles.inputRow}>
              <TextInput
                style={[styles.input, styles.inputFlex]}
                placeholder="XAI..."
                placeholderTextColor={COLORS.text + '40'}
                value={recipient}
                onChangeText={setRecipient}
                autoCapitalize="none"
                autoCorrect={false}
                editable={!sending}
              />
              <TouchableOpacity style={styles.scanButton} onPress={handleScanQR}>
                <Icon name="qrcode-scan" size={24} color={COLORS.primary} />
              </TouchableOpacity>
            </View>
          </View>

          <View style={styles.inputGroup}>
            <View style={styles.labelRow}>
              <Text style={styles.label}>Amount</Text>
              <TouchableOpacity onPress={handleMaxAmount}>
                <Text style={styles.maxButton}>MAX</Text>
              </TouchableOpacity>
            </View>
            <TextInput
              style={styles.input}
              placeholder="0.00"
              placeholderTextColor={COLORS.text + '40'}
              value={amount}
              onChangeText={setAmount}
              keyboardType="decimal-pad"
              editable={!sending}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Note (Optional)</Text>
            <TextInput
              style={[styles.input, styles.textArea]}
              placeholder="Add a note..."
              placeholderTextColor={COLORS.text + '40'}
              value={note}
              onChangeText={setNote}
              multiline
              numberOfLines={3}
              editable={!sending}
            />
          </View>
        </View>

        <View style={styles.footer}>
          {sending ? (
            <ActivityIndicator size="large" color={COLORS.primary} />
          ) : (
            <TouchableOpacity style={styles.sendButton} onPress={handleSend}>
              <Text style={styles.sendButtonText}>Send Transaction</Text>
            </TouchableOpacity>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  scrollView: {
    flex: 1,
  },
  content: {
    padding: 16,
    gap: 24,
  },
  balanceInfo: {
    backgroundColor: COLORS.card,
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  balanceLabel: {
    fontSize: 14,
    color: COLORS.text,
    opacity: 0.7,
    marginBottom: 4,
  },
  balanceAmount: {
    fontSize: 24,
    fontWeight: 'bold',
    color: COLORS.text,
  },
  form: {
    gap: 20,
  },
  inputGroup: {
    gap: 8,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.text,
  },
  labelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  maxButton: {
    fontSize: 12,
    fontWeight: '600',
    color: COLORS.primary,
  },
  inputRow: {
    flexDirection: 'row',
    gap: 8,
  },
  input: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    color: COLORS.text,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  inputFlex: {
    flex: 1,
  },
  scanButton: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: COLORS.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  textArea: {
    minHeight: 80,
    textAlignVertical: 'top',
  },
  footer: {
    marginTop: 8,
  },
  sendButton: {
    backgroundColor: COLORS.primary,
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 12,
    alignItems: 'center',
  },
  sendButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default Send;
