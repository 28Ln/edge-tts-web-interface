"""限流中间件集成测试

**Feature: production-readiness**
"""

import pytest
from unittest.mock import patch

from src.utils.rate_limiter import reset_rate_limiter, RateLimiter


class TestRateLimitingMiddleware:
    """限流中间件集成测试"""
    
    def setup_method(self):
        # 每个测试重置限流器
        reset_rate_limiter()
    
    def test_rate_limiting_blocks_excessive_requests(self, client):
        """测试限流阻止过量请求"""
        # 设置较小的限流值用于测试
        with patch('src.utils.middleware.get_rate_limiter') as mock_get_limiter:
            limiter = RateLimiter(requests_per_minute=5)
            mock_get_limiter.return_value = limiter
            
            # 前 5 个请求应该成功
            for i in range(5):
                response = client.get('/mcu/ping')
                assert response.status_code == 200, f"Request {i+1} should succeed"
            
            # 第 6 个请求应该被限流
            response = client.get('/mcu/ping')
            assert response.status_code == 429
            
            data = response.get_json()
            assert data['success'] is False
            assert data['error_code'] == 'RATE_LIMIT_EXCEEDED'
            assert 'retry_after' in data
            
            # 检查响应头
            assert 'Retry-After' in response.headers
            assert 'X-RateLimit-Limit' in response.headers
            assert response.headers['X-RateLimit-Limit'] == '5'
    
    def test_rate_limiting_headers_on_success(self, client):
        """测试成功请求包含限流头信息"""
        with patch('src.utils.middleware.get_rate_limiter') as mock_get_limiter:
            limiter = RateLimiter(requests_per_minute=10)
            mock_get_limiter.return_value = limiter
            
            response = client.get('/mcu/ping')
            assert response.status_code == 200
            
            # 检查限流头
            assert 'X-RateLimit-Limit' in response.headers
            assert 'X-RateLimit-Remaining' in response.headers
            assert response.headers['X-RateLimit-Limit'] == '10'
            assert int(response.headers['X-RateLimit-Remaining']) == 9  # 使用了 1 个

    def test_health_endpoints_skip_rate_limiting(self, client):
        """测试健康检查端点跳过限流"""
        with patch('src.utils.middleware.get_rate_limiter') as mock_get_limiter:
            limiter = RateLimiter(requests_per_minute=1)
            mock_get_limiter.return_value = limiter
            
            # 健康检查端点应该不受限流影响
            for i in range(5):
                response = client.get('/health')
                assert response.status_code == 200, f"Health check {i+1} should not be rate limited"
            
            # 版本端点也应该跳过限流
            for i in range(5):
                response = client.get('/version')
                assert response.status_code == 200, f"Version check {i+1} should not be rate limited"
    
    def test_different_ips_isolated(self, client):
        """测试不同 IP 的限流隔离"""
        with patch('src.utils.middleware.get_rate_limiter') as mock_get_limiter:
            limiter = RateLimiter(requests_per_minute=2)
            mock_get_limiter.return_value = limiter
            
            # 模拟第一个 IP 的请求
            with patch('src.utils.middleware._get_client_ip', return_value='192.168.1.1'):
                # 耗尽第一个 IP 的配额
                for i in range(2):
                    response = client.get('/mcu/ping')
                    assert response.status_code == 200
                
                # 第一个 IP 被限流
                response = client.get('/mcu/ping')
                assert response.status_code == 429
            
            # 模拟第二个 IP 的请求
            with patch('src.utils.middleware._get_client_ip', return_value='192.168.1.2'):
                # 第二个 IP 仍然可以请求
                response = client.get('/mcu/ping')
                assert response.status_code == 200
    
    def test_rate_limit_response_format(self, client):
        """测试限流响应格式"""
        with patch('src.utils.middleware.get_rate_limiter') as mock_get_limiter:
            limiter = RateLimiter(requests_per_minute=1)
            mock_get_limiter.return_value = limiter
            
            # 第一个请求成功
            response = client.get('/mcu/ping')
            assert response.status_code == 200
            
            # 第二个请求被限流
            response = client.get('/mcu/ping')
            assert response.status_code == 429
            
            data = response.get_json()
            
            # 验证响应格式
            assert 'success' in data
            assert 'error_code' in data
            assert 'message' in data
            assert 'retry_after' in data
            
            assert data['success'] is False
            assert data['error_code'] == 'RATE_LIMIT_EXCEEDED'
            assert isinstance(data['retry_after'], int)
            assert data['retry_after'] > 0
