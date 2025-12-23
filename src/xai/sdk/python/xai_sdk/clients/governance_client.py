from __future__ import annotations

"""
Governance Client for XAI SDK

Handles governance and voting operations.
"""

from datetime import datetime
from typing import Any

from ..exceptions import GovernanceError, ValidationError
from ..http_client import HTTPClient
from ..models import Proposal, ProposalStatus

class GovernanceClient:
    """Client for governance operations."""

    def __init__(self, http_client: HTTPClient) -> None:
        """
        Initialize Governance Client.

        Args:
            http_client: HTTP client instance
        """
        self.http_client = http_client

    def list_proposals(
        self,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        List governance proposals.

        Args:
            status: Filter by proposal status
            limit: Number of proposals to retrieve
            offset: Offset for pagination

        Returns:
            List of proposals with metadata

        Raises:
            GovernanceError: If proposal list retrieval fails
        """
        if limit > 100:
            limit = 100

        try:
            params: dict[str, Any] = {"limit": limit, "offset": offset}
            if status:
                params["status"] = status

            response = self.http_client.get("/governance/proposals", params=params)

            proposals = [
                Proposal(
                    id=p["id"],
                    title=p["title"],
                    description=p["description"],
                    creator=p["creator"],
                    status=ProposalStatus(p.get("status", "pending")),
                    created_at=datetime.fromisoformat(p["created_at"]),
                    voting_ends_at=datetime.fromisoformat(p["voting_ends_at"])
                    if p.get("voting_ends_at")
                    else None,
                    votes_for=p.get("votes_for", 0),
                    votes_against=p.get("votes_against", 0),
                    votes_abstain=p.get("votes_abstain", 0),
                )
                for p in response.get("proposals", [])
            ]

            return {
                "proposals": proposals,
                "total": response.get("total", 0),
                "limit": response.get("limit", limit),
                "offset": response.get("offset", offset),
            }
        except GovernanceError:

            raise

        except (KeyError, ValueError, TypeError) as e:

            raise GovernanceError(f"Failed to list proposals: {str(e)}") from e

    def get_proposal(self, proposal_id: int) -> Proposal:
        """
        Get proposal details.

        Args:
            proposal_id: Proposal ID

        Returns:
            Proposal details

        Raises:
            GovernanceError: If proposal retrieval fails
        """
        if proposal_id < 0:
            raise ValidationError("proposal_id must be non-negative")

        try:
            response = self.http_client.get(f"/governance/proposals/{proposal_id}")

            return Proposal(
                id=response["id"],
                title=response["title"],
                description=response["description"],
                creator=response["creator"],
                status=ProposalStatus(response.get("status", "pending")),
                created_at=datetime.fromisoformat(response["created_at"]),
                voting_starts_at=datetime.fromisoformat(response["voting_starts_at"])
                if response.get("voting_starts_at")
                else None,
                voting_ends_at=datetime.fromisoformat(response["voting_ends_at"])
                if response.get("voting_ends_at")
                else None,
                votes_for=response.get("votes_for", 0),
                votes_against=response.get("votes_against", 0),
                votes_abstain=response.get("votes_abstain", 0),
            )
        except GovernanceError:

            raise

        except (KeyError, ValueError, TypeError) as e:

            raise GovernanceError(f"Failed to get proposal: {str(e)}") from e

    def create_proposal(
        self,
        title: str,
        description: str,
        proposer: str,
        duration: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Proposal:
        """
        Create a governance proposal.

        Args:
            title: Proposal title
            description: Proposal description
            proposer: Address of proposer
            duration: Voting duration in seconds
            metadata: Optional metadata

        Returns:
            Created proposal

        Raises:
            GovernanceError: If proposal creation fails
        """
        if not title or not description or not proposer:
            raise ValidationError("title, description, and proposer are required")

        try:
            payload = {
                "title": title,
                "description": description,
                "proposer": proposer,
            }

            if duration:
                payload["duration"] = duration
            if metadata:
                payload["metadata"] = metadata

            response = self.http_client.post("/governance/proposals", data=payload)

            return Proposal(
                id=response["id"],
                title=response["title"],
                description=response["description"],
                creator=response["creator"],
                status=ProposalStatus(response.get("status", "pending")),
                created_at=datetime.fromisoformat(response["created_at"]),
                votes_for=response.get("votes_for", 0),
                votes_against=response.get("votes_against", 0),
            )
        except GovernanceError:
            raise
        except GovernanceError:

            raise

        except (KeyError, ValueError, TypeError) as e:

            raise GovernanceError(f"Failed to create proposal: {str(e)}") from e

    def vote(self, proposal_id: int, voter: str, choice: str) -> dict[str, Any]:
        """
        Vote on a proposal.

        Args:
            proposal_id: Proposal ID
            voter: Voter address
            choice: Vote choice (yes, no, abstain)

        Returns:
            Vote confirmation

        Raises:
            GovernanceError: If voting fails
        """
        if proposal_id < 0:
            raise ValidationError("proposal_id must be non-negative")

        if not voter:
            raise ValidationError("voter is required")

        if choice not in ["yes", "no", "abstain"]:
            raise ValidationError("choice must be 'yes', 'no', or 'abstain'")

        try:
            payload = {
                "voter": voter,
                "choice": choice,
            }

            return self.http_client.post(
                f"/governance/proposals/{proposal_id}/vote", data=payload
            )
        except GovernanceError:

            raise

        except (KeyError, ValueError, TypeError) as e:

            raise GovernanceError(f"Failed to vote: {str(e)}") from e

    def get_active_proposals(self) -> list[Proposal]:
        """
        Get active proposals.

        Returns:
            List of active proposals

        Raises:
            GovernanceError: If retrieval fails
        """
        try:
            result = self.list_proposals(status="active")
            return result["proposals"]
        except GovernanceError:

            raise

        except (KeyError, ValueError, TypeError) as e:

            raise GovernanceError(f"Failed to get active proposals: {str(e)}") from e

    def get_proposal_votes(self, proposal_id: int) -> dict[str, Any]:
        """
        Get vote details for a proposal.

        Args:
            proposal_id: Proposal ID

        Returns:
            Vote information

        Raises:
            GovernanceError: If retrieval fails
        """
        try:
            proposal = self.get_proposal(proposal_id)
            return {
                "proposal_id": proposal.id,
                "votes_for": proposal.votes_for,
                "votes_against": proposal.votes_against,
                "votes_abstain": proposal.votes_abstain,
                "total_votes": proposal.total_votes,
            }
        except GovernanceError:

            raise

        except (KeyError, ValueError, TypeError) as e:

            raise GovernanceError(f"Failed to get proposal votes: {str(e)}") from e
