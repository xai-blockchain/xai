// Mock react-native modules
jest.mock('react-native', () => ({
  Platform: {
    OS: 'ios',
    select: jest.fn((obj) => obj.ios),
  },
  Alert: {
    alert: jest.fn(),
  },
}));

// Mock react-native-keychain
jest.mock('react-native-keychain', () => ({
  ACCESSIBLE: {
    WHEN_UNLOCKED: 'WhenUnlocked',
    WHEN_UNLOCKED_THIS_DEVICE_ONLY: 'WhenUnlockedThisDeviceOnly',
  },
  setGenericPassword: jest.fn(() => Promise.resolve(true)),
  getGenericPassword: jest.fn(() =>
    Promise.resolve({
      username: 'test',
      password: 'test',
    })
  ),
  resetGenericPassword: jest.fn(() => Promise.resolve(true)),
}));

// Mock react-native-biometrics
jest.mock('react-native-biometrics', () => {
  return jest.fn().mockImplementation(() => ({
    isSensorAvailable: jest.fn(() =>
      Promise.resolve({
        available: true,
        biometryType: 'FaceID',
      })
    ),
    simplePrompt: jest.fn(() =>
      Promise.resolve({
        success: true,
      })
    ),
    createKeys: jest.fn(() => Promise.resolve({ publicKey: 'test' })),
    biometricKeysExist: jest.fn(() =>
      Promise.resolve({
        keysExist: true,
      })
    ),
    deleteKeys: jest.fn(() =>
      Promise.resolve({
        keysDeleted: true,
      })
    ),
    createSignature: jest.fn(() =>
      Promise.resolve({
        success: true,
        signature: 'test_signature',
      })
    ),
  }));
});

// Mock AsyncStorage
jest.mock('@react-native-async-storage/async-storage', () => ({
  setItem: jest.fn(() => Promise.resolve()),
  getItem: jest.fn(() => Promise.resolve(null)),
  removeItem: jest.fn(() => Promise.resolve()),
  getAllKeys: jest.fn(() => Promise.resolve([])),
  multiRemove: jest.fn(() => Promise.resolve()),
}));

// Mock crypto
global.crypto = {
  getRandomValues: (arr) => {
    for (let i = 0; i < arr.length; i++) {
      arr[i] = Math.floor(Math.random() * 256);
    }
    return arr;
  },
};
