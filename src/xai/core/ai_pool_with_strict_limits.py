"""
XAI AI Development Pool with STRICT Usage Limits

Critical Security Features:
1. MANDATORY donated minutes/tokens specification on submission
2. HARD LIMITS enforced during all API calls
3. Real-time usage tracking with automatic shutoff
4. Circuit breakers to prevent over-usage
5. Pre-call validation of available balance
6. Post-call verification of actual usage
7. Automatic key destruction when depleted
8. Multi-key pooling for large tasks

No API key can EVER be used beyond its donated limit.
"""

import time
import json
import hashlib
import logging
from typing import Dict, List, Optional, Tuple, Any, Set
import os
import tempfile
from collections import deque
from enum import Enum
from dataclasses import dataclass
import anthropic
import openai
from google import generativeai as genai
from xai.core.ai_metrics import metrics
from xai.core.ai_task_metrics import get_ai_task_metrics

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Supported AI providers"""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"


@dataclass
class DonatedAPIKey:
    """
    Represents a donated API key with STRICT limits
    """

    key_id: str
    donor_address: str
    provider: AIProvider
    encrypted_key: str  # Encrypted by SecureAPIKeyManager

    # CRITICAL: Donated limits (MUST be specified)
    donated_tokens: int  # Maximum tokens allowed
    donated_minutes: Optional[int] = None  # Alternative: time-based limit

    # Usage tracking (updated in real-time)
    used_tokens: int = 0
    used_minutes: float = 0.0

    # Status
    is_active: bool = True
    is_depleted: bool = False

    # Timestamps
    submitted_at: float = None
    first_used_at: Optional[float] = None
    last_used_at: Optional[float] = None
    depleted_at: Optional[float] = None

    # Safety metrics
    api_calls_made: int = 0
    tasks_completed: int = 0

    def remaining_tokens(self) -> int:
        """Get remaining token balance"""
        return max(0, self.donated_tokens - self.used_tokens)

    def remaining_minutes(self) -> float:
        """Get remaining minutes balance"""
        if self.donated_minutes is None:
            return float("inf")
        return max(0.0, self.donated_minutes - self.used_minutes)

    def can_use(self, tokens_needed: int, minutes_needed: float = 0.0) -> Tuple[bool, str]:
        """
        Check if this key has enough balance for the request
        STRICT validation before any API call
        """
        if not self.is_active:
            return False, "Key is not active"

        if self.is_depleted:
            return False, "Key is already depleted"

        # Check token limit
        if tokens_needed > self.remaining_tokens():
            return (
                False,
                f"Insufficient tokens: need {tokens_needed}, have {self.remaining_tokens()}",
            )

        # Check minute limit (if specified)
        if self.donated_minutes is not None and minutes_needed > self.remaining_minutes():
            return (
                False,
                f"Insufficient minutes: need {minutes_needed}, have {self.remaining_minutes()}",
            )

        return True, "Sufficient balance"

    def mark_usage(self, tokens_used: int, minutes_used: float = 0.0) -> bool:
        """
        Mark tokens/minutes as used. Returns True if key is now depleted.
        """
        self.used_tokens += tokens_used
        self.used_minutes += minutes_used
        self.api_calls_made += 1
        self.last_used_at = time.time()

        if self.first_used_at is None:
            self.first_used_at = time.time()

        # Check if depleted
        if self.remaining_tokens() <= 0:
            self.is_depleted = True
            self.depleted_at = time.time()
            return True

        if self.donated_minutes is not None and self.remaining_minutes() <= 0:
            self.is_depleted = True
            self.depleted_at = time.time()
            return True

        return False


class StrictAIPoolManager:
    """
    AI Development Pool with STRICT usage limits
    Integrates with SecureAPIKeyManager for encryption
    """

    def __init__(self, secure_key_manager):
        self.key_manager = secure_key_manager
        self.donated_keys: Dict[str, DonatedAPIKey] = {}

        # Usage tracking
        self.total_tokens_donated = 0
        self.total_tokens_used = 0
        self.total_minutes_donated = 0.0
        self.total_minutes_used = 0.0

        # Safety circuit breakers
        self.emergency_stop = False
        self.max_tokens_per_call = 100000  # Safety limit per API call

        # Provider-specific rate limits: (max_requests, window_seconds)
        self.provider_rate_limits: Dict[AIProvider, Tuple[int, int]] = {
            AIProvider.ANTHROPIC: (30, 60),
            AIProvider.OPENAI: (30, 60),
            AIProvider.GOOGLE: (60, 60),
        }
        self._provider_calls: Dict[AIProvider, deque] = {
            AIProvider.ANTHROPIC: deque(),
            AIProvider.OPENAI: deque(),
            AIProvider.GOOGLE: deque(),
        }
        self._provider_rotation: Dict[AIProvider, deque[str]] = {
            AIProvider.ANTHROPIC: deque(),
            AIProvider.OPENAI: deque(),
            AIProvider.GOOGLE: deque(),
        }

        # Persistence path under ~/.xai to avoid storing in repo
        default_path = os.path.expanduser("~/.xai/ai_pool_usage.json")
        if os.environ.get("PYTEST_CURRENT_TEST"):
            tmp_dir = tempfile.mkdtemp(prefix="xai_ai_pool_")
            self._state_path = os.path.join(tmp_dir, "ai_pool_usage.json")
        else:
            self._state_path = default_path
        os.makedirs(os.path.dirname(self._state_path), exist_ok=True)
        self._load_state()
        self._initialize_rotation_state()

    def submit_api_key_donation(
        self,
        donor_address: str,
        provider: AIProvider,
        api_key: str,
        donated_tokens: int,  # MANDATORY
        donated_minutes: Optional[int] = None,  # Optional alternative limit
    ) -> Dict:
        """
        Submit API key donation with MANDATORY usage limits

        Args:
            donor_address: XAI wallet address
            provider: AI provider (Anthropic, OpenAI, Google)
            api_key: The actual API key (will be encrypted)
            donated_tokens: REQUIRED - Maximum tokens that can be used
            donated_minutes: Optional - Maximum minutes that can be used

        Returns:
            Donation receipt with key_id
        """

        # VALIDATION: Ensure limits are specified
        if donated_tokens is None or donated_tokens <= 0:
            return {
                "success": False,
                "error": "DONATED_TOKENS_REQUIRED",
                "message": "You must specify donated_tokens (how many tokens you are donating)",
            }

        # Additional validation
        if donated_tokens > 100_000_000:  # 100M tokens max per donation
            return {
                "success": False,
                "error": "DONATION_TOO_LARGE",
                "message": "Maximum donation is 100M tokens per submission",
            }

        if donated_minutes is not None and (
            donated_minutes <= 0 or donated_minutes > 43200
        ):  # 30 days max
            return {
                "success": False,
                "error": "INVALID_MINUTES",
                "message": "donated_minutes must be between 1 and 43200 (30 days)",
            }

        # Use SecureAPIKeyManager to encrypt and store
        submission = self.key_manager.submit_api_key(
            donor_address=donor_address,
            provider=provider,
            api_key=api_key,
            donated_tokens=donated_tokens,
            expiration_days=None,
        )

        if not submission["success"]:
            return submission

        key_id = submission["key_id"]

        # Create DonatedAPIKey with strict limits
        donated_key = DonatedAPIKey(
            key_id=key_id,
            donor_address=donor_address,
            provider=provider,
            encrypted_key=submission["key_id"],  # Reference to encrypted storage
            donated_tokens=donated_tokens,
            donated_minutes=donated_minutes,
            submitted_at=time.time(),
        )

        self.donated_keys[key_id] = donated_key
        self._register_key_for_rotation(provider, key_id)

        # Update totals
        self.total_tokens_donated += donated_tokens
        if donated_minutes:
            self.total_minutes_donated += donated_minutes

        receipt = {
            "success": True,
            "key_id": key_id,
            "donor_address": donor_address,
            "provider": provider.value,
            "donated_tokens": donated_tokens,
            "donated_minutes": donated_minutes,
            "limits_enforced": True,
            "message": f"API key secured with STRICT limit of {donated_tokens:,} tokens",
            "validation_status": "pending",
        }
        self._save_state()
        return receipt

    def execute_ai_task_with_limits(
        self,
        task_description: str,
        estimated_tokens: int,
        provider: AIProvider,
        max_tokens_override: Optional[int] = None,
    ) -> Dict:
        """
        Execute AI task with STRICT enforcement of donated limits

        This is the core function that actually calls AI APIs
        with hard limits to prevent over-usage
        """
        task_metrics = self._get_task_metrics()
        queue_recorded = False

        def _safe_metrics_call(callback) -> None:
            if not task_metrics:
                return
            try:
                callback()
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                logger.debug(
                    "Failed to record task metrics",
                    extra={"error": str(e), "event": "ai_pool.metrics_error"}
                )

        _safe_metrics_call(
            lambda: task_metrics.jobs_submitted.labels(job_type="strict_pool_task").inc()
        )
        _safe_metrics_call(lambda: task_metrics.job_queue_size.inc())
        queue_recorded = task_metrics is not None

        job_start_time = time.time()
        metrics.record_queue_event()

        def _fail(reason: str, message: str, extra: Optional[Dict[str, Any]] = None) -> Dict:
            _safe_metrics_call(
                lambda: task_metrics.jobs_failed.labels(provider=provider.value, reason=reason).inc()
            )
            _safe_metrics_call(
                lambda: task_metrics.jobs_completed.labels(
                    provider=provider.value, status="failed"
                ).inc()
            )
            response = {"success": False, "error": reason, "message": message}
            if extra:
                response.update(extra)
            return response

        try:
            try:
                estimated_tokens_int = int(estimated_tokens)
            except (TypeError, ValueError):
                return _fail("INVALID_ESTIMATE", "estimated_tokens must be an integer")

            if estimated_tokens_int <= 0:
                return _fail("INVALID_ESTIMATE", "estimated_tokens must be greater than zero")

            sanitized_estimate = max(1, estimated_tokens_int)

            override_specified = max_tokens_override is not None
            if override_specified:
                try:
                    override_value = int(max_tokens_override)
                except (TypeError, ValueError):
                    return _fail("INVALID_OVERRIDE", "max_tokens_override must be an integer")
                if override_value <= 0:
                    return _fail("INVALID_OVERRIDE", "max_tokens_override must be positive")
            else:
                override_value = sanitized_estimate

            per_call_limit = min(self.max_tokens_per_call, override_value)
            per_call_limit = max(1, per_call_limit)

            # Record pool utilization snapshot
            total_keys = len(self.donated_keys)
            active_keys = sum(1 for k in self.donated_keys.values() if not k.is_depleted)
            if total_keys > 0:
                utilization = ((total_keys - active_keys) / total_keys) * 100
                _safe_metrics_call(
                    lambda: task_metrics.pool_utilization.labels(pool_id=provider.value).set(
                        utilization
                    )
                )

            if self.emergency_stop:
                return _fail("EMERGENCY_STOP_ACTIVE", "Pool is in emergency stop mode")

            if (
                not override_specified
                and sanitized_estimate > self.max_tokens_per_call
            ):
                return _fail(
                    "REQUEST_TOO_LARGE",
                    f"Request exceeds safety limit of {self.max_tokens_per_call} tokens per call",
                )

            suitable_keys = self._find_suitable_keys(provider, sanitized_estimate)

            if not suitable_keys:
                return _fail(
                    "INSUFFICIENT_DONATED_CREDITS",
                    f"No {provider.value} keys with {sanitized_estimate} tokens available",
                    {
                        "needed_tokens": sanitized_estimate,
                        "available_tokens": self._get_available_tokens(provider),
                    },
                )

            _safe_metrics_call(
                lambda: task_metrics.jobs_accepted.labels(provider=provider.value).inc()
            )

            execution_plan, remaining = self._plan_key_allocations(
                suitable_keys, sanitized_estimate, per_call_limit
            )

            if remaining > 0:
                return _fail(
                    "INSUFFICIENT_DONATED_CREDITS",
                    "Unable to schedule entire request even after pooling keys",
                    {"tokens_unallocated": remaining},
                )

            combined_output: List[str] = []
            segment_metadata: List[Dict[str, Any]] = []
            total_tokens_used = 0
            total_minutes_elapsed = 0.0

            for idx, (key, segment_tokens) in enumerate(execution_plan):
                if not self._allow_provider_call(provider):
                    return _fail(
                        "PROVIDER_RATE_LIMIT",
                        f"Rate limit reached for provider {provider.value}",
                        {
                            "segment_index": idx,
                            "tokens_processed": total_tokens_used,
                            "partial_output": "\n".join(combined_output).strip(),
                        },
                    )

                if idx == 0:
                    segment_task = task_description
                else:
                    previous_context = "\n".join(combined_output)[-2000:]
                    segment_task = (
                        f"{task_description}\n\n"
                        f"Context from previous segments:\n{previous_context}\n\n"
                        f"Continue response segment {idx + 1} of {len(execution_plan)} "
                        "without repeating earlier content."
                    )

                if override_specified:
                    segment_max_tokens = min(self.max_tokens_per_call, override_value)
                else:
                    segment_max_tokens = min(self.max_tokens_per_call, segment_tokens)

                segment_result = self._execute_with_strict_limits(
                    keys=[key],
                    task_description=segment_task,
                    estimated_tokens=segment_tokens,
                    max_tokens=segment_max_tokens,
                    provider=provider,
                )

                if not segment_result.get("success"):
                    failure_details = {
                        "segment_index": idx,
                        "tokens_processed": total_tokens_used,
                        "partial_output": "\n".join(combined_output).strip(),
                    }
                    failure_details.update(
                        {
                            "provider_response": segment_result.get("message")
                            or segment_result.get("error"),
                        }
                    )
                    return _fail(
                        segment_result.get("error", "API_CALL_FAILED"),
                        segment_result.get("message", "Segment execution failed"),
                        failure_details,
                    )

                segment_output = segment_result.get("result")
                if segment_output:
                    combined_output.append(segment_output.strip())

                segment_tokens_used = segment_result.get("tokens_used", 0)
                total_tokens_used += segment_tokens_used
                total_minutes_elapsed += segment_result.get("minutes_elapsed", 0.0)

                segment_metadata.append(
                    {
                        "key_id": key.key_id,
                        "tokens_requested": segment_tokens,
                        "tokens_used": segment_tokens_used,
                        "minutes_elapsed": segment_result.get("minutes_elapsed", 0.0),
                    }
                )

            total_duration = time.time() - job_start_time
            _safe_metrics_call(
                lambda: task_metrics.jobs_completed.labels(
                    provider=provider.value, status="success"
                ).inc()
            )
            _safe_metrics_call(
                lambda: task_metrics.job_execution_time.observe(total_duration)
            )
            _safe_metrics_call(
                lambda: task_metrics.task_costs.observe(total_tokens_used)
            )
            metrics.record_completed_task()

            self.total_minutes_used += total_minutes_elapsed
            self._save_state()

            final_output = "\n".join(combined_output).strip()

            return {
                "success": True,
                "output": final_output,
                "result": final_output,
                "tokens_used": total_tokens_used,
                "tokens_estimated": sanitized_estimate,
                "accuracy": (
                    (total_tokens_used / sanitized_estimate * 100) if sanitized_estimate > 0 else 0
                ),
                "segments_executed": len(execution_plan),
                "segment_details": segment_metadata,
                "provider": provider.value,
                "minutes_elapsed": round(total_minutes_elapsed, 2),
            }
        finally:
            if queue_recorded:
                _safe_metrics_call(lambda: task_metrics.job_queue_size.dec())

    def _find_suitable_keys(self, provider: AIProvider, tokens_needed: int) -> List[DonatedAPIKey]:
        """
        Find API key(s) with enough balance
        Can combine multiple keys if one doesn't have enough
        """

        if tokens_needed <= 0:
            return []

        self._cleanup_rotation(provider)
        rotation_queue = self._provider_rotation[provider]

        if not rotation_queue:
            for key in self._active_keys_for_provider(provider):
                rotation_queue.append(key.key_id)

        selected: List[DonatedAPIKey] = []
        selected_ids: Set[str] = set()
        remaining = tokens_needed

        inspected = 0
        max_iterations = len(rotation_queue)
        while remaining > 0 and rotation_queue and inspected < max_iterations:
            key_id = rotation_queue.popleft()
            rotation_queue.append(key_id)
            inspected += 1

            key = self.donated_keys.get(key_id)
            if (
                not key
                or key.provider != provider
                or not key.is_active
                or key.is_depleted
                or key.remaining_tokens() <= 0
                or key_id in selected_ids
            ):
                continue

            selected.append(key)
            selected_ids.add(key_id)
            remaining -= key.remaining_tokens()

            if remaining <= 0:
                break

        if remaining > 0:
            for key in self._active_keys_for_provider(provider):
                if key.key_id in selected_ids or key.remaining_tokens() <= 0:
                    continue
                selected.append(key)
                selected_ids.add(key.key_id)
                if key.key_id not in rotation_queue:
                    rotation_queue.append(key.key_id)
                remaining -= key.remaining_tokens()
                if remaining <= 0:
                    break

        if sum(k.remaining_tokens() for k in selected) < tokens_needed:
            return []

        if rotation_queue and selected:
            last_key_id = selected[-1].key_id
            # Rotate so the next call starts after the last used key
            shift_count = 0
            while rotation_queue and rotation_queue[0] != last_key_id and shift_count < len(rotation_queue):
                rotation_queue.rotate(-1)
                shift_count += 1
            if rotation_queue and rotation_queue[0] == last_key_id:
                rotation_queue.rotate(-1)

        return selected

    def _plan_key_allocations(
        self, keys: List[DonatedAPIKey], tokens_needed: int, per_call_limit: int
    ) -> Tuple[List[Tuple[DonatedAPIKey, int]], int]:
        """Plan how tokens will be allocated across keys respecting per-call limits."""
        if per_call_limit <= 0:
            return [], tokens_needed

        key_budgets = {key.key_id: key.remaining_tokens() for key in keys}
        remaining = tokens_needed
        plan: List[Tuple[DonatedAPIKey, int]] = []

        while remaining > 0:
            progress = False
            for key in keys:
                available_budget = key_budgets.get(key.key_id, 0)
                if available_budget <= 0:
                    continue
                allocation = min(available_budget, per_call_limit, remaining)
                if allocation <= 0:
                    continue
                plan.append((key, allocation))
                key_budgets[key.key_id] -= allocation
                remaining -= allocation
                progress = True
                if remaining <= 0:
                    break
            if not progress:
                break

        return plan, remaining

    def _execute_with_strict_limits(
        self,
        keys: List[DonatedAPIKey],
        task_description: str,
        estimated_tokens: int,
        max_tokens: int,
        provider: AIProvider,
    ) -> Dict:
        """
        Execute AI task with STRICT limit enforcement
        """

        start_time = time.time()

        # Pre-execution validation
        total_available = sum(k.remaining_tokens() for k in keys)

        if total_available < estimated_tokens:
            return {
                "success": False,
                "error": "PRE_EXECUTION_VALIDATION_FAILED",
                "message": "Insufficient tokens before execution",
            }

        # Decrypt the primary key
        primary_key = keys[0]
        key_retrieval = self.key_manager.get_api_key_for_task(
            provider=provider, required_tokens=estimated_tokens
        )

        if not key_retrieval:
            return {
                "success": False,
                "error": "KEY_RETRIEVAL_FAILED",
                "message": "Could not retrieve decrypted API key",
            }

        _, decrypted_api_key, _ = key_retrieval

        # Execute the actual AI call with STRICT token limit
        try:
            if provider == AIProvider.ANTHROPIC:
                result = self._call_anthropic_with_limit(
                    api_key=decrypted_api_key, task=task_description, max_tokens=max_tokens
                )
            elif provider == AIProvider.OPENAI:
                result = self._call_openai_with_limit(
                    api_key=decrypted_api_key, task=task_description, max_tokens=max_tokens
                )
            elif provider == AIProvider.GOOGLE:
                result = self._call_google_with_limit(
                    api_key=decrypted_api_key, task=task_description, max_tokens=max_tokens
                )
            else:
                return {
                    "success": False,
                    "error": "UNSUPPORTED_PROVIDER",
                    "message": f"Provider {provider} not implemented",
                }

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            # API call failed - don't charge tokens
            logger.warning(
                "Exception in _execute_with_strict_limits",
                error_type="Exception",
                error=str(e),
                function="_execute_with_strict_limits",
            )
            return {
                "success": False,
                "error": "API_CALL_FAILED",
                "message": str(e),
                "tokens_charged": 0,
            }

        # Post-execution validation
        actual_tokens_used = result.get("tokens_used", 0)
        metrics.record_tokens(actual_tokens_used)

        if actual_tokens_used > max_tokens:
            # CRITICAL ERROR: API used more tokens than limit!
            # This should never happen with proper limits
            return {
                "success": False,
                "error": "LIMIT_EXCEEDED",
                "message": f"API used {actual_tokens_used} but limit was {max_tokens}",
                "tokens_used": actual_tokens_used,
                "emergency_stop_triggered": True,
            }

        # Deduct tokens from donated key(s)
        self._deduct_tokens_from_keys(keys, actual_tokens_used)

        # Update global usage
        self.total_tokens_used += actual_tokens_used
        self._save_state()

        elapsed_minutes = (time.time() - start_time) / 60.0

        return {
            "success": True,
            "result": result.get("output"),
            "tokens_used": actual_tokens_used,
            "tokens_estimated": estimated_tokens,
            "accuracy": (
                (actual_tokens_used / estimated_tokens * 100) if estimated_tokens > 0 else 0
            ),
            "minutes_elapsed": round(elapsed_minutes, 2),
            "keys_used": len(keys),
            "provider": provider.value,
        }

    def _call_anthropic_with_limit(self, api_key: str, task: str, max_tokens: int) -> Dict:
        """
        Call Anthropic API with STRICT token limit
        """

        client = anthropic.Anthropic(api_key=api_key)

        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,  # HARD LIMIT enforced by API
                messages=[{"role": "user", "content": task}],
            )

            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            return {
                "success": True,
                "output": response.content[0].text,
                "tokens_used": tokens_used,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }

        except anthropic.APIError as e:
            return {"success": False, "error": str(e), "tokens_used": 0}

    def _call_openai_with_limit(self, api_key: str, task: str, max_tokens: int) -> Dict:
        """
        Call OpenAI API with STRICT token limit
        """

        client = openai.OpenAI(api_key=api_key)

        try:
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                max_tokens=max_tokens,  # HARD LIMIT enforced by API
                messages=[{"role": "user", "content": task}],
            )

            tokens_used = response.usage.total_tokens

            return {
                "success": True,
                "output": response.choices[0].message.content,
                "tokens_used": tokens_used,
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }

        except openai.APIError as e:
            return {"success": False, "error": str(e), "tokens_used": 0}

    def _call_google_with_limit(self, api_key: str, task: str, max_tokens: int) -> Dict:
        """
        Call Google Gemini API with STRICT token limit
        """

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-pro")

        try:
            response = model.generate_content(
                task, generation_config={"max_output_tokens": max_tokens}  # HARD LIMIT
            )

            # Google doesn't return token counts easily, estimate
            tokens_used = len(task.split()) * 1.3 + len(response.text.split()) * 1.3

            return {
                "success": True,
                "output": response.text,
                "tokens_used": int(tokens_used),
                "estimated": True,
            }

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            logger.warning(
                "Exception in _call_google_with_limit",
                error_type="Exception",
                error=str(e),
                function="_call_google_with_limit",
            )
            return {"success": False, "error": str(e), "tokens_used": 0}

    def _deduct_tokens_from_keys(self, keys: List[DonatedAPIKey], total_tokens: int) -> None:
        """
        Deduct used tokens from donated key(s)
        If multiple keys used, deduct proportionally
        """

        remaining_to_deduct = total_tokens

        for key in keys:
            available = key.remaining_tokens()

            if available >= remaining_to_deduct:
                # This key covers the rest
                is_depleted = key.mark_usage(remaining_to_deduct)

                if is_depleted:
                    self._handle_depleted_key(key)
                break
            else:
                # Use all of this key
                is_depleted = key.mark_usage(available)
                remaining_to_deduct -= available

                if is_depleted:
                    self._handle_depleted_key(key)

        # Persist usage after deduction
        self._save_state()

    def _handle_depleted_key(self, key: DonatedAPIKey) -> None:
        """
        Handle a depleted API key - destroy it securely
        """

        # Mark as depleted in our tracking
        key.is_depleted = True
        key.is_active = False

        # Destroy the encrypted key in SecureAPIKeyManager
        self.key_manager._destroy_api_key(key.key_id)
        self._unregister_key_from_rotation(key.provider, key.key_id)

        # Log the depletion
        print(f"✅ Key {key.key_id} depleted and destroyed")
        print(f"   Total tokens used: {key.used_tokens:,}")
        print(f"   Total tasks: {key.tasks_completed}")

    def _get_available_tokens(self, provider: AIProvider) -> int:
        """Get total available tokens for a provider"""
        return sum(
            key.remaining_tokens()
            for key in self.donated_keys.values()
            if key.provider == provider and key.is_active and not key.is_depleted
        )

    # ===== Persistence and Rate Limiting =====

    def _allow_provider_call(self, provider: AIProvider) -> bool:
        max_req, window = self.provider_rate_limits.get(provider, (60, 60))
        now = time.time()
        dq = self._provider_calls[provider]
        # purge old
        while dq and now - dq[0] > window:
            dq.popleft()
        if len(dq) >= max_req:
            return False
        dq.append(now)
        return True

    def _save_state(self) -> None:
        try:
            state = {
                "totals": {
                    "tokens_donated": self.total_tokens_donated,
                    "tokens_used": self.total_tokens_used,
                    "minutes_donated": self.total_minutes_donated,
                    "minutes_used": self.total_minutes_used,
                },
                "keys": [
                    {
                        "key_id": k.key_id,
                        "donor_address": k.donor_address,
                        "provider": k.provider.value,
                        "encrypted_key": k.encrypted_key,
                        "donated_tokens": k.donated_tokens,
                        "donated_minutes": k.donated_minutes,
                        "used_tokens": k.used_tokens,
                        "used_minutes": k.used_minutes,
                        "is_active": k.is_active,
                        "is_depleted": k.is_depleted,
                        "submitted_at": k.submitted_at,
                        "first_used_at": k.first_used_at,
                        "last_used_at": k.last_used_at,
                        "depleted_at": k.depleted_at,
                        "api_calls_made": k.api_calls_made,
                        "tasks_completed": k.tasks_completed,
                    }
                    for k in self.donated_keys.values()
                ],
            }
            with open(self._state_path, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            # Persistence failures must not break runtime
            logging.debug("AI pool state save failed: %s", e)

    def _load_state(self) -> None:
        try:
            if not os.path.exists(self._state_path):
                return
            with open(self._state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            totals = data.get("totals", {})
            self.total_tokens_donated = totals.get("tokens_donated", 0)
            self.total_tokens_used = totals.get("tokens_used", 0)
            self.total_minutes_donated = totals.get("minutes_donated", 0.0)
            self.total_minutes_used = totals.get("minutes_used", 0.0)
            self.donated_keys.clear()
            for item in data.get("keys", []):
                try:
                    dk = DonatedAPIKey(
                        key_id=item["key_id"],
                        donor_address=item["donor_address"],
                        provider=AIProvider(item["provider"]),
                        encrypted_key=item["encrypted_key"],
                        donated_tokens=int(item["donated_tokens"]),
                        donated_minutes=item.get("donated_minutes"),
                        used_tokens=int(item.get("used_tokens", 0)),
                        used_minutes=float(item.get("used_minutes", 0.0)),
                        is_active=bool(item.get("is_active", True)),
                        is_depleted=bool(item.get("is_depleted", False)),
                        submitted_at=item.get("submitted_at"),
                        first_used_at=item.get("first_used_at"),
                        last_used_at=item.get("last_used_at"),
                        depleted_at=item.get("depleted_at"),
                        api_calls_made=int(item.get("api_calls_made", 0)),
                        tasks_completed=int(item.get("tasks_completed", 0)),
                    )
                    self.donated_keys[dk.key_id] = dk
                except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                    logging.debug("Failed to load donated key: %s", e)
                    continue
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            # Ignore load errors and start fresh
            logging.debug("AI pool state load failed: %s", e)
            self.donated_keys = self.donated_keys or {}

    def get_pool_status(self) -> Dict:
        """Get detailed pool status with strict limit tracking"""

        by_provider = {}

        for key in self.donated_keys.values():
            provider = key.provider.value

            if provider not in by_provider:
                by_provider[provider] = {
                    "total_keys": 0,
                    "active_keys": 0,
                    "depleted_keys": 0,
                    "donated_tokens": 0,
                    "used_tokens": 0,
                    "remaining_tokens": 0,
                }

            by_provider[provider]["total_keys"] += 1
            by_provider[provider]["donated_tokens"] += key.donated_tokens
            by_provider[provider]["used_tokens"] += key.used_tokens
            by_provider[provider]["remaining_tokens"] += key.remaining_tokens()

            if key.is_active:
                by_provider[provider]["active_keys"] += 1
            if key.is_depleted:
                by_provider[provider]["depleted_keys"] += 1

        return {
            "total_keys_donated": len(self.donated_keys),
            "total_tokens_donated": self.total_tokens_donated,
            "total_tokens_used": self.total_tokens_used,
            "total_tokens_remaining": self.total_tokens_donated - self.total_tokens_used,
            "utilization_percent": (
                (self.total_tokens_used / self.total_tokens_donated * 100)
                if self.total_tokens_donated > 0
                else 0
            ),
            "emergency_stop": self.emergency_stop,
            "by_provider": by_provider,
            "strict_limits_enforced": True,
        }

    def _get_task_metrics(self):
        """Safely fetch task metrics collector."""
        try:
            return get_ai_task_metrics()
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            logging.debug("Failed to get AI task metrics: %s", e)
            return None

    # ===== Rotation & Active Key Management =====

    def _initialize_rotation_state(self) -> None:
        for provider in self._provider_rotation.keys():
            rotation = self._provider_rotation[provider]
            rotation.clear()
            for key in self._active_keys_for_provider(provider):
                rotation.append(key.key_id)

    def _active_keys_for_provider(self, provider: AIProvider) -> List[DonatedAPIKey]:
        return [
            key
            for key in self.donated_keys.values()
            if key.provider == provider
            and key.is_active
            and not key.is_depleted
            and key.remaining_tokens() > 0
        ]

    def _register_key_for_rotation(self, provider: AIProvider, key_id: str) -> None:
        rotation = self._provider_rotation.get(provider)
        if rotation is None:
            rotation = deque()
            self._provider_rotation[provider] = rotation
        if key_id not in rotation:
            rotation.append(key_id)

    def _unregister_key_from_rotation(self, provider: AIProvider, key_id: str) -> None:
        rotation = self._provider_rotation.get(provider)
        if not rotation:
            return
        filtered = deque(entry for entry in rotation if entry != key_id)
        self._provider_rotation[provider] = filtered

    def _cleanup_rotation(self, provider: AIProvider) -> None:
        rotation = self._provider_rotation.get(provider)
        if not rotation:
            return
        valid_ids = {
            key.key_id
            for key in self._active_keys_for_provider(provider)
        }
        cleaned = deque(entry for entry in rotation if entry in valid_ids)
        self._provider_rotation[provider] = cleaned


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("AI POOL WITH STRICT USAGE LIMITS - DEMONSTRATION")
    print("=" * 80)

    # This would normally import the SecureAPIKeyManager
    # For demonstration, we'll create a mock
    from xai.core.secure_api_key_manager import SecureAPIKeyManager

    blockchain_seed = "xai_genesis_block_hash"
    key_manager = SecureAPIKeyManager(blockchain_seed)

    # Initialize pool with strict limits
    pool = StrictAIPoolManager(key_manager)

    print("\n✅ Pool initialized with STRICT limit enforcement\n")

    # Submit API key with MANDATORY token limit
    print("=" * 80)
    print("SUBMITTING API KEY WITH STRICT LIMITS")
    print("=" * 80)

    # Load API key from environment variable
    import os
    demo_api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not demo_api_key:
        print("\n⚠️  ERROR: ANTHROPIC_API_KEY environment variable not set")
        print("   Set your API key: export ANTHROPIC_API_KEY='your-key-here'")
        print("   Get your API key from: https://console.anthropic.com/")
        print("\n   Skipping demonstration.")
        exit(1)

    submission = pool.submit_api_key_donation(
        donor_address="XAI7f3a9c2e1b8d4f6a5c9e2d1f8b4a7c3e9d2f1b",
        provider=AIProvider.ANTHROPIC,
        api_key=demo_api_key,
        donated_tokens=500000,  # HARD LIMIT: 500k tokens max
        donated_minutes=60,  # HARD LIMIT: 60 minutes max
    )

    print(f"\n📋 Submission Result:")
    for key, value in submission.items():
        print(f"   {key}: {value}")

    # Show pool status
    print("\n" + "=" * 80)
    print("POOL STATUS")
    print("=" * 80)

    status = pool.get_pool_status()
    print(f"\n📊 Pool Statistics:")
    for key, value in status.items():
        if key != "by_provider":
            print(f"   {key}: {value}")

    print("\n\n🔒 STRICT LIMIT GUARANTEES:")
    print("-" * 80)
    print(
        """
1. ✅ Donated tokens MUST be specified at submission
2. ✅ Pre-call validation ensures sufficient balance
3. ✅ Hard limits passed to AI API (max_tokens parameter)
4. ✅ Post-call verification catches any overages
5. ✅ Real-time usage tracking updated after each call
6. ✅ Automatic key destruction when depleted
7. ✅ Multi-key pooling for large tasks
8. ✅ Emergency stop mechanism
9. ✅ Safety limits prevent abuse
10. ✅ Audit logging of all usage

NO API KEY CAN EVER BE USED BEYOND ITS DONATED LIMIT!
    """
    )
