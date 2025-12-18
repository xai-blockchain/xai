import React, { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { RootStackParamList } from '@/types';
import { useWalletStore } from '@/store/wallet';
import { useAppStore } from '@/store/app';

// Screens
import OnboardingScreen from '@/screens/Onboarding';
import WelcomeScreen from '@/screens/Welcome';
import CreateWalletScreen from '@/screens/CreateWallet';
import ImportWalletScreen from '@/screens/ImportWallet';
import BackupMnemonicScreen from '@/screens/BackupMnemonic';
import VerifyMnemonicScreen from '@/screens/VerifyMnemonic';
import BiometricSetupScreen from '@/screens/BiometricSetup';
import MainTabNavigator from './MainTabNavigator';
import TransactionDetailScreen from '@/screens/TransactionDetail';
import QRScannerScreen from '@/screens/QRScanner';
import LockScreen from '@/screens/LockScreen';

const Stack = createNativeStackNavigator<RootStackParamList>();

const RootNavigator: React.FC = () => {
  const { wallet, loadWallet } = useWalletStore();
  const { isLocked, isInitialized, initialize } = useAppStore();

  useEffect(() => {
    const init = async () => {
      await initialize();
      await loadWallet();
    };
    init();
  }, []);

  if (!isInitialized) {
    return null; // Show splash screen
  }

  if (isLocked) {
    return <LockScreen />;
  }

  return (
    <NavigationContainer>
      <Stack.Navigator
        screenOptions={{
          headerShown: false,
          animation: 'slide_from_right',
        }}>
        {!wallet ? (
          <>
            <Stack.Screen name="Onboarding" component={OnboardingScreen} />
            <Stack.Screen name="Welcome" component={WelcomeScreen} />
            <Stack.Screen name="CreateWallet" component={CreateWalletScreen} />
            <Stack.Screen name="ImportWallet" component={ImportWalletScreen} />
            <Stack.Screen name="BackupMnemonic" component={BackupMnemonicScreen} />
            <Stack.Screen name="VerifyMnemonic" component={VerifyMnemonicScreen} />
            <Stack.Screen name="BiometricSetup" component={BiometricSetupScreen} />
          </>
        ) : (
          <>
            <Stack.Screen name="MainTabs" component={MainTabNavigator} />
            <Stack.Screen
              name="TransactionDetail"
              component={TransactionDetailScreen}
              options={{ headerShown: true, title: 'Transaction Details' }}
            />
            <Stack.Screen
              name="QRScanner"
              component={QRScannerScreen}
              options={{ headerShown: true, title: 'Scan QR Code' }}
            />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
};

export default RootNavigator;
