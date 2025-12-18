/**
 * Governance Example
 *
 * Demonstrates governance operations including creating proposals
 * and voting.
 */

import { XAIClient, VoteChoice } from '../src';

async function main() {
  const client = new XAIClient({
    baseUrl: 'http://localhost:12080',
  });

  try {
    // Create wallets for proposer and voters
    console.log('--- Creating Wallets ---');
    const proposerWallet = await client.wallet.create();
    const voter1Wallet = await client.wallet.create();
    const voter2Wallet = await client.wallet.create();
    console.log('Proposer:', proposerWallet.address);
    console.log('Voter 1:', voter1Wallet.address);
    console.log('Voter 2:', voter2Wallet.address);

    // Create a proposal
    console.log('\n--- Creating Proposal ---');
    const proposal = await client.governance.createProposal({
      title: 'Upgrade XAI Protocol to v2.0',
      description:
        'This proposal suggests upgrading the XAI protocol to version 2.0 with improved performance and security features.',
      proposer: proposerWallet.address,
      duration: 604800, // 7 days
    });
    console.log('Proposal created!');
    console.log('ID:', proposal.id);
    console.log('Title:', proposal.title);
    console.log('Status:', proposal.status);

    // List active proposals
    console.log('\n--- Active Proposals ---');
    const activeProposals = await client.governance.getActiveProposals();
    console.log(`Found ${activeProposals.length} active proposals`);
    activeProposals.forEach((p) => {
      console.log(`  #${p.id}: ${p.title} (${p.status})`);
    });

    // Vote on the proposal
    console.log('\n--- Voting on Proposal ---');
    await client.governance.vote(proposal.id, voter1Wallet.address, VoteChoice.YES);
    console.log('Voter 1 voted YES');

    await client.governance.vote(proposal.id, voter2Wallet.address, VoteChoice.NO);
    console.log('Voter 2 voted NO');

    // Get updated proposal details
    console.log('\n--- Proposal Results ---');
    const updatedProposal = await client.governance.getProposal(proposal.id);
    console.log('Title:', updatedProposal.title);
    console.log('Votes for:', updatedProposal.votesFor);
    console.log('Votes against:', updatedProposal.votesAgainst);
    console.log('Votes abstain:', updatedProposal.votesAbstain);
    console.log('Status:', updatedProposal.status);

    // Get vote details
    console.log('\n--- Vote Details ---');
    const votes = await client.governance.getProposalVotes(proposal.id);
    console.log('Total votes:', votes.totalVotes);
    console.log('For:', votes.votesFor);
    console.log('Against:', votes.votesAgainst);
    console.log('Abstain:', votes.votesAbstain);

    // List all proposals
    console.log('\n--- All Proposals ---');
    const allProposals = await client.governance.listProposals({
      limit: 10,
      offset: 0,
    });
    console.log(`Total proposals: ${allProposals.total}`);
    allProposals.data.forEach((p) => {
      console.log(`  #${p.id}: ${p.title}`);
      console.log(`    Status: ${p.status}`);
      console.log(`    Votes: ${p.votesFor} for, ${p.votesAgainst} against, ${p.votesAbstain} abstain`);
    });
  } catch (error) {
    console.error('Error:', error);
  } finally {
    client.close();
  }
}

main();
