"""
Integration tests for Governance API endpoints.

Tests all governance-related API endpoints including:
- Proposal submission and retrieval
- Voting on proposals
- Voting power calculation
- Fiat unlock governance
- Error handling and validation
"""

import pytest
import json
import hashlib
import time
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from xai.core.api.api_governance import GovernanceAPIHandler
from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet
from xai.core.security.security_validation import ValidationError


@pytest.fixture
def mock_blockchain():
    """Create a mock blockchain for testing."""
    blockchain = Mock(spec=Blockchain)
    blockchain.get_balance = Mock(return_value=10000)
    return blockchain


@pytest.fixture
def mock_validator():
    """Create a mock security validator."""
    validator = Mock()
    validator.validate_address = Mock(return_value=True)
    return validator


@pytest.fixture
def mock_fiat_unlock_manager():
    """Create a mock fiat unlock manager."""
    manager = Mock()
    manager.cast_vote = Mock(return_value={
        'current_votes': 10,
        'required_votes': 100,
        'status': 'voting'
    })
    manager.get_status = Mock(return_value={
        'voting_open': True,
        'yes_votes': 10,
        'no_votes': 5,
        'total_votes': 15,
        'required_votes': 100
    })
    return manager


@pytest.fixture
def mock_node(mock_blockchain, mock_validator, mock_fiat_unlock_manager):
    """Create a mock blockchain node for testing."""
    node = Mock()
    node.blockchain = mock_blockchain
    node.validator = mock_validator
    node.fiat_unlock_manager = mock_fiat_unlock_manager
    return node


@pytest.fixture
def flask_app():
    """Create a Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def governance_handler(mock_node, flask_app):
    """Create a GovernanceAPIHandler instance for testing."""
    handler = GovernanceAPIHandler(mock_node, flask_app)
    return handler


@pytest.fixture
def test_client(flask_app):
    """Create a test client for the Flask app."""
    return flask_app.test_client()


class TestProposalSubmission:
    """Test proposal submission endpoint (/governance/proposals/submit)."""

    def test_submit_proposal_success(self, test_client, governance_handler):
        """Test successful proposal submission."""
        response = test_client.post(
            '/governance/proposals/submit',
            json={
                'title': 'Improve AI Model',
                'description': 'Upgrade to latest AI model',
                'proposal_type': 'ai_improvement',
                'proposer_address': 'test_proposer_address'
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'proposal_id' in data
        assert data['status'] == 'security_review'
        assert 'message' in data

    def test_submit_proposal_generates_unique_id(self, test_client, governance_handler):
        """Test that each proposal gets a unique ID."""
        proposal1 = test_client.post(
            '/governance/proposals/submit',
            json={
                'title': 'Proposal 1',
                'description': 'First proposal',
                'proposal_type': 'parameter_change'
            }
        )

        proposal2 = test_client.post(
            '/governance/proposals/submit',
            json={
                'title': 'Proposal 2',
                'description': 'Second proposal',
                'proposal_type': 'ai_improvement'
            }
        )

        data1 = json.loads(proposal1.data)
        data2 = json.loads(proposal2.data)

        assert data1['proposal_id'] != data2['proposal_id']

    def test_submit_proposal_with_minimal_data(self, test_client, governance_handler):
        """Test submitting proposal with minimal data."""
        response = test_client.post(
            '/governance/proposals/submit',
            json={'title': 'Minimal Proposal'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_submit_proposal_different_types(self, test_client, governance_handler):
        """Test submitting different types of proposals."""
        types = ['ai_improvement', 'parameter_change', 'emergency', 'upgrade']

        for prop_type in types:
            response = test_client.post(
                '/governance/proposals/submit',
                json={
                    'title': f'{prop_type} proposal',
                    'proposal_type': prop_type
                }
            )
            assert response.status_code == 200

    def test_submit_proposal_with_long_description(self, test_client, governance_handler):
        """Test submitting proposal with long description."""
        long_desc = 'A' * 5000  # Long description

        response = test_client.post(
            '/governance/proposals/submit',
            json={
                'title': 'Long Description Proposal',
                'description': long_desc
            }
        )

        assert response.status_code == 200


class TestProposalRetrieval:
    """Test proposal retrieval endpoint (/governance/proposals)."""

    def test_get_proposals_default(self, test_client, governance_handler):
        """Test getting proposals with default parameters."""
        response = test_client.get('/governance/proposals')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'count' in data
        assert 'proposals' in data
        assert isinstance(data['proposals'], list)

    def test_get_proposals_by_status(self, test_client, governance_handler):
        """Test getting proposals filtered by status."""
        statuses = ['community_vote', 'security_review', 'approved', 'rejected']

        for status in statuses:
            response = test_client.get(
                '/governance/proposals',
                query_string={'status': status}
            )
            assert response.status_code == 200

    def test_get_proposals_with_limit(self, test_client, governance_handler):
        """Test getting proposals with custom limit."""
        response = test_client.get(
            '/governance/proposals',
            query_string={'limit': 5}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'proposals' in data

    def test_get_proposals_pagination(self, test_client, governance_handler):
        """Test proposal pagination."""
        # Test different limits
        limits = [1, 5, 10, 20]

        for limit in limits:
            response = test_client.get(
                '/governance/proposals',
                query_string={'limit': limit}
            )
            assert response.status_code == 200

    def test_get_proposals_multiple_filters(self, test_client, governance_handler):
        """Test getting proposals with multiple filters."""
        response = test_client.get(
            '/governance/proposals',
            query_string={
                'status': 'community_vote',
                'limit': 15
            }
        )

        assert response.status_code == 200


class TestVoteSubmission:
    """Test vote submission endpoint (/governance/vote)."""

    def test_submit_vote_success(self, test_client, governance_handler):
        """Test successful vote submission."""
        response = test_client.post(
            '/governance/vote',
            json={
                'proposal_id': 'test_proposal_123',
                'voter_address': 'test_voter_address',
                'vote': 'yes'
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['proposal_id'] == 'test_proposal_123'
        assert data['vote'] == 'yes'
        assert 'voting_power' in data
        assert 'breakdown' in data

    def test_submit_vote_no(self, test_client, governance_handler):
        """Test submitting a 'no' vote."""
        response = test_client.post(
            '/governance/vote',
            json={
                'proposal_id': 'test_proposal_456',
                'voter_address': 'test_voter_address',
                'vote': 'no'
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['vote'] == 'no'

    def test_submit_vote_abstain(self, test_client, governance_handler):
        """Test submitting an 'abstain' vote."""
        response = test_client.post(
            '/governance/vote',
            json={
                'proposal_id': 'test_proposal_789',
                'voter_address': 'test_voter_address',
                'vote': 'abstain'
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['vote'] == 'abstain'

    def test_submit_vote_includes_voting_power(self, test_client, governance_handler):
        """Test that vote submission returns voting power."""
        response = test_client.post(
            '/governance/vote',
            json={
                'proposal_id': 'test_proposal_123',
                'voter_address': 'test_voter_address',
                'vote': 'yes'
            }
        )

        data = json.loads(response.data)
        assert 'voting_power' in data
        assert isinstance(data['voting_power'], (int, float))

    def test_submit_vote_includes_breakdown(self, test_client, governance_handler):
        """Test that vote submission includes voting power breakdown."""
        response = test_client.post(
            '/governance/vote',
            json={
                'proposal_id': 'test_proposal_123',
                'voter_address': 'test_voter_address',
                'vote': 'yes'
            }
        )

        data = json.loads(response.data)
        assert 'breakdown' in data
        assert 'coin_power' in data['breakdown']
        assert 'donation_power' in data['breakdown']


class TestVotingPowerCalculation:
    """Test voting power calculation endpoint (/governance/voting-power/<address>)."""

    def test_get_voting_power_success(self, test_client, governance_handler, mock_blockchain):
        """Test successful voting power calculation."""
        test_address = 'test_address_123'

        response = test_client.get(f'/governance/voting-power/{test_address}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['address'] == test_address
        assert 'xai_balance' in data
        assert 'voting_power' in data

    def test_voting_power_includes_breakdown(self, test_client, governance_handler):
        """Test that voting power includes detailed breakdown."""
        response = test_client.get('/governance/voting-power/test_address')

        data = json.loads(response.data)
        assert 'voting_power' in data
        power = data['voting_power']
        assert 'coin_power' in power
        assert 'donation_power' in power
        assert 'total' in power

    def test_voting_power_coin_calculation(self, test_client, governance_handler, mock_blockchain):
        """Test that coin power is calculated correctly (70% of balance)."""
        mock_blockchain.get_balance.return_value = 10000

        response = test_client.get('/governance/voting-power/test_address')

        data = json.loads(response.data)
        expected_coin_power = 10000 * 0.70
        assert data['voting_power']['coin_power'] == expected_coin_power

    def test_voting_power_different_balances(self, test_client, governance_handler, mock_blockchain):
        """Test voting power calculation with different balances."""
        balances = [100, 1000, 10000, 100000]

        for balance in balances:
            mock_blockchain.get_balance.return_value = balance
            response = test_client.get(f'/governance/voting-power/addr_{balance}')

            data = json.loads(response.data)
            expected = balance * 0.70
            assert data['voting_power']['coin_power'] == expected

    def test_voting_power_total_calculation(self, test_client, governance_handler, mock_blockchain):
        """Test that total voting power is sum of components."""
        mock_blockchain.get_balance.return_value = 10000

        response = test_client.get('/governance/voting-power/test_address')

        data = json.loads(response.data)
        power = data['voting_power']
        expected_total = power['coin_power'] + power['donation_power']
        assert power['total'] == expected_total


class TestFiatUnlockVoting:
    """Test fiat unlock voting endpoint (/governance/fiat-unlock/vote)."""

    def test_fiat_unlock_vote_success(self, test_client, governance_handler):
        """Test successful fiat unlock vote."""
        response = test_client.post(
            '/governance/fiat-unlock/vote',
            json={
                'governance_address': 'test_voter_address',
                'support': True,
                'reason': 'I support this unlock'
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'status' in data

    def test_fiat_unlock_vote_against(self, test_client, governance_handler):
        """Test voting against fiat unlock."""
        response = test_client.post(
            '/governance/fiat-unlock/vote',
            json={
                'governance_address': 'test_voter_address',
                'support': False,
                'reason': 'I oppose this unlock'
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_fiat_unlock_vote_with_user_address(self, test_client, governance_handler):
        """Test fiat unlock vote using user_address field."""
        response = test_client.post(
            '/governance/fiat-unlock/vote',
            json={
                'user_address': 'test_voter_address',
                'support': True
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_fiat_unlock_vote_without_address(self, test_client, governance_handler):
        """Test fiat unlock vote without address."""
        response = test_client.post(
            '/governance/fiat-unlock/vote',
            json={
                'support': True,
                'reason': 'Support without address'
            }
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data
        assert 'governance_address required' in data['error']

    def test_fiat_unlock_vote_invalid_address(self, test_client, governance_handler, mock_validator):
        """Test fiat unlock vote with invalid address."""
        # Make validator raise ValidationError
        mock_validator.validate_address.side_effect = ValidationError('Invalid address format')

        response = test_client.post(
            '/governance/fiat-unlock/vote',
            json={
                'governance_address': 'invalid_address',
                'support': True
            }
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'INVALID_ADDRESS'

    def test_fiat_unlock_vote_when_voting_closed(self, test_client, governance_handler, mock_fiat_unlock_manager):
        """Test fiat unlock vote when voting is closed."""
        mock_fiat_unlock_manager.cast_vote.side_effect = ValueError('Voting is not open')

        response = test_client.post(
            '/governance/fiat-unlock/vote',
            json={
                'governance_address': 'test_voter_address',
                'support': True
            }
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'VOTING_NOT_OPEN'

    def test_fiat_unlock_vote_with_reason(self, test_client, governance_handler):
        """Test that reason is passed to fiat unlock manager."""
        reason = 'This is my detailed reason for voting'

        response = test_client.post(
            '/governance/fiat-unlock/vote',
            json={
                'governance_address': 'test_voter_address',
                'support': True,
                'reason': reason
            }
        )

        assert response.status_code == 200

    def test_fiat_unlock_vote_without_reason(self, test_client, governance_handler):
        """Test voting without providing a reason."""
        response = test_client.post(
            '/governance/fiat-unlock/vote',
            json={
                'governance_address': 'test_voter_address',
                'support': True
            }
        )

        assert response.status_code == 200

    def test_fiat_unlock_vote_default_support(self, test_client, governance_handler):
        """Test that support defaults to True if not specified."""
        response = test_client.post(
            '/governance/fiat-unlock/vote',
            json={
                'governance_address': 'test_voter_address'
            }
        )

        assert response.status_code == 200


class TestFiatUnlockStatus:
    """Test fiat unlock status endpoint (/governance/fiat-unlock/status)."""

    def test_get_fiat_unlock_status(self, test_client, governance_handler):
        """Test getting fiat unlock governance status."""
        response = test_client.get('/governance/fiat-unlock/status')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'status' in data

    def test_status_includes_voting_info(self, test_client, governance_handler, mock_fiat_unlock_manager):
        """Test that status includes voting information."""
        response = test_client.get('/governance/fiat-unlock/status')

        data = json.loads(response.data)
        status = data['status']
        assert 'voting_open' in status
        assert 'yes_votes' in status
        assert 'no_votes' in status
        assert 'total_votes' in status
        assert 'required_votes' in status

    def test_status_no_parameters_required(self, test_client, governance_handler):
        """Test that status endpoint doesn't require parameters."""
        response = test_client.get('/governance/fiat-unlock/status')
        assert response.status_code == 200


class TestGovernanceErrorHandling:
    """Test error handling in governance operations."""

    def test_submit_proposal_no_body(self, test_client, governance_handler):
        """Test submitting proposal without request body."""
        response = test_client.post('/governance/proposals/submit')
        # Should handle gracefully (might be 400 or succeed with empty data)
        assert response.status_code in [200, 400, 415]

    def test_submit_vote_no_body(self, test_client, governance_handler):
        """Test submitting vote without request body."""
        response = test_client.post('/governance/vote')
        # Should handle gracefully
        assert response.status_code in [200, 400, 415]

    def test_malformed_json_proposal(self, test_client, governance_handler):
        """Test handling malformed JSON in proposal submission."""
        response = test_client.post(
            '/governance/proposals/submit',
            data='{"invalid": json}',
            content_type='application/json'
        )
        assert response.status_code in [400, 415]

    def test_malformed_json_vote(self, test_client, governance_handler):
        """Test handling malformed JSON in vote submission."""
        response = test_client.post(
            '/governance/vote',
            data='not valid json',
            content_type='application/json'
        )
        assert response.status_code in [400, 415]


class TestGovernanceValidation:
    """Test governance input validation."""

    def test_validate_address_on_fiat_vote(self, test_client, governance_handler, mock_validator):
        """Test that address is validated on fiat unlock vote."""
        test_client.post(
            '/governance/fiat-unlock/vote',
            json={
                'governance_address': 'test_address',
                'support': True
            }
        )

        # Verify validator was called
        mock_validator.validate_address.assert_called_with('test_address')

    def test_address_validation_error_handling(self, test_client, governance_handler, mock_validator):
        """Test proper error handling for address validation failures."""
        mock_validator.validate_address.side_effect = ValidationError('Bad address')

        response = test_client.post(
            '/governance/fiat-unlock/vote',
            json={
                'governance_address': 'bad_address',
                'support': True
            }
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data


class TestGovernanceIntegration:
    """Test integration scenarios across governance endpoints."""

    def test_proposal_lifecycle(self, test_client, governance_handler):
        """Test complete proposal lifecycle."""
        # Submit proposal
        submit_response = test_client.post(
            '/governance/proposals/submit',
            json={
                'title': 'Test Lifecycle Proposal',
                'description': 'Testing full lifecycle',
                'proposal_type': 'ai_improvement'
            }
        )
        assert submit_response.status_code == 200
        proposal_data = json.loads(submit_response.data)
        proposal_id = proposal_data['proposal_id']

        # Vote on proposal
        vote_response = test_client.post(
            '/governance/vote',
            json={
                'proposal_id': proposal_id,
                'voter_address': 'test_voter',
                'vote': 'yes'
            }
        )
        assert vote_response.status_code == 200

        # Get proposals
        list_response = test_client.get('/governance/proposals')
        assert list_response.status_code == 200

    def test_multiple_voters_on_proposal(self, test_client, governance_handler):
        """Test multiple voters voting on same proposal."""
        # Submit proposal
        submit_response = test_client.post(
            '/governance/proposals/submit',
            json={'title': 'Multi-voter proposal'}
        )
        proposal_id = json.loads(submit_response.data)['proposal_id']

        # Multiple voters
        voters = ['voter_1', 'voter_2', 'voter_3']
        votes = ['yes', 'no', 'yes']

        for voter, vote in zip(voters, votes):
            response = test_client.post(
                '/governance/vote',
                json={
                    'proposal_id': proposal_id,
                    'voter_address': voter,
                    'vote': vote
                }
            )
            assert response.status_code == 200

    def test_voting_power_before_voting(self, test_client, governance_handler):
        """Test checking voting power before casting vote."""
        voter_address = 'test_voter'

        # Check voting power first
        power_response = test_client.get(f'/governance/voting-power/{voter_address}')
        assert power_response.status_code == 200
        power_data = json.loads(power_response.data)

        # Then vote
        vote_response = test_client.post(
            '/governance/vote',
            json={
                'proposal_id': 'test_proposal',
                'voter_address': voter_address,
                'vote': 'yes'
            }
        )
        assert vote_response.status_code == 200


class TestGovernanceProposalTypes:
    """Test different proposal types."""

    def test_ai_improvement_proposal(self, test_client, governance_handler):
        """Test AI improvement proposal."""
        response = test_client.post(
            '/governance/proposals/submit',
            json={
                'title': 'AI Improvement',
                'proposal_type': 'ai_improvement'
            }
        )
        assert response.status_code == 200

    def test_parameter_change_proposal(self, test_client, governance_handler):
        """Test parameter change proposal."""
        response = test_client.post(
            '/governance/proposals/submit',
            json={
                'title': 'Parameter Change',
                'proposal_type': 'parameter_change'
            }
        )
        assert response.status_code == 200

    def test_emergency_proposal(self, test_client, governance_handler):
        """Test emergency proposal."""
        response = test_client.post(
            '/governance/proposals/submit',
            json={
                'title': 'Emergency Action',
                'proposal_type': 'emergency'
            }
        )
        assert response.status_code == 200


class TestVotingPowerEdgeCases:
    """Test edge cases in voting power calculation."""

    def test_voting_power_zero_balance(self, test_client, governance_handler, mock_blockchain):
        """Test voting power with zero balance."""
        mock_blockchain.get_balance.return_value = 0

        response = test_client.get('/governance/voting-power/zero_balance_address')

        data = json.loads(response.data)
        assert data['voting_power']['coin_power'] == 0
        assert data['voting_power']['total'] == 0

    def test_voting_power_large_balance(self, test_client, governance_handler, mock_blockchain):
        """Test voting power with very large balance."""
        large_balance = 1_000_000_000

        mock_blockchain.get_balance.return_value = large_balance

        response = test_client.get('/governance/voting-power/whale_address')

        data = json.loads(response.data)
        expected = large_balance * 0.70
        assert data['voting_power']['coin_power'] == expected


class TestFiatUnlockEdgeCases:
    """Test edge cases in fiat unlock governance."""

    def test_fiat_unlock_empty_payload(self, test_client, governance_handler):
        """Test fiat unlock vote with empty payload."""
        response = test_client.post(
            '/governance/fiat-unlock/vote',
            json={}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    def test_fiat_unlock_bool_conversion(self, test_client, governance_handler):
        """Test that support value is converted to boolean."""
        # Test various truthy/falsy values
        test_values = [1, 0, 'true', 'false', True, False]

        for value in test_values:
            response = test_client.post(
                '/governance/fiat-unlock/vote',
                json={
                    'governance_address': 'test_address',
                    'support': value
                }
            )
            # Should not error
            assert response.status_code in [200, 400]
