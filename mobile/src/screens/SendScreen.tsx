/**
 * Send Screen - Enhanced with QR scanner and address book integration
 *
 * Production-ready features:
 * - QR code scanner for recipient address
 * - Address book integration
 * - Recent recipients
 * - Fee estimation (slow, standard, priority)
 * - Amount validation
 * - Transaction preview
 * - Biometric confirmation
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Alert,
  Modal,
  TouchableOpacity,
  Platform,
  KeyboardAvoidingView,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { BarCodeScanner, BarCodeEvent } from 'expo-barcode-scanner';
import * as LocalAuthentication from 'expo-local-authentication';
import * as Clipboard from 'expo-clipboard';
import { Card, Button, Input, AmountInput, Icon } from '../components';
import { useTheme } from '../theme';
import { useWallet } from '../context/WalletContext';
import { triggerHaptic } from '../hooks/useHaptics';
import { xaiApi } from '../services/api';
import { isValidAddress, signTransaction, generateTxId } from '../utils/crypto';
import { formatXai, formatXaiWithSymbol, parseXaiAmount, validateAmount, formatAddress } from '../utils/format';
import { loadSettings, getRecentRecipients, addRecentRecipient, getContacts } from '../utils/storage';
import { spacing, borderRadius } from '../theme/spacing';
import { Contact, MempoolStats } from '../types';

type FeeLevel = 'slow' | 'standard' | 'priority';

interface FeeOption {
  level: FeeLevel;
  label: string;
  rate: number;
  estimatedTime: string;
}

export function SendScreen() {
  const theme = useTheme();
  const navigation = useNavigation();

  const { activeWallet, refreshBalance } = useWallet();

  // Form state
  const [recipient, setRecipient] = useState('');
  const [amount, setAmount] = useState('');
  const [memo, setMemo] = useState('');
  const [selectedFee, setSelectedFee] = useState<FeeLevel>('standard');

  // Error state
  const [recipientError, setRecipientError] = useState('');
  const [amountError, setAmountError] = useState('');

  // UI state
  const [showScanner, setShowScanner] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [showAddressBook, setShowAddressBook] = useState(false);
  const [hasCameraPermission, setHasCameraPermission] = useState<boolean | null>(null);
  const [sending, setSending] = useState(false);

  // Data state
  const [feeOptions, setFeeOptions] = useState<FeeOption[]>([
    { level: 'slow', label: 'Slow', rate: 0.0001, estimatedTime: '~10 min' },
    { level: 'standard', label: 'Standard', rate: 0.0005, estimatedTime: '~3 min' },
    { level: 'priority', label: 'Priority', rate: 0.001, estimatedTime: '~30 sec' },
  ]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [recentRecipients, setRecentRecipients] = useState<string[]>([]);
  const [requireAuth, setRequireAuth] = useState(true);

  // Computed values
  const parsedAmount = parseXaiAmount(amount);
  const currentFee = feeOptions.find((f) => f.level === selectedFee)?.rate || 0.0005;
  const totalAmount = (parsedAmount || 0) + currentFee;
  const balance = activeWallet?.balance || 0;

  // Load settings and data
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      // Load settings
      const settings = await loadSettings();
      setRequireAuth(settings.security.requireAuthForSend);

      // Load contacts
      const loadedContacts = await getContacts();
      setContacts(loadedContacts);

      // Load recent recipients
      const recent = await getRecentRecipients();
      setRecentRecipients(recent);

      // Load fee recommendations from mempool
      const mempoolResult = await xaiApi.getMempoolStats();
      if (mempoolResult.success && mempoolResult.data?.fees?.recommendedFeeRates) {
        const rates = mempoolResult.data.fees.recommendedFeeRates;
        setFeeOptions([
          { level: 'slow', label: 'Slow', rate: rates.slow, estimatedTime: '~10 min' },
          { level: 'standard', label: 'Standard', rate: rates.standard, estimatedTime: '~3 min' },
          { level: 'priority', label: 'Priority', rate: rates.priority, estimatedTime: '~30 sec' },
        ]);
      }
    } catch (error) {
      console.error('Failed to load initial data:', error);
    }
  };

  // Request camera permission
  const requestCameraPermission = async () => {
    const { status } = await BarCodeScanner.requestPermissionsAsync();
    setHasCameraPermission(status === 'granted');
    return status === 'granted';
  };

  // Handle QR scan
  const handleBarCodeScanned = useCallback(({ data }: BarCodeEvent) => {
    setShowScanner(false);
    triggerHaptic('success');

    // Parse XAI URI: xai:<address>?amount=<amount>
    if (data.startsWith('xai:')) {
      const parts = data.substring(4).split('?');
      const address = parts[0];
      setRecipient(address);
      setRecipientError('');

      // Parse amount if present
      if (parts[1]) {
        const params = new URLSearchParams(parts[1]);
        const scannedAmount = params.get('amount');
        if (scannedAmount) {
          setAmount(scannedAmount);
          setAmountError('');
        }
      }
    } else if (isValidAddress(data)) {
      setRecipient(data);
      setRecipientError('');
    } else {
      Alert.alert('Invalid QR Code', 'The scanned code is not a valid XAI address');
    }
  }, []);

  // Open scanner
  const handleOpenScanner = async () => {
    if (hasCameraPermission === null) {
      const granted = await requestCameraPermission();
      if (granted) {
        setShowScanner(true);
      } else {
        Alert.alert('Camera Permission Required', 'Please enable camera access to scan QR codes');
      }
    } else if (hasCameraPermission) {
      setShowScanner(true);
    } else {
      Alert.alert('Camera Permission Denied', 'Please enable camera access in your device settings');
    }
  };

  // Handle contact selection
  const handleSelectContact = (contact: Contact) => {
    setRecipient(contact.address);
    setRecipientError('');
    setShowAddressBook(false);
    triggerHaptic('selection');
  };

  // Paste from clipboard
  const handlePaste = async () => {
    try {
      const text = await Clipboard.getStringAsync();
      if (text && isValidAddress(text.trim())) {
        setRecipient(text.trim());
        setRecipientError('');
        triggerHaptic('selection');
      } else if (text) {
        Alert.alert('Invalid Address', 'Clipboard does not contain a valid XAI address');
      }
    } catch {
      Alert.alert('Error', 'Failed to read clipboard');
    }
  };

  // Set max amount
  const handleSetMax = () => {
    const maxAmount = Math.max(0, balance - currentFee);
    setAmount(maxAmount.toString());
    setAmountError('');
    triggerHaptic('selection');
  };

  // Validate form
  const validateForm = (): boolean => {
    let valid = true;

    if (!recipient.trim()) {
      setRecipientError('Recipient address is required');
      valid = false;
    } else if (!isValidAddress(recipient.trim())) {
      setRecipientError('Invalid XAI address format');
      valid = false;
    } else if (recipient.trim().toLowerCase() === activeWallet?.address.toLowerCase()) {
      setRecipientError('Cannot send to yourself');
      valid = false;
    } else {
      setRecipientError('');
    }

    if (!parsedAmount || parsedAmount <= 0) {
      setAmountError('Please enter a valid amount');
      valid = false;
    } else {
      const validation = validateAmount(parsedAmount, balance, 0.0001);
      if (!validation.valid) {
        setAmountError(validation.error || 'Invalid amount');
        valid = false;
      } else if (totalAmount > balance) {
        setAmountError('Insufficient balance for amount + fee');
        valid = false;
      } else {
        setAmountError('');
      }
    }

    return valid;
  };

  // Handle send button
  const handleSendPress = () => {
    if (!validateForm()) {
      triggerHaptic('error');
      return;
    }
    setShowConfirmation(true);
  };

  // Confirm and send transaction
  const handleConfirmSend = async () => {
    if (!activeWallet || !parsedAmount) return;

    if (requireAuth) {
      const authResult = await LocalAuthentication.authenticateAsync({
        promptMessage: 'Authenticate to send XAI',
        cancelLabel: 'Cancel',
      });
      if (!authResult.success) return;
    }

    setSending(true);
    try {
      const nonceResult = await xaiApi.getNonce(activeWallet.address);
      if (!nonceResult.success || !nonceResult.data) {
        Alert.alert('Error', 'Failed to get nonce');
        setSending(false);
        setShowConfirmation(false);
        return;
      }

      const nonce = nonceResult.data.nextNonce;
      const timestamp = Math.floor(Date.now() / 1000);

      const tx = {
        sender: activeWallet.address,
        recipient: recipient.trim(),
        amount: parsedAmount,
        fee: currentFee,
        nonce,
        timestamp,
      };

      const signature = await signTransaction(tx, activeWallet.privateKey!);
      const txid = await generateTxId(tx);

      const result = await xaiApi.sendTransaction({
        ...tx,
        publicKey: activeWallet.publicKey,
        signature,
        txid,
        metadata: memo.trim() || undefined,
      });

      if (result.success && result.data) {
        triggerHaptic('success');
        await addRecentRecipient(recipient.trim());
        await refreshBalance();

        Alert.alert('Transaction Sent', `Your transaction of ${formatXaiWithSymbol(parsedAmount)} has been submitted.`, [
          { text: 'OK', onPress: () => navigation.goBack() },
        ]);
      } else {
        triggerHaptic('error');
        Alert.alert('Transaction Failed', result.error || 'Failed to send transaction');
      }
    } catch (error) {
      triggerHaptic('error');
      Alert.alert('Error', error instanceof Error ? error.message : 'Failed to send transaction');
    } finally {
      setSending(false);
      setShowConfirmation(false);
    }
  };

  // Get contact name for address
  const getContactName = (address: string): string | null => {
    const contact = contacts.find((c) => c.address.toLowerCase() === address.toLowerCase());
    return contact?.name || null;
  };

  // No wallet check
  if (!activeWallet) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <View style={styles.centerContent}>
          <Icon name="wallet" size={64} color={theme.colors.textMuted} />
          <Text style={[styles.emptyTitle, { color: theme.colors.text }]}>No Wallet</Text>
          <Text style={[styles.emptySubtitle, { color: theme.colors.textMuted }]}>
            Create or import a wallet to send XAI
          </Text>
          <Button title="Go to Wallet" onPress={() => navigation.navigate('Wallet' as never)} style={styles.emptyButton} />
        </View>
      </View>
    );
  }

  // Watch-only wallet check
  if (activeWallet.isWatchOnly) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <View style={styles.centerContent}>
          <Icon name="eye" size={64} color={theme.colors.semantic.warning} />
          <Text style={[styles.emptyTitle, { color: theme.colors.text }]}>Watch-Only Wallet</Text>
          <Text style={[styles.emptySubtitle, { color: theme.colors.textMuted }]}>
            Cannot send from a watch-only wallet
          </Text>
          <Button title="Go Back" variant="outline" onPress={() => navigation.goBack()} style={styles.emptyButton} />
        </View>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView style={[styles.container, { backgroundColor: theme.colors.background }]} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        {/* Balance Display */}
        <Card style={styles.balanceCard}>
          <Text style={[styles.balanceLabel, { color: theme.colors.textMuted }]}>Available Balance</Text>
          <Text style={[styles.balanceAmount, { color: theme.colors.text }]}>{formatXaiWithSymbol(balance)}</Text>
        </Card>

        {/* Recipient Input */}
        <Card title="Recipient">
          <Input
            label="Address"
            placeholder="XAI..."
            value={recipient}
            onChangeText={(text) => { setRecipient(text); setRecipientError(''); }}
            error={recipientError}
            autoCapitalize="none"
            autoCorrect={false}
            rightElement={
              <View style={styles.recipientActions}>
                <TouchableOpacity onPress={handlePaste} style={styles.actionButton}>
                  <Icon name="clipboard" size={18} color={theme.colors.brand.primary} />
                </TouchableOpacity>
                <TouchableOpacity onPress={handleOpenScanner} style={styles.actionButton}>
                  <Icon name="qr-code" size={18} color={theme.colors.brand.primary} />
                </TouchableOpacity>
                <TouchableOpacity onPress={() => setShowAddressBook(true)} style={styles.actionButton}>
                  <Icon name="users" size={18} color={theme.colors.brand.primary} />
                </TouchableOpacity>
              </View>
            }
          />

          {recipient && isValidAddress(recipient) && getContactName(recipient) && (
            <View style={[styles.contactMatch, { backgroundColor: theme.colors.brand.primaryMuted }]}>
              <Icon name="user" size={14} color={theme.colors.brand.primary} />
              <Text style={[styles.contactMatchText, { color: theme.colors.brand.primary }]}>{getContactName(recipient)}</Text>
            </View>
          )}

          {!recipient && recentRecipients.length > 0 && (
            <View style={styles.recentSection}>
              <Text style={[styles.recentLabel, { color: theme.colors.textMuted }]}>Recent Recipients</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                {recentRecipients.slice(0, 5).map((addr, index) => (
                  <TouchableOpacity key={index} style={[styles.recentItem, { backgroundColor: theme.colors.surface }]} onPress={() => { setRecipient(addr); setRecipientError(''); }}>
                    <Text style={[styles.recentName, { color: theme.colors.text }]}>{getContactName(addr) || formatAddress(addr, 6)}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </View>
          )}
        </Card>

        {/* Amount Input */}
        <Card title="Amount">
          <AmountInput label="Amount to Send" placeholder="0.0000" value={amount} onChangeText={(text) => { setAmount(text); setAmountError(''); }} error={amountError} symbol="XAI" onMax={handleSetMax} />
          <View style={styles.amountQuickSelect}>
            {[0.1, 0.5, 1, 10].map((quickAmount) => (
              <TouchableOpacity key={quickAmount} style={[styles.quickAmountButton, { borderColor: theme.colors.border }]} onPress={() => { if (quickAmount <= balance) { setAmount(quickAmount.toString()); setAmountError(''); triggerHaptic('selection'); } }} disabled={quickAmount > balance}>
                <Text style={[styles.quickAmountText, { color: quickAmount > balance ? theme.colors.textDisabled : theme.colors.text }]}>{quickAmount} XAI</Text>
              </TouchableOpacity>
            ))}
          </View>
        </Card>

        {/* Fee Selection */}
        <Card title="Network Fee">
          <View style={styles.feeOptions}>
            {feeOptions.map((option) => (
              <TouchableOpacity key={option.level} style={[styles.feeOption, { backgroundColor: selectedFee === option.level ? theme.colors.brand.primaryMuted : theme.colors.surface, borderColor: selectedFee === option.level ? theme.colors.brand.primary : theme.colors.border }]} onPress={() => { setSelectedFee(option.level); triggerHaptic('selection'); }}>
                <Text style={[styles.feeLabel, { color: theme.colors.text }]}>{option.label}</Text>
                <Text style={[styles.feeRate, { color: theme.colors.brand.primary }]}>{formatXai(option.rate)} XAI</Text>
                <Text style={[styles.feeTime, { color: theme.colors.textMuted }]}>{option.estimatedTime}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </Card>

        {/* Memo */}
        <Card title="Memo (Optional)">
          <Input placeholder="Add a note..." value={memo} onChangeText={setMemo} multiline numberOfLines={2} maxLength={100} showCharacterCount maxCharacters={100} />
        </Card>

        {/* Summary */}
        {parsedAmount && parsedAmount > 0 && (
          <Card title="Summary" style={styles.summaryCard}>
            <View style={styles.summaryRow}>
              <Text style={[styles.summaryLabel, { color: theme.colors.textMuted }]}>Amount</Text>
              <Text style={[styles.summaryValue, { color: theme.colors.text }]}>{formatXaiWithSymbol(parsedAmount)}</Text>
            </View>
            <View style={styles.summaryRow}>
              <Text style={[styles.summaryLabel, { color: theme.colors.textMuted }]}>Network Fee</Text>
              <Text style={[styles.summaryValue, { color: theme.colors.text }]}>{formatXaiWithSymbol(currentFee)}</Text>
            </View>
            <View style={[styles.summaryRow, styles.summaryTotal, { borderTopColor: theme.colors.border }]}>
              <Text style={[styles.summaryTotalLabel, { color: theme.colors.text }]}>Total</Text>
              <Text style={[styles.summaryTotalValue, { color: totalAmount > balance ? theme.colors.semantic.error : theme.colors.brand.primary }]}>{formatXaiWithSymbol(totalAmount)}</Text>
            </View>
          </Card>
        )}

        <Button title="Send" onPress={handleSendPress} disabled={!parsedAmount || parsedAmount <= 0 || !recipient} style={styles.sendButton} />
      </ScrollView>

      {/* QR Scanner Modal */}
      <Modal visible={showScanner} animationType="slide" onRequestClose={() => setShowScanner(false)}>
        <View style={[styles.scannerContainer, { backgroundColor: theme.colors.background }]}>
          <View style={styles.scannerHeader}>
            <Text style={[styles.scannerTitle, { color: theme.colors.text }]}>Scan QR Code</Text>
            <Button variant="ghost" onPress={() => setShowScanner(false)}><Icon name="close" size={24} color={theme.colors.text} /></Button>
          </View>
          <View style={styles.scannerArea}>
            <BarCodeScanner onBarCodeScanned={handleBarCodeScanned} style={StyleSheet.absoluteFillObject} />
            <View style={[styles.scannerOverlay, { borderColor: theme.colors.brand.primary }]} />
          </View>
          <Text style={[styles.scannerHint, { color: theme.colors.textMuted }]}>Align the QR code within the frame</Text>
        </View>
      </Modal>

      {/* Address Book Modal */}
      <Modal visible={showAddressBook} animationType="slide" transparent onRequestClose={() => setShowAddressBook(false)}>
        <View style={[styles.modalOverlay, { backgroundColor: theme.colors.overlay }]}>
          <View style={[styles.modalContent, { backgroundColor: theme.colors.surface }]}>
            <View style={[styles.modalHeader, { borderBottomColor: theme.colors.border }]}>
              <Text style={[styles.modalTitle, { color: theme.colors.text }]}>Address Book</Text>
              <Button variant="ghost" onPress={() => setShowAddressBook(false)}><Icon name="close" size={24} color={theme.colors.text} /></Button>
            </View>
            <ScrollView style={styles.contactList}>
              {contacts.length === 0 ? (
                <View style={styles.emptyContacts}>
                  <Icon name="users" size={48} color={theme.colors.textMuted} />
                  <Text style={[styles.emptyContactsText, { color: theme.colors.textMuted }]}>No contacts yet</Text>
                  <Button title="Add Contact" variant="secondary" size="small" onPress={() => { setShowAddressBook(false); navigation.navigate('AddressBook' as never); }} />
                </View>
              ) : (
                contacts.map((contact) => (
                  <TouchableOpacity key={contact.id} style={[styles.contactItem, { backgroundColor: theme.colors.background }]} onPress={() => handleSelectContact(contact)}>
                    <View style={[styles.contactAvatar, { backgroundColor: theme.colors.brand.primaryMuted }]}>
                      <Text style={[styles.contactAvatarText, { color: theme.colors.brand.primary }]}>{contact.name.charAt(0).toUpperCase()}</Text>
                    </View>
                    <View style={styles.contactInfo}>
                      <Text style={[styles.contactName, { color: theme.colors.text }]}>{contact.name}</Text>
                      <Text style={[styles.contactAddress, { color: theme.colors.textMuted }]}>{formatAddress(contact.address, 10)}</Text>
                    </View>
                    {contact.isFavorite && <Icon name="star" size={16} color={theme.colors.semantic.warning} />}
                  </TouchableOpacity>
                ))
              )}
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* Confirmation Modal */}
      <Modal visible={showConfirmation} animationType="fade" transparent onRequestClose={() => !sending && setShowConfirmation(false)}>
        <View style={[styles.modalOverlay, { backgroundColor: theme.colors.overlay }]}>
          <View style={[styles.confirmationModal, { backgroundColor: theme.colors.surface }]}>
            <Icon name="send" size={48} color={theme.colors.brand.primary} />
            <Text style={[styles.confirmTitle, { color: theme.colors.text }]}>Confirm Transaction</Text>
            <View style={[styles.confirmDetails, { backgroundColor: theme.colors.background }]}>
              <View style={styles.confirmRow}>
                <Text style={[styles.confirmLabel, { color: theme.colors.textMuted }]}>To</Text>
                <View style={styles.confirmValueContainer}>
                  {getContactName(recipient) && <Text style={[styles.confirmContact, { color: theme.colors.brand.primary }]}>{getContactName(recipient)}</Text>}
                  <Text style={[styles.confirmValue, { color: theme.colors.text }]}>{formatAddress(recipient, 10)}</Text>
                </View>
              </View>
              <View style={styles.confirmRow}>
                <Text style={[styles.confirmLabel, { color: theme.colors.textMuted }]}>Amount</Text>
                <Text style={[styles.confirmValue, { color: theme.colors.text }]}>{formatXaiWithSymbol(parsedAmount || 0)}</Text>
              </View>
              <View style={styles.confirmRow}>
                <Text style={[styles.confirmLabel, { color: theme.colors.textMuted }]}>Fee</Text>
                <Text style={[styles.confirmValue, { color: theme.colors.text }]}>{formatXaiWithSymbol(currentFee)}</Text>
              </View>
              <View style={[styles.confirmRow, styles.confirmTotalRow, { borderTopColor: theme.colors.border }]}>
                <Text style={[styles.confirmTotalLabel, { color: theme.colors.text }]}>Total</Text>
                <Text style={[styles.confirmTotalValue, { color: theme.colors.brand.primary }]}>{formatXaiWithSymbol(totalAmount)}</Text>
              </View>
            </View>
            <View style={styles.confirmActions}>
              <Button title="Cancel" variant="outline" onPress={() => setShowConfirmation(false)} disabled={sending} style={{ flex: 1 }} />
              <Button title={sending ? 'Sending...' : 'Confirm'} onPress={handleConfirmSend} loading={sending} style={{ flex: 1 }} />
            </View>
          </View>
        </View>
      </Modal>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: spacing['4'], paddingBottom: spacing['8'] },
  centerContent: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: spacing['8'] },
  emptyTitle: { fontSize: 20, fontWeight: '600', marginTop: spacing['4'] },
  emptySubtitle: { fontSize: 14, marginTop: spacing['2'], textAlign: 'center' },
  emptyButton: { marginTop: spacing['6'] },
  balanceCard: { alignItems: 'center', paddingVertical: spacing['4'] },
  balanceLabel: { fontSize: 12, marginBottom: spacing['1'] },
  balanceAmount: { fontSize: 24, fontWeight: '700' },
  recipientActions: { flexDirection: 'row', gap: spacing['3'] },
  actionButton: { padding: spacing['1'] },
  contactMatch: { flexDirection: 'row', alignItems: 'center', gap: spacing['2'], padding: spacing['2'], borderRadius: borderRadius.md, marginTop: spacing['2'] },
  contactMatchText: { fontSize: 13, fontWeight: '500' },
  recentSection: { marginTop: spacing['4'] },
  recentLabel: { fontSize: 12, marginBottom: spacing['2'] },
  recentItem: { paddingHorizontal: spacing['3'], paddingVertical: spacing['2'], borderRadius: borderRadius.md, marginRight: spacing['2'] },
  recentName: { fontSize: 13, fontWeight: '500' },
  amountQuickSelect: { flexDirection: 'row', gap: spacing['2'], marginTop: spacing['3'] },
  quickAmountButton: { flex: 1, paddingVertical: spacing['2'], borderRadius: borderRadius.md, borderWidth: 1, alignItems: 'center' },
  quickAmountText: { fontSize: 12, fontWeight: '500' },
  feeOptions: { flexDirection: 'row', gap: spacing['2'] },
  feeOption: { flex: 1, padding: spacing['3'], borderRadius: borderRadius.lg, borderWidth: 2, alignItems: 'center' },
  feeLabel: { fontSize: 13, fontWeight: '600', marginBottom: spacing['1'] },
  feeRate: { fontSize: 12, fontWeight: '500' },
  feeTime: { fontSize: 11, marginTop: spacing['1'] },
  summaryCard: { marginTop: spacing['2'] },
  summaryRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: spacing['2'] },
  summaryLabel: { fontSize: 14 },
  summaryValue: { fontSize: 14, fontFamily: 'monospace' },
  summaryTotal: { borderTopWidth: 1, marginTop: spacing['2'], paddingTop: spacing['3'] },
  summaryTotalLabel: { fontSize: 16, fontWeight: '600' },
  summaryTotalValue: { fontSize: 16, fontWeight: '700' },
  sendButton: { marginTop: spacing['6'] },
  scannerContainer: { flex: 1 },
  scannerHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: spacing['4'] },
  scannerTitle: { fontSize: 18, fontWeight: '600' },
  scannerArea: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  scannerOverlay: { width: 250, height: 250, borderWidth: 3, borderRadius: borderRadius.lg },
  scannerHint: { textAlign: 'center', padding: spacing['4'], fontSize: 14 },
  modalOverlay: { flex: 1, justifyContent: 'flex-end' },
  modalContent: { borderTopLeftRadius: borderRadius.xl, borderTopRightRadius: borderRadius.xl, maxHeight: '70%' },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: spacing['4'], borderBottomWidth: 1 },
  modalTitle: { fontSize: 18, fontWeight: '600' },
  contactList: { padding: spacing['4'] },
  emptyContacts: { alignItems: 'center', paddingVertical: spacing['8'] },
  emptyContactsText: { fontSize: 14, marginVertical: spacing['4'] },
  contactItem: { flexDirection: 'row', alignItems: 'center', padding: spacing['3'], borderRadius: borderRadius.lg, marginBottom: spacing['2'] },
  contactAvatar: { width: 40, height: 40, borderRadius: 20, justifyContent: 'center', alignItems: 'center', marginRight: spacing['3'] },
  contactAvatarText: { fontSize: 16, fontWeight: '600' },
  contactInfo: { flex: 1 },
  contactName: { fontSize: 16, fontWeight: '500' },
  contactAddress: { fontSize: 12, fontFamily: 'monospace', marginTop: 2 },
  confirmationModal: { margin: spacing['6'], padding: spacing['6'], borderRadius: borderRadius.xl, alignItems: 'center' },
  confirmTitle: { fontSize: 20, fontWeight: '600', marginTop: spacing['4'], marginBottom: spacing['6'] },
  confirmDetails: { width: '100%', padding: spacing['4'], borderRadius: borderRadius.lg },
  confirmRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', paddingVertical: spacing['2'] },
  confirmLabel: { fontSize: 14 },
  confirmValueContainer: { alignItems: 'flex-end' },
  confirmContact: { fontSize: 12, fontWeight: '500', marginBottom: 2 },
  confirmValue: { fontSize: 14, fontFamily: 'monospace' },
  confirmTotalRow: { borderTopWidth: 1, marginTop: spacing['2'], paddingTop: spacing['3'] },
  confirmTotalLabel: { fontSize: 16, fontWeight: '600' },
  confirmTotalValue: { fontSize: 18, fontWeight: '700' },
  confirmActions: { flexDirection: 'row', gap: spacing['3'], marginTop: spacing['6'], width: '100%' },
});
