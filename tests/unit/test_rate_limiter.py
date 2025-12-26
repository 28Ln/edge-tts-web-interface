"""限流器测试

**Feature: production-readiness**
"""

import time
import pytest
from hypothesis import given, strategies as st, assume, settings
from unittest.mock import patch

from src.utils.rate_limiter import RateLimiter, RateLimitRecord


class TestRateLimiter:
    """限流器测试"""
    
    def setup_method(self):
        self.limiter = RateLimiter(requests_per_minute=10)  # 测试用小限制
    
    def test_basic_functionality(self):
        """测试基本功能"""
        ip = "192.168.1.1"
        
        # 前 10 个请求应该被允许
        for i in range(10):
            assert self.limiter.is_allowed(ip) is True
        
        # 第 11 个请求应该被拒绝
        assert self.limiter.is_allowed(ip) is False
    
    @given(st.integers(min_value=1, max_value=50))
    @settings(max_examples=100)
    def test_rate_limit_threshold_enforcement(self, limit):
        """**Property 3: 限流阈值执行**
        For any IP making more than the configured limit of requests within a minute window,
        all requests exceeding the limit should receive rejection
        **Validates: Requirements 3.1**
        """
        limiter = RateLimiter(requests_per_minute=limit)
        ip = "192.168.1.100"
        
        # 在限制内的请求应该被允许
        for i in range(limit):
            assert limiter.is_allowed(ip) is True, f"Request {i+1} should be allowed"
        
        # 超过限制的请求应该被拒绝
        for i in range(5):  # 测试额外 5 个请求
            assert limiter.is_allowed(ip) is False, f"Request {limit+i+1} should be rejected"

    def test_window_reset_allows_requests(self):
        """**Property 4: 限流窗口重置**
        For any IP that was rate-limited, after the window expires (1 minute),
        subsequent requests should be allowed
        **Validates: Requirements 3.4**
        """
        ip = "192.168.1.2"
        
        # 耗尽配额
        for i in range(10):
            assert self.limiter.is_allowed(ip) is True
        
        # 确认被限流
        assert self.limiter.is_allowed(ip) is False
        
        # 模拟时间过去 61 秒（超过窗口）
        original_time = self.limiter._records[ip].window_start
        self.limiter._records[ip].window_start = original_time - 61
        self.limiter._records[ip].blocked_until = None
        
        # 窗口重置后应该允许请求
        assert self.limiter.is_allowed(ip) is True
    
    def test_ip_isolation(self):
        """测试不同 IP 之间的隔离"""
        # 每次测试使用新的 limiter 实例
        limiter = RateLimiter(requests_per_minute=10)
        
        ip1 = "10.0.0.1"
        ip2 = "10.0.0.2"
        
        # IP1 耗尽配额
        for i in range(10):
            assert limiter.is_allowed(ip1) is True
        
        # IP1 被限流
        assert limiter.is_allowed(ip1) is False
        
        # IP2 仍然可以请求
        assert limiter.is_allowed(ip2) is True
    
    def test_get_retry_after(self):
        """测试获取重试等待时间"""
        ip = "192.168.1.3"
        
        # 初始状态无需等待
        assert self.limiter.get_retry_after(ip) == 0
        
        # 耗尽配额
        for i in range(10):
            self.limiter.is_allowed(ip)
        
        # 被限流后需要等待
        retry_after = self.limiter.get_retry_after(ip)
        assert retry_after > 0
        assert retry_after <= 61  # 最多等待一个窗口周期
    
    def test_get_remaining_requests(self):
        """测试获取剩余请求数"""
        ip = "192.168.1.4"
        
        # 初始状态有完整配额
        assert self.limiter.get_remaining_requests(ip) == 10
        
        # 使用 3 个请求
        for i in range(3):
            self.limiter.is_allowed(ip)
        
        # 剩余 7 个
        assert self.limiter.get_remaining_requests(ip) == 7
        
        # 耗尽配额
        for i in range(7):
            self.limiter.is_allowed(ip)
        
        # 剩余 0 个
        assert self.limiter.get_remaining_requests(ip) == 0
    
    def test_cleanup_expired_records(self):
        """测试清理过期记录"""
        ip = "192.168.1.5"
        
        # 创建记录
        self.limiter.is_allowed(ip)
        assert ip in self.limiter._records
        
        # 模拟时间过去 3 个窗口周期
        self.limiter._records[ip].window_start = time.time() - 180
        
        self.limiter.cleanup_expired_records()
        
        # 记录应该被清理
        assert ip not in self.limiter._records
    
    def test_get_stats(self):
        """测试获取统计信息"""
        # 创建一些记录
        for i in range(3):
            ip = f"192.168.1.{i+10}"
            self.limiter.is_allowed(ip)
        
        stats = self.limiter.get_stats()
        
        assert stats['active_records'] == 3
        assert stats['blocked_ips'] == 0
        assert stats['requests_per_minute'] == 10
        assert stats['window_size'] == 60
    
    def test_concurrent_access_safety(self):
        """测试并发访问安全性"""
        import threading
        
        ip = "192.168.1.100"
        results = []
        
        def make_requests():
            for _ in range(5):
                result = self.limiter.is_allowed(ip)
                results.append(result)
                time.sleep(0.01)  # 小延迟模拟真实场景
        
        # 启动 3 个线程并发请求
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=make_requests)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证结果：应该有 10 个 True，5 个 False
        true_count = sum(1 for r in results if r is True)
        false_count = sum(1 for r in results if r is False)
        
        assert true_count == 10  # 限制内的请求
        assert false_count == 5  # 超限的请求


class TestRateLimitRecord:
    """限流记录测试"""
    
    def test_record_creation(self):
        """测试记录创建"""
        record = RateLimitRecord(ip="192.168.1.1")
        
        assert record.ip == "192.168.1.1"
        assert record.request_count == 0
        assert record.blocked_until is None
        assert isinstance(record.window_start, float)
        assert record.window_start <= time.time()


class TestRateLimiterIntegration:
    """限流器集成测试"""
    
    def test_environment_variable_configuration(self):
        """测试环境变量配置"""
        with patch.dict('os.environ', {'RATE_LIMIT_PER_MINUTE': '50'}):
            limiter = RateLimiter()
            assert limiter.requests_per_minute == 50
    
    def test_default_configuration(self):
        """测试默认配置"""
        with patch.dict('os.environ', {}, clear=True):
            limiter = RateLimiter()
            assert limiter.requests_per_minute == 100  # 默认值
