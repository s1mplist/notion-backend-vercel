"""
Rate limiting module for API calls.

Implements rate limiting to prevent API abuse and respect external API limits.
"""

import asyncio
import time
from collections import defaultdict, deque
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Sliding window rate limiter.

    Prevents excessive API calls by implementing a sliding window algorithm.
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str) -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Unique identifier for the rate limit (e.g., IP, user ID)

        Returns:
            True if request is allowed, False otherwise
        """
        async with self._lock:
            now = time.time()
            window_start = now - self.window_seconds

            # Clean old requests outside the window
            requests_queue = self.requests[key]
            while requests_queue and requests_queue[0] < window_start:
                requests_queue.popleft()

            # Check if we can make the request
            if len(requests_queue) < self.max_requests:
                requests_queue.append(now)
                logger.debug(
                    f"Rate limit check for {key}: {len(requests_queue)}/{self.max_requests}"
                )
                return True

            logger.warning(
                f"Rate limit exceeded for {key}: {len(requests_queue)}/{self.max_requests}"
            )
            return False

    async def wait_if_needed(self, key: str, max_wait_seconds: float = 60.0) -> bool:
        """
        Wait if rate limit is exceeded, return when request can be made.

        Args:
            key: Unique identifier for the rate limit
            max_wait_seconds: Maximum time to wait before giving up

        Returns:
            True if request can now be made, False if timeout
        """
        if await self.is_allowed(key):
            return True

        start_time = time.time()

        while time.time() - start_time < max_wait_seconds:
            # Calculate wait time until next slot is available
            async with self._lock:
                requests_queue = self.requests[key]
                if requests_queue:
                    oldest_request = requests_queue[0]
                    wait_time = oldest_request + self.window_seconds - time.time()
                    if wait_time > 0:
                        logger.info(f"Rate limited {key}, waiting {wait_time:.1f}s")
                        await asyncio.sleep(min(wait_time, 1.0))

                    if await self.is_allowed(key):
                        return True
                else:
                    # No requests in queue, should be allowed now
                    return await self.is_allowed(key)

        logger.error(f"Rate limit timeout for {key} after {max_wait_seconds}s")
        return False

    def get_stats(self, key: str) -> Dict[str, int]:
        """
        Get rate limiting statistics for a key.

        Args:
            key: Unique identifier for the rate limit

        Returns:
            Dictionary with current usage stats
        """
        now = time.time()
        window_start = now - self.window_seconds

        requests_queue = self.requests[key]
        # Count requests in current window
        current_requests = sum(
            1 for req_time in requests_queue if req_time >= window_start
        )

        return {
            "current_requests": current_requests,
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "remaining_requests": max(0, self.max_requests - current_requests),
        }


# Global rate limiter instances
notion_rate_limiter = RateLimiter(
    max_requests=100, window_seconds=60
)  # Notion API limits
webhook_rate_limiter = RateLimiter(
    max_requests=1000, window_seconds=60
)  # Webhook processing
