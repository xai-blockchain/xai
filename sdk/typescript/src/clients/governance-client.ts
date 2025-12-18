/**
 * Governance Client
 * Handles governance proposals and voting
 */

import { HTTPClient } from '../utils/http-client';
import { GovernanceProposal, GovernanceVote } from '../types';

export class GovernanceClient {
  constructor(private httpClient: HTTPClient) {}

  /**
   * Get all governance proposals
   */
  public async getProposals(status?: string): Promise<GovernanceProposal[]> {
    return this.httpClient.get<GovernanceProposal[]>('/governance/proposals', {
      params: status ? { status } : {},
    });
  }

  /**
   * Get a specific proposal by ID
   */
  public async getProposal(id: string): Promise<GovernanceProposal> {
    return this.httpClient.get<GovernanceProposal>(`/governance/proposals/${id}`);
  }

  /**
   * Create a new proposal
   */
  public async createProposal(
    title: string,
    description: string,
    proposer: string,
    duration?: number
  ): Promise<{ success: boolean; proposal_id: string }> {
    return this.httpClient.post('/governance/proposals', {
      title,
      description,
      proposer,
      duration,
    });
  }

  /**
   * Vote on a proposal
   */
  public async vote(
    proposalId: string,
    voter: string,
    vote: 'yes' | 'no' | 'abstain',
    signature: string
  ): Promise<{ success: boolean; message: string }> {
    return this.httpClient.post('/governance/vote', {
      proposal_id: proposalId,
      voter,
      vote,
      signature,
    });
  }

  /**
   * Get votes for a proposal
   */
  public async getVotes(proposalId: string): Promise<GovernanceVote[]> {
    return this.httpClient.get<GovernanceVote[]>(`/governance/proposals/${proposalId}/votes`);
  }

  /**
   * Get voting power for an address
   */
  public async getVotingPower(address: string): Promise<{ voting_power: number }> {
    return this.httpClient.get(`/governance/voting-power/${address}`);
  }

  /**
   * Execute a passed proposal
   */
  public async executeProposal(proposalId: string): Promise<{
    success: boolean;
    message: string;
  }> {
    return this.httpClient.post(`/governance/proposals/${proposalId}/execute`);
  }

  /**
   * Cancel a proposal
   */
  public async cancelProposal(proposalId: string, proposer: string): Promise<{
    success: boolean;
    message: string;
  }> {
    return this.httpClient.post(`/governance/proposals/${proposalId}/cancel`, {
      proposer,
    });
  }

  /**
   * Get governance parameters
   */
  public async getParameters(): Promise<Record<string, any>> {
    return this.httpClient.get('/governance/parameters');
  }

  /**
   * Get proposal result
   */
  public async getProposalResult(proposalId: string): Promise<{
    yes_votes: number;
    no_votes: number;
    abstain_votes: number;
    total_votes: number;
    passed: boolean;
  }> {
    return this.httpClient.get(`/governance/proposals/${proposalId}/result`);
  }
}
