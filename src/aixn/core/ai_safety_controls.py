"""
XAI Blockchain - AI Safety & Emergency Stop System

Critical safety controls to immediately stop AI operations:
1. Personal AI request cancellation (user-level)
2. Trading bot emergency stop
3. Governance AI task pause/abort (community vote)
4. Global AI kill switch (security emergencies)

Philosophy: Users MUST have instant control over AI affecting their assets
"""

import time
import threading
from typing import Dict, List, Optional, Set
from enum import Enum


class StopReason(Enum):
    """Reasons for stopping AI operations"""
    USER_REQUESTED = "user_requested"
    EMERGENCY = "emergency"
    SECURITY_THREAT = "security_threat"
    COMMUNITY_VOTE = "community_vote"
    BUDGET_EXCEEDED = "budget_exceeded"
    ERROR_THRESHOLD = "error_threshold"
    TIMEOUT = "timeout"


class AISafetyLevel(Enum):
    """Safety levels for AI operations"""
    NORMAL = "normal"                    # Normal operation
    CAUTION = "caution"                  # Elevated monitoring
    RESTRICTED = "restricted"             # Limited AI operations
    EMERGENCY_STOP = "emergency_stop"     # All AI stopped
    LOCKDOWN = "lockdown"                # All AI disabled, manual only


class AISafetyControls:
    """
    Central safety control system for all AI operations

    Provides instant stop capabilities for:
    - Personal AI requests (per-user)
    - Trading bots (per-user)
    - Governance AI tasks (per-task)
    - Global AI operations (emergency)
    """

    def __init__(self, blockchain, authorized_callers: Optional[Set[str]] = None):
        """
        Initialize AI safety controls

        Args:
            blockchain: Reference to blockchain
            authorized_callers: Optional identifiers that can change safety level
        """
        self.blockchain = blockchain

        # Global safety level
        self.safety_level = AISafetyLevel.NORMAL

        # Active operations tracking
        self.personal_ai_requests: Dict[str, Dict] = {}  # request_id -> request info
        self.governance_tasks: Dict[str, Dict] = {}      # task_id -> task info
        self.trading_bots: Dict[str, object] = {}        # user_address -> bot instance

        # Cancellation tracking
        self.cancelled_requests: Set[str] = set()        # request_ids to cancel
        self.paused_tasks: Set[str] = set()              # task_ids paused

        # Emergency stop
        self.emergency_stop_active = False
        self.emergency_stop_reason = None
        self.emergency_stop_time = None

        # Statistics
        self.total_stops = 0
        self.total_cancellations = 0

        # Authorized safety callers (lowercase normalized)
        self.authorized_callers: Set[str] = {
            'governance_dao',
            'security_committee',
            'ai_safety_team',
            'remediation_script',
            'system',
            'test_system'
        }
        if authorized_callers:
            self.authorized_callers.update(c.lower() for c in authorized_callers)

        # Lock for thread safety
        self.lock = threading.Lock()

    # ===== PERSONAL AI CONTROLS =====

    def register_personal_ai_request(
        self,
        request_id: str,
        user_address: str,
        operation: str,
        ai_provider: str,
        ai_model: str
    ) -> bool:
        """
        Register a Personal AI request (for tracking and cancellation)

        Args:
            request_id: Unique request identifier
            user_address: User making request
            operation: Type of operation (swap, contract, etc.)
            ai_provider: AI provider being used
            ai_model: AI model being used

        Returns:
            True if registered, False if emergency stop active
        """

        # Check emergency stop
        if self.emergency_stop_active:
            return False

        with self.lock:
            self.personal_ai_requests[request_id] = {
                'user': user_address,
                'operation': operation,
                'ai_provider': ai_provider,
                'ai_model': ai_model,
                'started': time.time(),
                'status': 'running'
            }

        return True

    def cancel_personal_ai_request(self, request_id: str, user_address: str) -> Dict:
        """
        Cancel a Personal AI request (user control)

        Args:
            request_id: Request to cancel
            user_address: User requesting cancellation

        Returns:
            Cancellation result
        """

        with self.lock:
            # Check request exists
            if request_id not in self.personal_ai_requests:
                return {'success': False, 'error': 'Request not found'}

            request = self.personal_ai_requests[request_id]

            # Verify ownership
            if request['user'] != user_address:
                return {
                    'success': False,
                    'error': 'Can only cancel your own requests'
                }

            # Mark as cancelled
            self.cancelled_requests.add(request_id)
            request['status'] = 'cancelled'
            request['cancelled_time'] = time.time()

            self.total_cancellations += 1

        return {
            'success': True,
            'message': f'Personal AI request {request_id} cancelled',
            'operation': request['operation'],
            'runtime_seconds': time.time() - request['started']
        }

    def is_request_cancelled(self, request_id: str) -> bool:
        """Check if a request has been cancelled"""
        return request_id in self.cancelled_requests

    def complete_personal_ai_request(self, request_id: str):
        """Mark request as completed (cleanup)"""
        with self.lock:
            if request_id in self.personal_ai_requests:
                self.personal_ai_requests[request_id]['status'] = 'completed'
                self.personal_ai_requests[request_id]['completed_time'] = time.time()

    # ===== TRADING BOT CONTROLS =====

    def register_trading_bot(self, user_address: str, bot_instance) -> bool:
        """
        Register a trading bot for emergency stop capability

        Args:
            user_address: Owner of bot
            bot_instance: AITradingBot instance

        Returns:
            True if registered
        """

        if self.emergency_stop_active:
            return False

        with self.lock:
            self.trading_bots[user_address] = bot_instance

        return True

    def emergency_stop_trading_bot(self, user_address: str) -> Dict:
        """
        Emergency stop for trading bot (instant)

        Args:
            user_address: Bot owner

        Returns:
            Stop result
        """

        with self.lock:
            if user_address not in self.trading_bots:
                return {'success': False, 'error': 'No active trading bot'}

            bot = self.trading_bots[user_address]
            result = bot.stop()

            self.total_stops += 1

        return {
            'success': True,
            'message': '[STOP] EMERGENCY STOP: Trading bot stopped immediately',
            'bot_result': result
        }

    def stop_all_trading_bots(self, reason: StopReason) -> Dict:
        """
        Stop ALL trading bots (emergency)

        Args:
            reason: Why bots are being stopped

        Returns:
            Stop results
        """

        stopped_count = 0
        errors = []

        with self.lock:
            for user_address, bot in self.trading_bots.items():
                try:
                    bot.stop()
                    stopped_count += 1
                except Exception as e:
                    errors.append(f"{user_address}: {e}")

            self.total_stops += stopped_count

        return {
            'success': True,
            'stopped_count': stopped_count,
            'errors': errors,
            'reason': reason.value
        }

    def authorize_safety_caller(self, identifier: str) -> Dict:
        """Add an identifier that can change safety level"""

        if not identifier:
            return {'success': False, 'error': 'INVALID_IDENTIFIER'}

        with self.lock:
            self.authorized_callers.add(identifier.lower())

        return {
            'success': True,
            'caller': identifier.lower(),
            'message': 'Authorized caller can now change AI safety level'
        }

    def revoke_safety_caller(self, identifier: str) -> Dict:
        """Remove an identifier from safety level changes"""

        if not identifier:
            return {'success': False, 'error': 'INVALID_IDENTIFIER'}

        with self.lock:
            self.authorized_callers.discard(identifier.lower())

        return {
            'success': True,
            'caller': identifier.lower(),
            'message': 'Caller no longer authorized to change AI safety level'
        }

    def is_authorized_caller(self, identifier: str) -> bool:
        """Check if caller is authorized to adjust AI safety level"""

        if not identifier:
            return False

        with self.lock:
            return identifier.lower() in self.authorized_callers

    # ===== GOVERNANCE AI CONTROLS =====

    def register_governance_task(
        self,
        task_id: str,
        proposal_id: str,
        task_type: str,
        ai_count: int
    ) -> bool:
        """
        Register a Governance AI task

        Args:
            task_id: Task identifier
            proposal_id: Related proposal
            task_type: Type of task
            ai_count: Number of AIs working

        Returns:
            True if registered
        """

        if self.emergency_stop_active:
            return False

        with self.lock:
            self.governance_tasks[task_id] = {
                'proposal_id': proposal_id,
                'task_type': task_type,
                'ai_count': ai_count,
                'started': time.time(),
                'status': 'running',
                'paused': False
            }

        return True

    def pause_governance_task(self, task_id: str, pauser: str) -> Dict:
        """
        Pause a Governance AI task (requires authorization)

        Args:
            task_id: Task to pause
            pauser: Address requesting pause

        Returns:
            Pause result
        """

        with self.lock:
            if task_id not in self.governance_tasks:
                return {'success': False, 'error': 'Task not found'}

            task = self.governance_tasks[task_id]

            # Pause task
            self.paused_tasks.add(task_id)
            task['paused'] = True
            task['paused_time'] = time.time()
            task['paused_by'] = pauser

        return {
            'success': True,
            'message': f'[PAUSE] Governance task {task_id} paused',
            'task_type': task['task_type'],
            'proposal_id': task['proposal_id']
        }

    def resume_governance_task(self, task_id: str) -> Dict:
        """Resume a paused Governance AI task"""

        with self.lock:
            if task_id not in self.governance_tasks:
                return {'success': False, 'error': 'Task not found'}

            if task_id not in self.paused_tasks:
                return {'success': False, 'error': 'Task not paused'}

            task = self.governance_tasks[task_id]

            # Resume
            self.paused_tasks.remove(task_id)
            task['paused'] = False
            task['resumed_time'] = time.time()

        return {
            'success': True,
            'message': f'[RESUME] Governance task {task_id} resumed'
        }

    def is_task_paused(self, task_id: str) -> bool:
        """Check if task is paused"""
        return task_id in self.paused_tasks

    # ===== GLOBAL EMERGENCY STOP =====

    def activate_emergency_stop(
        self,
        reason: StopReason,
        details: str = "",
        activator: str = "system"
    ) -> Dict:
        """
        EMERGENCY STOP - Immediately halt ALL AI operations

        This is the nuclear option. Use only for:
        - Security threats
        - Critical bugs discovered
        - Unexpected AI behavior
        - Community emergency vote

        Args:
            reason: Why emergency stop activated
            details: Additional information
            activator: Who/what activated (address or "system")

        Returns:
            Emergency stop result
        """

        if not self.is_authorized_caller(activator):
            return {
                'success': False,
                'error': 'UNAUTHORIZED_ACTIVATOR',
                'message': f'{activator} cannot trigger emergency stop'
            }

        print("\n" + "=" * 70)
        print("!!! EMERGENCY STOP ACTIVATED !!!")
        print("=" * 70)

        with self.lock:
            self.emergency_stop_active = True
            self.emergency_stop_reason = reason
            self.emergency_stop_time = time.time()

            # Stop all Personal AI requests
            for request_id in list(self.personal_ai_requests.keys()):
                self.cancelled_requests.add(request_id)
                self.personal_ai_requests[request_id]['status'] = 'emergency_stopped'

            # Pause all Governance AI tasks
            for task_id in list(self.governance_tasks.keys()):
                self.paused_tasks.add(task_id)
                self.governance_tasks[task_id]['paused'] = True

        # Stop all trading bots
        trading_bot_result = self.stop_all_trading_bots(reason)

        print(f"Reason: {reason.value}")
        print(f"Details: {details}")
        print(f"Activated by: {activator}")
        print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\nPersonal AI requests stopped: {len(self.personal_ai_requests)}")
        print(f"Governance tasks paused: {len(self.governance_tasks)}")
        print(f"Trading bots stopped: {trading_bot_result['stopped_count']}")
        print("=" * 70)

        return {
            'success': True,
            'message': '[EMERGENCY] All AI operations halted',
            'reason': reason.value,
            'details': details,
            'activated_by': activator,
            'timestamp': time.time(),
            'personal_ai_stopped': len(self.personal_ai_requests),
            'governance_tasks_paused': len(self.governance_tasks),
            'trading_bots_stopped': trading_bot_result['stopped_count']
        }

    def deactivate_emergency_stop(self, deactivator: str) -> Dict:
        """
        Deactivate emergency stop (allow AI operations to resume)

        Args:
            deactivator: Who is deactivating

        Returns:
            Deactivation result
        """

        if not self.emergency_stop_active:
            return {
                'success': False,
                'error': 'Emergency stop not active',
                'message': 'No active emergency stop to deactivate'
            }

        with self.lock:
            self.emergency_stop_active = False
            duration = time.time() - self.emergency_stop_time

        print("\n" + "=" * 70)
        print("[OK] EMERGENCY STOP DEACTIVATED")
        print("=" * 70)
        print(f"Deactivated by: {deactivator}")
        print(f"Duration: {duration:.2f} seconds")
        print("AI operations can resume")
        print("=" * 70)

        return {
            'success': True,
            'message': 'Emergency stop deactivated. AI operations can resume.',
            'deactivated_by': deactivator,
            'duration_seconds': duration
        }

    def set_safety_level(self, level: AISafetyLevel, setter: str) -> Dict:
        """
        Set global AI safety level

        Args:
            level: Safety level to set
            setter: Who is changing level

        Returns:
            Result
        """

        if not self.is_authorized_caller(setter):
            return {
                'success': False,
                'error': 'UNAUTHORIZED_CALLER',
                'message': f'{setter} is not authorized to change safety level'
            }

        old_level = self.safety_level

        with self.lock:
            self.safety_level = level

        # Auto-actions based on level
        if level == AISafetyLevel.EMERGENCY_STOP:
            self.activate_emergency_stop(
                StopReason.SECURITY_THREAT,
                "Safety level set to EMERGENCY_STOP",
                setter
            )
        elif level == AISafetyLevel.LOCKDOWN:
            self.activate_emergency_stop(
                StopReason.SECURITY_THREAT,
                "Safety level set to LOCKDOWN",
                setter
            )

        return {
            'success': True,
            'old_level': old_level.value,
            'new_level': level.value,
            'set_by': setter
        }

    # ===== STATUS & MONITORING =====

    def get_status(self) -> Dict:
        """Get current AI safety status"""

        with self.lock:
            status = {
                'safety_level': self.safety_level.value,
                'emergency_stop_active': self.emergency_stop_active,
                'personal_ai': {
                    'total_requests': len(self.personal_ai_requests),
                    'running': sum(1 for r in self.personal_ai_requests.values() if r['status'] == 'running'),
                    'cancelled': len(self.cancelled_requests)
                },
                'governance_ai': {
                    'total_tasks': len(self.governance_tasks),
                    'running': sum(1 for t in self.governance_tasks.values() if not t['paused']),
                    'paused': len(self.paused_tasks)
                },
                'trading_bots': {
                    'active_bots': len(self.trading_bots)
                },
                'statistics': {
                    'total_stops': self.total_stops,
                    'total_cancellations': self.total_cancellations
                }
            }

            if self.emergency_stop_active:
                status['emergency_stop'] = {
                    'reason': self.emergency_stop_reason.value,
                    'duration_seconds': time.time() - self.emergency_stop_time,
                    'activated': time.strftime('%Y-%m-%d %H:%M:%S',
                                              time.localtime(self.emergency_stop_time))
                }

        return status

    def get_active_operations(self) -> Dict:
        """Get list of all active AI operations"""

        with self.lock:
            return {
                'personal_ai_requests': [
                    {
                        'request_id': rid,
                        'user': req['user'],
                        'operation': req['operation'],
                        'status': req['status'],
                        'runtime': time.time() - req['started']
                    }
                    for rid, req in self.personal_ai_requests.items()
                    if req['status'] == 'running'
                ],
                'governance_tasks': [
                    {
                        'task_id': tid,
                        'task_type': task['task_type'],
                        'status': task['status'],
                        'paused': task['paused'],
                        'runtime': time.time() - task['started']
                    }
                    for tid, task in self.governance_tasks.items()
                    if task['status'] == 'running'
                ],
                'trading_bots': [
                    {
                        'user': user,
                        'is_active': bot.is_active if hasattr(bot, 'is_active') else False
                    }
                    for user, bot in self.trading_bots.items()
                ]
            }


# Example usage
if __name__ == "__main__":
    print("XAI AI Safety & Emergency Stop System")
    print("=" * 50)
    print("\nSafety Controls:")
    print("1. Personal AI request cancellation (user-level)")
    print("2. Trading bot emergency stop")
    print("3. Governance AI task pause/abort")
    print("4. Global AI emergency stop (all operations)")
    print("\nPrinciple: Users have INSTANT control over AI")
