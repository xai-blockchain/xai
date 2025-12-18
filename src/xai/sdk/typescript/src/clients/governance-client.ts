/**
 * Governance Client for XAI SDK
 *
 * Handles governance proposals, voting, and proposal lifecycle management.
 */

import { HTTPClient } from '../utils/http-client';
import {
  Proposal,
  ProposalStatus,
  ProposalQueryParams,
  CreateProposalParams,
  VoteChoice,
  PaginatedResponse,
} from '../types';
import { GovernanceError, ValidationError } from '../errors';

/**
 * Client for governance operations
 */
export class GovernanceClient {
  constructor(private httpClient: HTTPClient) {}

  /**
   * List governance proposals
   *
   * @param params - Query parameters with status filter, limit, and offset
   * @returns Paginated list of proposals
   *
   * @example
   * ```typescript
   * const result = await client.governance.listProposals({
   *   status: 'active',
   *   limit: 10
   * });
   * console.log('Active proposals:', result.data);
   * ```
   */
  async listProposals(params: ProposalQueryParams = {}): Promise<PaginatedResponse<Proposal>> {
    const limit = Math.min(params.limit || 20, 100);
    const offset = params.offset || 0;

    try {
      const queryParams: Record<string, unknown> = { limit, offset };
      if (params.status) {
        queryParams.status = params.status;
      }

      const response = await this.httpClient.get<{
        proposals: Array<{
          id: number;
          title: string;
          description: string;
          creator: string;
          status?: string;
          created_at: string;
          voting_ends_at?: string;
          votes_for?: number;
          votes_against?: number;
          votes_abstain?: number;
        }>;
        total: number;
        limit: number;
        offset: number;
      }>('/governance/proposals', queryParams);

      const proposals = (response.proposals || []).map((p) => ({
        id: p.id,
        title: p.title,
        description: p.description,
        creator: p.creator,
        status: (p.status as ProposalStatus) || ProposalStatus.PENDING,
        createdAt: p.created_at,
        votingEndsAt: p.voting_ends_at,
        votesFor: p.votes_for || 0,
        votesAgainst: p.votes_against || 0,
        votesAbstain: p.votes_abstain || 0,
      }));

      return {
        data: proposals,
        total: response.total || 0,
        limit: response.limit || limit,
        offset: response.offset || offset,
      };
    } catch (error) {
      if (error instanceof GovernanceError) {
        throw error;
      }
      throw new GovernanceError(`Failed to list proposals: ${error}`);
    }
  }

  /**
   * Get proposal details
   *
   * @param proposalId - Proposal ID
   * @returns Proposal details
   *
   * @example
   * ```typescript
   * const proposal = await client.governance.getProposal(1);
   * console.log('Proposal:', proposal.title);
   * console.log('Votes for:', proposal.votesFor);
   * console.log('Votes against:', proposal.votesAgainst);
   * ```
   */
  async getProposal(proposalId: number): Promise<Proposal> {
    if (proposalId < 0) {
      throw new ValidationError('proposalId must be non-negative');
    }

    try {
      const response = await this.httpClient.get<{
        id: number;
        title: string;
        description: string;
        creator: string;
        status?: string;
        created_at: string;
        voting_starts_at?: string;
        voting_ends_at?: string;
        votes_for?: number;
        votes_against?: number;
        votes_abstain?: number;
      }>(`/governance/proposals/${proposalId}`);

      return {
        id: response.id,
        title: response.title,
        description: response.description,
        creator: response.creator,
        status: (response.status as ProposalStatus) || ProposalStatus.PENDING,
        createdAt: response.created_at,
        votingStartsAt: response.voting_starts_at,
        votingEndsAt: response.voting_ends_at,
        votesFor: response.votes_for || 0,
        votesAgainst: response.votes_against || 0,
        votesAbstain: response.votes_abstain || 0,
      };
    } catch (error) {
      if (error instanceof GovernanceError) {
        throw error;
      }
      throw new GovernanceError(`Failed to get proposal: ${error}`);
    }
  }

  /**
   * Create a governance proposal
   *
   * @param params - Proposal creation parameters
   * @returns Created proposal
   *
   * @example
   * ```typescript
   * const proposal = await client.governance.createProposal({
   *   title: 'Upgrade Protocol',
   *   description: 'Propose upgrading the protocol to v2.0',
   *   proposer: '0x1234...',
   *   duration: 604800 // 7 days
   * });
   * console.log('Proposal created:', proposal.id);
   * ```
   */
  async createProposal(params: CreateProposalParams): Promise<Proposal> {
    if (!params.title || !params.description || !params.proposer) {
      throw new ValidationError('title, description, and proposer are required');
    }

    try {
      const payload: Record<string, unknown> = {
        title: params.title,
        description: params.description,
        proposer: params.proposer,
      };

      if (params.duration) {
        payload.duration = params.duration;
      }
      if (params.metadata) {
        payload.metadata = params.metadata;
      }

      const response = await this.httpClient.post<{
        id: number;
        title: string;
        description: string;
        creator: string;
        status?: string;
        created_at: string;
        votes_for?: number;
        votes_against?: number;
      }>('/governance/proposals', payload);

      return {
        id: response.id,
        title: response.title,
        description: response.description,
        creator: response.creator,
        status: (response.status as ProposalStatus) || ProposalStatus.PENDING,
        createdAt: response.created_at,
        votesFor: response.votes_for || 0,
        votesAgainst: response.votes_against || 0,
      };
    } catch (error) {
      if (error instanceof GovernanceError) {
        throw error;
      }
      throw new GovernanceError(`Failed to create proposal: ${error}`);
    }
  }

  /**
   * Vote on a proposal
   *
   * @param proposalId - Proposal ID
   * @param voter - Voter address
   * @param choice - Vote choice (yes, no, abstain)
   * @returns Vote confirmation
   *
   * @example
   * ```typescript
   * const vote = await client.governance.vote(1, '0x1234...', VoteChoice.YES);
   * console.log('Vote submitted');
   * ```
   */
  async vote(
    proposalId: number,
    voter: string,
    choice: VoteChoice
  ): Promise<Record<string, unknown>> {
    if (proposalId < 0) {
      throw new ValidationError('proposalId must be non-negative');
    }

    if (!voter) {
      throw new ValidationError('voter is required');
    }

    if (![VoteChoice.YES, VoteChoice.NO, VoteChoice.ABSTAIN].includes(choice)) {
      throw new ValidationError("choice must be 'yes', 'no', or 'abstain'");
    }

    try {
      const payload = {
        voter,
        choice,
      };

      return await this.httpClient.post(`/governance/proposals/${proposalId}/vote`, payload);
    } catch (error) {
      if (error instanceof GovernanceError) {
        throw error;
      }
      throw new GovernanceError(`Failed to vote: ${error}`);
    }
  }

  /**
   * Get active proposals
   *
   * @returns List of active proposals
   *
   * @example
   * ```typescript
   * const activeProposals = await client.governance.getActiveProposals();
   * console.log('Active proposals:', activeProposals);
   * ```
   */
  async getActiveProposals(): Promise<Proposal[]> {
    try {
      const result = await this.listProposals({ status: 'active' });
      return result.data;
    } catch (error) {
      if (error instanceof GovernanceError) {
        throw error;
      }
      throw new GovernanceError(`Failed to get active proposals: ${error}`);
    }
  }

  /**
   * Get vote details for a proposal
   *
   * @param proposalId - Proposal ID
   * @returns Vote information
   *
   * @example
   * ```typescript
   * const votes = await client.governance.getProposalVotes(1);
   * console.log('Votes for:', votes.votesFor);
   * console.log('Votes against:', votes.votesAgainst);
   * console.log('Total votes:', votes.totalVotes);
   * ```
   */
  async getProposalVotes(proposalId: number): Promise<{
    proposalId: number;
    votesFor: number;
    votesAgainst: number;
    votesAbstain: number;
    totalVotes: number;
  }> {
    try {
      const proposal = await this.getProposal(proposalId);
      return {
        proposalId: proposal.id,
        votesFor: proposal.votesFor || 0,
        votesAgainst: proposal.votesAgainst || 0,
        votesAbstain: proposal.votesAbstain || 0,
        totalVotes:
          (proposal.votesFor || 0) +
          (proposal.votesAgainst || 0) +
          (proposal.votesAbstain || 0),
      };
    } catch (error) {
      if (error instanceof GovernanceError) {
        throw error;
      }
      throw new GovernanceError(`Failed to get proposal votes: ${error}`);
    }
  }
}
