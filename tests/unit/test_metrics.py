"""Prometheus 指标收集测试

**Feature: production-readiness**
"""

import pytest
from hypothesis import given, strategies as st, assume
from unittest.mock import patch

from src.utils.metrics import MetricsCollector, get_metrics_collector, reset_metrics_collector


class TestMetricsCollector:
    """指标收集器测试"""
    
    def setup_method(self):
        self.collector = MetricsCollector()
    
    @given(st.integers(min_value=1, max_value=100))
    def test_request_count_accuracy(self, request_count):
        """**Property 5: 请求计数准确性**
        For any number of requests made to an endpoint,
        the counter should exactly match the number of requests
        **Validates: Requirements 4.2**
        """
        collector = MetricsCollector()
        
        for i in range(request_count):
            collector.inc_request_count('GET', '/api/test', 200)
        
        total = collector.get_request_count('GET', '/api/test')
        assert total == request_count, f"Expected {request_count}, got {total}"
    
    @given(
        st.lists(
            st.tuples(
                st.sampled_from(['GET', 'POST', 'PUT', 'DELETE']),
                st.sampled_from(['/api/v1/test', '/api/v2/data', '/health']),
                st.sampled_from([200, 201, 400, 404, 500])
            ),
            min_size=1,
            max_size=50
        )
    )
    def test_request_count_by_labels(self, requests):
        """测试按标签分组的请求计数"""
        collector = MetricsCollector()
        
        # 记录所有请求
        for method, endpoint, status in requests:
            collector.inc_request_count(method, endpoint, status)
        
        # 验证总数
        total = collector.get_request_count()
        assert total == len(requests)
    
    @given(st.floats(min_value=0.1, max_value=10000, allow_nan=False, allow_infinity=False))
    def test_latency_observation(self, latency_ms):
        """测试延迟记录"""
        collector = MetricsCollector()
        
        collector.observe_latency('GET', '/api/test', latency_ms)
        
        # 验证 sum 和 count
        key = 'GET|/api/test'
        assert collector._request_latency_count[key] == 1
        assert abs(collector._request_latency_sum[key] - latency_ms) < 0.001
    
    @given(st.lists(st.floats(min_value=0.1, max_value=5000, allow_nan=False, allow_infinity=False), min_size=1, max_size=20))
    def test_latency_histogram_buckets(self, latencies):
        """测试延迟直方图桶"""
        collector = MetricsCollector()
        
        for latency in latencies:
            collector.observe_latency('GET', '/api/test', latency)
        
        key = 'GET|/api/test'
        buckets = collector._request_latency_buckets[key]
        
        # 验证 +Inf 桶包含所有请求
        inf_bucket = [b for b in buckets if b.le == float('inf')][0]
        assert inf_bucket.count == len(latencies)
        
        # 验证桶是累积的
        for i in range(len(buckets) - 1):
            assert buckets[i].count <= buckets[i + 1].count
    
    def test_active_connections_gauge(self):
        """测试活跃连接数 Gauge"""
        collector = MetricsCollector()
        
        assert collector._active_connections == 0
        
        # 增加连接
        collector.inc_active_connections()
        collector.inc_active_connections()
        assert collector._active_connections == 2
        
        # 减少连接
        collector.dec_active_connections()
        assert collector._active_connections == 1
        
        # 不能为负
        collector.dec_active_connections()
        collector.dec_active_connections()
        assert collector._active_connections == 0
    
    def test_service_status_gauge(self):
        """测试服务状态 Gauge"""
        collector = MetricsCollector()
        
        # 默认所有服务健康
        assert collector._service_status['database'] == 1
        assert collector._service_status['ai_service'] == 1
        
        # 设置服务不健康
        collector.set_service_status('database', False)
        assert collector._service_status['database'] == 0
        
        # 恢复健康
        collector.set_service_status('database', True)
        assert collector._service_status['database'] == 1
    
    def test_error_count(self):
        """测试错误计数"""
        collector = MetricsCollector()
        
        collector.inc_error_count('ValidationError')
        collector.inc_error_count('ValidationError')
        collector.inc_error_count('DatabaseError')
        
        assert collector._error_count['ValidationError'] == 2
        assert collector._error_count['DatabaseError'] == 1
    
    def test_prometheus_export_format(self):
        """测试 Prometheus 导出格式"""
        collector = MetricsCollector()
        
        # 添加一些数据
        collector.inc_request_count('GET', '/api/test', 200)
        collector.inc_request_count('POST', '/api/data', 201)
        collector.observe_latency('GET', '/api/test', 50.5)
        collector.inc_error_count('ValidationError')
        
        output = collector.export_prometheus_format()
        
        # 验证格式
        assert '# HELP http_requests_total' in output
        assert '# TYPE http_requests_total counter' in output
        assert 'http_requests_total{method="GET",endpoint="/api/test",status="200"} 1' in output
        
        assert '# HELP http_request_duration_ms' in output
        assert '# TYPE http_request_duration_ms histogram' in output
        
        assert '# HELP http_active_connections' in output
        assert '# TYPE http_active_connections gauge' in output
        
        assert '# HELP service_status' in output
        assert 'service_status{service="database"} 1' in output
        
        assert '# HELP http_errors_total' in output
        assert 'http_errors_total{type="ValidationError"} 1' in output
    
    def test_get_stats(self):
        """测试获取统计摘要"""
        collector = MetricsCollector()
        
        collector.inc_request_count('GET', '/api/test', 200)
        collector.inc_request_count('GET', '/api/test', 500)
        collector.inc_error_count('ServerError')
        collector.inc_active_connections()
        
        stats = collector.get_stats()
        
        assert stats['total_requests'] == 2
        assert stats['total_errors'] == 1
        assert stats['active_connections'] == 1
        assert stats['error_rate'] == 0.5
    
    def test_reset(self):
        """测试重置功能"""
        collector = MetricsCollector()
        
        collector.inc_request_count('GET', '/api/test', 200)
        collector.inc_active_connections()
        collector.inc_error_count('Error')
        
        collector.reset()
        
        assert collector.get_request_count() == 0
        assert collector._active_connections == 0
        assert len(collector._error_count) == 0
    
    def test_thread_safety(self):
        """测试线程安全性"""
        import threading
        
        collector = MetricsCollector()
        results = []
        
        def record_requests():
            for _ in range(100):
                collector.inc_request_count('GET', '/api/test', 200)
        
        threads = [threading.Thread(target=record_requests) for _ in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 应该有 500 个请求
        assert collector.get_request_count() == 500


class TestMetricsGlobalInstance:
    """全局实例测试"""
    
    def setup_method(self):
        reset_metrics_collector()
    
    def teardown_method(self):
        reset_metrics_collector()
    
    def test_get_metrics_collector_singleton(self):
        """测试单例模式"""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        
        assert collector1 is collector2
    
    def test_reset_metrics_collector(self):
        """测试重置全局实例"""
        collector1 = get_metrics_collector()
        collector1.inc_request_count('GET', '/test', 200)
        
        reset_metrics_collector()
        
        collector2 = get_metrics_collector()
        assert collector2.get_request_count() == 0
