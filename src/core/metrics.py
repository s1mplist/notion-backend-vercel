"""
Monitoring and metrics collection module.

Provides execution tracking, performance metrics, and health monitoring.
"""

import time
import asyncio
from functools import wraps
from typing import Dict, Any, Callable, Optional
from collections import defaultdict, deque
import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MetricData:
    """Metric data container."""

    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExecutionStats:
    """Execution statistics container."""

    total_calls: int = 0
    total_duration: float = 0.0
    success_count: int = 0
    error_count: int = 0
    min_duration: float = float("inf")
    max_duration: float = 0.0
    recent_durations: deque = field(default_factory=lambda: deque(maxlen=100))

    def add_execution(self, duration: float, success: bool = True):
        """Add execution data."""
        self.total_calls += 1
        self.total_duration += duration
        self.min_duration = min(self.min_duration, duration)
        self.max_duration = max(self.max_duration, duration)
        self.recent_durations.append(duration)

        if success:
            self.success_count += 1
        else:
            self.error_count += 1

    @property
    def average_duration(self) -> float:
        """Calculate average duration."""
        return self.total_duration / self.total_calls if self.total_calls > 0 else 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        return (
            (self.success_count / self.total_calls * 100)
            if self.total_calls > 0
            else 0.0
        )

    @property
    def recent_average_duration(self) -> float:
        """Calculate recent average duration."""
        if not self.recent_durations:
            return 0.0
        return sum(self.recent_durations) / len(self.recent_durations)


class MetricsCollector:
    """Collects and manages application metrics."""

    def __init__(self):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.execution_stats: Dict[str, ExecutionStats] = defaultdict(ExecutionStats)
        self.start_time = datetime.now()

    def record_metric(
        self, name: str, value: float, tags: Optional[Dict[str, str]] = None
    ):
        """Record a metric value."""
        metric = MetricData(
            name=name, value=value, timestamp=datetime.now(), tags=tags or {}
        )
        self.metrics[name].append(metric)
        logger.debug(f"Metric recorded: {name}={value} {tags or ''}")

    def record_execution(
        self, function_name: str, duration: float, success: bool = True
    ):
        """Record function execution statistics."""
        stats = self.execution_stats[function_name]
        stats.add_execution(duration, success)

        # Also record as metrics
        self.record_metric(f"{function_name}.duration", duration)
        self.record_metric(f"{function_name}.success", 1 if success else 0)

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        uptime = datetime.now() - self.start_time

        stats = {
            "uptime_seconds": uptime.total_seconds(),
            "uptime_human": str(uptime),
            "functions": {},
        }

        for func_name, exec_stats in self.execution_stats.items():
            stats["functions"][func_name] = {
                "total_calls": exec_stats.total_calls,
                "success_count": exec_stats.success_count,
                "error_count": exec_stats.error_count,
                "success_rate": round(exec_stats.success_rate, 2),
                "average_duration": round(exec_stats.average_duration, 4),
                "recent_average_duration": round(exec_stats.recent_average_duration, 4),
                "min_duration": round(exec_stats.min_duration, 4)
                if exec_stats.min_duration != float("inf")
                else 0,
                "max_duration": round(exec_stats.max_duration, 4),
            }

        return stats

    def get_health_status(self) -> Dict[str, Any]:
        """Get application health status."""
        stats = self.get_stats()

        # Determine health based on error rates
        overall_health = "healthy"
        issues = []

        for func_name, func_stats in stats["functions"].items():
            error_rate = 100 - func_stats["success_rate"]
            if error_rate > 10:  # More than 10% error rate
                overall_health = "degraded"
                issues.append(f"{func_name}: {error_rate:.1f}% error rate")
            elif error_rate > 25:  # More than 25% error rate
                overall_health = "unhealthy"

        return {
            "status": overall_health,
            "timestamp": datetime.now().isoformat(),
            "uptime": stats["uptime_human"],
            "issues": issues,
            "functions_monitored": len(stats["functions"]),
        }


def track_execution_time(func_name: Optional[str] = None):
    """
    Decorator to track function execution time and success rate.

    Args:
        func_name: Custom name for the function (uses actual name if None)
    """

    def decorator(func: Callable):
        name = func_name or func.__name__

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                logger.error(f"{name} failed: {e}", exc_info=True)
                raise
            finally:
                duration = time.time() - start_time
                metrics_collector.record_execution(name, duration, success)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                logger.error(f"{name} failed: {e}", exc_info=True)
                raise
            finally:
                duration = time.time() - start_time
                metrics_collector.record_execution(name, duration, success)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Global metrics collector instance
metrics_collector = MetricsCollector()
