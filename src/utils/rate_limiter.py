"""IP 级别请求限流

**Feature: production-readiness**
"""

import time
import os
from typing import Dict, Optional
from dataclasses import dataclass, field
from threading import Lock

from src.utils.logger import get_logger


@dataclass
class RateLimitRecord:
    """限流记录"""
    ip: str
    request_count: int = 0
    window_start: float = field(default_factory=time.time)
    blocked_until: Optional[float] = None


class RateLimiter:
    """IP 级别请求限流器
    
    使用滑动窗口算法实现限流
    """
    
    def __init__(self, requests_per_minute: int = None):
        # 从环境变量读取配置，默认 100 请求/分钟
        self.requests_per_minute = requests_per_minute or int(
            os.environ.get('RATE_LIMIT_PER_MINUTE', '100')
        )
        self.window_size = 60  # 1 分钟窗口
        
        # 内存存储限流记录
        self._records: Dict[str, RateLimitRecord] = {}
        self._lock = Lock()
        
        self.logger = get_logger('rate_limiter')
        self.logger.info(f"限流器初始化：{self.requests_per_minute} 请求/分钟")
    
    def is_allowed(self, ip: str) -> bool:
        """检查 IP 是否允许请求
        
        Args:
            ip: 客户端 IP 地址
            
        Returns:
            bool: True 表示允许请求，False 表示被限流
        """
        with self._lock:
            now = time.time()
            
            # 获取或创建记录
            if ip not in self._records:
                self._records[ip] = RateLimitRecord(ip=ip, window_start=now)
            
            record = self._records[ip]
            
            # 检查是否在阻塞期内
            if record.blocked_until and now < record.blocked_until:
                return False

            # 检查窗口是否过期，需要重置
            if now - record.window_start >= self.window_size:
                record.window_start = now
                record.request_count = 0
                record.blocked_until = None
            
            # 检查是否超过限制
            if record.request_count >= self.requests_per_minute:
                # 设置阻塞到窗口结束
                record.blocked_until = record.window_start + self.window_size
                
                self.logger.warning(
                    f"IP {ip} 超过限流阈值 {self.requests_per_minute}/min，"
                    f"当前请求数：{record.request_count}"
                )
                return False
            
            # 允许请求，增加计数
            record.request_count += 1
            return True
    
    def get_retry_after(self, ip: str) -> int:
        """获取重试等待时间（秒）
        
        Args:
            ip: 客户端 IP 地址
            
        Returns:
            int: 重试等待时间（秒），0 表示可以立即重试
        """
        with self._lock:
            if ip not in self._records:
                return 0
            
            record = self._records[ip]
            now = time.time()
            
            if record.blocked_until and now < record.blocked_until:
                return int(record.blocked_until - now) + 1
            
            # 计算到窗口结束的时间
            window_end = record.window_start + self.window_size
            if now < window_end and record.request_count >= self.requests_per_minute:
                return int(window_end - now) + 1
            
            return 0
    
    def get_remaining_requests(self, ip: str) -> int:
        """获取剩余请求数
        
        Args:
            ip: 客户端 IP 地址
            
        Returns:
            int: 当前窗口内剩余请求数
        """
        with self._lock:
            if ip not in self._records:
                return self.requests_per_minute
            
            record = self._records[ip]
            now = time.time()
            
            # 窗口过期，重置计数
            if now - record.window_start >= self.window_size:
                return self.requests_per_minute
            
            return max(0, self.requests_per_minute - record.request_count)
    
    def cleanup_expired_records(self) -> None:
        """清理过期的限流记录
        
        定期调用此方法以释放内存
        """
        with self._lock:
            now = time.time()
            expired_ips = []
            
            for ip, record in self._records.items():
                # 记录超过 2 个窗口周期未活动，则清理
                if now - record.window_start > self.window_size * 2:
                    expired_ips.append(ip)
            
            for ip in expired_ips:
                del self._records[ip]
            
            if expired_ips:
                self.logger.debug(f"清理了 {len(expired_ips)} 个过期限流记录")
    
    def get_stats(self) -> Dict[str, int]:
        """获取限流统计信息
        
        Returns:
            Dict: 包含活跃记录数、被阻塞 IP 数等统计信息
        """
        with self._lock:
            now = time.time()
            active_records = len(self._records)
            blocked_ips = sum(
                1 for record in self._records.values()
                if record.blocked_until and now < record.blocked_until
            )
            
            return {
                'active_records': active_records,
                'blocked_ips': blocked_ips,
                'requests_per_minute': self.requests_per_minute,
                'window_size': self.window_size
            }


# 全局限流器实例
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """获取全局限流器实例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def reset_rate_limiter() -> None:
    """重置全局限流器（主要用于测试）"""
    global _rate_limiter
    _rate_limiter = None
