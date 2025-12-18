import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  SafeAreaView,
  Alert,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '@/types';
import { useWalletStore } from '@/store/wallet';
import { COLORS } from '@/constants';

type CreateWalletScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'CreateWallet'>;
};

const CreateWalletScreen: React.FC<CreateWalletScreenProps> = ({ navigation }) => {
  const { createWallet, isLoading } = useWalletStore();
  const [step, setStep] = useState<'info' | 'creating'>('info');

  const handleCreateWallet = async () => {
    setStep('creating');

    const result = await createWallet();

    if (result.success && result.mnemonic) {
      navigation.replace('BackupMnemonic', { mnemonic: result.mnemonic });
    } else {
      Alert.alert('Error', result.error || 'Failed to create wallet');
      setStep('info');
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        {step === 'info' ? (
          <>
            <View style={styles.header}>
              <Text style={styles.title}>Create New Wallet</Text>
              <Text style={styles.subtitle}>
                Your wallet will be secured with a 24-word recovery phrase
              </Text>
            </View>

            <View style={styles.infoBox}>
              <Text style={styles.infoTitle}>Important:</Text>
              <Text style={styles.infoText}>
                • Write down your recovery phrase{'\n'}
                • Store it in a safe place{'\n'}
                • Never share it with anyone{'\n'}
                • You'll need it to recover your wallet
              </Text>
            </View>

            <View style={styles.footer}>
              <TouchableOpacity
                style={styles.primaryButton}
                onPress={handleCreateWallet}
                disabled={isLoading}>
                <Text style={styles.primaryButtonText}>Continue</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.secondaryButton}
                onPress={() => navigation.goBack()}>
                <Text style={styles.secondaryButtonText}>Back</Text>
              </TouchableOpacity>
            </View>
          </>
        ) : (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color={COLORS.primary} />
            <Text style={styles.loadingText}>Creating your wallet...</Text>
          </View>
        )}
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
    justifyContent: 'space-between',
  },
  header: {
    marginTop: 40,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: COLORS.text,
    marginBottom: 12,
  },
  subtitle: {
    fontSize: 16,
    color: COLORS.text,
    opacity: 0.7,
    lineHeight: 24,
  },
  infoBox: {
    backgroundColor: COLORS.card,
    padding: 20,
    borderRadius: 12,
    borderLeftWidth: 4,
    borderLeftColor: COLORS.warning,
  },
  infoTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.text,
    marginBottom: 12,
  },
  infoText: {
    fontSize: 14,
    color: COLORS.text,
    lineHeight: 24,
  },
  footer: {
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
  },
  secondaryButtonText: {
    color: COLORS.primary,
    fontSize: 16,
    fontWeight: '600',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 20,
  },
  loadingText: {
    fontSize: 16,
    color: COLORS.text,
    opacity: 0.7,
  },
});

export default CreateWalletScreen;
