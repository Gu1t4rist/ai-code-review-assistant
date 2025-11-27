"""Prometheus metrics instrumentation.

NOTE: Metrics collection is currently DISABLED by default (enable_metrics=False in config).
This module is kept for future enhancement. When enabled, it provides:
- Code review metrics (duration, issues found, files processed)
- API call metrics (GitLab, AI providers)
- HTTP request metrics
- Webhook event metrics

To enable: Set ENABLE_METRICS=true in .env file
"""

from typing import Callable

from prometheus_client import Counter, Gauge, Histogram, generate_latest
from prometheus_client.core import CollectorRegistry

# Create a custom registry
registry = CollectorRegistry()

# Review metrics
review_total = Counter(
    "code_review_total",
    "Total number of code reviews performed",
    ["ai_provider", "ai_model", "status"],
    registry=registry,
)

review_duration_seconds = Histogram(
    "code_review_duration_seconds",
    "Duration of code review in seconds",
    ["ai_provider", "ai_model"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
    registry=registry,
)

review_files_processed = Histogram(
    "code_review_files_processed",
    "Number of files processed per review",
    ["ai_provider"],
    buckets=[1, 5, 10, 20, 50, 100],
    registry=registry,
)

review_issues_found = Counter(
    "code_review_issues_found_total",
    "Total number of issues found",
    ["severity", "ai_provider"],
    registry=registry,
)

# API metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
    registry=registry,
)

# GitLab API metrics
gitlab_api_calls_total = Counter(
    "gitlab_api_calls_total",
    "Total GitLab API calls",
    ["operation", "status"],
    registry=registry,
)

gitlab_api_duration_seconds = Histogram(
    "gitlab_api_duration_seconds",
    "GitLab API call duration in seconds",
    ["operation"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
    registry=registry,
)

# AI Provider metrics
ai_api_calls_total = Counter(
    "ai_api_calls_total",
    "Total AI provider API calls",
    ["provider", "model", "status"],
    registry=registry,
)

ai_api_duration_seconds = Histogram(
    "ai_api_duration_seconds",
    "AI provider API call duration in seconds",
    ["provider", "model"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0],
    registry=registry,
)

ai_tokens_used = Counter(
    "ai_tokens_used_total",
    "Total AI tokens used",
    ["provider", "model", "token_type"],
    registry=registry,
)

# Webhook metrics
webhook_events_total = Counter(
    "webhook_events_total",
    "Total webhook events received",
    ["event_type", "status"],
    registry=registry,
)

# System metrics
active_reviews = Gauge(
    "active_reviews",
    "Number of reviews currently in progress",
    registry=registry,
)

# Error metrics
errors_total = Counter(
    "errors_total",
    "Total errors",
    ["error_type", "component"],
    registry=registry,
)


def get_metrics() -> bytes:
    """Get metrics in Prometheus format."""
    return generate_latest(registry)


class MetricsTimer:
    """Context manager for timing operations."""

    def __init__(self, histogram: Histogram, labels: dict[str, str] | None = None):
        """Initialize timer.
        
        Args:
            histogram: Histogram to record duration
            labels: Labels for the histogram
        """
        self.histogram = histogram
        self.labels = labels or {}
        self.timer = None

    def __enter__(self) -> "MetricsTimer":
        """Start timer."""
        if self.labels:
            self.timer = self.histogram.labels(**self.labels).time()
        else:
            self.timer = self.histogram.time()
        self.timer.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop timer."""
        if self.timer:
            self.timer.__exit__(exc_type, exc_val, exc_tb)


def track_review_decorator(ai_provider: str, ai_model: str) -> Callable:
    """Decorator to track review metrics.
    
    Args:
        ai_provider: AI provider name
        ai_model: AI model name
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            active_reviews.inc()
            try:
                with MetricsTimer(
                    review_duration_seconds,
                    {"ai_provider": ai_provider, "ai_model": ai_model},
                ):
                    result = await func(*args, **kwargs)
                review_total.labels(
                    ai_provider=ai_provider,
                    ai_model=ai_model,
                    status="success",
                ).inc()
                return result
            except Exception as e:
                review_total.labels(
                    ai_provider=ai_provider,
                    ai_model=ai_model,
                    status="error",
                ).inc()
                errors_total.labels(
                    error_type=type(e).__name__,
                    component="review_engine",
                ).inc()
                raise
            finally:
                active_reviews.dec()
        return wrapper
    return decorator
