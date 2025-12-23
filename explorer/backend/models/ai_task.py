from __future__ import annotations

"""
AI Task models for XAI Explorer
"""
from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime
from enum import Enum

class TaskType(str, Enum):
    """AI task types"""
    SECURITY_AUDIT = "security_audit"
    CORE_FEATURE = "core_feature"
    BUG_FIX = "bug_fix"
    OPTIMIZATION = "optimization"
    SMART_CONTRACT = "smart_contract"
    TESTING = "testing"
    DOCUMENTATION = "documentation"

class TaskComplexity(str, Enum):
    """Task complexity levels"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    CRITICAL = "critical"

class TaskStatus(str, Enum):
    """Task status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class AITask(BaseModel):
    """AI Task model"""
    task_id: str
    task_type: TaskType
    complexity: TaskComplexity
    priority: str
    status: TaskStatus
    requester_address: str | None = None
    provider_address: str | None = None
    ai_model: str | None = None
    estimated_tokens: int | None = None
    actual_tokens: int | None = None
    cost_estimate: float | None = None
    actual_cost: float | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    compute_time_seconds: int | None = None
    result_hash: str | None = None
    result_data: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime

class AIProvider(BaseModel):
    """AI Provider model"""
    provider_address: str
    provider_name: str | None = None
    registration_date: datetime
    status: str = "active"
    reputation_score: float = 0.0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    total_earnings: float = 0.0
    average_compute_time: float | None = None
    uptime_percentage: float | None = None
    supported_models: list[str] = []
    hardware_specs: dict[str, Any] | None = None
    contact_info: dict[str, Any] | None = None
    created_at: datetime

class AIModelStats(BaseModel):
    """AI Model statistics"""
    model_name: str
    provider: str
    total_tasks: int = 0
    success_rate: float = 0.0
    average_compute_time: float | None = None
    average_cost: float | None = None
    quality_score: float | None = None
    last_used: datetime | None = None
    created_at: datetime
