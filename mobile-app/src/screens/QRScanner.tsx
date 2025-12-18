import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView, Alert } from 'react-native';
import { RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '@/types';
import { COLORS } from '@/constants';

type QRScannerScreenProps = {
  route: RouteProp<RootStackParamList, 'QRScanner'>;
  navigation: NativeStackNavigationProp<RootStackParamList, 'QRScanner'>;
};

const QRScanner: React.FC<QRScannerScreenProps> = ({ route, navigation }) => {
  const { onScan } = route.params;
  const [scanned, setScanned] = useState(false);

  const handleBarCodeScanned = ({ type, data }: { type: string; data: string }) => {
    if (scanned) return;

    setScanned(true);
    onScan(data);
    navigation.goBack();
  };

  // Note: This is a placeholder. In a real implementation, you would use
  // react-native-camera or expo-camera for QR code scanning

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.scanArea}>
          <Text style={styles.instructions}>QR Scanner</Text>
          <Text style={styles.subtitle}>Camera integration will be added</Text>

          <TouchableOpacity
            style={styles.testButton}
            onPress={() => {
              // For testing purposes
              const testAddress = 'XAI' + '0'.repeat(40);
              onScan(testAddress);
              navigation.goBack();
            }}>
            <Text style={styles.testButtonText}>Use Test Address</Text>
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scanArea: {
    width: 280,
    height: 280,
    borderWidth: 2,
    borderColor: COLORS.primary,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 16,
  },
  instructions: {
    fontSize: 20,
    fontWeight: '600',
    color: '#FFFFFF',
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 14,
    color: '#FFFFFF',
    opacity: 0.7,
    textAlign: 'center',
  },
  testButton: {
    backgroundColor: COLORS.primary,
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    marginTop: 20,
  },
  testButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
});

export default QRScanner;
