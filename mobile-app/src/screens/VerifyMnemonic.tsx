import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  Alert,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '@/types';
import { COLORS } from '@/constants';

type VerifyMnemonicScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'VerifyMnemonic'>;
  route: RouteProp<RootStackParamList, 'VerifyMnemonic'>;
};

const VerifyMnemonicScreen: React.FC<VerifyMnemonicScreenProps> = ({ navigation, route }) => {
  const { mnemonic } = route.params;
  const words = mnemonic.split(' ');
  const [selectedWords, setSelectedWords] = useState<string[]>([]);
  const [availableWords, setAvailableWords] = useState<string[]>([]);
  const [testIndices, setTestIndices] = useState<number[]>([]);

  useEffect(() => {
    // Select 4 random words to verify
    const indices: number[] = [];
    while (indices.length < 4) {
      const randomIndex = Math.floor(Math.random() * words.length);
      if (!indices.includes(randomIndex)) {
        indices.push(randomIndex);
      }
    }
    indices.sort((a, b) => a - b);
    setTestIndices(indices);

    // Create shuffled array of correct words
    const testWords = indices.map(i => words[i]);
    const shuffled = [...testWords].sort(() => Math.random() - 0.5);
    setAvailableWords(shuffled);
  }, []);

  const handleWordSelect = (word: string) => {
    setSelectedWords([...selectedWords, word]);
    setAvailableWords(availableWords.filter(w => w !== word));
  };

  const handleWordRemove = (index: number) => {
    const word = selectedWords[index];
    setAvailableWords([...availableWords, word]);
    setSelectedWords(selectedWords.filter((_, i) => i !== index));
  };

  const handleVerify = () => {
    const isCorrect = testIndices.every((wordIndex, i) => {
      return words[wordIndex] === selectedWords[i];
    });

    if (isCorrect) {
      navigation.navigate('BiometricSetup');
    } else {
      Alert.alert(
        'Verification Failed',
        'The words you selected are not in the correct order. Please try again.',
        [
          {
            text: 'Try Again',
            onPress: () => {
              setSelectedWords([]);
              setAvailableWords([...testIndices.map(i => words[i])].sort(() => Math.random() - 0.5));
            },
          },
        ],
      );
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>Verify Recovery Phrase</Text>
          <Text style={styles.subtitle}>
            Select the words in the correct order to verify your backup
          </Text>
        </View>

        <View style={styles.verifyContainer}>
          <Text style={styles.sectionTitle}>Select words #{testIndices.map(i => i + 1).join(', ')}</Text>

          <View style={styles.selectedContainer}>
            {testIndices.map((wordIndex, i) => (
              <TouchableOpacity
                key={i}
                style={styles.selectedSlot}
                onPress={() => selectedWords[i] && handleWordRemove(i)}
                disabled={!selectedWords[i]}>
                <Text style={styles.slotNumber}>{wordIndex + 1}</Text>
                <Text style={styles.selectedWord}>{selectedWords[i] || '___'}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <View style={styles.wordsContainer}>
          <Text style={styles.sectionTitle}>Available Words</Text>
          <View style={styles.wordGrid}>
            {availableWords.map((word, index) => (
              <TouchableOpacity
                key={index}
                style={styles.wordButton}
                onPress={() => handleWordSelect(word)}>
                <Text style={styles.wordButtonText}>{word}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <View style={styles.footer}>
          <TouchableOpacity
            style={[
              styles.primaryButton,
              selectedWords.length !== testIndices.length && styles.buttonDisabled,
            ]}
            onPress={handleVerify}
            disabled={selectedWords.length !== testIndices.length}>
            <Text style={styles.primaryButtonText}>Verify</Text>
          </TouchableOpacity>
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
  verifyContainer: {
    gap: 12,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.text,
    opacity: 0.7,
  },
  selectedContainer: {
    gap: 8,
  },
  selectedSlot: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.card,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: COLORS.border,
  },
  slotNumber: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.primary,
    marginRight: 12,
    width: 24,
  },
  selectedWord: {
    fontSize: 16,
    fontWeight: '500',
    color: COLORS.text,
    flex: 1,
  },
  wordsContainer: {
    flex: 1,
    gap: 12,
  },
  wordGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  wordButton: {
    backgroundColor: COLORS.primary,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
  },
  wordButtonText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#FFFFFF',
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

export default VerifyMnemonicScreen;
