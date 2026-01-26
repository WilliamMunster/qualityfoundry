"""MCP Rate Limiter

并发限制、速率限制、配额管理模块。

Features:
- 并发限制：per-user 同时调用数上限
- 速率限制：token bucket 算法
- 配额管理：daily/hourly 调用次数上限
"""

from __future__ import annotations

import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Optional
from datetime import date

logger = logging.getLogger(__name__)


# ==================== 配置常量 ====================

DEFAULT_CONCURRENT_LIMIT = 2  # 每用户最大并发数
DEFAULT_RATE_LIMIT_PER_MIN = 10  # 每分钟最大调用数
DEFAULT_DAILY_QUOTA = 100  # 每日配额


@dataclass
class RateLimitResult:
    """限流检查结果"""
    allowed: bool
    reason: Optional[str] = None
    retry_after_seconds: Optional[float] = None
    
    @staticmethod
    def ok() -> "RateLimitResult":
        return RateLimitResult(allowed=True)
    
    @staticmethod
    def denied(reason: str, retry_after: Optional[float] = None) -> "RateLimitResult":
        return RateLimitResult(allowed=False, reason=reason, retry_after_seconds=retry_after)


@dataclass
class TokenBucket:
    """Token Bucket 速率限制"""
    capacity: float  # 桶容量
    tokens: float    # 当前 token 数
    refill_rate: float  # 每秒补充速率
    last_refill: float = field(default_factory=time.monotonic)
    
    def try_consume(self, tokens: float = 1.0) -> tuple[bool, float]:
        """尝试消费 token
        
        Returns:
            (success, wait_seconds) - success 为 False 时，wait_seconds 表示需等待时间
        """
        now = time.monotonic()
        elapsed = now - self.last_refill
        
        # 补充 tokens
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True, 0.0
        else:
            # 需要等待的秒数
            wait = (tokens - self.tokens) / self.refill_rate
            return False, wait


@dataclass
class DailyUsage:
    """每日使用统计"""
    date: date
    call_count: int = 0
    elapsed_ms_total: float = 0.0
    
    def increment(self, elapsed_ms: float = 0.0) -> None:
        self.call_count += 1
        self.elapsed_ms_total += elapsed_ms
    
    def is_today(self) -> bool:
        return self.date == date.today()


class MCPRateLimiter:
    """MCP 调用限流器
    
    线程安全实现，支持：
    - 并发限制 (per user_id)
    - 速率限制 (token bucket per user_id)
    - 每日配额 (per user_id)
    """
    
    def __init__(
        self,
        concurrent_limit: int = DEFAULT_CONCURRENT_LIMIT,
        rate_limit_per_min: int = DEFAULT_RATE_LIMIT_PER_MIN,
        daily_quota: int = DEFAULT_DAILY_QUOTA,
    ):
        self.concurrent_limit = concurrent_limit
        self.rate_limit_per_min = rate_limit_per_min
        self.daily_quota = daily_quota
        
        # 状态存储
        self._lock = threading.Lock()
        self._active: dict[str, int] = {}  # user_id -> active_count
        self._buckets: dict[str, TokenBucket] = {}  # user_id -> bucket
        self._usage: dict[str, DailyUsage] = {}  # user_id -> daily_usage
    
    def _get_bucket(self, user_id: str) -> TokenBucket:
        """获取或创建 token bucket"""
        if user_id not in self._buckets:
            # 每分钟 N 次 = 容量 N，补充速率 N/60 per second
            self._buckets[user_id] = TokenBucket(
                capacity=float(self.rate_limit_per_min),
                tokens=float(self.rate_limit_per_min),
                refill_rate=self.rate_limit_per_min / 60.0,
            )
        return self._buckets[user_id]
    
    def _get_usage(self, user_id: str) -> DailyUsage:
        """获取或创建当日使用统计"""
        if user_id not in self._usage or not self._usage[user_id].is_today():
            self._usage[user_id] = DailyUsage(date=date.today())
        return self._usage[user_id]
    
    def check_limits(self, user_id: str) -> RateLimitResult:
        """检查所有限制
        
        Args:
            user_id: 用户 ID
            
        Returns:
            RateLimitResult: 是否允许调用
        """
        with self._lock:
            # 1. 并发限制
            active = self._active.get(user_id, 0)
            if active >= self.concurrent_limit:
                logger.warning(
                    f"Concurrent limit exceeded for user {user_id}: "
                    f"{active}/{self.concurrent_limit}"
                )
                return RateLimitResult.denied(
                    reason="CONCURRENT_LIMIT_EXCEEDED",
                    retry_after=1.0,  # 建议 1 秒后重试
                )
            
            # 2. 速率限制
            bucket = self._get_bucket(user_id)
            success, wait = bucket.try_consume(1.0)
            if not success:
                logger.warning(
                    f"Rate limit exceeded for user {user_id}, "
                    f"retry after {wait:.2f}s"
                )
                return RateLimitResult.denied(
                    reason="RATE_LIMIT_EXCEEDED",
                    retry_after=wait,
                )
            
            # 3. 每日配额
            usage = self._get_usage(user_id)
            if usage.call_count >= self.daily_quota:
                logger.warning(
                    f"Daily quota exceeded for user {user_id}: "
                    f"{usage.call_count}/{self.daily_quota}"
                )
                return RateLimitResult.denied(
                    reason="QUOTA_EXCEEDED",
                    retry_after=None,  # 明日重置
                )
            
            return RateLimitResult.ok()
    
    def acquire(self, user_id: str) -> None:
        """获取执行槽位（增加并发计数）"""
        with self._lock:
            self._active[user_id] = self._active.get(user_id, 0) + 1
            logger.debug(f"Acquired slot for {user_id}, active: {self._active[user_id]}")
    
    def release(self, user_id: str, elapsed_ms: float = 0.0) -> None:
        """释放执行槽位（减少并发计数 + 记录使用）"""
        with self._lock:
            if user_id in self._active:
                self._active[user_id] = max(0, self._active[user_id] - 1)
                if self._active[user_id] == 0:
                    del self._active[user_id]
            
            # 记录使用统计
            usage = self._get_usage(user_id)
            usage.increment(elapsed_ms)
            logger.debug(
                f"Released slot for {user_id}, "
                f"daily calls: {usage.call_count}/{self.daily_quota}"
            )
    
    def get_usage_stats(self, user_id: str) -> dict:
        """获取用户使用统计"""
        with self._lock:
            usage = self._get_usage(user_id)
            active = self._active.get(user_id, 0)
            bucket = self._get_bucket(user_id)
            
            return {
                "user_id": user_id,
                "active_calls": active,
                "concurrent_limit": self.concurrent_limit,
                "tokens_remaining": bucket.tokens,
                "rate_limit_per_min": self.rate_limit_per_min,
                "daily_calls": usage.call_count,
                "daily_quota": self.daily_quota,
                "daily_elapsed_ms": usage.elapsed_ms_total,
            }


# 全局单例
_rate_limiter: Optional[MCPRateLimiter] = None


def get_rate_limiter() -> MCPRateLimiter:
    """获取全局限流器实例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = MCPRateLimiter()
    return _rate_limiter


def reset_rate_limiter() -> None:
    """重置限流器（用于测试）"""
    global _rate_limiter
    _rate_limiter = None
