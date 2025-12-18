import 'package:flutter_test/flutter_test.dart';
import 'package:xai_sdk/src/models/transaction.dart';

void main() {
  group('Transaction', () {
    test('Transaction can be created with required fields', () {
      final tx = Transaction(
        sender: 'XAI123',
        recipient: 'XAI456',
        amount: 10.0,
        fee: 0.001,
        nonce: 0,
        timestamp: DateTime.now().millisecondsSinceEpoch ~/ 1000,
      );

      expect(tx.sender, equals('XAI123'));
      expect(tx.recipient, equals('XAI456'));
      expect(tx.amount, equals(10.0));
      expect(tx.fee, equals(0.001));
      expect(tx.nonce, equals(0));
    });

    test('Transaction calculates txid correctly', () {
      final timestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      final tx = Transaction(
        sender: 'XAI123',
        recipient: 'XAI456',
        amount: 10.0,
        fee: 0.001,
        nonce: 0,
        timestamp: timestamp,
      );

      final txid = tx.calculateTxid();

      expect(txid, isNotNull);
      expect(txid.length, equals(64)); // SHA-256 hash is 64 hex chars
    });

    test('Transaction txid is deterministic', () {
      final timestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      final tx = Transaction(
        sender: 'XAI123',
        recipient: 'XAI456',
        amount: 10.0,
        fee: 0.001,
        nonce: 0,
        timestamp: timestamp,
      );

      final txid1 = tx.calculateTxid();
      final txid2 = tx.calculateTxid();

      expect(txid1, equals(txid2));
    });

    test('Different transactions have different txids', () {
      final timestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      final tx1 = Transaction(
        sender: 'XAI123',
        recipient: 'XAI456',
        amount: 10.0,
        fee: 0.001,
        nonce: 0,
        timestamp: timestamp,
      );

      final tx2 = Transaction(
        sender: 'XAI789',
        recipient: 'XAI456',
        amount: 10.0,
        fee: 0.001,
        nonce: 0,
        timestamp: timestamp,
      );

      expect(tx1.calculateTxid(), isNot(equals(tx2.calculateTxid())));
    });

    test('Transaction can be serialized to JSON', () {
      final timestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      final tx = Transaction(
        sender: 'XAI123',
        recipient: 'XAI456',
        amount: 10.0,
        fee: 0.001,
        nonce: 0,
        timestamp: timestamp,
        publicKey: 'pubkey',
        signature: 'signature',
      );

      final json = tx.toJson();

      expect(json['sender'], equals('XAI123'));
      expect(json['recipient'], equals('XAI456'));
      expect(json['amount'], equals(10.0));
      expect(json['fee'], equals(0.001));
      expect(json['nonce'], equals(0));
      expect(json['public_key'], equals('pubkey'));
      expect(json['signature'], equals('signature'));
    });

    test('Transaction can be deserialized from JSON', () {
      final timestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      final json = {
        'txid': 'abc123',
        'sender': 'XAI123',
        'recipient': 'XAI456',
        'amount': 10.0,
        'fee': 0.001,
        'nonce': 0,
        'timestamp': timestamp,
        'status': 'confirmed',
        'public_key': 'pubkey',
        'signature': 'signature',
      };

      final tx = Transaction.fromJson(json);

      expect(tx.txid, equals('abc123'));
      expect(tx.sender, equals('XAI123'));
      expect(tx.recipient, equals('XAI456'));
      expect(tx.amount, equals(10.0));
      expect(tx.fee, equals(0.001));
      expect(tx.nonce, equals(0));
      expect(tx.status, equals(TransactionStatus.confirmed));
      expect(tx.publicKey, equals('pubkey'));
      expect(tx.signature, equals('signature'));
    });

    test('Transaction with signature creates new instance', () {
      final timestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      final tx = Transaction(
        sender: 'XAI123',
        recipient: 'XAI456',
        amount: 10.0,
        fee: 0.001,
        nonce: 0,
        timestamp: timestamp,
      );

      final signedTx = tx.withSignature('signature', 'pubkey');

      expect(signedTx.signature, equals('signature'));
      expect(signedTx.publicKey, equals('pubkey'));
      expect(signedTx.sender, equals(tx.sender));
      expect(signedTx.recipient, equals(tx.recipient));
      expect(signedTx.txid, isNotNull);
    });
  });

  group('TransactionInput', () {
    test('TransactionInput can be created', () {
      const input = TransactionInput(
        txid: 'abc123',
        vout: 0,
        amount: 5.0,
      );

      expect(input.txid, equals('abc123'));
      expect(input.vout, equals(0));
      expect(input.amount, equals(5.0));
    });

    test('TransactionInput can be serialized to JSON', () {
      const input = TransactionInput(
        txid: 'abc123',
        vout: 0,
        amount: 5.0,
      );

      final json = input.toJson();

      expect(json['txid'], equals('abc123'));
      expect(json['vout'], equals(0));
      expect(json['amount'], equals(5.0));
    });

    test('TransactionInput can be deserialized from JSON', () {
      final json = {
        'txid': 'abc123',
        'vout': 0,
        'amount': 5.0,
      };

      final input = TransactionInput.fromJson(json);

      expect(input.txid, equals('abc123'));
      expect(input.vout, equals(0));
      expect(input.amount, equals(5.0));
    });
  });

  group('TransactionOutput', () {
    test('TransactionOutput can be created', () {
      const output = TransactionOutput(
        address: 'XAI123',
        amount: 5.0,
      );

      expect(output.address, equals('XAI123'));
      expect(output.amount, equals(5.0));
    });

    test('TransactionOutput can be serialized to JSON', () {
      const output = TransactionOutput(
        address: 'XAI123',
        amount: 5.0,
      );

      final json = output.toJson();

      expect(json['address'], equals('XAI123'));
      expect(json['amount'], equals(5.0));
    });

    test('TransactionOutput can be deserialized from JSON', () {
      final json = {
        'address': 'XAI123',
        'amount': 5.0,
      };

      final output = TransactionOutput.fromJson(json);

      expect(output.address, equals('XAI123'));
      expect(output.amount, equals(5.0));
    });
  });

  group('TransactionStatus', () {
    test('TransactionStatus.fromString parses correctly', () {
      expect(TransactionStatus.fromString('pending'), equals(TransactionStatus.pending));
      expect(TransactionStatus.fromString('confirmed'), equals(TransactionStatus.confirmed));
      expect(TransactionStatus.fromString('failed'), equals(TransactionStatus.failed));
      expect(TransactionStatus.fromString('unknown'), equals(TransactionStatus.pending));
    });
  });
}
