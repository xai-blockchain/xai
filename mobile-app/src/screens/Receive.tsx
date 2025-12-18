import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  Share,
  Alert,
} from 'react-native';
import QRCode from 'react-native-qrcode-svg';
import * as Clipboard from '@react-native-clipboard/clipboard';
import { useWalletStore } from '@/store/wallet';
import { COLORS, UI } from '@/constants';

const Receive: React.FC = () => {
  const { wallet } = useWalletStore();
  const [copied, setCopied] = useState(false);

  if (!wallet) return null;

  const handleCopy = () => {
    Clipboard.setString(wallet.address);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleShare = async () => {
    try {
      await Share.share({
        message: `My XAI Wallet Address:\n${wallet.address}`,
        title: 'XAI Wallet Address',
      });
    } catch (error) {
      console.error('Share error:', error);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>Receive XAI</Text>
          <Text style={styles.subtitle}>Share your address to receive XAI tokens</Text>
        </View>

        <View style={styles.qrContainer}>
          <View style={styles.qrWrapper}>
            <QRCode value={wallet.address} size={UI.QR_SIZE} backgroundColor="#FFFFFF" />
          </View>
        </View>

        <View style={styles.addressContainer}>
          <Text style={styles.addressLabel}>Your Wallet Address</Text>
          <View style={styles.addressBox}>
            <Text style={styles.address}>{wallet.address}</Text>
          </View>
        </View>

        <View style={styles.actions}>
          <TouchableOpacity style={styles.primaryButton} onPress={handleCopy}>
            <Text style={styles.primaryButtonText}>{copied ? 'Copied!' : 'Copy Address'}</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.secondaryButton} onPress={handleShare}>
            <Text style={styles.secondaryButtonText}>Share Address</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.infoBox}>
          <Text style={styles.infoTitle}>Important:</Text>
          <Text style={styles.infoText}>
            • Only send XAI tokens to this address{'\n'}
            • Sending other tokens may result in permanent loss{'\n'}
            • Always verify the address before sending
          </Text>
        </View>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  content: {
    flex: 1,
    padding: 24,
    gap: 24,
  },
  header: {
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: COLORS.text,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: COLORS.text,
    opacity: 0.7,
    textAlign: 'center',
  },
  qrContainer: {
    alignItems: 'center',
    marginVertical: 20,
  },
  qrWrapper: {
    backgroundColor: '#FFFFFF',
    padding: 20,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  addressContainer: {
    gap: 8,
  },
  addressLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.text,
    textAlign: 'center',
  },
  addressBox: {
    backgroundColor: COLORS.card,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  address: {
    fontSize: 12,
    color: COLORS.text,
    textAlign: 'center',
    fontFamily: 'monospace',
  },
  actions: {
    gap: 12,
  },
  primaryButton: {
    backgroundColor: COLORS.primary,
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 12,
    alignItems: 'center',
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButton: {
    backgroundColor: 'transparent',
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 12,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: COLORS.primary,
  },
  secondaryButtonText: {
    color: COLORS.primary,
    fontSize: 16,
    fontWeight: '600',
  },
  infoBox: {
    backgroundColor: COLORS.card,
    padding: 16,
    borderRadius: 12,
    borderLeftWidth: 4,
    borderLeftColor: COLORS.primary,
  },
  infoTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.text,
    marginBottom: 8,
  },
  infoText: {
    fontSize: 12,
    color: COLORS.text,
    lineHeight: 20,
    opacity: 0.8,
  },
});

export default Receive;
