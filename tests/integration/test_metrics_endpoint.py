"""Prometheus 指标端点集成测试

**Feature: production-readiness**
"""

import pytest
from unittest.mock import patch

from src.utils.metrics import reset_metrics_collector, get_metrics_collector


class TestMetricsEndpoint:
    """指标端点集成测试"""
    
    def setup_method(self):
        reset_metrics_collector()
    
    def teardown_method(self):
        reset_metrics_collector()
    
    def test_metrics_endpoint_returns_prometheus_format(self, client):
        """测试 /metrics 端点返回 Prometheus 格式"""
        # 先发送一些请求生成指标
        client.get('/mcu/ping')
        client.get('/health')
        
        # 获取指标
        response = client.get('/metrics')
        
        assert response.status_code == 200
        assert response.content_type.startswith('text/plain')
        
        data = response.data.decode('utf-8')
        
        # 验证 Prometheus 格式
        assert '# HELP http_requests_total' in data
        assert '# TYPE http_requests_total counter' in data
        assert 'http_requests_total{' in data
        
        assert '# HELP http_request_duration_ms' in data
        assert '# TYPE http_request_duration_ms histogram' in data
        
        assert '# HELP http_active_connections' in data
        assert '# TYPE http_active_connections gauge' in data
        
        assert '# HELP service_status' in data
        assert 'service_status{service="database"}' in data
    
    def test_metrics_stats_endpoint(self, client):
        """测试 /metrics/stats 端点返回 JSON 统计"""
        # 先发送一些请求
        client.get('/mcu/ping')
        client.get('/mcu/ping')
        
        # 获取统计
        response = client.get('/metrics/stats')
        
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert 'stats' in data
        assert 'timestamp' in data
        
        stats = data['stats']
        assert 'total_requests' in stats
        assert 'total_errors' in stats
        assert 'active_connections' in stats
        assert 'service_status' in stats
    
    def test_metrics_records_request_count(self, client):
        """测试指标记录请求计数"""
        reset_metrics_collector()
        
        # 发送多个请求
        for _ in range(5):
            client.get('/mcu/ping')
        
        # 检查指标
        collector = get_metrics_collector()
        count = collector.get_request_count('GET', '/mcu/ping')
        
        # 应该有 5 个请求
        assert count == 5
    
    def test_metrics_records_latency(self, client):
        """测试指标记录延迟"""
        reset_metrics_collector()
        
        client.get('/mcu/ping')
        
        collector = get_metrics_collector()
        
        # 检查延迟记录
        key = 'GET|/mcu/ping'
        assert collector._request_latency_count[key] == 1
        assert collector._request_latency_sum[key] > 0
    
    def test_metrics_records_errors(self, client):
        """测试指标记录错误"""
        reset_metrics_collector()
        
        # 发送会产生 404 的请求
        client.get('/nonexistent-endpoint')
        
        collector = get_metrics_collector()
        
        # 检查错误计数
        assert collector._error_count['ClientError'] >= 1
    
    def test_metrics_endpoint_not_rate_limited(self, client):
        """测试 /metrics 端点不受限流影响"""
        from src.utils.rate_limiter import RateLimiter, reset_rate_limiter
        
        reset_rate_limiter()
        
        with patch('src.utils.middleware.get_rate_limiter') as mock_get_limiter:
            limiter = RateLimiter(requests_per_minute=1)
            mock_get_limiter.return_value = limiter
            
            # 多次访问 /metrics 应该都成功
            for i in range(5):
                response = client.get('/metrics')
                assert response.status_code == 200, f"Request {i+1} should not be rate limited"
