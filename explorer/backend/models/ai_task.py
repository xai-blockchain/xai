"""
AI Task models for XAI Explorer
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
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
    requester_address: Optional[str] = None
    provider_address: Optional[str] = None
    ai_model: Optional[str] = None
    estimated_tokens: Optional[int] = None
    actual_tokens: Optional[int] = None
    cost_estimate: Optional[float] = None
    actual_cost: Optional[float] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    compute_time_seconds: Optional[int] = None
    result_hash: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime


class AIProvider(BaseModel):
    """AI Provider model"""
    provider_address: str
    provider_name: Optional[str] = None
    registration_date: datetime
    status: str = "active"
    reputation_score: float = 0.0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    total_earnings: float = 0.0
    average_compute_time: Optional[float] = None
    uptime_percentage: Optional[float] = None
    supported_models: list[str] = []
    hardware_specs: Optional[Dict[str, Any]] = None
    contact_info: Optional[Dict[str, Any]] = None
    created_at: datetime


class AIModelStats(BaseModel):
    """AI Model statistics"""
    model_name: str
    provider: str
    total_tasks: int = 0
    success_rate: float = 0.0
    average_compute_time: Optional[float] = None
    average_cost: Optional[float] = None
    quality_score: Optional[float] = None
    last_used: Optional[datetime] = None
    created_at: datetime
