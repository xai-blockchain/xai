"""
XAI AI Development Governance DAO
Community-driven AI task proposal and voting system
"""

import time
import hashlib
import json
from enum import Enum
from typing import List, Dict, Optional
from cryptography.fernet import Fernet


class ProposalCategory(Enum):
    """Categories for AI development proposals"""

    ATOMIC_SWAP = "atomic_swap"  # New trading pair integrations
    SECURITY = "security"  # Security audits, pentests
    TRADING_FEATURES = "trading_features"  # DEX improvements
    MOBILE_APP = "mobile_app"  # Mobile features
    DESKTOP_MINER = "desktop_miner"  # Desktop app features
    BROWSER_EXTENSION = "browser_extension"  # Browser extension features
    COMMUNITY_SUPPORT = "community_support"  # Bots, moderation
    ANALYTICS = "analytics"  # Data analysis, insights
    MARKETING = "marketing"  # Content creation
    DEVELOPER_TOOLS = "developer_tools"  # SDKs, APIs
    EDUCATION = "education"  # Tutorials, docs
    RESEARCH = "research"  # Future tech research
    LOCALIZATION = "localization"  # Multi-language support
    COMPLIANCE = "compliance"  # Legal, regulatory
    INFRASTRUCTURE = "infrastructure"  # Core blockchain improvements
    PERFORMANCE = "performance"  # Optimization
    USER_EXPERIENCE = "user_experience"  # UI/UX improvements
    INTEGRATION = "integration"  # Third-party integrations
    GAMIFICATION = "gamification"  # Achievements, challenges
    OTHER = "other"  # Uncategorized


class ProposalStatus(Enum):
    """Lifecycle states of a proposal"""

    DRAFT = "draft"  # Being written
    SUBMITTED = "submitted"  # Awaiting security review
    SECURITY_REVIEW = "security_review"  # AI analyzing for threats
    COMMUNITY_VOTE = "community_vote"  # Open for voting
    THRESHOLD_25 = "threshold_25"  # 25% funded, re-vote triggered
    THRESHOLD_50 = "threshold_50"  # 50% funded, major checkpoint
    THRESHOLD_75 = "threshold_75"  # 75% funded, final go/no-go
    FULLY_FUNDED = "fully_funded"  # 100% funded, ready for execution
    IN_PROGRESS = "in_progress"  # AI is working on it
    CODE_REVIEW = "code_review"  # Human reviewing AI output
    TESTNET = "testnet"  # Testing on testnet
    DEPLOYED = "deployed"  # Live on mainnet
    REJECTED = "rejected"  # Failed security or vote
    CANCELLED = "cancelled"  # Proposer withdrew
    SUPERSEDED = "superseded"  # Replaced by better proposal


class SecurityThreat(Enum):
    """Potential security threats in proposals"""

    MALICIOUS_CODE = "malicious_code"  # Harmful code injection
    VALUE_DESTRUCTION = "value_destruction"  # Reduces coin value
    NETWORK_ATTACK = "network_attack"  # DDoS, spam, etc.
    CONSENSUS_BREAK = "consensus_break"  # Breaks blockchain consensus
    PRIVACY_VIOLATION = "privacy_violation"  # Exposes user data
    CENTRALIZATION = "centralization"  # Increases centralization
    INFLATION = "inflation"  # Increases supply unfairly
    FEE_MANIPULATION = "fee_manipulation"  # Manipulates fee structure
    ORACLE_MANIPULATION = "oracle_manipulation"  # Price oracle attacks
    GOVERNANCE_ATTACK = "governance_attack"  # Manipulates voting
    DEPENDENCY_RISK = "dependency_risk"  # Risky external dependencies
    ECONOMIC_ATTACK = "economic_attack"  # Harms tokenomics


class AITaskProposal:
    """Community-submitted AI development proposal"""

    def __init__(
        self,
        title: str,
        proposer_address: str,
        category: ProposalCategory,
        description: str,
        detailed_prompt: str,
        estimated_tokens: int,
        best_ai_model: str,
        expected_outcome: str,
    ):
        self.proposal_id = self._generate_id()
        self.title = title
        self.proposer_address = proposer_address
        self.category = category
        self.description = description  # User-friendly summary
        self.detailed_prompt = detailed_prompt  # Full AI instructions
        self.estimated_tokens = estimated_tokens
        self.best_ai_model = best_ai_model
        self.expected_outcome = expected_outcome

        # Lifecycle
        self.status = ProposalStatus.DRAFT
        self.submitted_at = None
        self.funded_amount = 0
        self.funding_goal = estimated_tokens

        # Security
        self.security_checks = []
        self.security_threats = []
        self.security_score = None  # 0-100, need 80+ to pass
        self.security_reviewed_by = None  # AI model that reviewed

        # Voting
        self.votes_for = 0
        self.votes_against = 0
        self.votes_abstain = 0
        self.voters = {}  # address -> vote weight
        self.quorum_required = 0.10  # 10% of token holders must vote

        # Funding milestones
        self.milestone_25_votes = None
        self.milestone_50_votes = None
        self.milestone_75_votes = None

        # Execution
        self.assigned_ai_model = None
        self.execution_started_at = None
        self.execution_completed_at = None
        self.result_hash = None

    def _generate_id(self):
        """Generate unique proposal ID"""
        data = f"{time.time()}{hash(self.title)}".encode()
        return hashlib.sha256(data).hexdigest()[:16]

    def to_dict(self):
        """Serialize for blockchain storage"""
        return {
            "proposal_id": self.proposal_id,
            "title": self.title,
            "proposer": self.proposer_address,
            "category": self.category.value,
            "description": self.description,
            "detailed_prompt": self.detailed_prompt,
            "estimated_tokens": self.estimated_tokens,
            "best_ai_model": self.best_ai_model,
            "expected_outcome": self.expected_outcome,
            "status": self.status.value,
            "submitted_at": self.submitted_at,
            "funded_amount": self.funded_amount,
            "funding_goal": self.funding_goal,
            "security_score": self.security_score,
            "security_threats": [t.value for t in self.security_threats],
            "votes_for": self.votes_for,
            "votes_against": self.votes_against,
            "votes_abstain": self.votes_abstain,
            "execution_started_at": self.execution_started_at,
            "execution_completed_at": self.execution_completed_at,
            "result_hash": self.result_hash,
        }


class ProposalSecurityAnalyzer:
    """AI-powered security analysis of proposals"""

    SECURITY_KEYWORDS = {
        SecurityThreat.MALICIOUS_CODE: [
            "eval(",
            "exec(",
            "system(",
            "subprocess",
            "rm -rf",
            "delete all",
            "__import__",
            "backdoor",
            "exploit",
            "payload",
        ],
        SecurityThreat.VALUE_DESTRUCTION: [
            "reduce supply",
            "destroy coins",
            "burn all",
            "zero balance",
            "delete wallets",
            "remove liquidity",
        ],
        SecurityThreat.INFLATION: [
            "mint unlimited",
            "create new coins",
            "bypass halving",
            "increase block reward",
            "remove supply cap",
        ],
        SecurityThreat.FEE_MANIPULATION: [
            "zero fees",
            "disable fees",
            "set fee to 0",
            "unlimited transactions free",
        ],
        SecurityThreat.CENTRALIZATION: [
            "single validator",
            "owner only",
            "admin control",
            "centralized server",
            "single point of failure",
        ],
        SecurityThreat.PRIVACY_VIOLATION: [
            "log user data",
            "track wallets",
            "expose private keys",
            "collect personal info",
            "KYC required",
        ],
    }

    def __init__(self, ai_model="claude-sonnet-4"):
        self.ai_model = ai_model
        self.fernet = Fernet(Fernet.generate_key())  # For API key encryption

    def analyze_proposal(self, proposal: AITaskProposal) -> Dict:
        """
        Multi-layer security analysis of proposal
        Returns security score and identified threats
        """
        threats = []
        warnings = []
        score = 100  # Start at perfect, deduct for issues

        # Layer 1: Keyword Analysis (Fast)
        keyword_threats = self._keyword_scan(proposal)
        threats.extend(keyword_threats)
        score -= len(keyword_threats) * 20  # -20 per threat

        # Layer 2: Intent Analysis (AI)
        intent_analysis = self._analyze_intent(proposal)
        if intent_analysis["suspicious"]:
            threats.extend(intent_analysis["threats"])
            score -= len(intent_analysis["threats"]) * 15

        # Layer 3: Economic Impact Analysis
        economic_risks = self._analyze_economics(proposal)
        if economic_risks["risky"]:
            warnings.extend(economic_risks["warnings"])
            score -= len(economic_risks["warnings"]) * 10

        # Layer 4: Code Pattern Analysis
        if "code" in proposal.detailed_prompt.lower():
            code_risks = self._analyze_code_patterns(proposal)
            threats.extend(code_risks)
            score -= len(code_risks) * 25

        # Layer 5: Dependency Analysis
        dependency_risks = self._analyze_dependencies(proposal)
        warnings.extend(dependency_risks)
        score -= len(dependency_risks) * 5

        # Ensure score is in valid range
        score = max(0, min(100, score))

        return {
            "score": score,
            "passed": score >= 80,  # Need 80+ to pass
            "threats": threats,
            "warnings": warnings,
            "recommendation": self._get_recommendation(score, threats),
            "reviewed_by": self.ai_model,
            "reviewed_at": time.time(),
        }

    def _keyword_scan(self, proposal: AITaskProposal) -> List[SecurityThreat]:
        """Fast keyword-based threat detection"""
        threats = []
        text = (
            proposal.title + " " + proposal.description + " " + proposal.detailed_prompt
        ).lower()

        for threat_type, keywords in self.SECURITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    threats.append(threat_type)
                    break  # One match per threat type is enough

        return threats

    def _analyze_intent(self, proposal: AITaskProposal) -> Dict:
        """
        AI-powered intent analysis
        In production, this would call Claude/GPT to analyze proposal intent
        """
        # Simulation - in production, call actual AI API
        prompt = f"""
        Analyze this blockchain development proposal for malicious intent:

        Title: {proposal.title}
        Description: {proposal.description}
        Category: {proposal.category.value}

        Question: Does this proposal appear to have malicious intent or could it
        harm the XAI blockchain, its users, or the value of XAI coin?

        Consider:
        - Does it try to steal funds?
        - Does it reduce coin value?
        - Does it centralize control?
        - Does it violate user privacy?
        - Does it break consensus rules?

        Respond with JSON:
        {{
            "suspicious": true/false,
            "threats": ["threat_type1", "threat_type2"],
            "reasoning": "explanation"
        }}
        """

        # Simulated AI response (replace with actual API call)
        # In production: result = call_ai_api(self.ai_model, prompt)
        result = {"suspicious": False, "threats": [], "reasoning": "Proposal appears legitimate"}

        return result

    def _analyze_economics(self, proposal: AITaskProposal) -> Dict:
        """Analyze economic impact on XAI value"""
        risks = []

        # Check if proposal affects tokenomics
        risky_terms = [
            "change block reward",
            "modify halving",
            "alter supply",
            "reduce fees to zero",
            "remove fee cap",
            "unlimited minting",
        ]

        text = (proposal.description + " " + proposal.detailed_prompt).lower()

        for term in risky_terms:
            if term in text:
                risks.append(f"Economic risk: mentions '{term}'")

        # Check if proposal is too expensive
        if proposal.estimated_tokens > 5000000:  # 5M tokens = ~$45
            risks.append("Very expensive proposal - review cost/benefit carefully")

        return {"risky": len(risks) > 0, "warnings": risks}

    def _analyze_code_patterns(self, proposal: AITaskProposal) -> List[SecurityThreat]:
        """Detect risky code patterns in proposal"""
        threats = []
        text = proposal.detailed_prompt.lower()

        # Dangerous code patterns
        if "execute shell" in text or "run command" in text:
            threats.append(SecurityThreat.MALICIOUS_CODE)

        if "modify consensus" in text or "change validation" in text:
            threats.append(SecurityThreat.CONSENSUS_BREAK)

        if "external api" in text and "no verification" in text:
            threats.append(SecurityThreat.ORACLE_MANIPULATION)

        return threats

    def _analyze_dependencies(self, proposal: AITaskProposal) -> List[str]:
        """Check for risky dependencies"""
        warnings = []
        text = proposal.detailed_prompt.lower()

        risky_deps = [
            "untrusted package",
            "unaudited library",
            "beta version",
            "experimental feature",
            "deprecated module",
        ]

        for dep in risky_deps:
            if dep in text:
                warnings.append(f"Dependency warning: {dep}")

        return warnings

    def _get_recommendation(self, score: int, threats: List) -> str:
        """Get human-readable recommendation"""
        if score >= 95:
            return "EXCELLENT - Highly recommended, minimal risk"
        elif score >= 80:
            return "GOOD - Recommended with minor review"
        elif score >= 60:
            return "MODERATE - Significant review required"
        elif score >= 40:
            return "RISKY - Major concerns, needs revision"
        else:
            return "DANGEROUS - Reject or major overhaul needed"


class AIGovernanceDAO:
    """Main governance system for AI development"""

    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.proposals = {}  # proposal_id -> AITaskProposal
        self.security_analyzer = ProposalSecurityAnalyzer()

        # Voting power calculation
        self.snapshot_height = None  # Block height for vote weight snapshot

        # Governance parameters (can be adjusted by meta-proposals)
        self.min_proposal_stake = 100  # Minimum XAI to submit proposal
        self.security_threshold = 80  # Minimum security score
        self.vote_quorum = 0.10  # 10% participation required
        self.approval_threshold = 0.66  # 66% approval needed

        # Funding milestone thresholds
        self.milestones = [0.25, 0.50, 0.75, 1.0]

    def submit_proposal(
        self,
        proposer_address: str,
        title: str,
        category: ProposalCategory,
        description: str,
        detailed_prompt: str,
        estimated_tokens: int,
        best_ai_model: str,
        expected_outcome: str,
    ) -> Dict:
        """
        Submit new AI task proposal
        Returns proposal_id if successful
        """
        # Verify proposer has minimum stake
        balance = self.blockchain.get_balance(proposer_address)
        if balance < self.min_proposal_stake:
            return {
                "success": False,
                "error": f"Insufficient stake. Need {self.min_proposal_stake} XAI, have {balance}",
            }

        # Create proposal
        proposal = AITaskProposal(
            title=title,
            proposer_address=proposer_address,
            category=category,
            description=description,
            detailed_prompt=detailed_prompt,
            estimated_tokens=estimated_tokens,
            best_ai_model=best_ai_model,
            expected_outcome=expected_outcome,
        )

        proposal.status = ProposalStatus.SUBMITTED
        proposal.submitted_at = time.time()

        # Automatic security analysis
        security_result = self.security_analyzer.analyze_proposal(proposal)

        proposal.security_score = security_result["score"]
        proposal.security_threats = security_result["threats"]
        proposal.security_reviewed_by = security_result["reviewed_by"]

        # Auto-reject if security score too low
        if security_result["score"] < self.security_threshold:
            proposal.status = ProposalStatus.REJECTED
            self.proposals[proposal.proposal_id] = proposal

            return {
                "success": False,
                "proposal_id": proposal.proposal_id,
                "error": "Failed security review",
                "security_score": security_result["score"],
                "threats": security_result["threats"],
                "recommendation": security_result["recommendation"],
            }

        # Passed security - open for voting
        proposal.status = ProposalStatus.COMMUNITY_VOTE
        self.proposals[proposal.proposal_id] = proposal

        # Take snapshot of voting power
        self.snapshot_height = self.blockchain.get_height()

        # Store on blockchain
        self._store_proposal_on_chain(proposal)

        return {
            "success": True,
            "proposal_id": proposal.proposal_id,
            "status": proposal.status.value,
            "security_score": security_result["score"],
            "voting_opens": time.time(),
            "voting_closes": time.time() + (7 * 86400),  # 7 days
            "message": "Proposal submitted and passed security review. Now open for community voting.",
        }

    def vote_on_proposal(
        self, proposal_id: str, voter_address: str, vote: str  # 'for', 'against', 'abstain'
    ) -> Dict:
        """
        Cast vote on proposal
        Vote weight = XAI balance at snapshot height
        """
        if proposal_id not in self.proposals:
            return {"success": False, "error": "Proposal not found"}

        proposal = self.proposals[proposal_id]

        # Check if proposal is in voting state
        if proposal.status not in [
            ProposalStatus.COMMUNITY_VOTE,
            ProposalStatus.THRESHOLD_25,
            ProposalStatus.THRESHOLD_50,
            ProposalStatus.THRESHOLD_75,
        ]:
            return {
                "success": False,
                "error": f"Proposal not open for voting (status: {proposal.status.value})",
            }

        # Get voter's balance at snapshot
        vote_weight = self.blockchain.get_balance_at_height(voter_address, self.snapshot_height)

        if vote_weight == 0:
            return {"success": False, "error": "No voting power (zero balance at snapshot)"}

        # Check if already voted
        if voter_address in proposal.voters:
            # Allow vote changes
            old_vote = proposal.voters[voter_address]["vote"]
            old_weight = proposal.voters[voter_address]["weight"]

            # Remove old vote
            if old_vote == "for":
                proposal.votes_for -= old_weight
            elif old_vote == "against":
                proposal.votes_against -= old_weight
            elif old_vote == "abstain":
                proposal.votes_abstain -= old_weight

        # Record new vote
        proposal.voters[voter_address] = {
            "vote": vote,
            "weight": vote_weight,
            "timestamp": time.time(),
        }

        # Update totals
        if vote == "for":
            proposal.votes_for += vote_weight
        elif vote == "against":
            proposal.votes_against += vote_weight
        elif vote == "abstain":
            proposal.votes_abstain += vote_weight

        # Store vote on blockchain
        self._store_vote_on_chain(proposal_id, voter_address, vote, vote_weight)

        # Check if funding milestone reached
        self._check_funding_milestones(proposal)

        return {
            "success": True,
            "vote_recorded": vote,
            "vote_weight": vote_weight,
            "current_tally": {
                "for": proposal.votes_for,
                "against": proposal.votes_against,
                "abstain": proposal.votes_abstain,
            },
        }

    def donate_to_proposal(
        self,
        proposal_id: str,
        donor_address: str,
        ai_model: str,
        api_key_encrypted: str,
        token_amount: int,
    ) -> Dict:
        """
        Donate AI tokens to fund proposal
        Triggers milestone votes when thresholds reached
        """
        if proposal_id not in self.proposals:
            return {"success": False, "error": "Proposal not found"}

        proposal = self.proposals[proposal_id]

        # Check if proposal is approved for funding
        if proposal.status == ProposalStatus.REJECTED:
            return {"success": False, "error": "Proposal was rejected"}

        if proposal.status == ProposalStatus.CANCELLED:
            return {"success": False, "error": "Proposal was cancelled"}

        # Record donation
        proposal.funded_amount += token_amount

        # Calculate funding percentage
        funding_pct = proposal.funded_amount / proposal.funding_goal

        # Check for milestone triggers
        if funding_pct >= 0.25 and proposal.status == ProposalStatus.COMMUNITY_VOTE:
            # 25% milestone - trigger re-vote
            proposal.status = ProposalStatus.THRESHOLD_25
            self._trigger_milestone_vote(proposal, 0.25)

        elif funding_pct >= 0.50 and proposal.status == ProposalStatus.THRESHOLD_25:
            # 50% milestone - major checkpoint
            proposal.status = ProposalStatus.THRESHOLD_50
            self._trigger_milestone_vote(proposal, 0.50)

        elif funding_pct >= 0.75 and proposal.status == ProposalStatus.THRESHOLD_50:
            # 75% milestone - final go/no-go
            proposal.status = ProposalStatus.THRESHOLD_75
            self._trigger_milestone_vote(proposal, 0.75)

        elif funding_pct >= 1.0 and proposal.status == ProposalStatus.THRESHOLD_75:
            # Fully funded - check final approval
            if self._check_final_approval(proposal):
                proposal.status = ProposalStatus.FULLY_FUNDED
                # Queue for AI execution
                self._queue_for_execution(proposal)
            else:
                # Funding reached but community voted against
                proposal.status = ProposalStatus.REJECTED
                # Refund donors
                self._refund_donors(proposal)

        return {
            "success": True,
            "funded_amount": proposal.funded_amount,
            "funding_goal": proposal.funding_goal,
            "funding_percentage": funding_pct * 100,
            "milestone_triggered": (
                proposal.status.value if "THRESHOLD" in proposal.status.value else None
            ),
        }

    def _check_funding_milestones(self, proposal: AITaskProposal):
        """Check if funding reached new milestone"""
        funding_pct = proposal.funded_amount / proposal.funding_goal

        for threshold in self.milestones:
            if funding_pct >= threshold:
                # Milestone reached - trigger community checkpoint vote
                self._trigger_milestone_vote(proposal, threshold)

    def _trigger_milestone_vote(self, proposal: AITaskProposal, threshold: float):
        """
        Trigger community vote at funding milestone
        Allows community to cancel if priorities changed
        """
        # Reset votes for this milestone
        milestone_key = f"milestone_{int(threshold * 100)}_votes"

        # Notify community
        notification = {
            "type": "milestone_vote",
            "proposal_id": proposal.proposal_id,
            "threshold": threshold,
            "message": f"Proposal '{proposal.title}' reached {threshold * 100}% funding. "
            f"Community vote: Should we continue funding this proposal?",
            "voting_period": 48 * 3600,  # 48 hours to vote
            "options": ["continue", "cancel", "defer"],
        }

        # Store notification on blockchain
        self._send_milestone_notification(notification)

    def _check_final_approval(self, proposal: AITaskProposal) -> bool:
        """Check if proposal has community approval at 100% funding"""
        total_votes = proposal.votes_for + proposal.votes_against + proposal.votes_abstain
        total_supply = self.blockchain.get_total_circulating_supply()

        # Check quorum
        participation = total_votes / total_supply
        if participation < self.vote_quorum:
            # Insufficient participation
            return False

        # Check approval threshold
        approval_rate = proposal.votes_for / (proposal.votes_for + proposal.votes_against)
        if approval_rate < self.approval_threshold:
            # Insufficient approval
            return False

        return True

    def _queue_for_execution(self, proposal: AITaskProposal):
        """Add fully-funded proposal to AI execution queue"""
        proposal.status = ProposalStatus.FULLY_FUNDED

        # This integrates with existing ai_development_pool.py
        # execution queue

    def _refund_donors(self, proposal: AITaskProposal):
        """Refund AI tokens if proposal cancelled after funding"""
        # Implementation would refund encrypted API keys back to donors
        pass

    def _store_proposal_on_chain(self, proposal: AITaskProposal):
        """Store proposal in blockchain"""
        tx = {
            "tx_type": "ai_proposal_submit",
            "proposal": proposal.to_dict(),
            "timestamp": time.time(),
        }
        # Add to blockchain
        # self.blockchain.add_transaction(tx)

    def _store_vote_on_chain(self, proposal_id: str, voter: str, vote: str, weight: float):
        """Store vote in blockchain"""
        tx = {
            "tx_type": "ai_proposal_vote",
            "proposal_id": proposal_id,
            "voter": voter,
            "vote": vote,
            "weight": weight,
            "timestamp": time.time(),
        }
        # Add to blockchain
        # self.blockchain.add_transaction(tx)

    def _send_milestone_notification(self, notification: Dict):
        """Send notification to community about milestone"""
        # Implementation would notify community
        pass

    def get_proposal(self, proposal_id: str) -> Optional[Dict]:
        """Get proposal details"""
        if proposal_id in self.proposals:
            return self.proposals[proposal_id].to_dict()
        return None

    def list_proposals(
        self,
        status: Optional[ProposalStatus] = None,
        category: Optional[ProposalCategory] = None,
        sort_by: str = "created",
    ) -> List[Dict]:
        """
        List proposals with optional filters
        """
        proposals = list(self.proposals.values())

        # Filter by status
        if status:
            proposals = [p for p in proposals if p.status == status]

        # Filter by category
        if category:
            proposals = [p for p in proposals if p.category == category]

        # Sort
        if sort_by == "created":
            proposals.sort(key=lambda p: p.submitted_at or 0, reverse=True)
        elif sort_by == "votes":
            proposals.sort(key=lambda p: p.votes_for, reverse=True)
        elif sort_by == "funding":
            proposals.sort(key=lambda p: p.funded_amount / p.funding_goal, reverse=True)

        return [p.to_dict() for p in proposals]

    def get_active_votes(self) -> List[Dict]:
        """Get all proposals currently open for voting"""
        active = [
            p
            for p in self.proposals.values()
            if p.status
            in [
                ProposalStatus.COMMUNITY_VOTE,
                ProposalStatus.THRESHOLD_25,
                ProposalStatus.THRESHOLD_50,
                ProposalStatus.THRESHOLD_75,
            ]
        ]

        return [p.to_dict() for p in active]

    def get_user_voting_power(self, address: str) -> float:
        """Get user's voting power (balance at snapshot)"""
        if self.snapshot_height is None:
            return self.blockchain.get_balance(address)
        return self.blockchain.get_balance_at_height(address, self.snapshot_height)


# Example usage
if __name__ == "__main__":
    # Simulated blockchain
    class MockBlockchain:
        def get_balance(self, address):
            return 1000  # 1000 XAI

        def get_height(self):
            return 150000

        def get_balance_at_height(self, address, height):
            return 1000

        def get_total_circulating_supply(self):
            return 100000000  # 100M XAI

    blockchain = MockBlockchain()
    dao = AIGovernanceDAO(blockchain)

    # Submit proposal
    result = dao.submit_proposal(
        proposer_address="XAI7f3a9c2e1b8d4f6a5c9e2d1f8b4a7c3e9d2f1b",
        title="Add Cardano (ADA) Atomic Swap Support",
        category=ProposalCategory.ATOMIC_SWAP,
        description="Implement HTLC atomic swap support for Cardano",
        detailed_prompt="""
        Implement HTLC atomic swap support for Cardano (ADA).

        Requirements:
        - Write Plutus smart contract for HTLC
        - Implement SPV client for Cardano blockchain
        - Add Cardano to atomic_swap_manager.py
        - Create comprehensive test suite
        - Write integration documentation
        """,
        estimated_tokens=200000,
        best_ai_model="claude-opus-4",
        expected_outcome="Cardano atomic swaps fully functional on mainnet",
    )

    print(json.dumps(result, indent=2))

    if result["success"]:
        # Vote on proposal
        vote_result = dao.vote_on_proposal(
            proposal_id=result["proposal_id"],
            voter_address="XAI7f3a9c2e1b8d4f6a5c9e2d1f8b4a7c3e9d2f1b",
            vote="for",
        )
        print(json.dumps(vote_result, indent=2))
