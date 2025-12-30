"""
Comprehensive tests for XAI SDK GovernanceClient module.

Tests cover:
- Proposal listing and filtering
- Proposal retrieval
- Proposal creation
- Voting on proposals
- Active proposals retrieval
- Proposal vote counting
- Error handling and validation
"""

from datetime import datetime
from unittest.mock import Mock
import pytest

from xai.sdk.python.xai_sdk.clients.governance_client import GovernanceClient
from xai.sdk.python.xai_sdk.exceptions import (
    GovernanceError,
    NetworkError,
    ValidationError,
    XAIError,
)
from xai.sdk.python.xai_sdk.models import Proposal, ProposalStatus


class TestGovernanceClientInit:
    """Tests for GovernanceClient initialization."""

    def test_init_with_http_client(self):
        """Test GovernanceClient initializes with HTTP client."""
        mock_http = Mock()
        client = GovernanceClient(mock_http)
        assert client.http_client is mock_http


class TestListProposals:
    """Tests for list_proposals method."""

    @pytest.fixture
    def client(self):
        """Create GovernanceClient with mocked HTTP client."""
        mock_http = Mock()
        return GovernanceClient(mock_http)

    def test_list_proposals_success(self, client):
        """Test successful proposal listing."""
        client.http_client.get.return_value = {
            "proposals": [
                {
                    "id": 1,
                    "title": "Proposal 1",
                    "description": "Description 1",
                    "creator": "0xcreator1",
                    "status": "active",
                    "created_at": "2024-01-15T10:00:00",
                    "voting_ends_at": "2024-01-22T10:00:00",
                    "votes_for": 100,
                    "votes_against": 50,
                    "votes_abstain": 10,
                },
                {
                    "id": 2,
                    "title": "Proposal 2",
                    "description": "Description 2",
                    "creator": "0xcreator2",
                    "status": "pending",
                    "created_at": "2024-01-16T10:00:00",
                },
            ],
            "total": 50,
            "limit": 20,
            "offset": 0,
        }

        result = client.list_proposals()

        assert len(result["proposals"]) == 2
        assert isinstance(result["proposals"][0], Proposal)
        assert result["proposals"][0].title == "Proposal 1"
        assert result["proposals"][0].status == ProposalStatus.ACTIVE
        assert result["total"] == 50

    def test_list_proposals_with_status_filter(self, client):
        """Test proposal listing with status filter."""
        client.http_client.get.return_value = {
            "proposals": [],
            "total": 0,
        }

        client.list_proposals(status="active")

        call_args = client.http_client.get.call_args
        assert call_args[1]["params"]["status"] == "active"

    def test_list_proposals_with_pagination(self, client):
        """Test proposal listing with pagination."""
        client.http_client.get.return_value = {
            "proposals": [],
            "total": 100,
            "limit": 10,
            "offset": 20,
        }

        result = client.list_proposals(limit=10, offset=20)

        call_args = client.http_client.get.call_args
        assert call_args[1]["params"]["limit"] == 10
        assert call_args[1]["params"]["offset"] == 20

    def test_list_proposals_limit_capped_at_100(self, client):
        """Test limit is capped at 100."""
        client.http_client.get.return_value = {
            "proposals": [],
            "total": 0,
        }

        client.list_proposals(limit=500)

        call_args = client.http_client.get.call_args
        assert call_args[1]["params"]["limit"] == 100

    def test_list_proposals_empty(self, client):
        """Test empty proposal list."""
        client.http_client.get.return_value = {
            "proposals": [],
            "total": 0,
        }

        result = client.list_proposals()

        assert result["proposals"] == []
        assert result["total"] == 0

    def test_list_proposals_missing_optional_fields(self, client):
        """Test proposals with missing optional fields."""
        client.http_client.get.return_value = {
            "proposals": [
                {
                    "id": 1,
                    "title": "Minimal Proposal",
                    "description": "Minimal description",
                    "creator": "0xcreator",
                    "created_at": "2024-01-15T10:00:00",
                },
            ],
            "total": 1,
        }

        result = client.list_proposals()

        proposal = result["proposals"][0]
        assert proposal.status == ProposalStatus.PENDING
        assert proposal.votes_for == 0
        assert proposal.votes_against == 0
        assert proposal.votes_abstain == 0
        assert proposal.voting_ends_at is None

    def test_list_proposals_parses_datetime(self, client):
        """Test datetime parsing in proposals."""
        client.http_client.get.return_value = {
            "proposals": [
                {
                    "id": 1,
                    "title": "Datetime Test",
                    "description": "Test",
                    "creator": "0xcreator",
                    "created_at": "2024-06-15T14:30:45",
                    "voting_ends_at": "2024-06-22T14:30:45",
                },
            ],
            "total": 1,
        }

        result = client.list_proposals()

        proposal = result["proposals"][0]
        assert isinstance(proposal.created_at, datetime)
        assert proposal.created_at.year == 2024
        assert proposal.created_at.month == 6
        assert isinstance(proposal.voting_ends_at, datetime)


class TestGetProposal:
    """Tests for get_proposal method."""

    @pytest.fixture
    def client(self):
        """Create GovernanceClient with mocked HTTP client."""
        mock_http = Mock()
        return GovernanceClient(mock_http)

    def test_get_proposal_success(self, client):
        """Test successful proposal retrieval."""
        client.http_client.get.return_value = {
            "id": 42,
            "title": "Important Proposal",
            "description": "This proposal is very important",
            "creator": "0xcreator",
            "status": "active",
            "created_at": "2024-01-15T10:00:00",
            "voting_starts_at": "2024-01-16T10:00:00",
            "voting_ends_at": "2024-01-23T10:00:00",
            "votes_for": 1000,
            "votes_against": 500,
            "votes_abstain": 200,
        }

        proposal = client.get_proposal(proposal_id=42)

        assert isinstance(proposal, Proposal)
        assert proposal.id == 42
        assert proposal.title == "Important Proposal"
        assert proposal.status == ProposalStatus.ACTIVE
        assert proposal.votes_for == 1000
        assert proposal.votes_against == 500
        assert proposal.votes_abstain == 200

    def test_get_proposal_calls_correct_endpoint(self, client):
        """Test get_proposal calls correct API endpoint."""
        client.http_client.get.return_value = {
            "id": 1,
            "title": "Test",
            "description": "Test",
            "creator": "0x123",
            "created_at": "2024-01-15T10:00:00",
        }

        client.get_proposal(proposal_id=123)

        client.http_client.get.assert_called_once_with("/governance/proposals/123")

    def test_get_proposal_negative_id_raises_validation(self, client):
        """Test negative proposal_id raises ValidationError."""
        with pytest.raises(ValidationError, match="proposal_id must be non-negative"):
            client.get_proposal(proposal_id=-1)

    def test_get_proposal_zero_id_valid(self, client):
        """Test zero proposal_id is valid."""
        client.http_client.get.return_value = {
            "id": 0,
            "title": "Genesis Proposal",
            "description": "First proposal",
            "creator": "0xcreator",
            "created_at": "2024-01-01T00:00:00",
        }

        proposal = client.get_proposal(proposal_id=0)

        assert proposal.id == 0

    def test_get_proposal_with_voting_times(self, client):
        """Test proposal with voting start and end times."""
        client.http_client.get.return_value = {
            "id": 5,
            "title": "Timed Proposal",
            "description": "With voting times",
            "creator": "0xcreator",
            "created_at": "2024-01-15T10:00:00",
            "voting_starts_at": "2024-01-16T10:00:00",
            "voting_ends_at": "2024-01-23T10:00:00",
        }

        proposal = client.get_proposal(proposal_id=5)

        assert isinstance(proposal.voting_starts_at, datetime)
        assert isinstance(proposal.voting_ends_at, datetime)

    def test_get_proposal_passed_status(self, client):
        """Test proposal with passed status."""
        client.http_client.get.return_value = {
            "id": 10,
            "title": "Passed Proposal",
            "description": "This passed",
            "creator": "0xcreator",
            "status": "passed",
            "created_at": "2024-01-01T00:00:00",
        }

        proposal = client.get_proposal(proposal_id=10)

        assert proposal.status == ProposalStatus.PASSED

    def test_get_proposal_failed_status(self, client):
        """Test proposal with failed status."""
        client.http_client.get.return_value = {
            "id": 11,
            "title": "Failed Proposal",
            "description": "This failed",
            "creator": "0xcreator",
            "status": "failed",
            "created_at": "2024-01-01T00:00:00",
        }

        proposal = client.get_proposal(proposal_id=11)

        assert proposal.status == ProposalStatus.FAILED


class TestCreateProposal:
    """Tests for create_proposal method."""

    @pytest.fixture
    def client(self):
        """Create GovernanceClient with mocked HTTP client."""
        mock_http = Mock()
        return GovernanceClient(mock_http)

    def test_create_proposal_success(self, client):
        """Test successful proposal creation."""
        client.http_client.post.return_value = {
            "id": 100,
            "title": "New Proposal",
            "description": "A new governance proposal",
            "creator": "0xcreator",
            "status": "pending",
            "created_at": "2024-01-15T10:00:00",
            "votes_for": 0,
            "votes_against": 0,
        }

        proposal = client.create_proposal(
            title="New Proposal",
            description="A new governance proposal",
            proposer="0xcreator",
        )

        assert isinstance(proposal, Proposal)
        assert proposal.id == 100
        assert proposal.title == "New Proposal"
        assert proposal.status == ProposalStatus.PENDING

    def test_create_proposal_with_duration(self, client):
        """Test proposal creation with custom duration."""
        client.http_client.post.return_value = {
            "id": 101,
            "title": "Duration Proposal",
            "description": "With duration",
            "creator": "0xcreator",
            "created_at": "2024-01-15T10:00:00",
        }

        client.create_proposal(
            title="Duration Proposal",
            description="With duration",
            proposer="0xcreator",
            duration=604800,  # 7 days in seconds
        )

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["duration"] == 604800

    def test_create_proposal_with_metadata(self, client):
        """Test proposal creation with metadata."""
        client.http_client.post.return_value = {
            "id": 102,
            "title": "Metadata Proposal",
            "description": "With metadata",
            "creator": "0xcreator",
            "created_at": "2024-01-15T10:00:00",
        }

        metadata = {"category": "treasury", "amount": "1000000"}
        client.create_proposal(
            title="Metadata Proposal",
            description="With metadata",
            proposer="0xcreator",
            metadata=metadata,
        )

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["metadata"] == metadata

    def test_create_proposal_empty_title_raises_validation(self, client):
        """Test empty title raises ValidationError."""
        with pytest.raises(
            ValidationError, match="title, description, and proposer are required"
        ):
            client.create_proposal(
                title="",
                description="Description",
                proposer="0xcreator",
            )

    def test_create_proposal_empty_description_raises_validation(self, client):
        """Test empty description raises ValidationError."""
        with pytest.raises(
            ValidationError, match="title, description, and proposer are required"
        ):
            client.create_proposal(
                title="Title",
                description="",
                proposer="0xcreator",
            )

    def test_create_proposal_empty_proposer_raises_validation(self, client):
        """Test empty proposer raises ValidationError."""
        with pytest.raises(
            ValidationError, match="title, description, and proposer are required"
        ):
            client.create_proposal(
                title="Title",
                description="Description",
                proposer="",
            )

    def test_create_proposal_none_values_raises_validation(self, client):
        """Test None values raise ValidationError."""
        with pytest.raises(ValidationError):
            client.create_proposal(
                title=None,
                description="Description",
                proposer="0xcreator",
            )


class TestVote:
    """Tests for vote method."""

    @pytest.fixture
    def client(self):
        """Create GovernanceClient with mocked HTTP client."""
        mock_http = Mock()
        return GovernanceClient(mock_http)

    def test_vote_yes_success(self, client):
        """Test successful yes vote."""
        client.http_client.post.return_value = {
            "proposal_id": 42,
            "voter": "0xvoter",
            "choice": "yes",
            "vote_weight": 100,
            "tx_hash": "0xvotehash",
        }

        result = client.vote(proposal_id=42, voter="0xvoter", choice="yes")

        assert result["choice"] == "yes"
        assert result["vote_weight"] == 100

    def test_vote_no_success(self, client):
        """Test successful no vote."""
        client.http_client.post.return_value = {
            "proposal_id": 42,
            "voter": "0xvoter",
            "choice": "no",
        }

        result = client.vote(proposal_id=42, voter="0xvoter", choice="no")

        assert result["choice"] == "no"

    def test_vote_abstain_success(self, client):
        """Test successful abstain vote."""
        client.http_client.post.return_value = {
            "proposal_id": 42,
            "voter": "0xvoter",
            "choice": "abstain",
        }

        result = client.vote(proposal_id=42, voter="0xvoter", choice="abstain")

        assert result["choice"] == "abstain"

    def test_vote_calls_correct_endpoint(self, client):
        """Test vote calls correct API endpoint."""
        client.http_client.post.return_value = {}

        client.vote(proposal_id=42, voter="0xvoter", choice="yes")

        call_args = client.http_client.post.call_args
        assert call_args[0][0] == "/governance/proposals/42/vote"
        assert call_args[1]["data"]["voter"] == "0xvoter"
        assert call_args[1]["data"]["choice"] == "yes"

    def test_vote_negative_proposal_id_raises_validation(self, client):
        """Test negative proposal_id raises ValidationError."""
        with pytest.raises(ValidationError, match="proposal_id must be non-negative"):
            client.vote(proposal_id=-1, voter="0xvoter", choice="yes")

    def test_vote_empty_voter_raises_validation(self, client):
        """Test empty voter raises ValidationError."""
        with pytest.raises(ValidationError, match="voter is required"):
            client.vote(proposal_id=42, voter="", choice="yes")

    def test_vote_invalid_choice_raises_validation(self, client):
        """Test invalid choice raises ValidationError."""
        with pytest.raises(
            ValidationError, match="choice must be 'yes', 'no', or 'abstain'"
        ):
            client.vote(proposal_id=42, voter="0xvoter", choice="maybe")

    def test_vote_uppercase_choice_raises_validation(self, client):
        """Test uppercase choice raises ValidationError."""
        with pytest.raises(ValidationError):
            client.vote(proposal_id=42, voter="0xvoter", choice="YES")


class TestGetActiveProposals:
    """Tests for get_active_proposals method."""

    @pytest.fixture
    def client(self):
        """Create GovernanceClient with mocked HTTP client."""
        mock_http = Mock()
        return GovernanceClient(mock_http)

    def test_get_active_proposals_success(self, client):
        """Test successful active proposals retrieval."""
        client.http_client.get.return_value = {
            "proposals": [
                {
                    "id": 1,
                    "title": "Active Proposal 1",
                    "description": "Description",
                    "creator": "0xcreator",
                    "status": "active",
                    "created_at": "2024-01-15T10:00:00",
                },
                {
                    "id": 2,
                    "title": "Active Proposal 2",
                    "description": "Description",
                    "creator": "0xcreator",
                    "status": "active",
                    "created_at": "2024-01-16T10:00:00",
                },
            ],
            "total": 2,
        }

        proposals = client.get_active_proposals()

        assert len(proposals) == 2
        assert isinstance(proposals[0], Proposal)
        assert proposals[0].status == ProposalStatus.ACTIVE

    def test_get_active_proposals_calls_list_with_active_status(self, client):
        """Test get_active_proposals uses status=active filter."""
        client.http_client.get.return_value = {
            "proposals": [],
            "total": 0,
        }

        client.get_active_proposals()

        call_args = client.http_client.get.call_args
        assert call_args[1]["params"]["status"] == "active"

    def test_get_active_proposals_empty(self, client):
        """Test empty active proposals list."""
        client.http_client.get.return_value = {
            "proposals": [],
            "total": 0,
        }

        proposals = client.get_active_proposals()

        assert proposals == []


class TestGetProposalVotes:
    """Tests for get_proposal_votes method."""

    @pytest.fixture
    def client(self):
        """Create GovernanceClient with mocked HTTP client."""
        mock_http = Mock()
        return GovernanceClient(mock_http)

    def test_get_proposal_votes_success(self, client):
        """Test successful vote retrieval."""
        client.http_client.get.return_value = {
            "id": 42,
            "title": "Vote Proposal",
            "description": "Description",
            "creator": "0xcreator",
            "status": "active",
            "created_at": "2024-01-15T10:00:00",
            "votes_for": 1000,
            "votes_against": 500,
            "votes_abstain": 200,
        }

        result = client.get_proposal_votes(proposal_id=42)

        assert result["proposal_id"] == 42
        assert result["votes_for"] == 1000
        assert result["votes_against"] == 500
        assert result["votes_abstain"] == 200
        assert result["total_votes"] == 1700

    def test_get_proposal_votes_zero_votes(self, client):
        """Test votes with no votes cast."""
        client.http_client.get.return_value = {
            "id": 99,
            "title": "No Votes Proposal",
            "description": "Description",
            "creator": "0xcreator",
            "created_at": "2024-01-15T10:00:00",
            "votes_for": 0,
            "votes_against": 0,
            "votes_abstain": 0,
        }

        result = client.get_proposal_votes(proposal_id=99)

        assert result["total_votes"] == 0

    def test_get_proposal_votes_uses_get_proposal(self, client):
        """Test get_proposal_votes calls get_proposal internally."""
        client.http_client.get.return_value = {
            "id": 1,
            "title": "Test",
            "description": "Test",
            "creator": "0x123",
            "created_at": "2024-01-15T10:00:00",
            "votes_for": 10,
            "votes_against": 5,
            "votes_abstain": 2,
        }

        client.get_proposal_votes(proposal_id=1)

        client.http_client.get.assert_called_once_with("/governance/proposals/1")


class TestGovernanceClientErrorHandling:
    """Tests for GovernanceClient error handling."""

    @pytest.fixture
    def client(self):
        """Create GovernanceClient with mocked HTTP client."""
        mock_http = Mock()
        return GovernanceClient(mock_http)

    def test_governance_error_passes_through_on_list(self, client):
        """Test GovernanceError passes through on list_proposals."""
        client.http_client.get.side_effect = GovernanceError("List failed")

        with pytest.raises(GovernanceError, match="List failed"):
            client.list_proposals()

    def test_governance_error_passes_through_on_get(self, client):
        """Test GovernanceError passes through on get_proposal."""
        client.http_client.get.side_effect = GovernanceError("Get failed")

        with pytest.raises(GovernanceError, match="Get failed"):
            client.get_proposal(proposal_id=1)

    def test_governance_error_passes_through_on_create(self, client):
        """Test GovernanceError passes through on create_proposal."""
        client.http_client.post.side_effect = GovernanceError("Create failed")

        with pytest.raises(GovernanceError, match="Create failed"):
            client.create_proposal(
                title="Title",
                description="Description",
                proposer="0xcreator",
            )

    def test_governance_error_passes_through_on_vote(self, client):
        """Test GovernanceError passes through on vote."""
        client.http_client.post.side_effect = GovernanceError("Vote failed")

        with pytest.raises(GovernanceError, match="Vote failed"):
            client.vote(proposal_id=1, voter="0xvoter", choice="yes")

    def test_key_error_wrapped_in_governance_error(self, client):
        """Test KeyError is wrapped in GovernanceError."""
        client.http_client.get.return_value = {}  # Missing required keys

        with pytest.raises(GovernanceError, match="Failed to get proposal"):
            client.get_proposal(proposal_id=1)

    def test_value_error_wrapped_in_governance_error(self, client):
        """Test ValueError is wrapped in GovernanceError."""
        client.http_client.get.return_value = {
            "id": 1,
            "title": "Test",
            "description": "Test",
            "creator": "0x123",
            "created_at": "invalid-date",
        }

        with pytest.raises(GovernanceError):
            client.get_proposal(proposal_id=1)


class TestGovernanceClientEdgeCases:
    """Tests for GovernanceClient edge cases."""

    @pytest.fixture
    def client(self):
        """Create GovernanceClient with mocked HTTP client."""
        mock_http = Mock()
        return GovernanceClient(mock_http)

    def test_very_long_title(self, client):
        """Test handling very long proposal title."""
        client.http_client.post.return_value = {
            "id": 1,
            "title": "A" * 1000,
            "description": "Description",
            "creator": "0xcreator",
            "created_at": "2024-01-15T10:00:00",
        }

        proposal = client.create_proposal(
            title="A" * 1000,
            description="Description",
            proposer="0xcreator",
        )

        assert len(proposal.title) == 1000

    def test_very_long_description(self, client):
        """Test handling very long proposal description."""
        client.http_client.post.return_value = {
            "id": 2,
            "title": "Title",
            "description": "B" * 10000,
            "creator": "0xcreator",
            "created_at": "2024-01-15T10:00:00",
        }

        proposal = client.create_proposal(
            title="Title",
            description="B" * 10000,
            proposer="0xcreator",
        )

        assert len(proposal.description) == 10000

    def test_unicode_in_title_and_description(self, client):
        """Test handling unicode in proposal."""
        client.http_client.post.return_value = {
            "id": 3,
            "title": "Unicode Test Title",
            "description": "Description with unicode",
            "creator": "0xcreator",
            "created_at": "2024-01-15T10:00:00",
        }

        proposal = client.create_proposal(
            title="Unicode Test Title",
            description="Description with unicode",
            proposer="0xcreator",
        )

        assert proposal is not None

    def test_large_vote_counts(self, client):
        """Test handling large vote counts."""
        client.http_client.get.return_value = {
            "id": 4,
            "title": "High Vote Proposal",
            "description": "Many votes",
            "creator": "0xcreator",
            "created_at": "2024-01-15T10:00:00",
            "votes_for": 999999999999,
            "votes_against": 888888888888,
            "votes_abstain": 777777777777,
        }

        proposal = client.get_proposal(proposal_id=4)

        assert proposal.votes_for == 999999999999
        assert proposal.total_votes == 999999999999 + 888888888888 + 777777777777

    def test_proposal_id_zero(self, client):
        """Test proposal ID zero is valid."""
        client.http_client.get.return_value = {
            "id": 0,
            "title": "Genesis Proposal",
            "description": "First proposal ever",
            "creator": "0xgenesis",
            "created_at": "2024-01-01T00:00:00",
        }

        proposal = client.get_proposal(proposal_id=0)

        assert proposal.id == 0

    def test_all_proposal_statuses(self, client):
        """Test all proposal status values."""
        for status_value in ["pending", "active", "passed", "failed"]:
            client.http_client.get.return_value = {
                "id": 1,
                "title": "Status Test",
                "description": "Testing status",
                "creator": "0xcreator",
                "status": status_value,
                "created_at": "2024-01-15T10:00:00",
            }

            proposal = client.get_proposal(proposal_id=1)

            assert proposal.status.value == status_value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
