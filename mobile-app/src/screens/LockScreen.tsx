import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView } from 'react';
import { useAppStore } from '@/store/app';
import BiometricService from '@/services/biometric';
import { COLORS } from '@/constants';

const LockScreen: React.FC = () => {
  const { unlockApp, settings, biometricConfig } = useAppStore();
  const [error, setError] = useState('');

  useEffect(() => {
    if (settings.biometricEnabled && biometricConfig.enabled) {
      attemptBiometric();
    }
  }, []);

  const attemptBiometric = async () => {
    const success = await BiometricService.authenticate('Unlock XAI Wallet');
    if (success) {
      unlockApp();
    } else {
      setError('Authentication failed');
    }
  };

  const handlePinUnlock = () => {
    // PIN entry will be implemented
    unlockApp();
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.logo}>🔒</Text>
          <Text style={styles.title}>Wallet Locked</Text>
          <Text style={styles.subtitle}>Authenticate to continue</Text>
        </View>

        {error && <Text style={styles.error}>{error}</Text>}

        <View style={styles.actions}>
          {settings.biometricEnabled && (
            <TouchableOpacity style={styles.primaryButton} onPress={attemptBiometric}>
              <Text style={styles.primaryButtonText}>
                Use {biometricConfig.biometryType || 'Biometric'}
              </Text>
            </TouchableOpacity>
          )}

          <TouchableOpacity style={styles.secondaryButton} onPress={handlePinUnlock}>
            <Text style={styles.secondaryButtonText}>Enter PIN</Text>
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
    justifyContent: 'center',
    gap: 32,
  },
  header: {
    alignItems: 'center',
  },
  logo: {
    fontSize: 80,
    marginBottom: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: COLORS.text,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: COLORS.text,
    opacity: 0.7,
  },
  error: {
    fontSize: 14,
    color: COLORS.error,
    textAlign: 'center',
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
});

export default LockScreen;
