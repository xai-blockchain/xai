# Complete AI Task Workflow - From Proposal to Deployment

## Overview

This document shows the **complete lifecycle** of an AI development task:
1. Community member submits proposal
2. Security review (automated AI)
3. Community voting
4. Task queuing and prioritization
5. AI execution with donated API credits
6. Code review by community
7. Deployment to blockchain

---

## Timeline: Example Task

### **Day 0: Blockchain Launches**
```
✅ Genesis block mined
✅ Mining begins
✅ API key donations start accumulating
❌ Governance LOCKED for 90 days
```

### **Days 1-90: Accumulation Phase**
```
Community donates API credits:
- Day 10: 50 donations, 25M tokens total
- Day 30: 150 donations, 75M tokens total
- Day 60: 300 donations, 150M tokens total
- Day 90: 500 donations, 250M tokens total

Status: Credits safely stored, unused
```

### **Day 91: Governance Unlocks!**
```
✅ AI improvements now allowed
✅ Community can submit proposals
✅ 250M donated tokens ready for use
```

---

## Phase 1: Proposal Submission

### **Day 92: Developer Submits Proposal**

**Who:** Any community member with 100+ XAI balance

**Via:** Web interface or API

```python
from ai_governance_dao import AIGovernanceDAO, ProposalCategory

# Submit proposal
result = dao.submit_proposal(
    proposer_address="XAI7f3a9c2e1b8d4f6a5c9e2d1f8b4a7c3e9d2f1b",
    title="Add Cardano (ADA) Atomic Swap Support",
    category=ProposalCategory.ATOMIC_SWAP,

    description="""
    Enable trustless atomic swaps between XAI and Cardano (ADA).
    This will allow users to trade XAI/ADA directly without exchanges.
    """,

    detailed_prompt="""
    Implement HTLC atomic swap support for Cardano (ADA).

    Requirements:
    1. Write Plutus smart contract for HTLC on Cardano side
    2. Implement SPV client for Cardano blockchain verification
    3. Add Cardano to atomic_swap_manager.py with proper HTLC handling
    4. Create comprehensive test suite covering:
       - Successful swaps
       - Timeout scenarios
       - Refund paths
       - Edge cases
    5. Write integration documentation and examples
    6. Ensure security best practices (no fund loss scenarios)

    Expected deliverables:
    - cardano_htlc.plutus (Cardano smart contract)
    - cardano_spv_client.py (SPV verification)
    - atomic_swap_manager.py updates (integration code)
    - test_cardano_atomic_swaps.py (test suite)
    - CARDANO_ATOMIC_SWAPS.md (documentation)
    """,

    estimated_tokens=200000,  # 200k tokens (~$1.50 at Claude rates)
    best_ai_model="claude-opus-4",  # Most capable for complex work
    expected_outcome="Cardano atomic swaps fully functional on testnet and mainnet"
)
```

**Response:**
```json
{
    "success": true,
    "proposal_id": "prop_a7c3e9d2f1b",
    "status": "submitted",
    "message": "Proposal submitted, entering security review..."
}
```

---

## Phase 2: Automatic Security Review

### **Day 92 (30 seconds later): AI Security Analysis**

**Automated Process:**

```python
# AIGovernanceDAO automatically triggers security review
security_result = security_analyzer.analyze_proposal(proposal)

# Multi-layer analysis:
# 1. Keyword scan for malicious terms
# 2. AI intent analysis (Claude reviews the proposal)
# 3. Economic impact analysis
# 4. Code pattern analysis
# 5. Dependency analysis

# Result:
{
    'score': 92,  # Out of 100
    'passed': True,  # Need 80+ to pass
    'threats': [],  # No threats detected
    'warnings': [
        "Complex integration - thorough testing required"
    ],
    'recommendation': 'EXCELLENT - Highly recommended, minimal risk'
}
```

**Outcome:**
- ✅ Security score: 92/100 (passes 80 threshold)
- ✅ Status changed: `SUBMITTED` → `COMMUNITY_VOTE`
- ✅ Voting period opens: 14 days

---

## Phase 3: Community Voting

### **Days 92-106: Community Votes**

**Who Can Vote:** Anyone holding XAI tokens

**Vote Weight:** Based on XAI balance at snapshot block

```python
# Community member votes
vote_result = dao.vote_on_proposal(
    proposal_id="prop_a7c3e9d2f1b",
    voter_address="XAI4b8f2d9a6c3e1f7b4d9a2c8f1e6b3d7a9c2e",
    vote="for"  # or "against" or "abstain"
)

# Vote weight = XAI balance at snapshot
# This voter has 10,000 XAI = 10,000 vote weight
```

**Voting Progress:**
```
Day 93:  50 voters,  500,000 for, 50,000 against (91% approval)
Day 95:  120 voters, 1,200,000 for, 100,000 against (92% approval)
Day 100: 300 voters, 3,500,000 for, 300,000 against (92% approval)
Day 106: 450 voters, 5,200,000 for, 400,000 against (93% approval)

Final Result:
✅ Participation: 5.6M votes (5.6% of supply) > 10% quorum ❌
Wait... need more votes!

Day 107: Marketing campaign to get more voters
Day 110: 650 voters, 11,500,000 for, 500,000 against (96% approval)

Final Result:
✅ Participation: 12M votes (12% of supply) > 10% quorum ✓
✅ Approval: 96% > 66% threshold ✓
✅ Proposal APPROVED!
```

---

## Phase 4: Timelock Period

### **Day 111: Proposal Enters Timelock**

**Safety Mechanism:** 7-day delay before execution

```python
# Proposal moved to timelock queue
timelock_proposal = TimelockProposal(
    proposal_id="prop_a7c3e9d2f1b",
    proposal_type=ProposalType.AI_IMPROVEMENT,
    approval_time=time.time(),
    timelock_days=7,  # Standard for AI improvements
    execution_data={
        'ai_model': 'claude-opus-4',
        'estimated_tokens': 200000,
        'detailed_prompt': '...'
    }
)

# Can execute on Day 118 (7 days later)
```

**Purpose:**
- Gives community time to review decision
- Allows cancellation if issues discovered
- Standard in DeFi governance (Compound, Uniswap use this)

---

## Phase 5: Task Queuing & Prioritization

### **Day 118: Timelock Expires, Task Queued**

```python
# Automatically moved to execution queue
task = DevelopmentTask(
    task_type="atomic_swap",
    description="Add Cardano (ADA) atomic swap support",
    estimated_tokens=200000,
    priority=8  # 1-10, based on proposal category & votes
)

# Added to priority queue
pool.create_development_task(
    task_type=task.task_type,
    description=task.description,
    estimated_tokens=task.estimated_tokens,
    priority=task.priority
)

# Queue status:
{
    'queue_position': 3,  # 2 higher priority tasks ahead
    'total_queued': 15,
    'status': 'Waiting for execution'
}
```

**Priority Calculation:**
```python
priority = base_priority + vote_bonus + urgency_bonus

# Base priority by category:
SECURITY = 10  # Always highest
ATOMIC_SWAP = 8
PERFORMANCE = 7
FEATURES = 6
DOCUMENTATION = 4

# Vote bonus: +1 if >90% approval
# Urgency bonus: +1 if marked urgent

# Our task: 8 (atomic swap) + 1 (96% approval) = 9/10 priority
```

---

### Blockchain AI Bridge

The node spawns `core/blockchain_ai_bridge.py` to monitor DAO proposals. When a proposal enters the `FULLY_FUNDED` state, the bridge maps the proposal category to a `DevelopmentTask` type, calculates a 1‑10 priority, and queues it in `AIDevelopmentPool`. The bridge stores the resulting `task_id`, flips the proposal to `IN_PROGRESS`, and watches `completed_tasks` so it can bump the proposal into `CODE_REVIEW` once the AI output arrives.

Nodes run `_run_ai_bridge_loop()` in a daemon thread (every 30 seconds) so this wiring happens autonomously without manual intervention.

## Phase 6: AI Execution

### **Day 119: AI Begins Work**

**Automatic Process:**

```python
# Task processor runs continuously
while True:
    # Check for available tasks and credits
    if task_queue and has_available_credits():
        task = get_highest_priority_task()

        # Execute with auto-switching
        result = executor.execute_long_task_with_auto_switch(
            task_id=task.task_id,
            task_description=task.detailed_prompt,
            provider=AIProvider.ANTHROPIC,  # Uses Claude Opus
            max_total_tokens=task.estimated_tokens * 1.2,  # 20% buffer
            streaming=True  # Show progress in real-time
        )
```

**Execution Log:**
```
[Day 119 09:00] Task prop_a7c3e9d2f1b started
[Day 119 09:00] Selected AI: claude-opus-4
[Day 119 09:00] Estimated: 200,000 tokens
[Day 119 09:00] Found API key: key_a7f3 (500k tokens available)

[Day 119 09:01] Generating cardano_htlc.plutus...
[Day 119 09:15] ✅ Smart contract complete (42k tokens)

[Day 119 09:16] Generating cardano_spv_client.py...
[Day 119 09:45] ✅ SPV client complete (68k tokens)

[Day 119 09:46] Updating atomic_swap_manager.py...
[Day 119 10:30] ✅ Integration code complete (45k tokens)

[Day 119 10:31] Generating test_cardano_atomic_swaps.py...
[Day 119 11:00] ✅ Test suite complete (38k tokens)

[Day 119 11:01] Writing CARDANO_ATOMIC_SWAPS.md...
[Day 119 11:15] ✅ Documentation complete (12k tokens)

[Day 119 11:16] Task completed!
[Day 119 11:16] Total tokens used: 205,432
[Day 119 11:16] Keys used: 1 (key_a7f3)
[Day 119 11:16] Status: SUCCESS
```

**Files Generated:**
```
/tmp/ai_task_prop_a7c3e9d2f1b/
├── cardano_htlc.plutus           (Smart contract)
├── cardano_spv_client.py         (SPV client)
├── atomic_swap_manager.py.patch  (Integration updates)
├── test_cardano_atomic_swaps.py  (Tests)
└── CARDANO_ATOMIC_SWAPS.md       (Documentation)
```

---

## Phase 7: Code Review Period

### **Day 119: Community Code Review**

**Automatic Notification:**
```
📢 PROPOSAL prop_a7c3e9d2f1b COMPLETED!

Title: Add Cardano (ADA) Atomic Swap Support
AI Model: claude-opus-4
Tokens Used: 205,432
Files Generated: 5

Code review period: 7 days
Review the code: https://github.com/.../ai-output/prop_a7c3e9d2f1b
Vote to deploy: /api/proposals/prop_a7c3e9d2f1b/approve-implementation
```

**Code Review Process:**
```python
# Community reviews AI-generated code
# Must get 50% of original approvers to approve implementation

# Original approval voters: 650
# Need to approve implementation: 325 (50%)

Day 120: 50 implementation approvals
Day 122: 150 implementation approvals
Day 124: 280 implementation approvals
Day 126: 350 implementation approvals ✓

# Implementation approved!
```

**Review Checklist:**
```
✅ Code matches proposal requirements
✅ No security vulnerabilities introduced
✅ Tests cover edge cases
✅ Documentation is clear
✅ Integration doesn't break existing features
✅ Code quality meets standards
```

---

## Phase 8: Testnet Deployment

### **Day 127: Deploy to Testnet**

```python
# Automatically deploy to testnet
deploy_result = deploy_to_testnet(
    files=[
        'cardano_htlc.plutus',
        'cardano_spv_client.py',
        'atomic_swap_manager.py.patch',
        'test_cardano_atomic_swaps.py'
    ],
    proposal_id='prop_a7c3e9d2f1b'
)

# Run automated tests
test_result = run_testnet_tests('test_cardano_atomic_swaps.py')

# Results:
{
    'tests_run': 24,
    'passed': 24,
    'failed': 0,
    'coverage': 94.2,
    'status': 'ALL TESTS PASSED'
}
```

**Testnet Period:** 7-14 days
- Community tests functionality
- Bug reports collected
- Fixes applied if needed

---

## Monitoring & Tooling

Detailed guidance in docs/monitoring.md for metrics, Grafana/Grafana dashboards, alert rules, CLI tools, and CI integration steps.

The bridge exports Prometheus metrics and helper scripts, see below.
## Monitoring & Tooling

The node exposes `/ai/metrics`, `/ai/bridge/status`, and `/ai/bridge/tasks` so Prometheus (or any dashboard) can scrape event counters, completion totals, tokens consumed, and bridge sync timestamps. Metrics are instrumented as Prometheus counters/gauges and available at `/metrics`, so you can hook them into Grafana + alerting rules.

Developers can also run two CLI helpers: `python tools/ai_inspect.py --base-url http://localhost:8545` to dump bridge state/metrics, and `python tools/ai_alert.py --base-url http://localhost:8545 --token-threshold 50000` to alert via optional webhook when token usage spikes. These scripts make it easy to validate infrastructure before voting or releasing AI work.

The node exposes `/ai/metrics`, `/ai/bridge/status`, and `/ai/bridge/tasks` so dashboards can poll queue/bridge snapshots (tokens consumed, completions, sync time).
Run `python tools/ai_inspect.py --base-url http://localhost:8545` for CLI dumps and watch polling for dashboards.

## Phase 9: Mainnet Deployment


### **Day 141: Deploy to Mainnet**

**Final Approval Vote:**
```python
# One final vote after testnet success
final_vote = dao.vote_on_deployment(
    proposal_id='prop_a7c3e9d2f1b',
    deployment_target='mainnet'
)

# Results:
# 89% approval (lower threshold: 66%)
# ✅ APPROVED for mainnet
```

**Deployment:**
```python
# Deploy to mainnet
deploy_to_mainnet(
    proposal_id='prop_a7c3e9d2f1b',
    files=deployment_package
)

# Update blockchain state
blockchain.update_atomic_swap_support(
    add_currency='ADA',
    contract_address='cardano_mainnet_htlc_addr...'
)
```

**Announcement:**
```
🚀 CARDANO ATOMIC SWAPS NOW LIVE!

You can now trade XAI ↔ ADA trustlessly!
No exchanges needed. Pure P2P.

Developed by: AI (Claude Opus)
Funded by: Community donated API credits
Approved by: 650 XAI holders
Code reviewed: 350 community members
Total cost: 205,432 tokens (~$1.54 USD)

Try it: /atomic-swap create XAI ADA 100
```

---

## Complete Integration: How Components Work Together

### **System Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                    GOVERNANCE LAYER                          │
│  - Submit proposals (ai_governance_dao.py)                  │
│  - Security review (automated AI)                           │
│  - Community voting                                          │
│  - 3-month lockout enforced (governance_parameters.py)      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    TIMELOCK LAYER                            │
│  - 7-day safety delay                                       │
│  - Allow community to cancel if needed                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    TASK QUEUE                                │
│  - Priority queue (ai_development_pool.py)                  │
│  - Automatic scheduling                                      │
│  - Resource allocation                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    API KEY POOL                              │
│  - Donated credits (ai_pool_with_strict_limits.py)         │
│  - Secure storage (secure_api_key_manager.py)              │
│  - Strict limit enforcement                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    AI EXECUTOR                               │
│  - Task execution (auto_switching_ai_executor.py)          │
│  - Auto-switching between keys                              │
│  - Real-time monitoring                                      │
│  - Output generation                                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    CODE REVIEW                               │
│  - Community reviews output                                 │
│  - Vote to approve implementation                           │
│  - Security checks                                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT                                │
│  - Testnet deployment                                       │
│  - Testing period                                           │
│  - Mainnet deployment                                       │
│  - Live on blockchain                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Automated Task Processor

### **Background Service (Runs Continuously)**

```python
# This runs 24/7 on blockchain nodes
class AITaskProcessor:
    def __init__(self):
        self.dao = AIGovernanceDAO(blockchain)
        self.pool = StrictAIPoolManager(key_manager)
        self.executor = AutoSwitchingAIExecutor(pool, key_manager)

    def run_forever(self):
        """
        Continuously process approved tasks
        """
        while True:
            # 1. Check for timelock-expired proposals
            ready_proposals = self.dao.get_ready_for_execution()

            for proposal in ready_proposals:
                # 2. Convert to task
                task = self._proposal_to_task(proposal)

                # 3. Add to queue
                self.pool.create_development_task(
                    task_type=task.task_type,
                    description=task.description,
                    estimated_tokens=task.estimated_tokens,
                    priority=task.priority
                )

            # 4. Process highest priority task
            task = self._get_next_task()

            if task and self._has_sufficient_credits(task):
                # 5. Execute with AI
                result = self.executor.execute_long_task_with_auto_switch(
                    task_id=task.task_id,
                    task_description=task.detailed_prompt,
                    provider=self._select_best_provider(task),
                    max_total_tokens=task.estimated_tokens * 1.2
                )

                # 6. Save output
                self._save_task_output(task.task_id, result)

                # 7. Notify community
                self._notify_code_review_ready(task.task_id)

            # Wait before next iteration
            time.sleep(60)  # Check every minute
```

---

## API Endpoints for Task Management

### **Submit Proposal**
```http
POST /api/governance/proposals/submit

{
    "proposer_address": "XAI...",
    "title": "Add Cardano atomic swaps",
    "category": "atomic_swap",
    "description": "...",
    "detailed_prompt": "...",
    "estimated_tokens": 200000,
    "best_ai_model": "claude-opus-4"
}
```

### **Vote on Proposal**
```http
POST /api/governance/proposals/{proposal_id}/vote

{
    "voter_address": "XAI...",
    "vote": "for",  // "for", "against", "abstain"
    "signature": "..."
}
```

### **Get Proposal Status**
```http
GET /api/governance/proposals/{proposal_id}

Response:
{
    "proposal_id": "prop_a7c3e9d2f1b",
    "status": "community_vote",
    "votes_for": 11500000,
    "votes_against": 500000,
    "approval_percent": 96,
    "days_remaining": 3,
    "security_score": 92
}
```

### **Get Task Queue**
```http
GET /api/ai/task-queue

Response:
{
    "pending_tasks": [
        {
            "task_id": "task_001",
            "title": "Add Cardano atomic swaps",
            "priority": 9,
            "estimated_tokens": 200000,
            "position": 1
        },
        {
            "task_id": "task_002",
            "title": "Optimize block validation",
            "priority": 7,
            "estimated_tokens": 150000,
            "position": 2
        }
    ],
    "in_progress": {
        "task_id": "task_003",
        "title": "Security audit of wallet code",
        "progress_percent": 45,
        "tokens_used": 90000,
        "tokens_budget": 200000
    }
}
```

### **Get AI Pool Status**
```http
GET /api/ai/pool-status

Response:
{
    "total_tokens_available": 250000000,
    "total_tokens_used": 87000000,
    "active_tasks": 1,
    "completed_tasks": 47,
    "pending_review": 2,
    "deployed": 45
}
```

---

## Example: Multiple Tasks Running

### **Day 120: Busy Development Day**

```
Queue Status:
┌──────────────────────────────────────────────────────────┐
│ Priority 10: Security audit (IN PROGRESS)               │
│   Progress: 65% (130k / 200k tokens)                    │
│   ETA: 15 minutes                                        │
├──────────────────────────────────────────────────────────┤
│ Priority 9: Cardano atomic swaps (QUEUED)               │
│   Position: #1 in queue                                 │
│   Will start: When current task completes               │
├──────────────────────────────────────────────────────────┤
│ Priority 7: Performance optimization (QUEUED)           │
│   Position: #2 in queue                                 │
├──────────────────────────────────────────────────────────┤
│ Priority 6: Mobile wallet UI (CODE REVIEW)              │
│   Status: Awaiting community approval                   │
│   Reviews: 180/325 needed                               │
├──────────────────────────────────────────────────────────┤
│ Priority 4: API documentation (TESTNET)                 │
│   Status: Testing on testnet                            │
│   Days remaining: 5                                      │
└──────────────────────────────────────────────────────────┘

API Key Pool:
- Total: 250M tokens donated
- Used: 87M tokens
- Available: 163M tokens
- Active keys: 44
- Can process: ~815 more similar tasks
```

---

## Security & Safety

### **Built-in Safeguards**

1. **Governance Lockout** (Days 0-90)
   - No AI tasks allowed during initial phase
   - Prevents premature/rushed development
   - Community builds up donated credits

2. **Security Review** (Automated AI)
   - Every proposal scanned for malicious intent
   - Must score 80+ to proceed
   - Protects against harmful proposals

3. **Community Voting**
   - 10% quorum required
   - 66% approval needed
   - Democratic decision-making

4. **Timelock Period** (7 days)
   - Delay before execution
   - Allows cancellation if issues found
   - Standard safety mechanism

5. **Code Review** (Community)
   - Output reviewed before deployment
   - Must get 50% of approvers
   - Catch AI mistakes

6. **Testnet Testing** (7-14 days)
   - Test on testnet first
   - Community validates functionality
   - No mainnet risk

7. **API Key Limits** (Strict)
   - Each key has hard limit
   - Prevents over-usage
   - Automatic destruction when depleted

---

## Summary: Complete Workflow

```
Day 0:    Blockchain launches, governance LOCKED
Days 1-90: Community donates API credits (250M tokens accumulated)
Day 91:   Governance UNLOCKS
Day 92:   Developer submits proposal
Day 92:   AI security review (passes with 92/100)
Day 92:   Voting opens (14 days)
Day 106:  Voting closes (96% approval, 12% turnout) ✅
Day 111:  Timelock starts (7 days)
Day 118:  Timelock expires, task queued
Day 119:  AI begins work (Claude Opus)
Day 119:  Task completes (205k tokens, 5 files)
Day 119:  Code review period opens (7 days)
Day 126:  Code review approves (350/325 needed) ✅
Day 127:  Deploy to testnet
Days 127-141: Testnet testing (all tests pass)
Day 141:  Final vote (89% approval) ✅
Day 141:  Deploy to mainnet ✅
Day 141:  Feature LIVE! 🚀

Total time: 49 days from submission to deployment
Total cost: 205,432 tokens (~$1.54 USD)
Community involvement: 650 voters + 350 code reviewers
```

**Result:** Community-driven, AI-developed, democratically approved blockchain improvement deployed for ~$1.54!

---

## What You Have Now

✅ Complete governance system (voting, timelocks, security)
✅ Secure API key donation & storage system
✅ Strict usage limits per key
✅ Automatic task queuing & prioritization
✅ AI execution with auto-switching
✅ Code review process
✅ Testnet/mainnet deployment pipeline

**Status:** Fully integrated system ready for deployment! 🎉
