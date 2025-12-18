import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '@/types';
import { useAppStore } from '@/store/app';
import BiometricService from '@/services/biometric';
import { COLORS } from '@/constants';

type BiometricSetupScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'BiometricSetup'>;
};

const BiometricSetupScreen: React.FC<BiometricSetupScreenProps> = ({ navigation }) => {
  const { enableBiometric } = useAppStore();
  const [available, setAvailable] = useState(false);
  const [biometryType, setBiometryType] = useState<string>('');

  useEffect(() => {
    checkBiometric();
  }, []);

  const checkBiometric = async () => {
    const result = await BiometricService.isAvailable();
    setAvailable(result.available);
    setBiometryType(result.biometryType || 'Biometric');
  };

  const handleEnable = async () => {
    const result = await enableBiometric();
    if (result.success) {
      navigation.replace('MainTabs');
    }
  };

  const handleSkip = () => {
    navigation.replace('MainTabs');
  };

  if (!available) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.content}>
          <View style={styles.header}>
            <Text style={styles.icon}>🔐</Text>
            <Text style={styles.title}>Biometric Unavailable</Text>
            <Text style={styles.subtitle}>
              Biometric authentication is not available on this device
            </Text>
          </View>

          <TouchableOpacity style={styles.primaryButton} onPress={handleSkip}>
            <Text style={styles.primaryButtonText}>Continue</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.icon}>🔐</Text>
          <Text style={styles.title}>Enable {biometryType}</Text>
          <Text style={styles.subtitle}>
            Use {biometryType} to quickly and securely access your wallet
          </Text>
        </View>

        <View style={styles.benefits}>
          <BenefitItem text="Quick access to your wallet" />
          <BenefitItem text="Enhanced security" />
          <BenefitItem text="No need to remember PIN" />
        </View>

        <View style={styles.footer}>
          <TouchableOpacity style={styles.primaryButton} onPress={handleEnable}>
            <Text style={styles.primaryButtonText}>Enable {biometryType}</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.secondaryButton} onPress={handleSkip}>
            <Text style={styles.secondaryButtonText}>Skip for Now</Text>
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
};

const BenefitItem: React.FC<{ text: string }> = ({ text }) => (
  <View style={styles.benefitItem}>
    <Text style={styles.checkmark}>✓</Text>
    <Text style={styles.benefitText}>{text}</Text>
  </View>
);

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
    alignItems: 'center',
    marginTop: 60,
  },
  icon: {
    fontSize: 80,
    marginBottom: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: COLORS.text,
    marginBottom: 12,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    color: COLORS.text,
    opacity: 0.7,
    lineHeight: 24,
    textAlign: 'center',
  },
  benefits: {
    gap: 16,
  },
  benefitItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  checkmark: {
    fontSize: 24,
    color: COLORS.success,
  },
  benefitText: {
    fontSize: 16,
    color: COLORS.text,
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
});

export default BiometricSetupScreen;
