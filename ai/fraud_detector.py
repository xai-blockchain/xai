"""
Minimal fraud detector that operates on simple heuristics.
"""

from typing import Dict, List


class AIFraudDetector:
    """Heuristic fraud detector used by the XAI node."""

    def __init__(self):
        self.address_history: set[str] = set()
        self.flagged_addresses: set[str] = set()

    def analyze_transaction(self, data: Dict[str, object]) -> Dict[str, object]:
        sender = data.get('sender', '')
        amount = float(data.get('amount', 0) or 0)
        reasons: List[str] = []
        score = 0.0

        if amount >= 1000:
            score += 30
            reasons.append('large_amount')
        if amount >= 5000:
            score += 20
            reasons.append('high_value')
        if data.get('recipient') and data.get('recipient').endswith('XAI'):
            score -= 5

        if data.get('priority') == 'high' and amount > 2000:
            score += 10
            reasons.append('priority_overshoot')

        normalized_score = min(max(score, 0.0), 100.0)

        self.address_history.add(sender)
        if normalized_score > 60:
            self.flagged_addresses.add(sender)

        return {
            'success': True,
            'analysis': {
                'score': normalized_score,
                'flags': reasons
            },
            'address': sender,
            'is_flagged': sender in self.flagged_addresses
        }
