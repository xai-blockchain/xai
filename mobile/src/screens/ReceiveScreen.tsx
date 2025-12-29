/**
 * Receive Screen - QR code generation and address sharing
 *
 * Production-ready features:
 * - QR code generation for wallet address
 * - Share address functionality
 * - Copy address button
 * - Amount request option
 * - Multi-wallet support
 */

import React, { useState, useMemo, useCallback, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Alert,
  Share,
  Dimensions,
} from 'react-native';
import * as Clipboard from 'expo-clipboard';
import QRCode from 'react-native-qrcode-svg';
import { useRoute, RouteProp } from '@react-navigation/native';
import { Card, Button, Input, Icon } from '../components';
import { useTheme } from '../theme';
import { useWallet, useWalletList } from '../context/WalletContext';
import { triggerHaptic } from '../hooks/useHaptics';
import { formatXai, formatAddress } from '../utils/format';
import { spacing, borderRadius } from '../theme/spacing';
import { RootStackParamList } from '../types';

type ReceiveScreenRouteProp = RouteProp<RootStackParamList, 'Receive'>;

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const QR_SIZE = Math.min(SCREEN_WIDTH - 100, 280);

export function ReceiveScreen() {
  const theme = useTheme();
  const route = useRoute<ReceiveScreenRouteProp>();
  const { activeWallet, balances } = useWallet();
  const walletList = useWalletList();

  // State
  const [selectedWalletId, setSelectedWalletId] = useState<string | null>(
    route.params?.walletId || activeWallet?.id || null
  );
  const [requestAmount, setRequestAmount] = useState('');
  const [showAmountInput, setShowAmountInput] = useState(false);
  const [showWalletPicker, setShowWalletPicker] = useState(false);
  const qrRef = useRef<any>(null);

  // Get selected wallet
  const selectedWallet = useMemo(
    () => walletList.find((w) => w.id === selectedWalletId) || activeWallet,
    [walletList, selectedWalletId, activeWallet]
  );

  // Generate QR data
  const qrData = useMemo(() => {
    if (!selectedWallet) return '';

    // XAI URI format: xai:<address>?amount=<amount>
    if (requestAmount && parseFloat(requestAmount) > 0) {
      return `xai:${selectedWallet.address}?amount=${requestAmount}`;
    }
    return selectedWallet.address;
  }, [selectedWallet, requestAmount]);

  // Copy address to clipboard
  const handleCopyAddress = useCallback(async () => {
    if (!selectedWallet) return;

    try {
      await Clipboard.setStringAsync(selectedWallet.address);
      triggerHaptic('success');
      Alert.alert('Copied', 'Address copied to clipboard');
    } catch (error) {
      Alert.alert('Error', 'Failed to copy address');
    }
  }, [selectedWallet]);

  // Share address
  const handleShareAddress = useCallback(async () => {
    if (!selectedWallet) return;

    try {
      const message = requestAmount && parseFloat(requestAmount) > 0
        ? `Send ${requestAmount} XAI to my address:\n${selectedWallet.address}`
        : `My XAI address:\n${selectedWallet.address}`;

      await Share.share({
        message,
        title: 'My XAI Address',
      });
      triggerHaptic('success');
    } catch (error) {
      // User cancelled share
    }
  }, [selectedWallet, requestAmount]);

  // Copy QR code as image
  const handleCopyQRCode = useCallback(async () => {
    // Note: Copying QR as image requires additional native modules
    // For now, we'll just copy the address
    await handleCopyAddress();
  }, [handleCopyAddress]);

  // Toggle amount input
  const handleToggleAmount = useCallback(() => {
    setShowAmountInput(!showAmountInput);
    if (showAmountInput) {
      setRequestAmount('');
    }
    triggerHaptic('selection');
  }, [showAmountInput]);

  // No wallet state
  if (!selectedWallet) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <View style={styles.emptyState}>
          <Icon name="wallet" size={64} color={theme.colors.textMuted} />
          <Text style={[styles.emptyTitle, { color: theme.colors.text }]}>
            No Wallet Available
          </Text>
          <Text style={[styles.emptySubtitle, { color: theme.colors.textMuted }]}>
            Create or import a wallet to receive XAI
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
      {/* Wallet Selector (if multiple wallets) */}
      {walletList.length > 1 && (
        <Card>
          <Button
            variant="ghost"
            onPress={() => setShowWalletPicker(true)}
            style={styles.walletSelector}
          >
            <View style={styles.walletSelectorContent}>
              <View
                style={[
                  styles.walletColorDot,
                  { backgroundColor: getWalletColor(selectedWallet.color, theme) },
                ]}
              />
              <View style={styles.walletInfo}>
                <Text style={[styles.walletName, { color: theme.colors.text }]}>
                  {selectedWallet.name}
                </Text>
                <Text style={[styles.walletAddress, { color: theme.colors.textMuted }]}>
                  {formatAddress(selectedWallet.address, 8)}
                </Text>
              </View>
              <Icon name="chevron-down" size={20} color={theme.colors.textMuted} />
            </View>
          </Button>
        </Card>
      )}

      {/* QR Code Card */}
      <Card style={styles.qrCard}>
        <View style={styles.qrCodeContainer}>
          <View style={[styles.qrCodeWrapper, { backgroundColor: '#ffffff' }]}>
            <QRCode
              value={qrData}
              size={QR_SIZE}
              color="#000000"
              backgroundColor="#ffffff"
              getRef={qrRef}
              logo={undefined}
              logoSize={50}
              logoBackgroundColor="transparent"
              ecl="M"
            />
          </View>
          <Text style={[styles.scanInstruction, { color: theme.colors.textMuted }]}>
            Scan to receive XAI
          </Text>
        </View>

        {/* Address Display */}
        <View style={styles.addressContainer}>
          <Text style={[styles.addressLabel, { color: theme.colors.textMuted }]}>
            Your Address
          </Text>
          <Text
            style={[styles.addressText, { color: theme.colors.text }]}
            selectable
          >
            {selectedWallet.address}
          </Text>
        </View>

        {/* Amount Request Toggle */}
        <Button
          variant="ghost"
          onPress={handleToggleAmount}
          style={styles.amountToggle}
        >
          <View style={styles.amountToggleContent}>
            <Icon
              name={showAmountInput ? 'minus-circle' : 'plus-circle'}
              size={20}
              color={theme.colors.brand.primary}
            />
            <Text style={[styles.amountToggleText, { color: theme.colors.brand.primary }]}>
              {showAmountInput ? 'Remove amount request' : 'Request specific amount'}
            </Text>
          </View>
        </Button>

        {/* Amount Input */}
        {showAmountInput && (
          <View style={styles.amountInputContainer}>
            <Input
              label="Request Amount (XAI)"
              placeholder="0.0000"
              value={requestAmount}
              onChangeText={setRequestAmount}
              keyboardType="decimal-pad"
              rightElement={
                <Text style={[styles.xaiSymbol, { color: theme.colors.textMuted }]}>
                  XAI
                </Text>
              }
            />
            {requestAmount && parseFloat(requestAmount) > 0 && (
              <View
                style={[
                  styles.amountPreview,
                  { backgroundColor: theme.colors.brand.primaryMuted },
                ]}
              >
                <Text style={[styles.amountPreviewText, { color: theme.colors.brand.primary }]}>
                  Requesting {formatXai(parseFloat(requestAmount))} XAI
                </Text>
              </View>
            )}
          </View>
        )}
      </Card>

      {/* Action Buttons */}
      <View style={styles.actions}>
        <Button
          title="Copy Address"
          variant="primary"
          onPress={handleCopyAddress}
          icon="copy"
          style={styles.actionButton}
        />
        <Button
          title="Share"
          variant="secondary"
          onPress={handleShareAddress}
          icon="share"
          style={styles.actionButton}
        />
      </View>

      {/* Balance Info */}
      <Card title="Current Balance" style={styles.balanceCard}>
        <Text style={[styles.balanceAmount, { color: theme.colors.text }]}>
          {formatXai(selectedWallet.balance)} XAI
        </Text>
        {selectedWallet.isWatchOnly && (
          <View
            style={[
              styles.watchOnlyBadge,
              { backgroundColor: theme.colors.semantic.warningMuted },
            ]}
          >
            <Icon name="eye" size={14} color={theme.colors.semantic.warning} />
            <Text style={[styles.watchOnlyText, { color: theme.colors.semantic.warning }]}>
              Watch-only wallet
            </Text>
          </View>
        )}
      </Card>

      {/* Tips Card */}
      <Card title="Tips">
        <View style={styles.tipsList}>
          <View style={styles.tipItem}>
            <Icon name="info" size={16} color={theme.colors.brand.primary} />
            <Text style={[styles.tipText, { color: theme.colors.textMuted }]}>
              Only send XAI tokens to this address
            </Text>
          </View>
          <View style={styles.tipItem}>
            <Icon name="shield" size={16} color={theme.colors.semantic.success} />
            <Text style={[styles.tipText, { color: theme.colors.textMuted }]}>
              Verify the address before sharing
            </Text>
          </View>
          <View style={styles.tipItem}>
            <Icon name="clock" size={16} color={theme.colors.semantic.warning} />
            <Text style={[styles.tipText, { color: theme.colors.textMuted }]}>
              Transactions typically confirm in 30-60 seconds
            </Text>
          </View>
        </View>
      </Card>

      {/* Wallet Picker Modal */}
      {showWalletPicker && (
        <View style={[styles.modalOverlay, { backgroundColor: theme.colors.overlay }]}>
          <View style={[styles.modalContent, { backgroundColor: theme.colors.surface }]}>
            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: theme.colors.text }]}>
                Select Wallet
              </Text>
              <Button
                title="Done"
                variant="ghost"
                size="small"
                onPress={() => setShowWalletPicker(false)}
              />
            </View>
            <ScrollView style={styles.walletList}>
              {walletList.map((wallet) => (
                <Button
                  key={wallet.id}
                  variant="ghost"
                  onPress={() => {
                    setSelectedWalletId(wallet.id);
                    setShowWalletPicker(false);
                    triggerHaptic('selection');
                  }}
                  style={[
                    styles.walletOption,
                    selectedWalletId === wallet.id && {
                      backgroundColor: theme.colors.brand.primaryMuted,
                    },
                  ]}
                >
                  <View style={styles.walletOptionContent}>
                    <View
                      style={[
                        styles.walletColorDot,
                        { backgroundColor: getWalletColor(wallet.color, theme) },
                      ]}
                    />
                    <View style={styles.walletInfo}>
                      <Text style={[styles.walletName, { color: theme.colors.text }]}>
                        {wallet.name}
                      </Text>
                      <Text style={[styles.walletBalance, { color: theme.colors.textMuted }]}>
                        {formatXai(wallet.balance)} XAI
                      </Text>
                    </View>
                    {selectedWalletId === wallet.id && (
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

// Helper to get wallet color
function getWalletColor(color: string | undefined, theme: any): string {
  const colors: Record<string, string> = {
    indigo: '#6366f1',
    emerald: '#10b981',
    amber: '#f59e0b',
    rose: '#f43f5e',
    cyan: '#06b6d4',
    purple: '#8b5cf6',
  };
  return colors[color || 'indigo'] || colors.indigo;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    padding: spacing['4'],
    paddingBottom: spacing['8'],
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing['8'],
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginTop: spacing['4'],
    textAlign: 'center',
  },
  emptySubtitle: {
    fontSize: 14,
    marginTop: spacing['2'],
    textAlign: 'center',
  },
  // Wallet selector
  walletSelector: {
    padding: spacing['2'],
  },
  walletSelectorContent: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  walletColorDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: spacing['3'],
  },
  walletInfo: {
    flex: 1,
  },
  walletName: {
    fontSize: 16,
    fontWeight: '600',
  },
  walletAddress: {
    fontSize: 12,
    marginTop: 2,
    fontFamily: 'monospace',
  },
  walletBalance: {
    fontSize: 12,
    marginTop: 2,
  },
  // QR Card
  qrCard: {
    alignItems: 'center',
    paddingVertical: spacing['6'],
  },
  qrCodeContainer: {
    alignItems: 'center',
    marginBottom: spacing['4'],
  },
  qrCodeWrapper: {
    padding: spacing['4'],
    borderRadius: borderRadius.lg,
  },
  scanInstruction: {
    fontSize: 14,
    marginTop: spacing['3'],
  },
  // Address
  addressContainer: {
    width: '100%',
    alignItems: 'center',
    paddingHorizontal: spacing['4'],
    marginBottom: spacing['4'],
  },
  addressLabel: {
    fontSize: 12,
    marginBottom: spacing['2'],
  },
  addressText: {
    fontSize: 14,
    fontFamily: 'monospace',
    textAlign: 'center',
    lineHeight: 22,
  },
  // Amount toggle
  amountToggle: {
    width: '100%',
    padding: spacing['2'],
  },
  amountToggleContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing['2'],
  },
  amountToggleText: {
    fontSize: 14,
    fontWeight: '500',
  },
  // Amount input
  amountInputContainer: {
    width: '100%',
    paddingTop: spacing['3'],
  },
  xaiSymbol: {
    fontSize: 14,
    fontWeight: '600',
  },
  amountPreview: {
    padding: spacing['2'],
    borderRadius: borderRadius.md,
    alignItems: 'center',
    marginTop: spacing['2'],
  },
  amountPreviewText: {
    fontSize: 14,
    fontWeight: '500',
  },
  // Actions
  actions: {
    flexDirection: 'row',
    gap: spacing['3'],
    marginBottom: spacing['4'],
  },
  actionButton: {
    flex: 1,
  },
  // Balance card
  balanceCard: {
    alignItems: 'center',
    paddingVertical: spacing['4'],
  },
  balanceAmount: {
    fontSize: 24,
    fontWeight: '700',
  },
  watchOnlyBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing['2'],
    padding: spacing['2'],
    borderRadius: borderRadius.md,
    marginTop: spacing['3'],
  },
  watchOnlyText: {
    fontSize: 12,
    fontWeight: '500',
  },
  // Tips
  tipsList: {
    gap: spacing['3'],
  },
  tipItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing['2'],
  },
  tipText: {
    fontSize: 14,
    flex: 1,
  },
  // Modal
  modalOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'flex-end',
  },
  modalContent: {
    borderTopLeftRadius: borderRadius.xl,
    borderTopRightRadius: borderRadius.xl,
    maxHeight: '60%',
    paddingBottom: spacing['6'],
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: spacing['4'],
    borderBottomWidth: 1,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  walletList: {
    padding: spacing['2'],
  },
  walletOption: {
    padding: spacing['3'],
    borderRadius: borderRadius.md,
    marginBottom: spacing['1'],
  },
  walletOptionContent: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
});
