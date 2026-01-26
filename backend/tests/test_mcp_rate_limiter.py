"""MCP Rate Limiter Tests

测试并发限制、速率限制、配额管理功能。
"""

import time

from qualityfoundry.protocol.mcp.rate_limiter import (
    MCPRateLimiter,
    TokenBucket,
    DailyUsage,
    get_rate_limiter,
    reset_rate_limiter,
)


class TestTokenBucket:
    """Token Bucket 单元测试"""

    def test_try_consume_success(self):
        bucket = TokenBucket(capacity=10.0, tokens=10.0, refill_rate=1.0)
        success, wait = bucket.try_consume(1.0)
        assert success is True
        assert wait == 0.0
        assert bucket.tokens == 9.0

    def test_try_consume_empty_bucket(self):
        bucket = TokenBucket(capacity=10.0, tokens=0.0, refill_rate=1.0)
        success, wait = bucket.try_consume(1.0)
        assert success is False
        assert wait > 0

    def test_refill_over_time(self):
        bucket = TokenBucket(capacity=10.0, tokens=0.0, refill_rate=10.0)  # 10/s
        time.sleep(0.1)  # Wait 100ms
        success, _ = bucket.try_consume(0.5)  # Should have ~1 token
        assert success is True


class TestDailyUsage:
    """Daily Usage 单元测试"""

    def test_increment(self):
        from datetime import date
        usage = DailyUsage(date=date.today())
        usage.increment(100.0)
        assert usage.call_count == 1
        assert usage.elapsed_ms_total == 100.0

    def test_is_today(self):
        from datetime import date, timedelta
        today = DailyUsage(date=date.today())
        yesterday = DailyUsage(date=date.today() - timedelta(days=1))
        assert today.is_today() is True
        assert yesterday.is_today() is False


class TestMCPRateLimiter:
    """MCPRateLimiter 集成测试"""

    def setup_method(self):
        reset_rate_limiter()

    def test_concurrent_limit_allows_within_limit(self):
        limiter = MCPRateLimiter(concurrent_limit=2)
        
        # 第一次调用应该允许
        result = limiter.check_limits("user1")
        assert result.allowed is True
        limiter.acquire("user1")
        
        # 第二次调用也应该允许
        result = limiter.check_limits("user1")
        assert result.allowed is True
        limiter.acquire("user1")
        
        # 第三次应该被拒绝
        result = limiter.check_limits("user1")
        assert result.allowed is False
        assert result.reason == "CONCURRENT_LIMIT_EXCEEDED"

    def test_concurrent_limit_release(self):
        limiter = MCPRateLimiter(concurrent_limit=1)
        
        limiter.acquire("user1")
        result = limiter.check_limits("user1")
        assert result.allowed is False
        
        limiter.release("user1")
        result = limiter.check_limits("user1")
        assert result.allowed is True

    def test_rate_limit_token_bucket(self):
        limiter = MCPRateLimiter(rate_limit_per_min=2)  # 2 calls/min
        
        # 第一次和第二次应该允许
        result = limiter.check_limits("user1")
        assert result.allowed is True
        result = limiter.check_limits("user1")
        assert result.allowed is True
        
        # 第三次应该被限流
        result = limiter.check_limits("user1")
        assert result.allowed is False
        assert result.reason == "RATE_LIMIT_EXCEEDED"
        assert result.retry_after_seconds is not None

    def test_daily_quota_exceeded(self):
        limiter = MCPRateLimiter(daily_quota=2)
        
        # 消费配额
        limiter.release("user1")  # call 1
        limiter.release("user1")  # call 2
        
        # 第三次应该超配额
        result = limiter.check_limits("user1")
        assert result.allowed is False
        assert result.reason == "QUOTA_EXCEEDED"

    def test_get_usage_stats(self):
        limiter = MCPRateLimiter(concurrent_limit=2, rate_limit_per_min=10, daily_quota=100)
        limiter.acquire("user1")
        limiter.release("user1", elapsed_ms=500.0)
        
        stats = limiter.get_usage_stats("user1")
        assert stats["user_id"] == "user1"
        assert stats["active_calls"] == 0
        assert stats["daily_calls"] == 1
        assert stats["daily_elapsed_ms"] == 500.0

    def test_different_users_isolated(self):
        limiter = MCPRateLimiter(concurrent_limit=1)
        
        limiter.acquire("user1")
        result = limiter.check_limits("user1")
        assert result.allowed is False
        
        # user2 不受 user1 影响
        result = limiter.check_limits("user2")
        assert result.allowed is True


class TestGlobalRateLimiter:
    """全局限流器测试"""

    def setup_method(self):
        reset_rate_limiter()

    def test_get_rate_limiter_singleton(self):
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2

    def test_reset_creates_new_instance(self):
        limiter1 = get_rate_limiter()
        reset_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is not limiter2
