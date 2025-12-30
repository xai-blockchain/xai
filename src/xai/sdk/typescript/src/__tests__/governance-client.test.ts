/**
 * GovernanceClient Unit Tests
 *
 * Comprehensive tests for governance operations including:
 * - Proposal listing and filtering
 * - Proposal retrieval
 * - Proposal creation
 * - Voting
 * - Active proposals and vote details
 * - Error handling and validation
 */

import { GovernanceClient } from '../clients/governance-client';
import { HTTPClient } from '../utils/http-client';
import { ValidationError, GovernanceError } from '../errors';
import { ProposalStatus, VoteChoice } from '../types';

// Mock HTTPClient
jest.mock('../utils/http-client');

const MockHTTPClient = HTTPClient as jest.MockedClass<typeof HTTPClient>;

describe('GovernanceClient', () => {
  let governanceClient: GovernanceClient;
  let mockHttpClient: jest.Mocked<HTTPClient>;

  beforeEach(() => {
    jest.clearAllMocks();
    mockHttpClient = new MockHTTPClient({
      baseUrl: 'http://localhost:5000',
    }) as jest.Mocked<HTTPClient>;
    governanceClient = new GovernanceClient(mockHttpClient);
  });

  describe('listProposals', () => {
    it('should list proposals with default pagination', async () => {
      const mockResponse = {
        proposals: [
          {
            id: 1,
            title: 'Proposal 1',
            description: 'Description 1',
            creator: '0xcreator1',
            status: 'active',
            created_at: '2024-01-01T00:00:00Z',
            voting_ends_at: '2024-01-08T00:00:00Z',
            votes_for: 100,
            votes_against: 50,
            votes_abstain: 10,
          },
          {
            id: 2,
            title: 'Proposal 2',
            description: 'Description 2',
            creator: '0xcreator2',
            status: 'pending',
            created_at: '2024-01-02T00:00:00Z',
          },
        ],
        total: 2,
        limit: 20,
        offset: 0,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await governanceClient.listProposals();

      expect(mockHttpClient.get).toHaveBeenCalledWith('/governance/proposals', {
        limit: 20,
        offset: 0,
      });
      expect(result.data).toHaveLength(2);
      expect(result.total).toBe(2);
      expect(result.data[0]).toEqual({
        id: 1,
        title: 'Proposal 1',
        description: 'Description 1',
        creator: '0xcreator1',
        status: ProposalStatus.ACTIVE,
        createdAt: '2024-01-01T00:00:00Z',
        votingEndsAt: '2024-01-08T00:00:00Z',
        votesFor: 100,
        votesAgainst: 50,
        votesAbstain: 10,
      });
    });

    it('should list proposals with status filter', async () => {
      const mockResponse = {
        proposals: [],
        total: 0,
        limit: 20,
        offset: 0,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      await governanceClient.listProposals({ status: 'active' });

      expect(mockHttpClient.get).toHaveBeenCalledWith('/governance/proposals', {
        limit: 20,
        offset: 0,
        status: 'active',
      });
    });

    it('should list proposals with custom pagination', async () => {
      const mockResponse = {
        proposals: [],
        total: 100,
        limit: 50,
        offset: 50,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await governanceClient.listProposals({ limit: 50, offset: 50 });

      expect(mockHttpClient.get).toHaveBeenCalledWith('/governance/proposals', {
        limit: 50,
        offset: 50,
      });
      expect(result.limit).toBe(50);
      expect(result.offset).toBe(50);
    });

    it('should cap limit at 100', async () => {
      const mockResponse = {
        proposals: [],
        total: 0,
        limit: 100,
        offset: 0,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      await governanceClient.listProposals({ limit: 500 });

      expect(mockHttpClient.get).toHaveBeenCalledWith('/governance/proposals', {
        limit: 100,
        offset: 0,
      });
    });

    it('should handle empty proposals', async () => {
      const mockResponse = {
        proposals: null,
        total: 0,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await governanceClient.listProposals();

      expect(result.data).toEqual([]);
      expect(result.total).toBe(0);
    });

    it('should handle missing vote counts', async () => {
      const mockResponse = {
        proposals: [
          {
            id: 1,
            title: 'New Proposal',
            description: 'Description',
            creator: '0xcreator',
            created_at: '2024-01-01T00:00:00Z',
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await governanceClient.listProposals();

      expect(result.data[0].votesFor).toBe(0);
      expect(result.data[0].votesAgainst).toBe(0);
      expect(result.data[0].votesAbstain).toBe(0);
      expect(result.data[0].status).toBe(ProposalStatus.PENDING);
    });

    it('should wrap unknown errors in GovernanceError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Database error'));

      await expect(governanceClient.listProposals()).rejects.toThrow(GovernanceError);
      await expect(governanceClient.listProposals()).rejects.toThrow('Failed to list proposals');
    });
  });

  describe('getProposal', () => {
    it('should get proposal by ID', async () => {
      const mockResponse = {
        id: 1,
        title: 'Upgrade Protocol',
        description: 'Upgrade to v2.0',
        creator: '0xcreator',
        status: 'active',
        created_at: '2024-01-01T00:00:00Z',
        voting_starts_at: '2024-01-01T00:00:00Z',
        voting_ends_at: '2024-01-08T00:00:00Z',
        votes_for: 500,
        votes_against: 200,
        votes_abstain: 50,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await governanceClient.getProposal(1);

      expect(mockHttpClient.get).toHaveBeenCalledWith('/governance/proposals/1');
      expect(result).toEqual({
        id: 1,
        title: 'Upgrade Protocol',
        description: 'Upgrade to v2.0',
        creator: '0xcreator',
        status: ProposalStatus.ACTIVE,
        createdAt: '2024-01-01T00:00:00Z',
        votingStartsAt: '2024-01-01T00:00:00Z',
        votingEndsAt: '2024-01-08T00:00:00Z',
        votesFor: 500,
        votesAgainst: 200,
        votesAbstain: 50,
      });
    });

    it('should throw ValidationError for negative proposal ID', async () => {
      await expect(governanceClient.getProposal(-1)).rejects.toThrow(ValidationError);
      await expect(governanceClient.getProposal(-1)).rejects.toThrow(
        'proposalId must be non-negative'
      );
    });

    it('should accept proposal ID of 0', async () => {
      const mockResponse = {
        id: 0,
        title: 'Genesis Proposal',
        description: 'First proposal',
        creator: '0xgenesis',
        created_at: '2024-01-01T00:00:00Z',
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await governanceClient.getProposal(0);

      expect(result.id).toBe(0);
    });

    it('should wrap unknown errors in GovernanceError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Not found'));

      await expect(governanceClient.getProposal(999)).rejects.toThrow(GovernanceError);
      await expect(governanceClient.getProposal(999)).rejects.toThrow('Failed to get proposal');
    });
  });

  describe('createProposal', () => {
    it('should create proposal with required fields', async () => {
      const mockResponse = {
        id: 10,
        title: 'New Proposal',
        description: 'A new proposal',
        creator: '0xproposer',
        status: 'pending',
        created_at: '2024-01-01T00:00:00Z',
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await governanceClient.createProposal({
        title: 'New Proposal',
        description: 'A new proposal',
        proposer: '0xproposer',
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/governance/proposals', {
        title: 'New Proposal',
        description: 'A new proposal',
        proposer: '0xproposer',
      });
      expect(result).toEqual({
        id: 10,
        title: 'New Proposal',
        description: 'A new proposal',
        creator: '0xproposer',
        status: ProposalStatus.PENDING,
        createdAt: '2024-01-01T00:00:00Z',
        votesFor: 0,
        votesAgainst: 0,
      });
    });

    it('should create proposal with optional fields', async () => {
      const mockResponse = {
        id: 11,
        title: 'Duration Proposal',
        description: 'With duration',
        creator: '0xproposer',
        created_at: '2024-01-01T00:00:00Z',
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      await governanceClient.createProposal({
        title: 'Duration Proposal',
        description: 'With duration',
        proposer: '0xproposer',
        duration: 604800,
        metadata: { category: 'upgrade' },
      });

      expect(mockHttpClient.post).toHaveBeenCalledWith('/governance/proposals', {
        title: 'Duration Proposal',
        description: 'With duration',
        proposer: '0xproposer',
        duration: 604800,
        metadata: { category: 'upgrade' },
      });
    });

    it('should throw ValidationError for missing title', async () => {
      await expect(
        governanceClient.createProposal({
          title: '',
          description: 'Description',
          proposer: '0xproposer',
        })
      ).rejects.toThrow(ValidationError);
      await expect(
        governanceClient.createProposal({
          title: '',
          description: 'Description',
          proposer: '0xproposer',
        })
      ).rejects.toThrow('title, description, and proposer are required');
    });

    it('should throw ValidationError for missing description', async () => {
      await expect(
        governanceClient.createProposal({
          title: 'Title',
          description: '',
          proposer: '0xproposer',
        })
      ).rejects.toThrow(ValidationError);
    });

    it('should throw ValidationError for missing proposer', async () => {
      await expect(
        governanceClient.createProposal({
          title: 'Title',
          description: 'Description',
          proposer: '',
        })
      ).rejects.toThrow(ValidationError);
    });

    it('should wrap unknown errors in GovernanceError', async () => {
      mockHttpClient.post = jest.fn().mockRejectedValue(new Error('Insufficient stake'));

      await expect(
        governanceClient.createProposal({
          title: 'Title',
          description: 'Description',
          proposer: '0xproposer',
        })
      ).rejects.toThrow(GovernanceError);
      await expect(
        governanceClient.createProposal({
          title: 'Title',
          description: 'Description',
          proposer: '0xproposer',
        })
      ).rejects.toThrow('Failed to create proposal');
    });
  });

  describe('vote', () => {
    it('should vote YES on proposal', async () => {
      const mockResponse = {
        success: true,
        vote: 'yes',
      };

      mockHttpClient.post = jest.fn().mockResolvedValue(mockResponse);

      const result = await governanceClient.vote(1, '0xvoter', VoteChoice.YES);

      expect(mockHttpClient.post).toHaveBeenCalledWith('/governance/proposals/1/vote', {
        voter: '0xvoter',
        choice: 'yes',
      });
      expect(result).toEqual(mockResponse);
    });

    it('should vote NO on proposal', async () => {
      mockHttpClient.post = jest.fn().mockResolvedValue({ success: true });

      await governanceClient.vote(1, '0xvoter', VoteChoice.NO);

      expect(mockHttpClient.post).toHaveBeenCalledWith('/governance/proposals/1/vote', {
        voter: '0xvoter',
        choice: 'no',
      });
    });

    it('should vote ABSTAIN on proposal', async () => {
      mockHttpClient.post = jest.fn().mockResolvedValue({ success: true });

      await governanceClient.vote(1, '0xvoter', VoteChoice.ABSTAIN);

      expect(mockHttpClient.post).toHaveBeenCalledWith('/governance/proposals/1/vote', {
        voter: '0xvoter',
        choice: 'abstain',
      });
    });

    it('should throw ValidationError for negative proposal ID', async () => {
      await expect(
        governanceClient.vote(-1, '0xvoter', VoteChoice.YES)
      ).rejects.toThrow(ValidationError);
      await expect(
        governanceClient.vote(-1, '0xvoter', VoteChoice.YES)
      ).rejects.toThrow('proposalId must be non-negative');
    });

    it('should throw ValidationError for empty voter', async () => {
      await expect(
        governanceClient.vote(1, '', VoteChoice.YES)
      ).rejects.toThrow(ValidationError);
      await expect(
        governanceClient.vote(1, '', VoteChoice.YES)
      ).rejects.toThrow('voter is required');
    });

    it('should throw ValidationError for invalid choice', async () => {
      await expect(
        governanceClient.vote(1, '0xvoter', 'invalid' as VoteChoice)
      ).rejects.toThrow(ValidationError);
      await expect(
        governanceClient.vote(1, '0xvoter', 'invalid' as VoteChoice)
      ).rejects.toThrow("choice must be 'yes', 'no', or 'abstain'");
    });

    it('should wrap unknown errors in GovernanceError', async () => {
      mockHttpClient.post = jest.fn().mockRejectedValue(new Error('Already voted'));

      await expect(
        governanceClient.vote(1, '0xvoter', VoteChoice.YES)
      ).rejects.toThrow(GovernanceError);
      await expect(
        governanceClient.vote(1, '0xvoter', VoteChoice.YES)
      ).rejects.toThrow('Failed to vote');
    });
  });

  describe('getActiveProposals', () => {
    it('should get active proposals', async () => {
      const mockResponse = {
        proposals: [
          {
            id: 1,
            title: 'Active Proposal',
            description: 'Currently active',
            creator: '0xcreator',
            status: 'active',
            created_at: '2024-01-01T00:00:00Z',
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await governanceClient.getActiveProposals();

      expect(mockHttpClient.get).toHaveBeenCalledWith('/governance/proposals', {
        limit: 20,
        offset: 0,
        status: 'active',
      });
      expect(result).toHaveLength(1);
      expect(result[0].title).toBe('Active Proposal');
    });

    it('should return empty array when no active proposals', async () => {
      const mockResponse = {
        proposals: [],
        total: 0,
        limit: 20,
        offset: 0,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockResponse);

      const result = await governanceClient.getActiveProposals();

      expect(result).toEqual([]);
    });

    it('should wrap unknown errors in GovernanceError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Network error'));

      await expect(governanceClient.getActiveProposals()).rejects.toThrow(GovernanceError);
      await expect(governanceClient.getActiveProposals()).rejects.toThrow(
        'Failed to list proposals'
      );
    });
  });

  describe('getProposalVotes', () => {
    it('should get proposal votes', async () => {
      const mockProposalResponse = {
        id: 1,
        title: 'Proposal',
        description: 'Description',
        creator: '0xcreator',
        status: 'active',
        created_at: '2024-01-01T00:00:00Z',
        votes_for: 100,
        votes_against: 50,
        votes_abstain: 25,
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockProposalResponse);

      const result = await governanceClient.getProposalVotes(1);

      expect(result).toEqual({
        proposalId: 1,
        votesFor: 100,
        votesAgainst: 50,
        votesAbstain: 25,
        totalVotes: 175,
      });
    });

    it('should handle proposal with no votes', async () => {
      const mockProposalResponse = {
        id: 2,
        title: 'New Proposal',
        description: 'No votes yet',
        creator: '0xcreator',
        created_at: '2024-01-01T00:00:00Z',
      };

      mockHttpClient.get = jest.fn().mockResolvedValue(mockProposalResponse);

      const result = await governanceClient.getProposalVotes(2);

      expect(result).toEqual({
        proposalId: 2,
        votesFor: 0,
        votesAgainst: 0,
        votesAbstain: 0,
        totalVotes: 0,
      });
    });

    it('should wrap unknown errors in GovernanceError', async () => {
      mockHttpClient.get = jest.fn().mockRejectedValue(new Error('Proposal not found'));

      await expect(governanceClient.getProposalVotes(999)).rejects.toThrow(GovernanceError);
      await expect(governanceClient.getProposalVotes(999)).rejects.toThrow(
        'Failed to get proposal'
      );
    });
  });
});
