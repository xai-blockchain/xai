/**
 * Wallet Screen - Multi-wallet management with backup verification
 *
 * Production-ready features:
 * - Multi-wallet support (create, import, switch)
 * - Mnemonic backup verification
 * - Watch-only wallet support
 * - Transaction history with pagination
 * - Wallet renaming and customization
 * - Secure key export
 */

import React, { useEffect, useState, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Alert,
  FlatList,
  Modal,
  TouchableOpacity,
} from 'react-native';
import * as Clipboard from 'expo-clipboard';
import * as LocalAuthentication from 'expo-local-authentication';
import { useNavigation } from '@react-navigation/native';
import {
  useWallet,
  useWalletList,
  useActiveWallet,
  useSyncStatus,
} from '../context/WalletContext';
import { Card, Button, Input, TransactionItem, Icon, StatusBadge } from '../components';
import { useTheme } from '../theme';
import { triggerHaptic } from '../hooks/useHaptics';
import {
  formatXaiWithSymbol,
  formatAddress,
  formatDate,
  formatRelativeTime,
} from '../utils/format';
import { validateMnemonic } from '../utils/crypto';
import { loadSettings } from '../utils/storage';
import { xaiApi } from '../services/api';
import { Transaction } from '../types';
import { spacing, borderRadius } from '../theme/spacing';

type WalletView =
  | 'main'
  | 'create'
  | 'import'
  | 'import-mnemonic'
  | 'import-key'
  | 'watch-only'
  | 'history'
  | 'backup'
  | 'backup-verify'
  | 'wallet-list';

interface BackupState {
  mnemonic: string[];
  shuffledWords: string[];
  selectedWords: string[];
  verificationIndices: number[];
}

export function WalletScreen() {
  const theme = useTheme();
  const navigation = useNavigation();

  const {
    activeWallet,
    balances,
    isLoading,
    isConnected,
    createWallet,
    importWalletFromMnemonic,
    importWalletFromPrivateKey,
    addWatchOnlyWallet,
    switchWallet,
    removeWallet,
    renameWallet,
    verifyBackup,
    refreshBalance,
  } = useWallet();

  const walletList = useWalletList();
  const { wallet: activeWalletData, balance } = useActiveWallet();
  const syncStatus = useSyncStatus();

  // State
  const [view, setView] = useState<WalletView>('main');
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loadingTx, setLoadingTx] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const LIMIT = 20;

  // Input states
  const [mnemonicInput, setMnemonicInput] = useState('');
  const [privateKeyInput, setPrivateKeyInput] = useState('');
  const [addressInput, setAddressInput] = useState('');
  const [walletNameInput, setWalletNameInput] = useState('');
  const [inputError, setInputError] = useState('');

  // Backup state
  const [backupState, setBackupState] = useState<BackupState | null>(null);
  const [newMnemonic, setNewMnemonic] = useState<string[] | null>(null);

  // Editing
  const [editingWalletId, setEditingWalletId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

  // Security settings
  const [requireAuth, setRequireAuth] = useState(true);

  // Load security settings
  useEffect(() => {
    loadSettings().then((settings) => {
      setRequireAuth(settings.security.requireAuthForExport);
    });
  }, []);

  // Fetch transactions
  const fetchTransactions = useCallback(
    async (reset: boolean = false) => {
      if (!activeWallet) return;

      const offset = reset ? 0 : page * LIMIT;
      setLoadingTx(true);

      try {
        const result = await xaiApi.getHistory(activeWallet.address, LIMIT, offset);
        if (result.success && result.data) {
          if (reset) {
            setTransactions(result.data.transactions);
            setPage(1);
          } else {
            setTransactions((prev) => [...prev, ...result.data!.transactions]);
            setPage((prev) => prev + 1);
          }
          setHasMore(result.data.transactions.length === LIMIT);
        }
      } catch (error) {
        console.error('Failed to fetch transactions:', error);
      } finally {
        setLoadingTx(false);
      }
    },
    [activeWallet, page]
  );

  useEffect(() => {
    if (activeWallet && view === 'history') {
      fetchTransactions(true);
    }
  }, [activeWallet, view]);

  // Refresh handler
  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await refreshBalance();
    if (view === 'history') {
      await fetchTransactions(true);
    }
    setRefreshing(false);
  }, [refreshBalance, fetchTransactions, view]);

  // Reset inputs
  const resetInputs = useCallback(() => {
    setMnemonicInput('');
    setPrivateKeyInput('');
    setAddressInput('');
    setWalletNameInput('');
    setInputError('');
  }, []);

  // Create new wallet
  const handleCreateWallet = async () => {
    try {
      const result = await createWallet(walletNameInput || undefined);
      setNewMnemonic(result.mnemonic);
      setView('backup');
      resetInputs();
      triggerHaptic('success');
    } catch (error) {
      Alert.alert('Error', 'Failed to create wallet');
    }
  };

  // Import from mnemonic
  const handleImportMnemonic = async () => {
    const words = mnemonicInput.trim().toLowerCase().split(/\s+/);
    if (words.length !== 12 && words.length !== 24) {
      setInputError('Please enter 12 or 24 words');
      return;
    }

    if (!validateMnemonic(words.join(' '))) {
      setInputError('Invalid recovery phrase');
      return;
    }

    try {
      await importWalletFromMnemonic(words, walletNameInput || undefined);
      setView('main');
      resetInputs();
      triggerHaptic('success');
      Alert.alert('Success', 'Wallet imported successfully');
    } catch (error) {
      setInputError(error instanceof Error ? error.message : 'Import failed');
    }
  };

  // Import from private key
  const handleImportPrivateKey = async () => {
    const key = privateKeyInput.trim();
    if (key.length !== 64 && key.length !== 66) {
      setInputError('Invalid private key format');
      return;
    }

    try {
      await importWalletFromPrivateKey(key, walletNameInput || undefined);
      setView('main');
      resetInputs();
      triggerHaptic('success');
      Alert.alert('Success', 'Wallet imported successfully');
    } catch (error) {
      setInputError(error instanceof Error ? error.message : 'Import failed');
    }
  };

  // Add watch-only wallet
  const handleAddWatchOnly = async () => {
    const address = addressInput.trim();
    if (!address.startsWith('XAI') || address.length !== 43) {
      setInputError('Invalid XAI address format');
      return;
    }

    try {
      await addWatchOnlyWallet(address, walletNameInput || undefined);
      setView('main');
      resetInputs();
      triggerHaptic('success');
      Alert.alert('Success', 'Watch-only wallet added');
    } catch (error) {
      setInputError(error instanceof Error ? error.message : 'Failed to add wallet');
    }
  };

  // Switch wallet
  const handleSwitchWallet = async (walletId: string) => {
    try {
      await switchWallet(walletId);
      setView('main');
      triggerHaptic('selection');
    } catch (error) {
      Alert.alert('Error', 'Failed to switch wallet');
    }
  };

  // Delete wallet
  const handleDeleteWallet = (walletId: string, walletName: string) => {
    const wallet = walletList.find((w) => w.id === walletId);
    const isBackedUp = wallet?.isBackedUp;

    Alert.alert(
      'Delete Wallet',
      isBackedUp
        ? `Delete "${walletName}"? This action cannot be undone.`
        : `Warning: "${walletName}" has NOT been backed up! If you delete it, you will lose access to all funds. Are you sure?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            const success = await removeWallet(walletId);
            if (success) {
              triggerHaptic('success');
              if (walletList.length <= 1) {
                setView('main');
              }
            } else {
              Alert.alert('Error', 'Failed to delete wallet');
            }
          },
        },
      ]
    );
  };

  // Rename wallet
  const handleRenameWallet = async () => {
    if (!editingWalletId || !editingName.trim()) return;

    await renameWallet(editingWalletId, editingName.trim());
    setEditingWalletId(null);
    setEditingName('');
    triggerHaptic('success');
  };

  // Copy address
  const handleCopyAddress = async () => {
    if (activeWallet) {
      await Clipboard.setStringAsync(activeWallet.address);
      triggerHaptic('success');
      Alert.alert('Copied', 'Address copied to clipboard');
    }
  };

  // Export private key (with authentication)
  const handleExportKey = async () => {
    if (!activeWallet || activeWallet.isWatchOnly) {
      Alert.alert('Error', 'Cannot export key from watch-only wallet');
      return;
    }

    if (requireAuth) {
      const result = await LocalAuthentication.authenticateAsync({
        promptMessage: 'Authenticate to export private key',
        cancelLabel: 'Cancel',
      });

      if (!result.success) {
        return;
      }
    }

    Alert.alert(
      'Export Private Key',
      'Never share your private key with anyone. Anyone with your private key can access your funds.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Show Key',
          onPress: () => {
            Alert.alert('Private Key', activeWallet.privateKey!, [
              {
                text: 'Copy',
                onPress: () => {
                  Clipboard.setStringAsync(activeWallet.privateKey!);
                  triggerHaptic('success');
                },
              },
              { text: 'Close' },
            ]);
          },
        },
      ]
    );
  };

  // Claim faucet
  const handleClaimFaucet = async () => {
    if (!activeWallet) return;

    try {
      const result = await xaiApi.claimFaucet(activeWallet.address);
      if (result.success && result.data) {
        Alert.alert('Success', result.data.message);
        await refreshBalance();
      } else {
        Alert.alert('Error', result.error || 'Failed to claim faucet');
      }
    } catch {
      Alert.alert('Error', 'Failed to claim faucet');
    }
  };

  // Start backup verification
  const startBackupVerification = useCallback(() => {
    if (!newMnemonic) return;

    // Select 4 random indices for verification
    const indices: number[] = [];
    while (indices.length < 4) {
      const idx = Math.floor(Math.random() * newMnemonic.length);
      if (!indices.includes(idx)) {
        indices.push(idx);
      }
    }
    indices.sort((a, b) => a - b);

    // Create shuffled word list for selection
    const shuffled = [...newMnemonic].sort(() => Math.random() - 0.5);

    setBackupState({
      mnemonic: newMnemonic,
      shuffledWords: shuffled,
      selectedWords: [],
      verificationIndices: indices,
    });
    setView('backup-verify');
  }, [newMnemonic]);

  // Select word for verification
  const handleSelectWord = (word: string) => {
    if (!backupState) return;

    if (backupState.selectedWords.length >= 4) return;

    setBackupState({
      ...backupState,
      selectedWords: [...backupState.selectedWords, word],
    });
  };

  // Remove selected word
  const handleRemoveWord = (index: number) => {
    if (!backupState) return;

    setBackupState({
      ...backupState,
      selectedWords: backupState.selectedWords.filter((_, i) => i !== index),
    });
  };

  // Verify backup
  const handleVerifyBackup = async () => {
    if (!backupState || !activeWallet) return;

    const { mnemonic, selectedWords, verificationIndices } = backupState;

    // Check if selected words match the expected words at verification indices
    const isValid = verificationIndices.every(
      (idx, i) => mnemonic[idx] === selectedWords[i]
    );

    if (isValid) {
      await verifyBackup(activeWallet.id);
      triggerHaptic('success');
      Alert.alert('Success', 'Your wallet backup has been verified!', [
        {
          text: 'OK',
          onPress: () => {
            setBackupState(null);
            setNewMnemonic(null);
            setView('main');
          },
        },
      ]);
    } else {
      triggerHaptic('error');
      Alert.alert(
        'Incorrect',
        'The words you selected do not match. Please try again.',
        [
          {
            text: 'Retry',
            onPress: () => {
              setBackupState({
                ...backupState,
                selectedWords: [],
              });
            },
          },
        ]
      );
    }
  };

  // Get wallet color
  const getWalletColor = (color?: string) => {
    const colors: Record<string, string> = {
      indigo: theme.colors.brand.primary,
      emerald: theme.colors.semantic.success,
      amber: theme.colors.semantic.warning,
      rose: '#f43f5e',
      cyan: '#06b6d4',
      purple: '#8b5cf6',
    };
    return colors[color || 'indigo'] || colors.indigo;
  };

  // ============== Render Views ==============

  // No wallet - show create/import options
  if (!activeWallet && view === 'main') {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <View style={styles.centerContent}>
          <Icon name="wallet" size={64} color={theme.colors.brand.primary} />
          <Text style={[styles.title, { color: theme.colors.text }]}>XAI Wallet</Text>
          <Text style={[styles.subtitle, { color: theme.colors.textMuted }]}>
            Create a new wallet or import an existing one
          </Text>
          <Button
            title="Create New Wallet"
            onPress={() => setView('create')}
            style={styles.fullWidthButton}
          />
          <Button
            title="Import Existing Wallet"
            variant="outline"
            onPress={() => setView('import')}
            style={styles.fullWidthButton}
          />
          <Button
            title="Watch-Only Wallet"
            variant="ghost"
            onPress={() => setView('watch-only')}
            style={styles.fullWidthButton}
          />
        </View>
      </View>
    );
  }

  // Create wallet view
  if (view === 'create') {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <ScrollView contentContainerStyle={styles.centerContent}>
          <Icon name="plus-circle" size={48} color={theme.colors.brand.primary} />
          <Text style={[styles.title, { color: theme.colors.text }]}>Create New Wallet</Text>
          <Text style={[styles.subtitle, { color: theme.colors.textMuted }]}>
            A new wallet will be generated with a 24-word recovery phrase. Make sure to back it up
            securely.
          </Text>
          <Input
            label="Wallet Name (optional)"
            placeholder="My Wallet"
            value={walletNameInput}
            onChangeText={setWalletNameInput}
            containerStyle={styles.fullWidthInput}
          />
          <Button
            title="Create Wallet"
            onPress={handleCreateWallet}
            loading={isLoading}
            style={styles.fullWidthButton}
          />
          <Button
            title="Cancel"
            variant="outline"
            onPress={() => {
              setView(activeWallet ? 'main' : 'main');
              resetInputs();
            }}
            style={styles.fullWidthButton}
          />
        </ScrollView>
      </View>
    );
  }

  // Import options view
  if (view === 'import') {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <ScrollView contentContainerStyle={styles.centerContent}>
          <Icon name="download" size={48} color={theme.colors.brand.primary} />
          <Text style={[styles.title, { color: theme.colors.text }]}>Import Wallet</Text>
          <Text style={[styles.subtitle, { color: theme.colors.textMuted }]}>
            Choose how to import your wallet
          </Text>
          <Button
            title="Recovery Phrase (12/24 words)"
            variant="secondary"
            onPress={() => setView('import-mnemonic')}
            style={styles.fullWidthButton}
          />
          <Button
            title="Private Key"
            variant="secondary"
            onPress={() => setView('import-key')}
            style={styles.fullWidthButton}
          />
          <Button
            title="Cancel"
            variant="outline"
            onPress={() => {
              setView(activeWallet ? 'main' : 'main');
              resetInputs();
            }}
            style={styles.fullWidthButton}
          />
        </ScrollView>
      </View>
    );
  }

  // Import mnemonic view
  if (view === 'import-mnemonic') {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <ScrollView contentContainerStyle={styles.centerContent}>
          <Text style={[styles.title, { color: theme.colors.text }]}>Recovery Phrase</Text>
          <Text style={[styles.subtitle, { color: theme.colors.textMuted }]}>
            Enter your 12 or 24 word recovery phrase
          </Text>
          <Input
            label="Recovery Phrase"
            placeholder="word1 word2 word3 ..."
            value={mnemonicInput}
            onChangeText={(text) => {
              setMnemonicInput(text);
              setInputError('');
            }}
            error={inputError}
            multiline
            numberOfLines={4}
            autoCapitalize="none"
            autoCorrect={false}
            containerStyle={styles.fullWidthInput}
          />
          <Input
            label="Wallet Name (optional)"
            placeholder="Imported Wallet"
            value={walletNameInput}
            onChangeText={setWalletNameInput}
            containerStyle={styles.fullWidthInput}
          />
          <Button
            title="Import"
            onPress={handleImportMnemonic}
            loading={isLoading}
            style={styles.fullWidthButton}
          />
          <Button
            title="Cancel"
            variant="outline"
            onPress={() => {
              setView('import');
              resetInputs();
            }}
            style={styles.fullWidthButton}
          />
        </ScrollView>
      </View>
    );
  }

  // Import private key view
  if (view === 'import-key') {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <ScrollView contentContainerStyle={styles.centerContent}>
          <Text style={[styles.title, { color: theme.colors.text }]}>Private Key</Text>
          <Text style={[styles.subtitle, { color: theme.colors.textMuted }]}>
            Enter your private key to restore your wallet
          </Text>
          <Input
            label="Private Key"
            placeholder="Enter your private key"
            value={privateKeyInput}
            onChangeText={(text) => {
              setPrivateKeyInput(text);
              setInputError('');
            }}
            error={inputError}
            secureTextEntry
            autoCapitalize="none"
            autoCorrect={false}
            containerStyle={styles.fullWidthInput}
          />
          <Input
            label="Wallet Name (optional)"
            placeholder="Imported Wallet"
            value={walletNameInput}
            onChangeText={setWalletNameInput}
            containerStyle={styles.fullWidthInput}
          />
          <Button
            title="Import"
            onPress={handleImportPrivateKey}
            loading={isLoading}
            style={styles.fullWidthButton}
          />
          <Button
            title="Cancel"
            variant="outline"
            onPress={() => {
              setView('import');
              resetInputs();
            }}
            style={styles.fullWidthButton}
          />
        </ScrollView>
      </View>
    );
  }

  // Watch-only view
  if (view === 'watch-only') {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <ScrollView contentContainerStyle={styles.centerContent}>
          <Icon name="eye" size={48} color={theme.colors.semantic.warning} />
          <Text style={[styles.title, { color: theme.colors.text }]}>Watch-Only Wallet</Text>
          <Text style={[styles.subtitle, { color: theme.colors.textMuted }]}>
            Monitor an address without the ability to send transactions
          </Text>
          <Input
            label="Address"
            placeholder="XAI..."
            value={addressInput}
            onChangeText={(text) => {
              setAddressInput(text);
              setInputError('');
            }}
            error={inputError}
            autoCapitalize="none"
            autoCorrect={false}
            containerStyle={styles.fullWidthInput}
          />
          <Input
            label="Wallet Name (optional)"
            placeholder="Watch Only"
            value={walletNameInput}
            onChangeText={setWalletNameInput}
            containerStyle={styles.fullWidthInput}
          />
          <Button
            title="Add Wallet"
            onPress={handleAddWatchOnly}
            loading={isLoading}
            style={styles.fullWidthButton}
          />
          <Button
            title="Cancel"
            variant="outline"
            onPress={() => {
              setView(activeWallet ? 'main' : 'main');
              resetInputs();
            }}
            style={styles.fullWidthButton}
          />
        </ScrollView>
      </View>
    );
  }

  // Backup view (show mnemonic)
  if (view === 'backup' && newMnemonic) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <ScrollView contentContainerStyle={styles.backupContent}>
          <Icon name="shield" size={48} color={theme.colors.semantic.warning} />
          <Text style={[styles.title, { color: theme.colors.text }]}>
            Backup Your Wallet
          </Text>
          <Text style={[styles.subtitle, { color: theme.colors.textMuted }]}>
            Write down these 24 words in order. This is the ONLY way to recover your wallet.
          </Text>

          <View style={[styles.mnemonicGrid, { backgroundColor: theme.colors.surface }]}>
            {newMnemonic.map((word, index) => (
              <View key={index} style={styles.wordContainer}>
                <Text style={[styles.wordNumber, { color: theme.colors.textMuted }]}>
                  {index + 1}
                </Text>
                <Text style={[styles.word, { color: theme.colors.text }]}>{word}</Text>
              </View>
            ))}
          </View>

          <View style={styles.warningBox}>
            <Icon name="alert-triangle" size={20} color={theme.colors.semantic.error} />
            <Text style={[styles.warningText, { color: theme.colors.semantic.error }]}>
              Never share your recovery phrase. Anyone with these words can access your funds.
            </Text>
          </View>

          <Button
            title="I've Written It Down"
            onPress={startBackupVerification}
            style={styles.fullWidthButton}
          />
          <Button
            title="Skip for Now"
            variant="ghost"
            onPress={() => {
              setNewMnemonic(null);
              setView('main');
            }}
            style={styles.fullWidthButton}
          />
        </ScrollView>
      </View>
    );
  }

  // Backup verification view
  if (view === 'backup-verify' && backupState) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <ScrollView contentContainerStyle={styles.backupContent}>
          <Text style={[styles.title, { color: theme.colors.text }]}>Verify Backup</Text>
          <Text style={[styles.subtitle, { color: theme.colors.textMuted }]}>
            Select words #{backupState.verificationIndices.map((i) => i + 1).join(', #')} in order
          </Text>

          {/* Selected words */}
          <View style={styles.selectedWordsContainer}>
            {backupState.verificationIndices.map((idx, i) => (
              <TouchableOpacity
                key={idx}
                style={[
                  styles.selectedWordSlot,
                  {
                    backgroundColor: backupState.selectedWords[i]
                      ? theme.colors.brand.primaryMuted
                      : theme.colors.surface,
                    borderColor: theme.colors.border,
                  },
                ]}
                onPress={() => backupState.selectedWords[i] && handleRemoveWord(i)}
              >
                <Text style={[styles.wordNumber, { color: theme.colors.textMuted }]}>
                  #{idx + 1}
                </Text>
                <Text style={[styles.word, { color: theme.colors.text }]}>
                  {backupState.selectedWords[i] || '___'}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Word options */}
          <View style={styles.wordOptionsContainer}>
            {backupState.shuffledWords.map((word, index) => {
              const isSelected = backupState.selectedWords.includes(word);
              return (
                <TouchableOpacity
                  key={index}
                  style={[
                    styles.wordOption,
                    {
                      backgroundColor: isSelected
                        ? theme.colors.surfaceOverlay
                        : theme.colors.surface,
                      opacity: isSelected ? 0.5 : 1,
                    },
                  ]}
                  onPress={() => !isSelected && handleSelectWord(word)}
                  disabled={isSelected}
                >
                  <Text
                    style={[
                      styles.wordOptionText,
                      { color: isSelected ? theme.colors.textMuted : theme.colors.text },
                    ]}
                  >
                    {word}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          <Button
            title="Verify"
            onPress={handleVerifyBackup}
            disabled={backupState.selectedWords.length !== 4}
            style={styles.fullWidthButton}
          />
        </ScrollView>
      </View>
    );
  }

  // Wallet list view
  if (view === 'wallet-list') {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <View style={styles.header}>
          <Text style={[styles.headerTitle, { color: theme.colors.text }]}>My Wallets</Text>
          <Button
            title="Done"
            variant="ghost"
            size="small"
            onPress={() => setView('main')}
          />
        </View>

        <ScrollView contentContainerStyle={styles.walletListContent}>
          {walletList.map((wallet) => (
            <Card
              key={wallet.id}
              onPress={() => handleSwitchWallet(wallet.id)}
              style={[
                styles.walletCard,
                wallet.id === activeWallet?.id && {
                  borderColor: theme.colors.brand.primary,
                  borderWidth: 2,
                },
              ]}
            >
              <View style={styles.walletCardContent}>
                <View
                  style={[
                    styles.walletColorDot,
                    { backgroundColor: getWalletColor(wallet.color) },
                  ]}
                />
                <View style={styles.walletCardInfo}>
                  <View style={styles.walletCardNameRow}>
                    <Text style={[styles.walletCardName, { color: theme.colors.text }]}>
                      {wallet.name}
                    </Text>
                    {wallet.isWatchOnly && (
                      <View
                        style={[
                          styles.watchOnlyBadge,
                          { backgroundColor: theme.colors.semantic.warningMuted },
                        ]}
                      >
                        <Text
                          style={[styles.watchOnlyText, { color: theme.colors.semantic.warning }]}
                        >
                          Watch
                        </Text>
                      </View>
                    )}
                    {!wallet.isBackedUp && !wallet.isWatchOnly && (
                      <View
                        style={[
                          styles.notBackedUpBadge,
                          { backgroundColor: theme.colors.semantic.errorMuted },
                        ]}
                      >
                        <Text
                          style={[styles.notBackedUpText, { color: theme.colors.semantic.error }]}
                        >
                          Backup
                        </Text>
                      </View>
                    )}
                  </View>
                  <Text style={[styles.walletCardAddress, { color: theme.colors.textMuted }]}>
                    {formatAddress(wallet.address, 8)}
                  </Text>
                  <Text style={[styles.walletCardBalance, { color: theme.colors.brand.primary }]}>
                    {formatXaiWithSymbol(wallet.balance)}
                  </Text>
                </View>
                <View style={styles.walletCardActions}>
                  <TouchableOpacity
                    onPress={() => {
                      setEditingWalletId(wallet.id);
                      setEditingName(wallet.name);
                    }}
                    hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
                  >
                    <Icon name="edit" size={18} color={theme.colors.textMuted} />
                  </TouchableOpacity>
                  <TouchableOpacity
                    onPress={() => handleDeleteWallet(wallet.id, wallet.name)}
                    hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
                  >
                    <Icon name="trash" size={18} color={theme.colors.semantic.error} />
                  </TouchableOpacity>
                </View>
              </View>
            </Card>
          ))}

          <Button
            title="Add New Wallet"
            variant="outline"
            icon="plus"
            onPress={() => setView('create')}
            style={styles.addWalletButton}
          />
        </ScrollView>

        {/* Rename Modal */}
        <Modal
          visible={!!editingWalletId}
          transparent
          animationType="fade"
          onRequestClose={() => setEditingWalletId(null)}
        >
          <View style={[styles.modalOverlay, { backgroundColor: theme.colors.overlay }]}>
            <View style={[styles.renameModal, { backgroundColor: theme.colors.surface }]}>
              <Text style={[styles.renameTitle, { color: theme.colors.text }]}>Rename Wallet</Text>
              <Input
                value={editingName}
                onChangeText={setEditingName}
                placeholder="Wallet name"
                autoFocus
              />
              <View style={styles.renameButtons}>
                <Button
                  title="Cancel"
                  variant="outline"
                  onPress={() => setEditingWalletId(null)}
                  style={{ flex: 1 }}
                />
                <Button
                  title="Save"
                  onPress={handleRenameWallet}
                  style={{ flex: 1 }}
                />
              </View>
            </View>
          </View>
        </Modal>
      </View>
    );
  }

  // Transaction history view
  if (view === 'history') {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <View style={styles.header}>
          <Text style={[styles.headerTitle, { color: theme.colors.text }]}>Transaction History</Text>
          <Button
            title="Back"
            variant="outline"
            size="small"
            onPress={() => setView('main')}
          />
        </View>
        <FlatList
          data={transactions}
          keyExtractor={(item) => item.txid}
          renderItem={({ item }) => (
            <TouchableOpacity
              onPress={() =>
                navigation.navigate('TransactionDetail' as never, { txid: item.txid } as never)
              }
            >
              <TransactionItem transaction={item} currentAddress={activeWallet!.address} />
            </TouchableOpacity>
          )}
          onEndReached={() => hasMore && !loadingTx && fetchTransactions()}
          onEndReachedThreshold={0.3}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={theme.colors.brand.primary}
            />
          }
          contentContainerStyle={styles.listContent}
          ListEmptyComponent={
            <View style={styles.emptyList}>
              <Icon name="inbox" size={48} color={theme.colors.textMuted} />
              <Text style={[styles.emptyText, { color: theme.colors.textMuted }]}>
                No transactions yet
              </Text>
            </View>
          }
          ListFooterComponent={
            loadingTx ? (
              <Text style={[styles.loadingText, { color: theme.colors.textMuted }]}>
                Loading...
              </Text>
            ) : null
          }
        />
      </View>
    );
  }

  // Main wallet view
  return (
    <ScrollView
      style={[styles.container, { backgroundColor: theme.colors.background }]}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor={theme.colors.brand.primary}
        />
      }
    >
      {/* Connection Status */}
      {!isConnected && (
        <View style={[styles.offlineBanner, { backgroundColor: theme.colors.semantic.warningMuted }]}>
          <Icon name="wifi-off" size={16} color={theme.colors.semantic.warning} />
          <Text style={[styles.offlineText, { color: theme.colors.semantic.warning }]}>
            Offline - Using cached data
          </Text>
        </View>
      )}

      {/* Wallet Selector */}
      {walletList.length > 1 && (
        <Card onPress={() => setView('wallet-list')}>
          <View style={styles.walletSelector}>
            <View
              style={[
                styles.walletColorDot,
                { backgroundColor: getWalletColor(activeWallet?.color) },
              ]}
            />
            <View style={styles.walletSelectorInfo}>
              <Text style={[styles.walletSelectorName, { color: theme.colors.text }]}>
                {activeWallet?.name}
              </Text>
              <Text style={[styles.walletSelectorCount, { color: theme.colors.textMuted }]}>
                {walletList.length} wallet{walletList.length > 1 ? 's' : ''}
              </Text>
            </View>
            <Icon name="chevron-right" size={20} color={theme.colors.textMuted} />
          </View>
        </Card>
      )}

      {/* Backup Warning */}
      {activeWallet && !activeWallet.isBackedUp && !activeWallet.isWatchOnly && (
        <Card
          style={[styles.warningCard, { backgroundColor: theme.colors.semantic.errorMuted }]}
          onPress={() => {
            // Re-generate mnemonic flow not possible without original
            Alert.alert(
              'Backup Required',
              'Your wallet has not been backed up. If you lose access, you will lose your funds permanently.'
            );
          }}
        >
          <View style={styles.warningCardContent}>
            <Icon name="alert-triangle" size={24} color={theme.colors.semantic.error} />
            <View style={styles.warningCardText}>
              <Text style={[styles.warningCardTitle, { color: theme.colors.semantic.error }]}>
                Backup Required
              </Text>
              <Text style={[styles.warningCardSubtitle, { color: theme.colors.text }]}>
                Your wallet is not backed up
              </Text>
            </View>
          </View>
        </Card>
      )}

      {/* Balance Card */}
      <Card style={styles.balanceCard}>
        <Text style={[styles.balanceLabel, { color: theme.colors.textMuted }]}>Balance</Text>
        <Text style={[styles.balanceAmount, { color: theme.colors.text }]}>
          {formatXaiWithSymbol(balance)}
        </Text>
        {activeWallet?.isWatchOnly && (
          <View
            style={[styles.watchOnlyIndicator, { backgroundColor: theme.colors.semantic.warningMuted }]}
          >
            <Icon name="eye" size={14} color={theme.colors.semantic.warning} />
            <Text style={[styles.watchOnlyIndicatorText, { color: theme.colors.semantic.warning }]}>
              Watch-only
            </Text>
          </View>
        )}
      </Card>

      {/* Address Card */}
      <Card title="Your Address">
        <Text style={[styles.addressFull, { color: theme.colors.text }]}>
          {activeWallet?.address}
        </Text>
        <View style={styles.addressActions}>
          <Button
            title="Copy"
            size="small"
            onPress={handleCopyAddress}
            style={{ flex: 1, marginRight: spacing['2'] }}
          />
          <Button
            title="Receive"
            variant="outline"
            size="small"
            onPress={() => navigation.navigate('Receive' as never)}
            style={{ flex: 1 }}
          />
        </View>
      </Card>

      {/* Faucet Card (Testnet) */}
      <Card title="Testnet Faucet">
        <Text style={[styles.faucetText, { color: theme.colors.textMuted }]}>
          Get free testnet XAI tokens for testing
        </Text>
        <Button title="Claim Tokens" variant="secondary" size="small" onPress={handleClaimFaucet} />
      </Card>

      {/* Quick Actions */}
      <Card title="Quick Actions">
        <Button
          title="View Transaction History"
          variant="secondary"
          size="small"
          onPress={() => setView('history')}
          style={styles.actionButton}
        />
        {!activeWallet?.isWatchOnly && (
          <Button
            title="Export Private Key"
            variant="outline"
            size="small"
            onPress={handleExportKey}
            style={styles.actionButton}
          />
        )}
        <Button
          title="Delete Wallet"
          variant="danger"
          size="small"
          onPress={() => handleDeleteWallet(activeWallet!.id, activeWallet!.name)}
        />
      </Card>

      {/* Wallet Info */}
      <Card title="Wallet Info">
        <View style={styles.infoRow}>
          <Text style={[styles.infoLabel, { color: theme.colors.textMuted }]}>Created</Text>
          <Text style={[styles.infoValue, { color: theme.colors.text }]}>
            {formatDate(activeWallet!.createdAt / 1000)}
          </Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={[styles.infoLabel, { color: theme.colors.textMuted }]}>Public Key</Text>
          <Text style={[styles.infoValue, { color: theme.colors.text }]}>
            {formatAddress(activeWallet!.publicKey || '', 12)}
          </Text>
        </View>
        <View style={[styles.infoRow, { borderBottomWidth: 0 }]}>
          <Text style={[styles.infoLabel, { color: theme.colors.textMuted }]}>Backed Up</Text>
          <StatusBadge
            status={activeWallet!.isBackedUp ? 'success' : 'warning'}
            label={activeWallet!.isBackedUp ? 'Yes' : 'No'}
            size="small"
          />
        </View>
      </Card>
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
  centerContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing['8'],
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: spacing['4'],
    borderBottomWidth: 1,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
  },
  listContent: {
    padding: spacing['4'],
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    marginTop: spacing['4'],
    marginBottom: spacing['2'],
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    textAlign: 'center',
    marginBottom: spacing['6'],
    lineHeight: 24,
  },
  fullWidthButton: {
    width: '100%',
    marginBottom: spacing['3'],
  },
  fullWidthInput: {
    width: '100%',
  },
  // Balance
  balanceCard: {
    alignItems: 'center',
    paddingVertical: spacing['6'],
  },
  balanceLabel: {
    fontSize: 14,
    marginBottom: spacing['2'],
  },
  balanceAmount: {
    fontSize: 32,
    fontWeight: '700',
  },
  // Address
  addressFull: {
    fontSize: 14,
    fontFamily: 'monospace',
    marginBottom: spacing['4'],
    lineHeight: 22,
  },
  addressActions: {
    flexDirection: 'row',
  },
  // Faucet
  faucetText: {
    fontSize: 14,
    marginBottom: spacing['3'],
  },
  // Actions
  actionButton: {
    marginBottom: spacing['3'],
  },
  // Info
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing['3'],
    borderBottomWidth: 1,
  },
  infoLabel: {
    fontSize: 14,
  },
  infoValue: {
    fontSize: 14,
    fontFamily: 'monospace',
  },
  // Empty
  emptyList: {
    alignItems: 'center',
    paddingVertical: spacing['8'],
  },
  emptyText: {
    marginTop: spacing['3'],
    fontSize: 16,
  },
  loadingText: {
    textAlign: 'center',
    paddingVertical: spacing['4'],
  },
  // Backup
  backupContent: {
    padding: spacing['6'],
    alignItems: 'center',
  },
  mnemonicGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: spacing['4'],
    borderRadius: borderRadius.lg,
    marginVertical: spacing['4'],
    gap: spacing['2'],
  },
  wordContainer: {
    width: '30%',
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing['2'],
  },
  wordNumber: {
    fontSize: 12,
    width: 24,
    marginRight: spacing['1'],
  },
  word: {
    fontSize: 14,
    fontWeight: '500',
  },
  warningBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    padding: spacing['4'],
    gap: spacing['3'],
    marginBottom: spacing['4'],
  },
  warningText: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
  },
  // Verification
  selectedWordsContainer: {
    flexDirection: 'row',
    gap: spacing['3'],
    marginVertical: spacing['6'],
  },
  selectedWordSlot: {
    padding: spacing['3'],
    borderRadius: borderRadius.md,
    borderWidth: 1,
    alignItems: 'center',
    minWidth: 70,
  },
  wordOptionsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing['2'],
    justifyContent: 'center',
    marginBottom: spacing['6'],
  },
  wordOption: {
    paddingHorizontal: spacing['4'],
    paddingVertical: spacing['2'],
    borderRadius: borderRadius.md,
  },
  wordOptionText: {
    fontSize: 14,
    fontWeight: '500',
  },
  // Wallet list
  walletListContent: {
    padding: spacing['4'],
  },
  walletCard: {
    marginBottom: spacing['3'],
  },
  walletCardContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  walletColorDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: spacing['3'],
  },
  walletCardInfo: {
    flex: 1,
  },
  walletCardNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing['2'],
  },
  walletCardName: {
    fontSize: 16,
    fontWeight: '600',
  },
  walletCardAddress: {
    fontSize: 12,
    fontFamily: 'monospace',
    marginTop: 2,
  },
  walletCardBalance: {
    fontSize: 14,
    fontWeight: '600',
    marginTop: 4,
  },
  walletCardActions: {
    flexDirection: 'row',
    gap: spacing['4'],
  },
  watchOnlyBadge: {
    paddingHorizontal: spacing['2'],
    paddingVertical: 2,
    borderRadius: borderRadius.sm,
  },
  watchOnlyText: {
    fontSize: 10,
    fontWeight: '600',
  },
  notBackedUpBadge: {
    paddingHorizontal: spacing['2'],
    paddingVertical: 2,
    borderRadius: borderRadius.sm,
  },
  notBackedUpText: {
    fontSize: 10,
    fontWeight: '600',
  },
  addWalletButton: {
    marginTop: spacing['4'],
  },
  // Wallet selector
  walletSelector: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  walletSelectorInfo: {
    flex: 1,
  },
  walletSelectorName: {
    fontSize: 16,
    fontWeight: '600',
  },
  walletSelectorCount: {
    fontSize: 12,
    marginTop: 2,
  },
  // Warning card
  warningCard: {
    marginBottom: spacing['4'],
  },
  warningCardContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing['3'],
  },
  warningCardText: {
    flex: 1,
  },
  warningCardTitle: {
    fontSize: 14,
    fontWeight: '600',
  },
  warningCardSubtitle: {
    fontSize: 12,
    marginTop: 2,
  },
  // Watch only indicator
  watchOnlyIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing['2'],
    paddingHorizontal: spacing['3'],
    paddingVertical: spacing['2'],
    borderRadius: borderRadius.md,
    marginTop: spacing['3'],
  },
  watchOnlyIndicatorText: {
    fontSize: 12,
    fontWeight: '500',
  },
  // Offline banner
  offlineBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing['2'],
    padding: spacing['3'],
    marginBottom: spacing['4'],
    borderRadius: borderRadius.md,
  },
  offlineText: {
    fontSize: 14,
    fontWeight: '500',
  },
  // Rename modal
  modalOverlay: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing['6'],
  },
  renameModal: {
    width: '100%',
    padding: spacing['6'],
    borderRadius: borderRadius.xl,
  },
  renameTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: spacing['4'],
    textAlign: 'center',
  },
  renameButtons: {
    flexDirection: 'row',
    gap: spacing['3'],
    marginTop: spacing['4'],
  },
});
