/**
 * XAI Mobile App - Main Entry Point
 *
 * Cross-platform React Native app for the XAI blockchain.
 * Supports iOS, Android, and Web via Expo.
 */

import React, { useEffect, useState, useCallback } from 'react';
import { StatusBar, View, Text, StyleSheet } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import * as SecureStore from 'expo-secure-store';

import { WalletProvider } from './src/context/WalletContext';
import {
  HomeScreen,
  WalletScreen,
  SendScreen,
  ExplorerScreen,
  SettingsScreen,
  ReceiveScreen,
  TransactionDetailScreen,
  AddressBookScreen,
} from './src/screens';
import {
  useTheme,
  useNavigationTheme,
  darkTheme,
  lightTheme,
} from './src/theme';
import { Icon, IconName } from './src/components/Icon';
import { Onboarding } from './src/components/Onboarding';
import { LoadingOverlay } from './src/components/ProgressIndicator';
import { triggerHaptic } from './src/hooks/useHaptics';
import { initNetworkMonitoring, stopNetworkMonitoring } from './src/utils/offline';

// Storage key for onboarding completion
const ONBOARDING_KEY = 'xai_onboarding_complete';

// Type definitions for navigation
export type RootStackParamList = {
  Main: undefined;
  Send: { recipient?: string; amount?: number } | undefined;
  Receive: { walletId?: string } | undefined;
  TransactionDetail: { txid: string };
  Settings: undefined;
  AddressBook: { selectMode?: boolean } | undefined;
};

type MainTabParamList = {
  Home: undefined;
  Wallet: undefined;
  Explorer: undefined;
  Settings: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<MainTabParamList>();

// Tab bar icon component
function TabBarIcon({
  name,
  focused,
  color,
}: {
  name: IconName;
  focused: boolean;
  color: string;
}) {
  return (
    <View style={styles.tabIconContainer}>
      <Icon name={name} size={24} color={color} />
      {focused && <View style={[styles.tabIndicator, { backgroundColor: color }]} />}
    </View>
  );
}

// Main tab navigator
function MainTabs() {
  const theme = useTheme();

  return (
    <Tab.Navigator
      screenOptions={{
        headerStyle: {
          backgroundColor: theme.colors.background,
        },
        headerTintColor: theme.colors.text,
        headerTitleStyle: {
          fontWeight: '600',
          fontSize: 18,
        },
        headerShadowVisible: false,
        tabBarStyle: {
          backgroundColor: theme.colors.surface,
          borderTopColor: theme.colors.border,
          borderTopWidth: 1,
          paddingBottom: 8,
          paddingTop: 8,
          height: 64,
        },
        tabBarActiveTintColor: theme.colors.brand.primary,
        tabBarInactiveTintColor: theme.colors.textMuted,
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: '600',
          marginTop: 2,
        },
        tabBarHideOnKeyboard: true,
      }}
      screenListeners={{
        tabPress: () => {
          triggerHaptic('selection');
        },
      }}
    >
      <Tab.Screen
        name="Home"
        component={HomeScreen}
        options={{
          title: 'XAI Wallet',
          tabBarLabel: 'Home',
          tabBarIcon: ({ focused, color }) => (
            <TabBarIcon name="home" focused={focused} color={color} />
          ),
          tabBarAccessibilityLabel: 'Home tab',
        }}
      />
      <Tab.Screen
        name="Wallet"
        component={WalletScreen}
        options={{
          title: 'Wallet',
          tabBarLabel: 'Wallet',
          tabBarIcon: ({ focused, color }) => (
            <TabBarIcon name="wallet" focused={focused} color={color} />
          ),
          tabBarAccessibilityLabel: 'Wallet tab',
        }}
      />
      <Tab.Screen
        name="Explorer"
        component={ExplorerScreen}
        options={{
          title: 'Explorer',
          tabBarLabel: 'Explorer',
          tabBarIcon: ({ focused, color }) => (
            <TabBarIcon name="explorer" focused={focused} color={color} />
          ),
          tabBarAccessibilityLabel: 'Block explorer tab',
        }}
      />
      <Tab.Screen
        name="Settings"
        component={SettingsScreen}
        options={{
          title: 'Settings',
          tabBarLabel: 'Settings',
          tabBarIcon: ({ focused, color }) => (
            <TabBarIcon name="settings" focused={focused} color={color} />
          ),
          tabBarAccessibilityLabel: 'Settings tab',
        }}
      />
    </Tab.Navigator>
  );
}

// Root navigator with modal screens
function RootNavigator() {
  const theme = useTheme();

  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: {
          backgroundColor: theme.colors.background,
        },
        headerTintColor: theme.colors.text,
        headerTitleStyle: {
          fontWeight: '600',
        },
        headerShadowVisible: false,
        contentStyle: {
          backgroundColor: theme.colors.background,
        },
        animation: 'slide_from_bottom',
      }}
    >
      <Stack.Screen
        name="Main"
        component={MainTabs}
        options={{ headerShown: false }}
      />
      <Stack.Screen
        name="Send"
        component={SendScreen}
        options={{
          title: 'Send XAI',
          presentation: 'modal',
          headerBackTitle: 'Cancel',
        }}
      />
      <Stack.Screen
        name="Receive"
        component={ReceiveScreen}
        options={{
          title: 'Receive XAI',
          presentation: 'modal',
          headerBackTitle: 'Close',
        }}
      />
      <Stack.Screen
        name="TransactionDetail"
        component={TransactionDetailScreen}
        options={{
          title: 'Transaction',
          presentation: 'card',
          headerBackTitle: 'Back',
        }}
      />
      <Stack.Screen
        name="AddressBook"
        component={AddressBookScreen}
        options={{
          title: 'Address Book',
          presentation: 'modal',
          headerBackTitle: 'Cancel',
        }}
      />
    </Stack.Navigator>
  );
}

// App content with navigation and providers
function AppContent() {
  const navigationTheme = useNavigationTheme();
  const theme = useTheme();

  // Initialize network monitoring
  useEffect(() => {
    initNetworkMonitoring();
    return () => {
      stopNetworkMonitoring();
    };
  }, []);

  return (
    <NavigationContainer theme={navigationTheme}>
      <StatusBar
        barStyle={theme.isDark ? 'light-content' : 'dark-content'}
        backgroundColor={theme.colors.background}
      />
      <RootNavigator />
    </NavigationContainer>
  );
}

// Main app component with onboarding logic
export default function App() {
  const [isLoading, setIsLoading] = useState(true);
  const [showOnboarding, setShowOnboarding] = useState(false);

  // Check if onboarding has been completed
  useEffect(() => {
    const checkOnboarding = async () => {
      try {
        const completed = await SecureStore.getItemAsync(ONBOARDING_KEY);
        setShowOnboarding(!completed);
      } catch (error) {
        // Default to showing app if check fails
        setShowOnboarding(false);
      } finally {
        setIsLoading(false);
      }
    };

    checkOnboarding();
  }, []);

  // Handle onboarding completion
  const handleOnboardingComplete = useCallback(async () => {
    try {
      await SecureStore.setItemAsync(ONBOARDING_KEY, 'true');
      setShowOnboarding(false);
    } catch (error) {
      // Still hide onboarding on error
      setShowOnboarding(false);
    }
  }, []);

  // Show loading state
  if (isLoading) {
    return (
      <SafeAreaProvider>
        <View style={[styles.loadingContainer, { backgroundColor: darkTheme.colors.background }]}>
          <Icon name="xai-logo" size={80} color={darkTheme.colors.brand.primary} />
          <Text style={[styles.loadingText, { color: darkTheme.colors.text }]}>
            XAI Wallet
          </Text>
        </View>
      </SafeAreaProvider>
    );
  }

  // Show onboarding for new users
  if (showOnboarding) {
    return (
      <SafeAreaProvider>
        <Onboarding onComplete={handleOnboardingComplete} />
      </SafeAreaProvider>
    );
  }

  // Main app
  return (
    <SafeAreaProvider>
      <WalletProvider>
        <AppContent />
      </WalletProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    fontSize: 24,
    fontWeight: '700',
    marginTop: 16,
  },
  tabIconContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    height: 28,
  },
  tabIndicator: {
    width: 4,
    height: 4,
    borderRadius: 2,
    marginTop: 4,
  },
});
