"""Blockchain ↔ AI bridge implementation."""

import hashlib
import logging
import os
import sys
import time
from typing import Dict, List, Optional, Set

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_BLOCKCHAIN_DIR = os.path.join(ROOT_DIR, 'aixn-blockchain')
if AI_BLOCKCHAIN_DIR not in sys.path:
    sys.path.insert(0, AI_BLOCKCHAIN_DIR)

from ai_development_pool import AIDevelopmentPool
from ai_metrics import metrics

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class BlockchainAIBridge:
    """Glue between funded governance proposals and the AI development pool."""

    TASK_TYPE_MAP = {
        'atomic_swap': 'code_generation',
        'security': 'security_audit',
        'trading_features': 'code_generation',
        'mobile_app': 'code_generation',
        'browser_extension': 'code_generation',
        'community_support': 'documentation',
        'analytics': 'documentation',
        'marketing': 'documentation',
        'developer_tools': 'code_generation',
        'education': 'documentation',
        'research': 'code_generation',
        'localization': 'code_generation',
        'compliance': 'security_audit',
        'infrastructure': 'code_generation',
        'performance': 'optimization',
        'user_experience': 'code_generation',
        'integration': 'code_generation',
        'gamification': 'documentation',
        'other': 'code_generation'
    }

    PRIORITY_MAP = {
        'security': 9,
        'compliance': 9,
        'infrastructure': 8,
        'performance': 8,
        'atomic_swap': 7,
        'trading_features': 7,
        'integration': 7,
        'research': 6,
        'developer_tools': 6,
        'mobile_app': 5,
        'browser_extension': 5,
        'community_support': 4,
        'marketing': 4,
        'analytics': 4,
        'education': 3,
        'localization': 3,
        'gamification': 2,
        'other': 1
    }

    def __init__(
        self,
        blockchain,
        governance_dao,
        development_pool: Optional[AIDevelopmentPool] = None
    ):
        """Initialize bridge with blockchain, DAO, and AI pool."""
        self.blockchain = blockchain
        self.governance_dao = governance_dao
        self.development_pool = development_pool or AIDevelopmentPool()
        self.proposal_task_map: Dict[str, str] = {}
        self.queued_proposals: Set[str] = set()

    def sync_full_proposals(self) -> List[Dict[str, Optional[str]]]:
        """Queue fully funded proposals and update completed statuses."""
        created_tasks = []
        self._update_completed_proposals()
        metrics.record_bridge_sync()

        for proposal in self.governance_dao.proposals.values():
            if not self._should_queue_proposal(proposal):
                continue

            result = self._queue_proposal(proposal)
            created_tasks.append(result)

        return created_tasks

    def _should_queue_proposal(self, proposal) -> bool:
        status = getattr(proposal, 'status', None)
        if status is None:
            return False

        status_name = getattr(status, 'name', '').lower()
        if status_name != 'fully_funded':
            return False

        return proposal.proposal_id not in self.proposal_task_map

    def _queue_proposal(self, proposal) -> Dict[str, Optional[str]]:
        category = getattr(proposal.category, 'value', 'other')
        task_type = self.TASK_TYPE_MAP.get(category, 'code_generation')
        priority = self.PRIORITY_MAP.get(category, 5)
        description = proposal.detailed_prompt or proposal.description

        result = self.development_pool.create_development_task(
            task_type=task_type,
            description=description,
            estimated_tokens=proposal.estimated_tokens,
            priority=priority
        )

        task_id = result.get('task_id')

        if task_id:
            self.proposal_task_map[proposal.proposal_id] = task_id
            self.queued_proposals.add(proposal.proposal_id)
            proposal.status = proposal.status.__class__.IN_PROGRESS
            proposal.execution_started_at = time.time()
            proposal.assigned_ai_model = proposal.best_ai_model
            logger.info(
                "Queued AI proposal %s as task %s (model %s)",
                proposal.proposal_id,
                task_id,
                proposal.best_ai_model
            )
            metrics.record_queue_event()
        else:
            logger.warning(
                "Failed to queue AI proposal %s (status %s)",
                proposal.proposal_id,
                proposal.status
            )

        return {
            'proposal_id': proposal.proposal_id,
            'queued': bool(task_id),
            'task_id': task_id
        }

    def _update_completed_proposals(self):
        completed_ids = {
            task.task_id for task in self.development_pool.completed_tasks
        }

        for proposal_id, task_id in list(self.proposal_task_map.items()):
            if task_id not in completed_ids:
                continue

            proposal = self.governance_dao.proposals.get(proposal_id)
            if not proposal:
                continue

            proposal.status = proposal.status.__class__.CODE_REVIEW
            proposal.execution_completed_at = time.time()
            task = next(
                (t for t in self.development_pool.completed_tasks if t.task_id == task_id),
                None
            )

            if task and task.result and isinstance(task.result, dict):
                output = task.result.get('output') or ''
                if output:
                    proposal.result_hash = hashlib.sha256(output.encode()).hexdigest()

            metrics.record_completed_task()
            self.queued_proposals.discard(proposal_id)
            del self.proposal_task_map[proposal_id]
            logger.info("AI task %s completed for proposal %s", task_id, proposal_id)
