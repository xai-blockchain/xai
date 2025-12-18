import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  SafeAreaView,
  Alert,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '@/types';
import { useWalletStore } from '@/store/wallet';
import { COLORS } from '@/constants';

type ImportWalletScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'ImportWallet'>;
};

const ImportWalletScreen: React.FC<ImportWalletScreenProps> = ({ navigation }) => {
  const { importWallet, isLoading } = useWalletStore();
  const [method, setMethod] = useState<'mnemonic' | 'privateKey'>('mnemonic');
  const [input, setInput] = useState('');

  const handleImport = async () => {
    if (!input.trim()) {
      Alert.alert('Error', 'Please enter your recovery phrase or private key');
      return;
    }

    const result = await importWallet(method, input.trim());

    if (result.success) {
      navigation.replace('BiometricSetup');
    } else {
      Alert.alert('Error', result.error || 'Failed to import wallet');
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>Import Wallet</Text>
          <Text style={styles.subtitle}>Restore your wallet using your recovery phrase or private key</Text>
        </View>

        <View style={styles.methodSelector}>
          <TouchableOpacity
            style={[styles.methodButton, method === 'mnemonic' && styles.methodButtonActive]}
            onPress={() => setMethod('mnemonic')}>
            <Text
              style={[
                styles.methodButtonText,
                method === 'mnemonic' && styles.methodButtonTextActive,
              ]}>
              Recovery Phrase
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.methodButton, method === 'privateKey' && styles.methodButtonActive]}
            onPress={() => setMethod('privateKey')}>
            <Text
              style={[
                styles.methodButtonText,
                method === 'privateKey' && styles.methodButtonTextActive,
              ]}>
              Private Key
            </Text>
          </TouchableOpacity>
        </View>

        <View style={styles.inputContainer}>
          <Text style={styles.label}>
            {method === 'mnemonic' ? 'Enter your 24-word recovery phrase' : 'Enter your private key'}
          </Text>
          <TextInput
            style={styles.input}
            placeholder={
              method === 'mnemonic'
                ? 'word1 word2 word3...'
                : '0x...'
            }
            placeholderTextColor={COLORS.text + '40'}
            value={input}
            onChangeText={setInput}
            multiline
            numberOfLines={method === 'mnemonic' ? 4 : 2}
            autoCapitalize="none"
            autoCorrect={false}
            editable={!isLoading}
          />
        </View>

        <View style={styles.footer}>
          {isLoading ? (
            <ActivityIndicator size="large" color={COLORS.primary} />
          ) : (
            <>
              <TouchableOpacity style={styles.primaryButton} onPress={handleImport}>
                <Text style={styles.primaryButtonText}>Import Wallet</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.secondaryButton} onPress={() => navigation.goBack()}>
                <Text style={styles.secondaryButtonText}>Back</Text>
              </TouchableOpacity>
            </>
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
    padding: 24,
    gap: 24,
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
  methodSelector: {
    flexDirection: 'row',
    gap: 12,
  },
  methodButton: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: COLORS.border,
    alignItems: 'center',
  },
  methodButtonActive: {
    backgroundColor: COLORS.primary,
    borderColor: COLORS.primary,
  },
  methodButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.text,
  },
  methodButtonTextActive: {
    color: '#FFFFFF',
  },
  inputContainer: {
    gap: 8,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.text,
  },
  input: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    fontSize: 14,
    color: COLORS.text,
    minHeight: 100,
    textAlignVertical: 'top',
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  footer: {
    gap: 12,
    marginTop: 20,
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
});

export default ImportWalletScreen;
