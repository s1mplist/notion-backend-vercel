"""
Test core functionality - configuration, rate limiting, and metrics.
"""

import pytest
import asyncio
from datetime import datetime


class TestConfiguration:
    """Test configuration management."""

    def test_settings_loading(self, mock_environment):
        """Test settings loading from environment."""
        from core.config import get_settings

        settings = get_settings()

        assert settings.notion_api_token == "test-token-123"
        assert settings.vercel_blob_store_id == "test-store-id"
        assert settings.vercel_blob_token == "test-blob-token"
        assert settings.notion_database_id == "test-database-id"

    def test_settings_validation(self):
        """Test settings validation."""
        from core.config import Settings

        # Test missing required fields
        with pytest.raises(ValueError):
            Settings()

    def test_settings_cache(self, mock_environment):
        """Test settings caching."""
        from core.config import get_settings

        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the same instance due to caching
        assert settings1 is settings2


class TestRateLimiter:
    """Test rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_within_limit(self):
        """Test rate limiter allows requests within limit."""
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_requests=5, window_seconds=60)

        # Should allow first 5 requests
        for _ in range(5):
            allowed = await limiter.is_allowed("test-key")
            assert allowed is True

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_over_limit(self):
        """Test rate limiter blocks requests over limit."""
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_requests=2, window_seconds=60)

        # Use up the limit
        await limiter.is_allowed("test-key")
        await limiter.is_allowed("test-key")

        # Third request should be blocked
        allowed = await limiter.is_allowed("test-key")
        assert allowed is False

    @pytest.mark.asyncio
    async def test_rate_limiter_sliding_window(self):
        """Test rate limiter sliding window behavior."""
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_requests=2, window_seconds=1)

        # Use up limit
        await limiter.is_allowed("test-key")
        await limiter.is_allowed("test-key")

        # Should be blocked immediately
        allowed = await limiter.is_allowed("test-key")
        assert allowed is False

        # Wait for window to slide
        await asyncio.sleep(1.1)

        # Should be allowed again
        allowed = await limiter.is_allowed("test-key")
        assert allowed is True

    @pytest.mark.asyncio
    async def test_rate_limiter_different_keys(self):
        """Test rate limiter with different keys."""
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_requests=1, window_seconds=60)

        # Different keys should have separate limits
        allowed1 = await limiter.is_allowed("key1")
        allowed2 = await limiter.is_allowed("key2")

        assert allowed1 is True
        assert allowed2 is True

    @pytest.mark.asyncio
    async def test_rate_limiter_wait_if_needed(self):
        """Test rate limiter wait functionality."""
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_requests=1, window_seconds=0.5)

        # Use up limit
        await limiter.is_allowed("test-key")

        start_time = datetime.now()
        await limiter.wait_if_needed("test-key")
        end_time = datetime.now()

        # Should have waited approximately the window duration
        wait_time = (end_time - start_time).total_seconds()
        assert wait_time >= 0.4  # Allow some tolerance


class TestMetrics:
    """Test metrics collection."""

    def test_metrics_collector_initialization(self):
        """Test metrics collector initialization."""
        from core.metrics import MetricsCollector

        collector = MetricsCollector()

        assert len(collector.execution_times) == 0
        assert collector.error_count == 0
        assert collector.total_requests == 0

    def test_metrics_record_execution_time(self):
        """Test recording execution times."""
        from core.metrics import MetricsCollector

        collector = MetricsCollector()

        collector.record_execution_time("test_operation", 1.5)
        collector.record_execution_time("test_operation", 2.0)

        assert len(collector.execution_times["test_operation"]) == 2
        assert collector.execution_times["test_operation"][0] == 1.5
        assert collector.execution_times["test_operation"][1] == 2.0

    def test_metrics_record_error(self):
        """Test recording errors."""
        from core.metrics import MetricsCollector

        collector = MetricsCollector()

        collector.record_error()
        collector.record_error()

        assert collector.error_count == 2

    def test_metrics_get_statistics(self):
        """Test getting statistics."""
        from core.metrics import MetricsCollector

        collector = MetricsCollector()

        # Add some test data
        collector.record_execution_time("test_op", 1.0)
        collector.record_execution_time("test_op", 2.0)
        collector.record_execution_time("test_op", 3.0)
        collector.record_error()
        collector.total_requests = 10

        stats = collector.get_statistics()

        assert stats.total_requests == 10
        assert stats.error_count == 1
        assert stats.error_rate == 0.1
        assert "test_op" in stats.avg_execution_times
        assert stats.avg_execution_times["test_op"] == 2.0

    def test_metrics_health_status(self):
        """Test health status calculation."""
        from core.metrics import MetricsCollector

        collector = MetricsCollector()

        # Healthy system
        collector.total_requests = 100
        collector.error_count = 1
        assert collector.is_healthy() is True

        # Unhealthy system
        collector.error_count = 20  # 20% error rate
        assert collector.is_healthy() is False

        # No requests yet
        collector.total_requests = 0
        collector.error_count = 0
        assert collector.is_healthy() is True

    @pytest.mark.asyncio
    async def test_track_execution_time_decorator(self):
        """Test execution time tracking decorator."""
        from core.metrics import track_execution_time, get_metrics_collector

        collector = get_metrics_collector()
        collector.reset()  # Clear any existing data

        @track_execution_time("test_function")
        async def test_async_function():
            await asyncio.sleep(0.1)
            return "result"

        result = await test_async_function()

        assert result == "result"
        assert "test_function" in collector.execution_times
        assert len(collector.execution_times["test_function"]) == 1
        assert collector.execution_times["test_function"][0] >= 0.1

    def test_track_execution_time_decorator_sync(self):
        """Test execution time tracking decorator for sync functions."""
        from core.metrics import track_execution_time, get_metrics_collector
        import time

        collector = get_metrics_collector()
        collector.reset()

        @track_execution_time("sync_function")
        def test_sync_function():
            time.sleep(0.1)
            return "sync_result"

        result = test_sync_function()

        assert result == "sync_result"
        assert "sync_function" in collector.execution_times
        assert len(collector.execution_times["sync_function"]) == 1
        assert collector.execution_times["sync_function"][0] >= 0.1
