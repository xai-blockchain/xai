"""
AI Task Execution Metrics for XAI Blockchain

Comprehensive Prometheus metrics for AI task lifecycle, provider management,
and execution tracking following proven patterns.
"""

from prometheus_client import REGISTRY, CollectorRegistry, Counter, Gauge, Histogram, Summary


class AITaskMetrics:
    """Metrics for AI task execution and provider management."""

    def __init__(self, registry=None):
        self.registry = registry or REGISTRY

        # Job lifecycle metrics
        self.jobs_submitted = Counter(
            'xai_ai_jobs_submitted_total',
            'Total AI jobs submitted',
            ['job_type'],
            registry=self.registry
        )

        self.jobs_accepted = Counter(
            'xai_ai_jobs_accepted_total',
            'Total jobs accepted by providers',
            ['provider'],
            registry=self.registry
        )

        self.jobs_completed = Counter(
            'xai_ai_jobs_completed_total',
            'Total jobs completed',
            ['provider', 'status'],
            registry=self.registry
        )

        self.jobs_failed = Counter(
            'xai_ai_jobs_failed_total',
            'Total jobs failed',
            ['provider', 'reason'],
            registry=self.registry
        )

        self.job_execution_time = Histogram(
            'xai_ai_job_execution_seconds',
            'Job execution time in seconds',
            buckets=[1, 5, 10, 30, 60, 300, 600, 1800],
            registry=self.registry
        )

        self.job_queue_size = Gauge(
            'xai_ai_job_queue_size',
            'Current number of jobs in queue',
            registry=self.registry
        )

        # Provider management metrics
        self.providers_registered = Counter(
            'xai_ai_providers_registered_total',
            'Total AI providers registered',
            ['capability'],
            registry=self.registry
        )

        self.providers_active = Gauge(
            'xai_ai_providers_active',
            'Currently active AI providers',
            registry=self.registry
        )

        self.provider_reputation = Gauge(
            'xai_ai_provider_reputation_score',
            'Provider reputation score (0-100)',
            ['provider'],
            registry=self.registry
        )

        self.provider_stake = Gauge(
            'xai_ai_provider_stake',
            'Provider stake amount',
            ['provider', 'denom'],
            registry=self.registry
        )

        self.provider_slashing = Counter(
            'xai_ai_provider_slashing_events_total',
            'Provider slashing events',
            ['provider', 'reason'],
            registry=self.registry
        )

        # Model selection and routing metrics
        self.model_selections = Counter(
            'xai_ai_model_selections_total',
            'AI model selection events',
            ['model', 'provider'],
            registry=self.registry
        )

        self.model_switching = Counter(
            'xai_ai_model_switching_total',
            'Model switching events (auto-switching)',
            ['from_model', 'to_model', 'reason'],
            registry=self.registry
        )

        # Execution pool metrics
        self.pool_utilization = Gauge(
            'xai_ai_pool_utilization_percentage',
            'AI execution pool utilization',
            ['pool_id'],
            registry=self.registry
        )

        self.pool_queue_depth = Gauge(
            'xai_ai_pool_queue_depth',
            'Tasks queued in execution pool',
            ['pool_id'],
            registry=self.registry
        )

        # AI trading bot metrics
        self.trading_decisions = Counter(
            'xai_ai_trading_decisions_total',
            'AI trading bot decisions',
            ['decision_type', 'model'],
            registry=self.registry
        )

        self.trading_accuracy = Gauge(
            'xai_ai_trading_accuracy_percentage',
            'AI trading prediction accuracy',
            ['model', 'timeframe'],
            registry=self.registry
        )

        # Cost and billing metrics
        self.task_costs = Histogram(
            'xai_ai_task_cost_tokens',
            'Task cost in tokens',
            buckets=[10, 50, 100, 500, 1000, 5000, 10000],
            registry=self.registry
        )

        self.revenue_by_provider = Counter(
            'xai_ai_revenue_by_provider_total',
            'Revenue earned by providers',
            ['provider', 'denom'],
            registry=self.registry
        )

        # Performance metrics
        self.inference_latency = Histogram(
            'xai_ai_inference_latency_seconds',
            'AI inference latency',
            ['model', 'provider'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
            registry=self.registry
        )

        self.batch_processing_time = Histogram(
            'xai_ai_batch_processing_seconds',
            'Batch job processing time',
            ['batch_size'],
            registry=self.registry
        )

        # Quality metrics
        self.task_retries = Counter(
            'xai_ai_task_retries_total',
            'Task retry attempts',
            ['provider', 'reason'],
            registry=self.registry
        )

        self.quality_score = Gauge(
            'xai_ai_task_quality_score',
            'Task output quality score',
            ['provider', 'task_type'],
            registry=self.registry
        )


# Singleton instance
_ai_metrics_instance = None


def get_ai_task_metrics(registry=None):
    """Get or create singleton AI task metrics instance."""
    global _ai_metrics_instance
    if _ai_metrics_instance is None:
        _ai_metrics_instance = AITaskMetrics(registry=registry)
    return _ai_metrics_instance


# Convenience function for tracking job execution
def track_job_execution(job_type, provider, duration_seconds, status='success'):
    """Track AI job execution with automatic metric updates."""
    metrics = get_ai_task_metrics()

    # Record completion
    metrics.jobs_completed.labels(
        provider=provider,
        status=status
    ).inc()

    # Record execution time
    metrics.job_execution_time.observe(duration_seconds)


# Convenience function for tracking provider reputation
def update_provider_reputation(provider_id, reputation_score):
    """Update provider reputation score."""
    metrics = get_ai_task_metrics()
    metrics.provider_reputation.labels(provider=provider_id).set(reputation_score)
