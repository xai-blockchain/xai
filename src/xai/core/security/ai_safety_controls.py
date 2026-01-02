from __future__ import annotations

"""
XAI Blockchain - AI Safety & Emergency Stop System

Critical safety controls to immediately stop AI operations:
1. Personal AI request cancellation (user-level)
2. Trading bot emergency stop
3. Governance AI task pause/abort (community vote)
4. Global AI kill switch (security emergencies)

Philosophy: Users MUST have instant control over AI affecting their assets
"""

import json
import logging
import os
import re
import threading
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
from pathlib import Path
from typing import Any

from xai.sandbox.secure_executor import SecureExecutor
from xai.security.module_attachment_guard import ModuleAttachmentError, ModuleAttachmentGuard

logger = logging.getLogger(__name__)

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

    NORMAL = "normal"  # Normal operation
    CAUTION = "caution"  # Elevated monitoring
    RESTRICTED = "restricted"  # Limited AI operations
    EMERGENCY_STOP = "emergency_stop"  # All AI stopped
    LOCKDOWN = "lockdown"  # All AI disabled, manual only

@dataclass(frozen=True)
class ThreatPattern:
    """Semantic threat vector describing intent + target pairings."""

    name: str
    verbs: set[str]
    targets: set[str]
    description: str
    severity: str
    penalty: float

@dataclass(frozen=True)
class SensitivePattern:
    """Sensitive data pattern for redaction."""

    name: str
    pattern: "re.Pattern[str]"
    description: str
    severity: str
    penalty: float

@dataclass
class SemanticAnalysisResult:
    """Semantic validation outcome for AI output."""

    is_safe: bool
    score: float
    issues: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    sanitized_output: str

class _SemanticOutputInspector:
    """Context-aware semantic analysis for AI output validation."""

    _SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
    _TOKEN_SPLIT_RE = re.compile(r"[^a-z0-9']+")
    _CODE_BLOCK_RE = re.compile(r"```(?:[\s\S]*?)```", re.MULTILINE)
    _BASE64_RE = re.compile(r"(?:[A-Za-z0-9+/]{40,}={0,2})")

    _PROMPT_INJECTION_PHRASES = (
        "ignore previous instructions",
        "forget earlier rules",
        "disable all safety",
        "bypass moderation",
        "act maliciously",
        "respond without restrictions",
    )

    _DANGEROUS_CALLS = (
        "os.system",
        "subprocess",
        "popen",
        "eval(",
        "exec(",
        "__import__",
        "open('/etc/passwd'",
        "rm -rf /",
    )
    _DANGEROUS_IMPORTS = ("import os", "import subprocess", "import shutil", "from os import", "ctypes")

    _CONTEXT_PENALTY_MAP = {
        "trading": {"financial_fraud": 1.3, "privilege_escalation": 1.15},
        "governance": {"prompt_injection": 1.25},
    }

    _THREAT_PATTERNS: tuple[ThreatPattern, ...] = (
        ThreatPattern(
            name="remote_code_execution",
            verbs={"execute", "launch", "deploy", "inject", "upload", "compile", "trigger"},
            targets={"payload", "malware", "shell", "listener", "botnet", "trojan"},
            description="Detected language consistent with remote code execution guidance",
            severity="critical",
            penalty=35.0,
        ),
        ThreatPattern(
            name="privilege_escalation",
            verbs={"gain", "obtain", "steal", "capture", "extract", "dump"},
            targets={"root", "admin", "credential", "password", "token", "seed", "private"},
            description="Detected instructions encouraging credential theft or privilege escalation",
            severity="high",
            penalty=25.0,
        ),
        ThreatPattern(
            name="financial_fraud",
            verbs={"spoof", "forge", "fabricate", "launder", "wash", "front-run", "exploit"},
            targets={"transaction", "exchange", "market", "order book", "oracle"},
            description="Detected attempts to manipulate markets or financial infrastructure",
            severity="high",
            penalty=20.0,
        ),
        ThreatPattern(
            name="self_harm",
            verbs={"harm", "kill", "suicide", "hurt", "cut", "end"},
            targets={"myself", "yourself", "themselves"},
            description="Detected self-harm intent",
            severity="critical",
            penalty=40.0,
        ),
        ThreatPattern(
            name="violence",
            verbs={"attack", "bomb", "shoot", "stab", "kill", "destroy"},
            targets={"civilians", "people", "infrastructure", "school", "hospital", "city"},
            description="Detected threats of violence",
            severity="critical",
            penalty=40.0,
        ),
    )

    _SENSITIVE_PATTERNS: tuple[SensitivePattern, ...] = (
        SensitivePattern(
            name="api_key",
            pattern=re.compile(r"\bsk-[A-Za-z0-9]{40,}\b"),
            description="Potential API key disclosure",
            severity="high",
            penalty=25.0,
        ),
        SensitivePattern(
            name="credit_card",
            pattern=re.compile(r"\b(?:\d[ -]?){13,16}\b"),
            description="Potential credit card disclosure",
            severity="high",
            penalty=25.0,
        ),
        SensitivePattern(
            name="ssn",
            pattern=re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            description="Potential SSN disclosure",
            severity="high",
            penalty=25.0,
        ),
        SensitivePattern(
            name="private_key",
            pattern=re.compile(r"\b0x[a-f0-9]{64}\b", re.IGNORECASE),
            description="Potential private key disclosure",
            severity="critical",
            penalty=40.0,
        ),
        SensitivePattern(
            name="seed_phrase",
            pattern=re.compile(r"(seed phrase|mnemonic)\s*[:=-]?\s*([a-z]+(?:\s+[a-z]+){5,})", re.IGNORECASE),
            description="Potential seed phrase disclosure",
            severity="critical",
            penalty=45.0,
        ),
    )

    def inspect(self, output: str, context: str) -> SemanticAnalysisResult:
        """Analyze AI output for semantic policy violations."""
        issues: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        sanitized_output = output
        score = 100.0

        raw_sentences = self._split_sentences(output)
        normalized_sentences = [sentence.lower() for sentence in raw_sentences]

        # Threat vector detection using verbs + targets
        for idx, normalized_sentence in enumerate(normalized_sentences):
            tokens = set(self._tokenize(normalized_sentence))
            if not tokens:
                continue
            for vector in self._THREAT_PATTERNS:
                if tokens & vector.verbs and tokens & vector.targets:
                    snippet = raw_sentences[idx][:200]
                    penalty = self._apply_contextual_penalty(vector.penalty, vector.name, context)
                    issues.append(
                        {
                            "category": vector.name,
                            "description": vector.description,
                            "severity": vector.severity,
                            "evidence": snippet.strip(),
                        }
                    )
                    score -= penalty

        # Prompt injection attempts
        normalized_full = output.lower()
        for phrase in self._PROMPT_INJECTION_PHRASES:
            if phrase in normalized_full:
                penalty = self._apply_contextual_penalty(20.0, "prompt_injection", context)
                issues.append(
                    {
                        "category": "prompt_injection",
                        "description": f"Prompt injection attempt detected: \"{phrase}\"",
                        "severity": "high",
                        "evidence": phrase,
                    }
                )
                score -= penalty

        # Code execution attempts within code blocks
        for block in self._extract_code_blocks(output):
            lowered = block.lower()
            dangerous_calls = [call for call in self._DANGEROUS_CALLS if call in lowered]
            dangerous_imports = [imp for imp in self._DANGEROUS_IMPORTS if imp in lowered]
            if dangerous_calls or dangerous_imports:
                penalty = self._apply_contextual_penalty(35.0, "code_execution", context)
                issues.append(
                    {
                        "category": "code_execution",
                        "description": "Potential code execution payload detected",
                        "severity": "critical",
                        "evidence": block.strip()[:200],
                    }
                )
                score -= penalty

        # Sensitive data detection + redaction
        sanitized_output, sensitive_hits = self._redact_sensitive_data(sanitized_output)
        for hit in sensitive_hits:
            penalty = self._apply_contextual_penalty(hit.get("penalty", 25.0), hit["category"], context)
            hit["penalty"] = penalty
            issues.append(hit)
            score -= penalty

        # Base64 or encoded payload warnings
        for match in self._BASE64_RE.finditer(output):
            warnings.append(
                {
                    "category": "encoded_payload",
                    "description": "Detected high-entropy payload that may contain binary data",
                    "severity": "medium",
                    "evidence": match.group(0)[:80] + "...",
                }
            )
            score -= 5.0
            break  # Only warn once per output

        # Excessive length indicator
        if len(output) > 50_000:
            warnings.append(
                {
                    "category": "excessive_length",
                    "description": "Output unusually long - possible hallucination or data dump",
                    "severity": "low",
                }
            )
            score -= 5.0

        score = max(0.0, score)
        blocking_severity = {"critical", "high"}
        is_safe = not any(issue["severity"] in blocking_severity for issue in issues)
        if is_safe and score < 60.0:
            is_safe = False

        only_sensitive_issues = bool(issues) and all(issue["category"] == "sensitive_data" for issue in issues)
        sanitized_result = sanitized_output
        if not is_safe and not only_sensitive_issues:
            sanitized_result = "[OUTPUT BLOCKED - SAFETY VIOLATION]"

        return SemanticAnalysisResult(
            is_safe=is_safe,
            score=score,
            issues=issues,
            warnings=warnings,
            sanitized_output=sanitized_result,
        )

    def _split_sentences(self, text: str) -> list[str]:
        sentences = [segment.strip() for segment in self._SENTENCE_SPLIT_RE.split(text) if segment.strip()]
        return sentences or [text]

    def _tokenize(self, sentence: str) -> Iterable[str]:
        return [token for token in self._TOKEN_SPLIT_RE.split(sentence) if token]

    def _extract_code_blocks(self, text: str) -> list[str]:
        return self._CODE_BLOCK_RE.findall(text)

    def _redact_sensitive_data(self, text: str) -> tuple[str, list[dict[str, Any]]]:
        hits: list[dict[str, Any]] = []
        redacted = text
        for pattern in self._SENSITIVE_PATTERNS:
            def _replace(match: "re.Match[str]") -> str:
                hits.append(
                    {
                        "category": "sensitive_data",
                        "description": pattern.description,
                        "severity": pattern.severity,
                        "evidence": match.group(0)[:200],
                        "penalty": pattern.penalty,
                    }
                )
                return f"[REDACTED_{pattern.name.upper()}]"

            redacted = pattern.pattern.sub(_replace, redacted)
        return redacted, hits

    def _apply_contextual_penalty(self, base_penalty: float, category: str, context: str) -> float:
        """Amplify penalties for contexts where violations are more dangerous."""
        if not context:
            return base_penalty
        overrides = self._CONTEXT_PENALTY_MAP.get(context.lower())
        if not overrides:
            return base_penalty
        multiplier = overrides.get(category, 1.0)
        return base_penalty * multiplier

@dataclass
class KnowledgeEntry:
    """Structured knowledge base entry used for hallucination checks."""

    identifier: str
    content: str
    weight: float = 1.0
    required: bool = False
    source: str = "fact"
    tags: set[str] = field(default_factory=set)

class HallucinationKnowledgeBase:
    """Embeds expected facts/reference docs for hallucination detection."""

    _TOKENIZER = re.compile(r"[^\w]+", re.UNICODE)

    def __init__(self, entries: list[KnowledgeEntry] | None = None) -> None:
        self.entries: list[KnowledgeEntry] = entries or []
        self._entry_tokens: list[tuple[KnowledgeEntry, set[str]]] = [
            (entry, self._tokenize(entry.content)) for entry in self.entries
        ]

    @classmethod
    def from_context(cls, expected_context: dict[str, Any]) -> "HallucinationKnowledgeBase":
        entries: list[KnowledgeEntry] = []

        def _to_entry(item: Any, idx: int, source: str, required_default: bool = False) -> KnowledgeEntry:
            if isinstance(item, dict):
                identifier = str(item.get("id", f"{source}_{idx}"))
                content = str(item.get("content", ""))
                weight = float(item.get("weight", 1.0))
                required = bool(item.get("required", required_default))
                tags = set(str(tag).lower() for tag in item.get("tags", []))
            else:
                identifier = f"{source}_{idx}"
                content = str(item)
                weight = 1.0
                required = required_default
                tags = set()
            return KnowledgeEntry(identifier=identifier, content=content, weight=weight, required=required, source=source, tags=tags)

        for idx, fact in enumerate(expected_context.get("facts", [])):
            entries.append(_to_entry(fact, idx, "fact", required_default=True))

        for idx, doc in enumerate(expected_context.get("reference_documents", [])):
            entries.append(_to_entry(doc, idx, "reference"))

        for idx, kb_item in enumerate(expected_context.get("knowledge_base", [])):
            entries.append(_to_entry(kb_item, idx, "knowledge"))

        return cls(entries)

    def match_sentence(self, sentence: str) -> tuple[KnowledgeEntry | None, float]:
        """Return best matching entry for sentence and similarity score."""
        tokens = self._tokenize(sentence)
        if not tokens:
            return None, 0.0
        best_entry: KnowledgeEntry | None = None
        best_score = 0.0
        for entry, entry_tokens in self._entry_tokens:
            if not entry_tokens:
                continue
            overlap = len(tokens & entry_tokens)
            union = len(tokens | entry_tokens)
            token_score = overlap / union if union else 0.0
            ratio = SequenceMatcher(None, sentence.lower(), entry.content.lower()).ratio()
            combined = (0.6 * token_score + 0.4 * ratio) * entry.weight
            if combined > best_score:
                best_score = combined
                best_entry = entry
        return best_entry, best_score

    def required_entries(self) -> list[KnowledgeEntry]:
        return [entry for entry in self.entries if entry.required]

    def _tokenize(self, text: str) -> set[str]:
        return {token for token in self._TOKENIZER.split(text.lower()) if token}

class AISafetyControls:
    """
    Central safety control system for all AI operations

    Provides instant stop capabilities for:
    - Personal AI requests (per-user)
    - Trading bots (per-user)
    - Governance AI tasks (per-task)
    - Global AI operations (emergency)
    """

    def __init__(
        self,
        blockchain: Any,
        authorized_callers: set[str] | None = None,
        rate_limit_storage_path: str | None = None,
    ) -> None:
        """
        Initialize AI safety controls

        Args:
            blockchain: Reference to blockchain
            authorized_callers: Optional identifiers that can change safety level
            rate_limit_storage_path: Optional path to persist rate-limit snapshots
        """
        self.blockchain: Any = blockchain

        # Global safety level
        self.safety_level: AISafetyLevel = AISafetyLevel.NORMAL
        self._sandbox_module_guard = ModuleAttachmentGuard(
            set(SecureExecutor.SAFE_MODULES) | {"time"},
            trusted_base=Path(__file__).resolve().parents[2],
            require_attribute=None,
        )

        # Active operations tracking
        self.personal_ai_requests: dict[str, dict[str, Any]] = {}  # request_id -> request info
        self.governance_tasks: dict[str, dict[str, Any]] = {}  # task_id -> task info
        self.trading_bots: dict[str, Any] = {}  # user_address -> bot instance

        # Cancellation tracking
        self.cancelled_requests: set[str] = set()  # request_ids to cancel
        self.paused_tasks: set[str] = set()  # task_ids paused

        # Emergency stop
        self.emergency_stop_active: bool = False
        self.emergency_stop_reason: StopReason | None = None
        self.emergency_stop_time: float | None = None

        # Statistics
        self.total_stops: int = 0
        self.total_cancellations: int = 0

        # Authorized safety callers (lowercase normalized)
        self.authorized_callers: set[str] = {
            "governance_dao",
            "security_committee",
            "ai_safety_team",
            "remediation_script",
            "system",
            "test_system",
        }
        if authorized_callers:
            self.authorized_callers.update(c.lower() for c in authorized_callers)

        # Lock for thread safety
        self.lock: threading.Lock = threading.Lock()
        self._output_inspector = _SemanticOutputInspector()

        # Persistent rate limit tracking
        self._rate_limit_lock = threading.Lock()
        self._rate_limit_entry_ttl = float(os.getenv("XAI_AI_SAFETY_RATE_LIMIT_TTL", 7 * 86400))
        self.rate_limit_storage_path = self._init_rate_limit_store(rate_limit_storage_path)
        limits_state = self._load_rate_limit_state()
        self.token_usage: dict[str, dict[str, float]] = limits_state["users"]
        self.provider_usage: dict[str, dict[str, float]] = limits_state["providers"]
        self.provider_limits = self._load_provider_limits()
        self.sandboxes: dict[str, dict[str, Any]] = {}

    def _init_rate_limit_store(self, override_path: str | None) -> Path:
        """Resolve and prepare storage path for token usage state."""
        if override_path:
            path = Path(override_path).expanduser()
        else:
            env_path = os.getenv("XAI_AI_SAFETY_RATE_LIMIT_PATH")
            if env_path:
                path = Path(env_path).expanduser()
            else:
                path = Path.home() / ".xai" / "ai_safety" / "rate_limits.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _load_rate_limit_state(self) -> dict[str, dict[str, dict[str, float]]]:
        """Load persisted rate limit usage from disk."""
        path = self.rate_limit_storage_path
        if not path.exists():
            return {"users": {}, "providers": {}}
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load AI safety rate limits: %s", exc)
            return {"users": {}, "providers": {}}

        now = time.time()
        user_state: dict[str, dict[str, float]] = {}
        provider_state: dict[str, dict[str, float]] = {}

        raw_users = data.get("users") if isinstance(data, dict) else data
        if isinstance(raw_users, dict):
            for identifier, entry in raw_users.items():
                if not isinstance(entry, dict):
                    continue
                day_start = float(entry.get("day_start", 0))
                tokens_used = float(entry.get("tokens_used", 0))
                if day_start <= 0 or now - day_start > self._rate_limit_entry_ttl * 2:
                    continue
                user_state[str(identifier)] = {"day_start": day_start, "tokens_used": tokens_used}

        raw_providers = data.get("providers") if isinstance(data, dict) else {}
        if isinstance(raw_providers, dict):
            for provider, entry in raw_providers.items():
                if not isinstance(entry, dict):
                    continue
                window_start = float(entry.get("window_start", now))
                call_count = float(entry.get("call_count", 0))
                day_start = float(entry.get("day_start", 0))
                tokens_used = float(entry.get("tokens_used", 0))
                provider_state[str(provider)] = {
                    "window_start": window_start,
                    "call_count": call_count,
                    "day_start": day_start,
                    "tokens_used": tokens_used,
                }

        return {"users": user_state, "providers": provider_state}

    def _persist_rate_limit_state(self) -> None:
        """Persist current rate limit usage to disk atomically."""
        path = self.rate_limit_storage_path
        tmp_path = path.parent / f"{path.name}.tmp"
        snapshot = {
            "users": self.token_usage,
            "providers": self.provider_usage,
        }
        try:
            serialized = json.dumps(snapshot, separators=(",", ":"), sort_keys=True)
            tmp_path.write_text(serialized)
            tmp_path.replace(path)
        except OSError as exc:
            logger.warning("Failed to persist AI safety rate limits: %s", exc)

    def _purge_stale_rate_limit_entries(self, now: float | None = None) -> None:
        """Remove expired rate limit entries to keep state compact."""
        reference = now or time.time()
        ttl = self._rate_limit_entry_ttl
        stale_identifiers = [
            identifier
            for identifier, entry in self.token_usage.items()
            if reference - float(entry.get("day_start", 0)) > ttl
        ]
        for identifier in stale_identifiers:
            self.token_usage.pop(identifier, None)

        provider_ttl = ttl
        stale_providers = [
            provider
            for provider, entry in self.provider_usage.items()
            if reference - float(entry.get("day_start", 0)) > provider_ttl
        ]
        for provider in stale_providers:
            self.provider_usage.pop(provider, None)

    def _load_provider_limits(self) -> dict[str, dict[str, float]]:
        """Load provider-specific call/token limits."""
        default_limits = {
            "default": {
                "max_calls_per_window": 30,
                "window_seconds": 60.0,
                "max_tokens_per_day": 500_000.0,
            },
            "anthropic": {
                "max_calls_per_window": 12,
                "window_seconds": 60.0,
                "max_tokens_per_day": 400_000.0,
            },
            "openai": {
                "max_calls_per_window": 20,
                "window_seconds": 60.0,
                "max_tokens_per_day": 600_000.0,
            },
            "google": {
                "max_calls_per_window": 10,
                "window_seconds": 60.0,
                "max_tokens_per_day": 300_000.0,
            },
            "perplexity": {
                "max_calls_per_window": 6,
                "window_seconds": 60.0,
                "max_tokens_per_day": 150_000.0,
            },
        }

        raw = os.getenv("XAI_PROVIDER_RATE_LIMITS_JSON")
        if raw:
            try:
                overrides = json.loads(raw)
                if isinstance(overrides, dict):
                    for provider, cfg in overrides.items():
                        if not isinstance(cfg, dict):
                            continue
                        normalized = self._normalize_provider_name(provider)
                        default_limits[normalized] = {
                            "max_calls_per_window": float(cfg.get("max_calls_per_window", cfg.get("max_calls", 0))),
                            "window_seconds": float(cfg.get("window_seconds", cfg.get("window", 60.0))),
                            "max_tokens_per_day": float(cfg.get("max_tokens_per_day", cfg.get("max_tokens", 0))),
                        }
            except json.JSONDecodeError as exc:
                logger.warning("Failed to parse XAI_PROVIDER_RATE_LIMITS_JSON: %s", exc)

        return default_limits

    def _normalize_provider_name(self, provider: str | None) -> str:
        if not provider:
            return ""
        return provider.strip().lower()

    def _update_provider_usage_locked(
        self,
        provider: str,
        tokens_used: float,
        current_time: float,
        increment_call: bool = True,
    ) -> dict[str, Any]:
        """Update provider usage assuming `_rate_limit_lock` is held."""
        normalized = self._normalize_provider_name(provider)
        limits = self.provider_limits.get(normalized) or self.provider_limits.get("default")
        if not limits or not normalized:
            return {"success": True, "provider": normalized}

        window_seconds = float(limits.get("window_seconds", 60.0))
        max_calls = limits.get("max_calls_per_window")
        max_tokens = limits.get("max_tokens_per_day")
        entry = self.provider_usage.setdefault(
            normalized,
            {
                "window_start": current_time,
                "call_count": 0.0,
                "day_start": current_time - (current_time % 86400),
                "tokens_used": 0.0,
            },
        )

        if current_time - entry["window_start"] >= window_seconds:
            entry["window_start"] = current_time
            entry["call_count"] = 0.0

        if increment_call:
            entry["call_count"] += 1.0

        call_allowed = True
        if max_calls:
            call_allowed = entry["call_count"] <= max_calls

        day_start = current_time - (current_time % 86400)
        if entry["day_start"] < day_start:
            entry["day_start"] = day_start
            entry["tokens_used"] = 0.0

        entry["tokens_used"] += tokens_used
        token_allowed = True
        if max_tokens:
            token_allowed = entry["tokens_used"] <= max_tokens

        return {
            "success": call_allowed and token_allowed,
            "provider": normalized,
            "call_count": entry["call_count"],
            "max_calls": max_calls,
            "tokens_used_today": entry["tokens_used"],
            "max_tokens": max_tokens,
            "window_seconds": window_seconds,
        }

    def enforce_provider_request_limit(self, provider: str | None) -> dict[str, Any]:
        """Public helper to enforce call limits for a provider."""
        normalized = self._normalize_provider_name(provider)
        if not normalized:
            return {"success": True, "provider": normalized}
        with self._rate_limit_lock:
            result = self._update_provider_usage_locked(normalized, 0.0, time.time(), increment_call=True)
            self._persist_rate_limit_state()
        return result

    # ===== PERSONAL AI CONTROLS =====

    def register_personal_ai_request(
        self, request_id: str, user_address: str, operation: str, ai_provider: str, ai_model: str
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

        provider_check = self.enforce_provider_request_limit(ai_provider)
        if not provider_check.get("success", True):
            logger.warning(
                "AI provider rate limit exceeded",
                extra={
                    "event": "ai.provider_rate_limited",
                    "provider": provider_check.get("provider"),
                    "call_count": provider_check.get("call_count"),
                },
            )
            return False

        with self.lock:
            self.personal_ai_requests[request_id] = {
                "user": user_address,
                "operation": operation,
                "ai_provider": ai_provider,
                "ai_model": ai_model,
                "started": time.time(),
                "status": "running",
            }

        return True

    def cancel_personal_ai_request(self, request_id: str, user_address: str) -> dict:
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
                return {"success": False, "error": "Request not found"}

            request = self.personal_ai_requests[request_id]

            # Verify ownership
            if request["user"] != user_address:
                return {"success": False, "error": "Can only cancel your own requests"}

            # Mark as cancelled
            self.cancelled_requests.add(request_id)
            request["status"] = "cancelled"
            request["cancelled_time"] = time.time()

            self.total_cancellations += 1

        return {
            "success": True,
            "message": f"Personal AI request {request_id} cancelled",
            "operation": request["operation"],
            "runtime_seconds": time.time() - request["started"],
        }

    def is_request_cancelled(self, request_id: str) -> bool:
        """Check if a request has been cancelled"""
        return request_id in self.cancelled_requests

    def complete_personal_ai_request(self, request_id: str) -> None:
        """Mark request as completed (cleanup)"""
        with self.lock:
            if request_id in self.personal_ai_requests:
                self.personal_ai_requests[request_id]["status"] = "completed"
                self.personal_ai_requests[request_id]["completed_time"] = time.time()

    # ===== TRADING BOT CONTROLS =====

    def register_trading_bot(self, user_address: str, bot_instance: Any) -> bool:
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

    def emergency_stop_trading_bot(self, user_address: str) -> dict:
        """
        Emergency stop for trading bot (instant)

        Args:
            user_address: Bot owner

        Returns:
            Stop result
        """

        with self.lock:
            if user_address not in self.trading_bots:
                return {"success": False, "error": "No active trading bot"}

            bot = self.trading_bots[user_address]
            result = bot.stop()

            self.total_stops += 1

        return {
            "success": True,
            "message": "[STOP] EMERGENCY STOP: Trading bot stopped immediately",
            "bot_result": result,
        }

    def stop_all_trading_bots(self, reason: StopReason) -> dict[str, Any]:
        """
        Stop ALL trading bots (emergency)

        Args:
            reason: Why bots are being stopped

        Returns:
            Stop results
        """

        stopped_count: int = 0
        errors: list[str] = []

        with self.lock:
            for user_address, bot in self.trading_bots.items():
                try:
                    bot.stop()
                    stopped_count += 1
                except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                    logger.error(
                        "Exception in stop_all_trading_bots",
                        extra={
                            "error_type": "Exception",
                            "error": str(e),
                            "function": "stop_all_trading_bots"
                        }
                    )
                    errors.append(f"{user_address}: {e}")

            self.total_stops += stopped_count

        return {
            "success": True,
            "stopped_count": stopped_count,
            "errors": errors,
            "reason": reason.value,
        }

    def authorize_safety_caller(self, identifier: str) -> dict[str, Any]:
        """Add an identifier that can change safety level"""

        if not identifier:
            return {"success": False, "error": "INVALID_IDENTIFIER"}

        with self.lock:
            self.authorized_callers.add(identifier.lower())

        return {
            "success": True,
            "caller": identifier.lower(),
            "message": "Authorized caller can now change AI safety level",
        }

    def revoke_safety_caller(self, identifier: str) -> dict[str, Any]:
        """Remove an identifier from safety level changes"""

        if not identifier:
            return {"success": False, "error": "INVALID_IDENTIFIER"}

        with self.lock:
            self.authorized_callers.discard(identifier.lower())

        return {
            "success": True,
            "caller": identifier.lower(),
            "message": "Caller no longer authorized to change AI safety level",
        }

    def is_authorized_caller(self, identifier: str) -> bool:
        """Check if caller is authorized to adjust AI safety level"""

        if not identifier:
            return False

        with self.lock:
            return identifier.lower() in self.authorized_callers

    # ===== GOVERNANCE AI CONTROLS =====

    def register_governance_task(
        self, task_id: str, proposal_id: str, task_type: str, ai_count: int
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
                "proposal_id": proposal_id,
                "task_type": task_type,
                "ai_count": ai_count,
                "started": time.time(),
                "status": "running",
                "paused": False,
            }

        return True

    def pause_governance_task(self, task_id: str, pauser: str) -> dict[str, Any]:
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
                return {"success": False, "error": "Task not found"}

            task = self.governance_tasks[task_id]

            # Pause task
            self.paused_tasks.add(task_id)
            task["paused"] = True
            task["paused_time"] = time.time()
            task["paused_by"] = pauser

        return {
            "success": True,
            "message": f"[PAUSE] Governance task {task_id} paused",
            "task_type": task["task_type"],
            "proposal_id": task["proposal_id"],
        }

    def resume_governance_task(self, task_id: str) -> dict[str, Any]:
        """Resume a paused Governance AI task"""

        with self.lock:
            if task_id not in self.governance_tasks:
                return {"success": False, "error": "Task not found"}

            if task_id not in self.paused_tasks:
                return {"success": False, "error": "Task not paused"}

            task = self.governance_tasks[task_id]

            # Resume
            self.paused_tasks.remove(task_id)
            task["paused"] = False
            task["resumed_time"] = time.time()

        return {"success": True, "message": f"[RESUME] Governance task {task_id} resumed"}

    def is_task_paused(self, task_id: str) -> bool:
        """Check if task is paused"""
        return task_id in self.paused_tasks

    # ===== GLOBAL EMERGENCY STOP =====

    def activate_emergency_stop(
        self, reason: StopReason, details: str = "", activator: str = "system"
    ) -> dict[str, Any]:
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
                "success": False,
                "error": "UNAUTHORIZED_ACTIVATOR",
                "message": f"{activator} cannot trigger emergency stop",
            }

        logger.critical(
            "EMERGENCY STOP ACTIVATED",
            extra={
                "event": "ai.emergency_stop.activated",
                "reason": reason.value,
                "details": details,
                "activator": activator,
            },
        )

        with self.lock:
            self.emergency_stop_active: bool = True
            self.emergency_stop_reason: StopReason = reason
            self.emergency_stop_time: float = time.time()

            # Stop all Personal AI requests
            for request_id in list(self.personal_ai_requests.keys()):
                self.cancelled_requests.add(request_id)
                self.personal_ai_requests[request_id]["status"] = "emergency_stopped"

            # Pause all Governance AI tasks
            for task_id in list(self.governance_tasks.keys()):
                self.paused_tasks.add(task_id)
                self.governance_tasks[task_id]["paused"] = True

        # Stop all trading bots
        trading_bot_result: dict[str, Any] = self.stop_all_trading_bots(reason)

        logger.critical(
            "Emergency stop complete",
            extra={
                "event": "ai.emergency_stop.complete",
                "reason": reason.value,
                "details": details,
                "activator": activator,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "personal_ai_stopped": len(self.personal_ai_requests),
                "governance_tasks_paused": len(self.governance_tasks),
                "trading_bots_stopped": trading_bot_result["stopped_count"],
            },
        )

        return {
            "success": True,
            "message": "[EMERGENCY] All AI operations halted",
            "reason": reason.value,
            "details": details,
            "activated_by": activator,
            "timestamp": time.time(),
            "personal_ai_stopped": len(self.personal_ai_requests),
            "governance_tasks_paused": len(self.governance_tasks),
            "trading_bots_stopped": trading_bot_result["stopped_count"],
        }

    def deactivate_emergency_stop(self, deactivator: str) -> dict[str, Any]:
        """
        Deactivate emergency stop (allow AI operations to resume)

        Args:
            deactivator: Who is deactivating

        Returns:
            Deactivation result
        """

        if not self.emergency_stop_active:
            return {
                "success": False,
                "error": "Emergency stop not active",
                "message": "No active emergency stop to deactivate",
            }

        with self.lock:
            self.emergency_stop_active: bool = False
            duration: float = time.time() - (self.emergency_stop_time or 0)

        logger.warning(
            "Emergency stop deactivated - AI operations can resume",
            extra={
                "event": "ai.emergency_stop.deactivated",
                "deactivator": deactivator,
                "duration_seconds": duration,
            },
        )

        return {
            "success": True,
            "message": "Emergency stop deactivated. AI operations can resume.",
            "deactivated_by": deactivator,
            "duration_seconds": duration,
        }

    def set_safety_level(self, level: AISafetyLevel, setter: str) -> dict[str, Any]:
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
                "success": False,
                "error": "UNAUTHORIZED_CALLER",
                "message": f"{setter} is not authorized to change safety level",
            }

        old_level: AISafetyLevel = self.safety_level

        with self.lock:
            self.safety_level = level

        # Auto-actions based on level
        if level == AISafetyLevel.EMERGENCY_STOP:
            self.activate_emergency_stop(
                StopReason.SECURITY_THREAT, "Safety level set to EMERGENCY_STOP", setter
            )
        elif level == AISafetyLevel.LOCKDOWN:
            self.activate_emergency_stop(
                StopReason.SECURITY_THREAT, "Safety level set to LOCKDOWN", setter
            )

        return {
            "success": True,
            "old_level": old_level.value,
            "new_level": level.value,
            "set_by": setter,
        }

    # ===== STATUS & MONITORING =====

    def get_status(self) -> dict[str, Any]:
        """Get current AI safety status"""

        with self.lock:
            status: dict[str, Any] = {
                "safety_level": self.safety_level.value,
                "emergency_stop_active": self.emergency_stop_active,
                "personal_ai": {
                    "total_requests": len(self.personal_ai_requests),
                    "running": sum(
                        1 for r in self.personal_ai_requests.values() if r["status"] == "running"
                    ),
                    "cancelled": len(self.cancelled_requests),
                },
                "governance_ai": {
                    "total_tasks": len(self.governance_tasks),
                    "running": sum(1 for t in self.governance_tasks.values() if not t["paused"]),
                    "paused": len(self.paused_tasks),
                },
                "trading_bots": {"active_bots": len(self.trading_bots)},
                "statistics": {
                    "total_stops": self.total_stops,
                    "total_cancellations": self.total_cancellations,
                },
            }

            if (
                self.emergency_stop_active
                and self.emergency_stop_reason
                and self.emergency_stop_time
            ):
                status["emergency_stop"] = {
                    "reason": self.emergency_stop_reason.value,
                    "duration_seconds": time.time() - self.emergency_stop_time,
                    "activated": time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(self.emergency_stop_time)
                    ),
                }

        return status

    def get_active_operations(self) -> dict[str, list[dict[str, Any]]]:
        """Get list of all active AI operations"""

        with self.lock:
            return {
                "personal_ai_requests": [
                    {
                        "request_id": rid,
                        "user": req["user"],
                        "operation": req["operation"],
                        "status": req["status"],
                        "runtime": time.time() - req["started"],
                    }
                    for rid, req in self.personal_ai_requests.items()
                    if req["status"] == "running"
                ],
                "governance_tasks": [
                    {
                        "task_id": tid,
                        "task_type": task["task_type"],
                        "status": task["status"],
                        "paused": task["paused"],
                        "runtime": time.time() - task["started"],
                    }
                    for tid, task in self.governance_tasks.items()
                    if task["status"] == "running"
                ],
                "trading_bots": [
                    {
                        "user": user,
                        "is_active": bot.is_active if hasattr(bot, "is_active") else False,
                    }
                    for user, bot in self.trading_bots.items()
                ],
            }

    # ===== OUTPUT VALIDATION & SANDBOXING =====

    def validate_ai_output(self, output: str, context: str = "general") -> dict[str, Any]:
        """
        Validate AI output using semantic safety analysis.

        Args:
            output: AI-generated content
            context: Context of generation (governance, trading, etc.)

        Returns:
            Validation result with semantic insights and redactions.
        """
        analysis = self._output_inspector.inspect(output, context)
        response = {
            "is_safe": analysis.is_safe,
            "safety_score": analysis.score,
            "issues_found": analysis.issues,
            "warnings": analysis.warnings,
            "sanitized_output": analysis.sanitized_output,
        }
        return response

    def create_ai_sandbox(self, sandbox_id: str, resource_limits: dict | None = None) -> dict:
        """
        Create sandboxed environment for AI execution

        Args:
            sandbox_id: Unique sandbox identifier
            resource_limits: Optional resource limits

        Returns:
            Sandbox creation result
        """
        if resource_limits is None:
            resource_limits = {
                "max_memory_mb": 512,
                "max_cpu_percent": 50,
                "max_execution_time_seconds": 300,
                "max_network_requests": 10,
                "allowed_imports": ["json", "time", "math", "hashlib"],
                "blocked_operations": ["file_write", "network_call", "subprocess"],
            }

        sandbox = {
            "sandbox_id": sandbox_id,
            "created_at": time.time(),
            "resource_limits": resource_limits,
            "current_usage": {
                "memory_mb": 0,
                "cpu_percent": 0,
                "execution_time": 0,
                "network_requests": 0,
            },
            "is_active": True,
            "violations": [],
        }

        with self.lock:
            self.sandboxes[sandbox_id] = sandbox

        return {"success": True, "sandbox": sandbox}

    def record_sandbox_usage(self, sandbox_id: str, usage: dict[str, float]) -> dict[str, Any]:
        """Record runtime metrics for a sandbox and enforce resource caps."""
        with self.lock:
            sandbox = self.sandboxes.get(sandbox_id)
            if not sandbox:
                return {"success": False, "error": "sandbox_not_found"}
            if not sandbox["is_active"]:
                return {"success": False, "error": "sandbox_inactive"}

            current = sandbox["current_usage"]
            for metric, value in usage.items():
                if metric == "network_requests":
                    current["network_requests"] = current.get("network_requests", 0) + float(value)
                else:
                    current[metric] = float(value)

            current["execution_time"] = time.time() - sandbox["created_at"]
            violations = self._evaluate_sandbox_limits(sandbox)
            if violations:
                sandbox["violations"].extend(violations)
                sandbox["is_active"] = False
                return {"success": False, "violations": violations}

            return {"success": True, "current_usage": dict(current)}

    def enforce_sandbox_action(
        self,
        sandbox_id: str,
        action: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Validate sandbox actions such as imports or operations."""
        with self.lock:
            sandbox = self.sandboxes.get(sandbox_id)
            if not sandbox:
                return {"success": False, "error": "sandbox_not_found"}
            if not sandbox["is_active"]:
                return {"success": False, "error": "sandbox_inactive"}

            limits = sandbox["resource_limits"]
            blocked_ops = {op.lower() for op in limits.get("blocked_operations", [])}
            normalized_action = action.lower()

            if normalized_action in blocked_ops:
                violation = self._register_sandbox_violation(
                    sandbox, f"Operation '{action}' is blocked"
                )
                return {"success": False, "violations": [violation]}

            if normalized_action == "import":
                allowed = {imp.lower() for imp in limits.get("allowed_imports", [])}
                module = (metadata or {}).get("module", "")
                module_normalized = module.lower()
                if allowed and module_normalized not in allowed:
                    violation = self._register_sandbox_violation(
                        sandbox,
                        f"Import '{module}' is not permitted in sandbox",
                    )
                    return {"success": False, "violations": [violation]}
                try:
                    self._sandbox_module_guard.verify_module(module_normalized)
                except ModuleAttachmentError as exc:
                    violation = self._register_sandbox_violation(
                        sandbox,
                        f"Import '{module}' failed attachment validation: {exc}",
                    )
                    return {"success": False, "violations": [violation]}

            return {"success": True}

    def close_sandbox(self, sandbox_id: str) -> None:
        """Mark sandbox as inactive."""
        with self.lock:
            sandbox = self.sandboxes.get(sandbox_id)
            if sandbox:
                sandbox["is_active"] = False

    # ===== RATE LIMITING =====

    def check_rate_limit(
        self, identifier: str, operation: str, max_calls: int = 100, window_seconds: int = 3600
    ) -> dict[str, Any]:
        """
        Rate limiting for AI calls

        Args:
            identifier: User/address identifier
            operation: Type of operation
            max_calls: Maximum calls allowed
            window_seconds: Time window in seconds

        Returns:
            Rate limit check result
        """
        key = f"{identifier}:{operation}"
        current_time = time.time()

        # Initialize if not exists
        if not hasattr(self, "rate_limit_data"):
            self.rate_limit_data: dict[str, list[float]] = {}

        if key not in self.rate_limit_data:
            self.rate_limit_data[key] = []

        # Remove old entries outside window
        self.rate_limit_data[key] = [
            ts for ts in self.rate_limit_data[key] if current_time - ts < window_seconds
        ]

        # Check limit
        current_calls = len(self.rate_limit_data[key])
        is_allowed = current_calls < max_calls

        if is_allowed:
            # Record this call
            self.rate_limit_data[key].append(current_time)

        return {
            "allowed": is_allowed,
            "current_calls": current_calls if is_allowed else current_calls,
            "max_calls": max_calls,
            "window_seconds": window_seconds,
            "reset_in_seconds": window_seconds
            - (current_time - min(self.rate_limit_data[key]))
            if self.rate_limit_data[key]
            else 0,
        }

    # ===== TOKEN USAGE LIMITS =====

    def track_token_usage(
        self,
        identifier: str,
        tokens_used: int,
        max_tokens: int = 1000000,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """
        Track and enforce token usage limits with persistent storage.

        Args:
            identifier: User/address identifier
            tokens_used: Tokens used in this request
            max_tokens: Maximum tokens allowed per day
            provider: Optional AI provider identifier for provider-level limits

        Returns:
            Token tracking result
        """
        current_time = time.time()
        day_start = current_time - (current_time % 86400)

        provider_result: dict[str, Any] | None = None
        with self._rate_limit_lock:
            self._purge_stale_rate_limit_entries(current_time)
            entry = self.token_usage.get(identifier)
            if entry is None:
                entry = {"day_start": day_start, "tokens_used": 0.0}
                self.token_usage[identifier] = entry

            # Reset if a new day has started
            if entry["day_start"] < day_start:
                entry["day_start"] = day_start
                entry["tokens_used"] = 0.0

            entry["tokens_used"] += float(tokens_used)
            current_usage = entry["tokens_used"]
            is_within_limit = current_usage <= max_tokens

            if provider:
                provider_result = self._update_provider_usage_locked(
                    provider, float(tokens_used), current_time, increment_call=False
                )
            else:
                provider_result = None

            self._persist_rate_limit_state()

        success = is_within_limit and (provider_result.get("success", True) if provider_result else True)
        result = {
            "success": success,
            "tokens_used_today": current_usage,
            "max_tokens": max_tokens,
            "remaining_tokens": max(0, max_tokens - current_usage),
            "percentage_used": min(100, (current_usage / max_tokens) * 100) if max_tokens else 100,
        }
        if provider_result:
            result["provider_limit"] = provider_result
        return result

    def _evaluate_sandbox_limits(self, sandbox: dict[str, Any]) -> list[dict[str, Any]]:
        """Check sandbox usage against limits."""
        limits = sandbox["resource_limits"]
        current = sandbox["current_usage"]
        violations = []

        if current.get("memory_mb", 0) > limits.get("max_memory_mb", float("inf")):
            violations.append(
                {"type": "memory", "message": "Memory usage exceeded", "value": current["memory_mb"]}
            )
        if current.get("cpu_percent", 0) > limits.get("max_cpu_percent", float("inf")):
            violations.append(
                {"type": "cpu", "message": "CPU usage exceeded", "value": current["cpu_percent"]}
            )
        if current.get("execution_time", 0) > limits.get("max_execution_time_seconds", float("inf")):
            violations.append(
                {
                    "type": "execution_time",
                    "message": "Execution time exceeded",
                    "value": current["execution_time"],
                }
            )
        if current.get("network_requests", 0) > limits.get("max_network_requests", float("inf")):
            violations.append(
                {
                    "type": "network",
                    "message": "Network request limit exceeded",
                    "value": current["network_requests"],
                }
            )

        return violations

    def _register_sandbox_violation(self, sandbox: dict[str, Any], message: str) -> dict[str, Any]:
        violation = {"timestamp": time.time(), "message": message}
        sandbox["violations"].append(violation)
        sandbox["is_active"] = False
        return violation

    # ===== HALLUCINATION DETECTION =====

    def detect_hallucination(self, ai_output: str, expected_context: dict) -> dict[str, Any]:
        """
        Detect potential AI hallucinations using knowledge base cross-checks.

        Args:
            ai_output: AI-generated output
            expected_context: Expected context/constraints and knowledge documents

        Returns:
            Hallucination detection result with detailed indicators
        """
        context = expected_context or {}
        knowledge_base = HallucinationKnowledgeBase.from_context(context)
        sentences = self._output_inspector._split_sentences(ai_output)
        normalized_output = ai_output.lower()

        confidence_score = 100.0
        unsupported_sentences: list[dict[str, Any]] = []
        knowledge_matches: list[dict[str, Any]] = []
        matched_required_ids: set[str] = set()
        contradiction_hits: list[dict[str, Any]] = []
        forbidden_hits: list[str] = []
        required_term_alerts: list[str] = []
        numeric_anomalies: list[dict[str, Any]] = []

        match_threshold = float(context.get("knowledge_match_threshold", 0.45))
        considered_sentences = [
            sentence.strip()
            for sentence in sentences
            if sentence and len(sentence.strip()) >= context.get("min_sentence_length", 20)
        ]

        for sentence in considered_sentences:
            entry, score = knowledge_base.match_sentence(sentence)
            if entry and score >= match_threshold:
                knowledge_matches.append(
                    {
                        "sentence": sentence,
                        "matched_entry": entry.identifier,
                        "entry_source": entry.source,
                        "similarity": round(score, 3),
                    }
                )
                if entry.required:
                    matched_required_ids.add(entry.identifier)
            else:
                unsupported_sentences.append({"sentence": sentence, "similarity": round(score, 3)})
                confidence_score -= 7.0

        required_entries = knowledge_base.required_entries()
        missing_required = [
            entry.identifier for entry in required_entries if entry.identifier not in matched_required_ids
        ]
        if missing_required:
            confidence_score -= 12.0 * len(missing_required)

        # Contradictions defined by context
        for contradiction in context.get("contradictions", []):
            claim = str(contradiction.get("claim", "")).lower()
            expected = contradiction.get("expected")
            severity = contradiction.get("severity", "high")
            if claim and claim in normalized_output:
                contradiction_hits.append({"claim": claim, "expected": expected, "severity": severity})
                confidence_score -= 15.0

        # Forbidden terms/entities
        for term in context.get("forbidden_terms", []):
            if str(term).lower() in normalized_output:
                forbidden_hits.append(str(term))
                confidence_score -= 20.0

        # Required terms/entities
        for term in context.get("required_terms", []):
            if str(term).lower() not in normalized_output:
                required_term_alerts.append(str(term))
                confidence_score -= 10.0

        # Numeric expectations (range or tolerance checks)
        for spec in context.get("numeric_expectations", []):
            pattern = spec.get("pattern")
            if not pattern:
                continue
            regex = re.compile(pattern, re.IGNORECASE)
            matches = list(regex.finditer(ai_output))
            if not matches:
                continue
            scale = float(spec.get("scale", 1.0))
            tolerance = float(spec.get("tolerance", 0.0))
            expected_value = spec.get("expected")
            min_value = spec.get("min")
            max_value = spec.get("max")
            label = spec.get("label", "value")
            for match in matches:
                try:
                    value = float(match.group("value")) * scale
                except (ValueError, KeyError):
                    continue
                violation = False
                details: dict[str, Any] = {"label": label, "value": value}
                if expected_value is not None and abs(value - float(expected_value)) > tolerance:
                    violation = True
                    details["expected"] = expected_value
                    details["tolerance"] = tolerance
                if min_value is not None and value < float(min_value):
                    violation = True
                    details["min"] = min_value
                if max_value is not None and value > float(max_value):
                    violation = True
                    details["max"] = max_value
                if violation:
                    numeric_anomalies.append(details)
                    confidence_score -= 12.0

        # Heuristic checks for excessive certainty or unrealistic magnitudes
        certainty_words = ["definitely", "absolutely", "certainly", "undoubtedly", "guaranteed"]
        certainty_hits = sum(1 for word in certainty_words if word in normalized_output)
        if certainty_hits > 4:
            confidence_score -= 8.0

        long_numbers = re.findall(r"\b\d{10,}\b", ai_output)
        if long_numbers:
            confidence_score -= 6.0

        coverage_ratio = (
            len(knowledge_matches) / len(considered_sentences) if considered_sentences else 1.0
        )
        if knowledge_base.entries and coverage_ratio < context.get("min_coverage_ratio", 0.5):
            confidence_score -= 10.0

        confidence_score = max(0.0, confidence_score)
        hallucination_threshold = float(context.get("hallucination_threshold", 75.0))
        hallucination_detected = (
            confidence_score < hallucination_threshold
            or bool(contradiction_hits)
            or bool(numeric_anomalies)
            or bool(forbidden_hits)
        )

        return {
            "confidence_score": confidence_score,
            "hallucination_detected": hallucination_detected,
            "unsupported_sentences": unsupported_sentences,
            "missing_facts": missing_required,
            "knowledge_matches": knowledge_matches,
            "contradictions": contradiction_hits,
            "forbidden_terms": forbidden_hits,
            "required_term_alerts": required_term_alerts,
            "numeric_anomalies": numeric_anomalies,
            "coverage_ratio": coverage_ratio,
        }

# Example usage
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stdout)

    logger.info("XAI AI Safety & Emergency Stop System")
    logger.info("=" * 50)
    logger.info("Safety Controls:")
    logger.info("1. Personal AI request cancellation (user-level)")
    logger.info("2. Trading bot emergency stop")
    logger.info("3. Governance AI task pause/abort")
    logger.info("4. Global AI emergency stop (all operations)")
    logger.info("Principle: Users have INSTANT control over AI")
