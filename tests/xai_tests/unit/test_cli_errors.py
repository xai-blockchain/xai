"""
Comprehensive tests for CLI error handling

Tests invalid commands, missing arguments, format validation,
and error message clarity.
"""

import pytest
import sys
from unittest.mock import Mock, patch
from io import StringIO


class CLI:
    """Mock CLI for testing"""

    VALID_COMMANDS = ['send', 'balance', 'mine', 'help']

    def __init__(self):
        self.output = []

    def execute(self, command, args=None):
        """Execute CLI command"""
        args = args or {}

        if command not in self.VALID_COMMANDS:
            raise ValueError(f"Invalid command: {command}")

        if command == 'send':
            return self._send(args)
        elif command == 'balance':
            return self._balance(args)
        elif command == 'mine':
            return self._mine(args)
        elif command == 'help':
            return self._help()

    def _send(self, args):
        """Handle send command"""
        if 'address' not in args:
            raise ValueError("Missing required argument: address")
        if 'amount' not in args:
            raise ValueError("Missing required argument: amount")
        if 'private_key' not in args:
            raise ValueError("Missing required argument: private_key")

        # Validate address format
        if not args['address'].startswith('XAI'):
            raise ValueError("Invalid address format (must start with 'XAI')")

        # Validate amount
        try:
            amount = float(args['amount'])
            if amount <= 0:
                raise ValueError("Invalid amount (must be positive)")
        except (ValueError, TypeError):
            raise ValueError("Invalid amount (must be a number)")

        # Validate private key
        if len(args['private_key']) < 32:
            raise ValueError("Invalid private key (too short)")

        return f"Sent {args['amount']} to {args['address']}"

    def _balance(self, args):
        """Handle balance command"""
        if 'address' not in args:
            raise ValueError("Missing required argument: address")

        if not args['address'].startswith('XAI'):
            raise ValueError("Invalid address format (must start with 'XAI')")

        return f"Balance for {args['address']}: 100.0 XAI"

    def _mine(self, args):
        """Handle mine command"""
        if 'address' not in args:
            raise ValueError("Missing required argument: address")

        return f"Mining to address {args['address']}"

    def _help(self):
        """Show help message"""
        return "Available commands: " + ", ".join(self.VALID_COMMANDS)


class TestCLIErrors:
    """Tests for CLI error handling"""

    def test_invalid_command(self):
        """Test error on invalid command"""
        cli = CLI()

        with pytest.raises(ValueError) as exc_info:
            cli.execute('invalid_command')

        assert "Invalid command" in str(exc_info.value)

    def test_missing_required_address_argument(self):
        """Test error when address argument missing"""
        cli = CLI()

        with pytest.raises(ValueError) as exc_info:
            cli.execute('send', {'amount': '10.0', 'private_key': 'key'})

        assert "Missing required argument: address" in str(exc_info.value)

    def test_missing_required_amount_argument(self):
        """Test error when amount argument missing"""
        cli = CLI()

        with pytest.raises(ValueError) as exc_info:
            cli.execute('send', {'address': 'XAI123', 'private_key': 'key'})

        assert "Missing required argument: amount" in str(exc_info.value)

    def test_invalid_address_format(self):
        """Test error on invalid address format"""
        cli = CLI()

        with pytest.raises(ValueError) as exc_info:
            cli.execute('balance', {'address': 'INVALID123'})

        assert "Invalid address format" in str(exc_info.value)

    def test_invalid_amount_format(self):
        """Test error on invalid amount"""
        cli = CLI()

        with pytest.raises(ValueError) as exc_info:
            cli.execute('send', {
                'address': 'XAI123',
                'amount': 'not_a_number',
                'private_key': 'a' * 64
            })

        assert "Invalid amount" in str(exc_info.value)

    def test_negative_amount_rejected(self):
        """Test error on negative amount"""
        cli = CLI()

        with pytest.raises(ValueError) as exc_info:
            cli.execute('send', {
                'address': 'XAI123',
                'amount': '-10.0',
                'private_key': 'a' * 64
            })

        assert "Invalid amount" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    def test_zero_amount_rejected(self):
        """Test error on zero amount"""
        cli = CLI()

        with pytest.raises(ValueError) as exc_info:
            cli.execute('send', {
                'address': 'XAI123',
                'amount': '0',
                'private_key': 'a' * 64
            })

        assert "Invalid amount" in str(exc_info.value)

    def test_invalid_private_key(self):
        """Test error on invalid private key"""
        cli = CLI()

        with pytest.raises(ValueError) as exc_info:
            cli.execute('send', {
                'address': 'XAI123',
                'amount': '10.0',
                'private_key': 'short'
            })

        assert "Invalid private key" in str(exc_info.value)

    def test_error_messages_are_clear(self):
        """Test error messages are user-friendly"""
        cli = CLI()

        # Test various error scenarios
        errors = []

        # Invalid command
        try:
            cli.execute('badcmd')
        except ValueError as e:
            errors.append(str(e))

        # Missing argument
        try:
            cli.execute('send', {})
        except ValueError as e:
            errors.append(str(e))

        # Invalid format
        try:
            cli.execute('balance', {'address': 'BAD'})
        except ValueError as e:
            errors.append(str(e))

        # All errors should be descriptive
        for error in errors:
            assert len(error) > 10  # Reasonable length
            assert error  # Not empty

    def test_help_command_works(self):
        """Test help command provides useful information"""
        cli = CLI()

        help_text = cli.execute('help')

        assert 'send' in help_text
        assert 'balance' in help_text
        assert 'mine' in help_text

    def test_valid_command_succeeds(self):
        """Test valid command executes successfully"""
        cli = CLI()

        result = cli.execute('send', {
            'address': 'XAI123abc',
            'amount': '10.5',
            'private_key': 'a' * 64
        })

        assert 'Sent' in result
        assert '10.5' in result
        assert 'XAI123abc' in result

    def test_balance_command_requires_address(self):
        """Test balance command validates address"""
        cli = CLI()

        with pytest.raises(ValueError) as exc_info:
            cli.execute('balance', {})

        assert "Missing required argument" in str(exc_info.value)

    def test_mine_command_requires_address(self):
        """Test mine command validates address"""
        cli = CLI()

        with pytest.raises(ValueError) as exc_info:
            cli.execute('mine', {})

        assert "Missing required argument" in str(exc_info.value)

    def test_case_sensitive_commands(self):
        """Test commands are case-sensitive"""
        cli = CLI()

        with pytest.raises(ValueError) as exc_info:
            cli.execute('SEND', {})

        assert "Invalid command" in str(exc_info.value)
