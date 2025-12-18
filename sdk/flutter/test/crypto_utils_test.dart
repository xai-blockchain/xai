import 'package:flutter_test/flutter_test.dart';
import 'package:xai_sdk/src/utils/crypto_utils.dart';

void main() {
  group('CryptoUtils', () {
    test('generateKeyPair returns valid key pair', () {
      final keyPair = CryptoUtils.generateKeyPair();

      expect(keyPair, isNotNull);
      expect(keyPair['privateKey'], isNotNull);
      expect(keyPair['publicKey'], isNotNull);
      expect(keyPair['privateKey']!.length, greaterThan(0));
      expect(keyPair['publicKey']!.length, greaterThan(0));
      expect(keyPair['publicKey']!.startsWith('04'), isTrue); // Uncompressed format
    });

    test('derivePublicKey derives correct public key from private key', () {
      final keyPair = CryptoUtils.generateKeyPair();
      final privateKey = keyPair['privateKey']!;
      final expectedPublicKey = keyPair['publicKey']!;

      final derivedPublicKey = CryptoUtils.derivePublicKey(privateKey);

      expect(derivedPublicKey, equals(expectedPublicKey));
    });

    test('signMessage and verifySignature work correctly', () {
      final keyPair = CryptoUtils.generateKeyPair();
      final privateKey = keyPair['privateKey']!;
      final publicKey = keyPair['publicKey']!;
      const message = 'Test message';

      final signature = CryptoUtils.signMessage(message, privateKey);

      expect(signature, isNotNull);
      expect(signature.length, greaterThan(0));

      final isValid = CryptoUtils.verifySignature(message, signature, publicKey);

      expect(isValid, isTrue);
    });

    test('verifySignature returns false for invalid signature', () {
      final keyPair = CryptoUtils.generateKeyPair();
      final publicKey = keyPair['publicKey']!;
      const message = 'Test message';
      const invalidSignature = 'invalid_signature';

      final isValid = CryptoUtils.verifySignature(message, invalidSignature, publicKey);

      expect(isValid, isFalse);
    });

    test('verifySignature returns false for wrong message', () {
      final keyPair = CryptoUtils.generateKeyPair();
      final privateKey = keyPair['privateKey']!;
      final publicKey = keyPair['publicKey']!;
      const message = 'Test message';
      const wrongMessage = 'Wrong message';

      final signature = CryptoUtils.signMessage(message, privateKey);
      final isValid = CryptoUtils.verifySignature(wrongMessage, signature, publicKey);

      expect(isValid, isFalse);
    });

    test('publicKeyToAddress generates valid XAI address', () {
      final keyPair = CryptoUtils.generateKeyPair();
      final publicKey = keyPair['publicKey']!;

      final address = CryptoUtils.publicKeyToAddress(publicKey);

      expect(address, isNotNull);
      expect(address.startsWith('XAI'), isTrue);
      expect(address.length, greaterThan(3));
    });

    test('isValidAddress validates XAI addresses correctly', () {
      final keyPair = CryptoUtils.generateKeyPair();
      final publicKey = keyPair['publicKey']!;
      final validAddress = CryptoUtils.publicKeyToAddress(publicKey);

      expect(CryptoUtils.isValidAddress(validAddress), isTrue);
      expect(CryptoUtils.isValidAddress('COINBASE'), isTrue);
      expect(CryptoUtils.isValidAddress('invalid'), isFalse);
      expect(CryptoUtils.isValidAddress(''), isFalse);
    });

    test('sha256Hash produces correct hash', () {
      const data = 'Test data';

      final hash = CryptoUtils.sha256Hash(data);

      expect(hash, isNotNull);
      expect(hash.length, equals(64)); // SHA-256 produces 32 bytes = 64 hex chars
    });

    test('sha256Hash is deterministic', () {
      const data = 'Test data';

      final hash1 = CryptoUtils.sha256Hash(data);
      final hash2 = CryptoUtils.sha256Hash(data);

      expect(hash1, equals(hash2));
    });

    test('different private keys produce different public keys', () {
      final keyPair1 = CryptoUtils.generateKeyPair();
      final keyPair2 = CryptoUtils.generateKeyPair();

      expect(keyPair1['privateKey'], isNot(equals(keyPair2['privateKey'])));
      expect(keyPair1['publicKey'], isNot(equals(keyPair2['publicKey'])));
    });

    test('different public keys produce different addresses', () {
      final keyPair1 = CryptoUtils.generateKeyPair();
      final keyPair2 = CryptoUtils.generateKeyPair();

      final address1 = CryptoUtils.publicKeyToAddress(keyPair1['publicKey']!);
      final address2 = CryptoUtils.publicKeyToAddress(keyPair2['publicKey']!);

      expect(address1, isNot(equals(address2)));
    });
  });
}
