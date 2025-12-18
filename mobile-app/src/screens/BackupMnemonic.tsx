import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  ScrollView,
  Alert,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '@/types';
import { COLORS } from '@/constants';
import * as Clipboard from '@react-native-clipboard/clipboard';

type BackupMnemonicScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'BackupMnemonic'>;
  route: RouteProp<RootStackParamList, 'BackupMnemonic'>;
};

const BackupMnemonicScreen: React.FC<BackupMnemonicScreenProps> = ({ navigation, route }) => {
  const { mnemonic } = route.params;
  const words = mnemonic.split(' ');
  const [copied, setCopied] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  const handleCopy = () => {
    Clipboard.setString(mnemonic);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleContinue = () => {
    if (!confirmed) {
      Alert.alert(
        'Confirmation Required',
        'Please confirm that you have securely backed up your recovery phrase',
      );
      return;
    }
    navigation.navigate('VerifyMnemonic', { mnemonic });
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>Backup Recovery Phrase</Text>
          <Text style={styles.subtitle}>
            Write down these 24 words in order and keep them safe
          </Text>
        </View>

        <View style={styles.warningBox}>
          <Text style={styles.warningTitle}>⚠️ Critical Security Information</Text>
          <Text style={styles.warningText}>
            • Anyone with this phrase can access your funds{'\n'}
            • Never share it with anyone{'\n'}
            • Store it offline in multiple secure locations{'\n'}
            • XAI will never ask for your recovery phrase
          </Text>
        </View>

        <View style={styles.mnemonicContainer}>
          {words.map((word, index) => (
            <View key={index} style={styles.wordItem}>
              <Text style={styles.wordNumber}>{index + 1}</Text>
              <Text style={styles.word}>{word}</Text>
            </View>
          ))}
        </View>

        <TouchableOpacity style={styles.copyButton} onPress={handleCopy}>
          <Text style={styles.copyButtonText}>{copied ? 'Copied!' : 'Copy to Clipboard'}</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.checkboxContainer}
          onPress={() => setConfirmed(!confirmed)}>
          <View style={[styles.checkbox, confirmed && styles.checkboxChecked]}>
            {confirmed && <Text style={styles.checkmark}>✓</Text>}
          </View>
          <Text style={styles.checkboxLabel}>
            I have written down and securely stored my recovery phrase
          </Text>
        </TouchableOpacity>

        <View style={styles.footer}>
          <TouchableOpacity
            style={[styles.primaryButton, !confirmed && styles.buttonDisabled]}
            onPress={handleContinue}
            disabled={!confirmed}>
            <Text style={styles.primaryButtonText}>Continue</Text>
          </TouchableOpacity>
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
    marginTop: 20,
  },
  title: {
    fontSize: 28,
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
  warningBox: {
    backgroundColor: COLORS.warning + '20',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: COLORS.warning,
  },
  warningTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.text,
    marginBottom: 8,
  },
  warningText: {
    fontSize: 13,
    color: COLORS.text,
    lineHeight: 22,
  },
  mnemonicContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  wordItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.card,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    width: '48%',
  },
  wordNumber: {
    fontSize: 12,
    fontWeight: '600',
    color: COLORS.primary,
    marginRight: 8,
    width: 20,
  },
  word: {
    fontSize: 14,
    fontWeight: '500',
    color: COLORS.text,
    flex: 1,
  },
  copyButton: {
    backgroundColor: COLORS.card,
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  copyButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.primary,
  },
  checkboxContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: COLORS.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkboxChecked: {
    backgroundColor: COLORS.primary,
    borderColor: COLORS.primary,
  },
  checkmark: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: 'bold',
  },
  checkboxLabel: {
    flex: 1,
    fontSize: 14,
    color: COLORS.text,
    lineHeight: 20,
  },
  footer: {
    marginTop: 8,
  },
  primaryButton: {
    backgroundColor: COLORS.primary,
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 12,
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default BackupMnemonicScreen;
