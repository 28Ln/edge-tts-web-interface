"""健康检查状态管理测试

**Feature: production-readiness**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock

from src.utils.health_checker import (
    HealthChecker, HealthStatus, ServiceHealth,
    get_health_checker, reset_health_checker
)


class TestHealthChecker:
    """健康检查器测试"""
    
    def setup_method(self):
        self.checker = HealthChecker(failure_threshold=3, recovery_threshold=2)
    
    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=5, deadline=None)
    def test_health_status_transition(self, failure_threshold):
        """**Property 6: 健康检查状态转换**
        For any service with N consecutive failures where N >= failure_threshold,
        the service should transition to UNHEALTHY status
        **Validates: Requirements 5.4**
        """
        checker = HealthChecker(failure_threshold=failure_threshold, recovery_threshold=2)
        
        # 注册一个总是失败的服务
        fail_count = 0
        def always_fail():
            nonlocal fail_count
            fail_count += 1
            return False
        
        checker.register_service('test_service', always_fail)
        
        # 执行 failure_threshold 次检查
        for i in range(failure_threshold):
            service = checker.check_service('test_service')
            
            if i < failure_threshold - 1:
                # 还没达到阈值，应该是 DEGRADED
                assert service.status in [HealthStatus.DEGRADED, HealthStatus.UNKNOWN]
            else:
                # 达到阈值，应该是 UNHEALTHY
                assert service.status == HealthStatus.UNHEALTHY
        
        assert service.consecutive_failures == failure_threshold
    
    @given(st.integers(min_value=1, max_value=5), st.integers(min_value=1, max_value=5))
    @settings(max_examples=5, deadline=None)
    def test_recovery_requires_consecutive_successes(self, failure_threshold, recovery_threshold):
        """测试恢复需要连续成功"""
        checker = HealthChecker(
            failure_threshold=failure_threshold, 
            recovery_threshold=recovery_threshold
        )
        
        # 控制检查结果
        should_succeed = False
        def controlled_check():
            return should_succeed
        
        checker.register_service('test_service', controlled_check)
        
        # 先让服务变成 UNHEALTHY
        should_succeed = False
        for _ in range(failure_threshold):
            checker.check_service('test_service')
        
        service = checker.get_service_status('test_service')
        assert service.status == HealthStatus.UNHEALTHY
        
        # 开始恢复
        should_succeed = True
        for i in range(recovery_threshold):
            service = checker.check_service('test_service')
            
            if i < recovery_threshold - 1:
                # 还没达到恢复阈值
                assert service.status == HealthStatus.UNHEALTHY
            else:
                # 达到恢复阈值，应该恢复
                assert service.status == HealthStatus.HEALTHY
    
    def test_register_and_check_service(self):
        """测试注册和检查服务"""
        def healthy_check():
            return True
        
        self.checker.register_service('test', healthy_check)
        
        service = self.checker.check_service('test')
        
        assert service.name == 'test'
        assert service.status == HealthStatus.HEALTHY
        assert service.consecutive_failures == 0
        assert service.last_check_time is not None
        assert service.last_success_time is not None
    
    def test_failure_increments_counter(self):
        """测试失败增加计数器"""
        def failing_check():
            return False
        
        self.checker.register_service('failing', failing_check)
        
        # 第一次失败
        service = self.checker.check_service('failing')
        assert service.consecutive_failures == 1
        assert service.status == HealthStatus.DEGRADED
        
        # 第二次失败
        service = self.checker.check_service('failing')
        assert service.consecutive_failures == 2
        assert service.status == HealthStatus.DEGRADED
        
        # 第三次失败 - 达到阈值
        service = self.checker.check_service('failing')
        assert service.consecutive_failures == 3
        assert service.status == HealthStatus.UNHEALTHY
    
    def test_success_resets_failure_counter(self):
        """测试成功重置失败计数器"""
        results = [False, False, True]  # 两次失败后成功
        call_count = 0
        
        def intermittent_check():
            nonlocal call_count
            result = results[call_count % len(results)]
            call_count += 1
            return result
        
        self.checker.register_service('intermittent', intermittent_check)
        
        # 两次失败
        self.checker.check_service('intermittent')
        service = self.checker.check_service('intermittent')
        assert service.consecutive_failures == 2
        
        # 一次成功 - 重置计数器
        service = self.checker.check_service('intermittent')
        assert service.consecutive_failures == 0
        assert service.status == HealthStatus.HEALTHY
    
    def test_exception_counts_as_failure(self):
        """测试异常计为失败"""
        def error_check():
            raise RuntimeError("Service unavailable")
        
        self.checker.register_service('error', error_check)
        
        service = self.checker.check_service('error')
        
        assert service.consecutive_failures == 1
        assert service.status == HealthStatus.DEGRADED
        assert "Service unavailable" in service.last_error
    
    def test_check_all_services(self):
        """测试检查所有服务"""
        self.checker.register_service('healthy', lambda: True)
        self.checker.register_service('unhealthy', lambda: False)
        
        results = self.checker.check_all()
        
        assert len(results) == 2
        assert results['healthy'].status == HealthStatus.HEALTHY
        assert results['unhealthy'].status == HealthStatus.DEGRADED
    
    def test_get_overall_status(self):
        """测试获取整体状态"""
        self.checker.register_service('healthy', lambda: True)
        self.checker.register_service('unhealthy', lambda: False)
        
        # 初始状态
        assert self.checker.get_overall_status() == HealthStatus.UNKNOWN
        
        # 检查后
        self.checker.check_all()
        assert self.checker.get_overall_status() == HealthStatus.DEGRADED
        
        # 让 unhealthy 服务达到阈值
        for _ in range(2):
            self.checker.check_service('unhealthy')
        
        assert self.checker.get_overall_status() == HealthStatus.UNHEALTHY
    
    def test_get_summary(self):
        """测试获取摘要"""
        self.checker.register_service('service1', lambda: True)
        self.checker.register_service('service2', lambda: False)
        
        self.checker.check_all()
        
        summary = self.checker.get_summary()
        
        assert 'overall_status' in summary
        assert 'services' in summary
        assert 'total_services' in summary
        assert summary['total_services'] == 2
        assert summary['healthy_count'] == 1
    
    def test_reset_service(self):
        """测试重置服务状态"""
        self.checker.register_service('test', lambda: False)
        
        # 让服务失败
        for _ in range(3):
            self.checker.check_service('test')
        
        service = self.checker.get_service_status('test')
        assert service.status == HealthStatus.UNHEALTHY
        
        # 重置
        self.checker.reset_service('test')
        
        service = self.checker.get_service_status('test')
        assert service.status == HealthStatus.UNKNOWN
        assert service.consecutive_failures == 0
    
    def test_unregistered_service_raises_error(self):
        """测试检查未注册服务抛出错误"""
        with pytest.raises(ValueError) as exc_info:
            self.checker.check_service('nonexistent')
        
        assert '未注册的服务' in str(exc_info.value)


class TestServiceHealth:
    """服务健康状态测试"""
    
    def test_default_values(self):
        """测试默认值"""
        service = ServiceHealth(name='test')
        
        assert service.name == 'test'
        assert service.status == HealthStatus.UNKNOWN
        assert service.consecutive_failures == 0
        assert service.last_check_time is None
        assert service.last_error is None


class TestGlobalHealthChecker:
    """全局健康检查器测试"""
    
    def setup_method(self):
        reset_health_checker()
    
    def teardown_method(self):
        reset_health_checker()
    
    def test_singleton(self):
        """测试单例模式"""
        checker1 = get_health_checker()
        checker2 = get_health_checker()
        
        assert checker1 is checker2
    
    def test_reset(self):
        """测试重置"""
        checker1 = get_health_checker()
        checker1.register_service('test', lambda: True)
        
        reset_health_checker()
        
        checker2 = get_health_checker()
        assert checker2 is not checker1
        assert len(checker2._services) == 0
