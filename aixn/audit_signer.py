"""Stubbed audit signer for tests."""

class AuditSigner:
    def __init__(self, trade_dir):
        self.trade_dir = trade_dir

    def public_key(self):
        return 'AUDIT_PUBLIC_KEY'

    def sign(self, data):
        return 'signed'
