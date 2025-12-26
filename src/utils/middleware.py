"""
Flask 中间件
- 请求 ID 追踪
- 性能监控
- 请求日志
- IP 限流
"""

import time
import uuid
from functools import wraps
from flask import Flask, request, g, jsonify
from .logger import get_logger
from .rate_limiter import get_rate_limiter, reset_rate_limiter
from .metrics import get_metrics_collector

logger = get_logger("middleware")


def generate_request_id() -> str:
    """生成请求 ID"""
    return str(uuid.uuid4())[:8]


def _get_client_ip() -> str:
    """获取客户端真实 IP"""
    # 优先从代理头获取真实 IP
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr or '127.0.0.1'


def _should_skip_rate_limit(path: str) -> bool:
    """判断是否跳过限流检查"""
    skip_paths = {
        '/health', '/health/ready', '/health/live',
        '/version', '/metrics', '/metrics/stats', '/favicon.ico',
        '/docs', '/openapi.json', '/redoc'
    }
    
    # 跳过静态资源
    if path.startswith('/static/'):
        return True
    
    # 跳过特定路径
    return path in skip_paths


def register_middleware(app: Flask):
    """注册中间件"""
    
    @app.before_request
    def before_request():
        """请求前处理"""
        # 生成请求 ID
        g.request_id = request.headers.get('X-Request-ID') or generate_request_id()
        g.start_time = time.time()
        
        # 记录请求日志
        client_ip = _get_client_ip()
        logger.info(
            f"[{g.request_id}] --> {request.method} {request.path} "
            f"| client={client_ip}"
        )
        
        # 增加活跃连接数
        metrics = get_metrics_collector()
        metrics.inc_active_connections()
        
        # 限流检查（跳过健康检查和静态资源）
        if not _should_skip_rate_limit(request.path):
            rate_limiter = get_rate_limiter()
            
            if not rate_limiter.is_allowed(client_ip):
                retry_after = rate_limiter.get_retry_after(client_ip)
                
                logger.warning(
                    f"[{g.request_id}] 限流触发 - IP: {client_ip}, "
                    f"路径: {request.path}, 重试等待: {retry_after}s"
                )
                
                # 记录限流指标
                metrics.inc_request_count(request.method, request.path, 429)
                metrics.inc_error_count('RateLimitExceeded')
                
                response = jsonify({
                    'success': False,
                    'error_code': 'RATE_LIMIT_EXCEEDED',
                    'message': f'请求过于频繁，请 {retry_after} 秒后重试',
                    'retry_after': retry_after
                })
                response.status_code = 429
                response.headers['Retry-After'] = str(retry_after)
                response.headers['X-RateLimit-Limit'] = str(rate_limiter.requests_per_minute)
                response.headers['X-RateLimit-Remaining'] = '0'
                response.headers['X-Request-ID'] = g.request_id
                
                return response
    
    @app.after_request
    def after_request(response):
        """请求后处理"""
        # 计算耗时
        duration = (time.time() - g.start_time) * 1000  # 毫秒
        
        # 记录指标
        metrics = get_metrics_collector()
        metrics.inc_request_count(request.method, request.path, response.status_code)
        metrics.observe_latency(request.method, request.path, duration)
        metrics.dec_active_connections()
        
        # 记录错误
        if response.status_code >= 400:
            error_type = 'ClientError' if response.status_code < 500 else 'ServerError'
            metrics.inc_error_count(error_type)
        
        # 添加响应头
        response.headers['X-Request-ID'] = g.request_id
        response.headers['X-Response-Time'] = f"{duration:.2f}ms"
        
        # 添加限流相关头信息（非限流响应）
        if response.status_code != 429 and not _should_skip_rate_limit(request.path):
            client_ip = _get_client_ip()
            rate_limiter = get_rate_limiter()
            
            response.headers['X-RateLimit-Limit'] = str(rate_limiter.requests_per_minute)
            response.headers['X-RateLimit-Remaining'] = str(rate_limiter.get_remaining_requests(client_ip))
        
        # 记录响应日志
        status = response.status_code
        level = "INFO" if status < 400 else "WARNING" if status < 500 else "ERROR"
        
        log_func = getattr(logger, level.lower())
        log_func(
            f"[{g.request_id}] <-- {status} | {duration:.2f}ms"
        )
        
        return response
    
    @app.teardown_request
    def teardown_request(exception=None):
        """请求结束清理"""
        if exception:
            logger.error(f"[{g.get('request_id', 'unknown')}] 请求异常: {exception}")


def get_request_id() -> str:
    """获取当前请求 ID"""
    return getattr(g, 'request_id', 'no-request')


class RequestContext:
    """请求上下文，用于在服务层获取请求信息"""
    
    @staticmethod
    def get_id() -> str:
        return get_request_id()
    
    @staticmethod
    def get_client_ip() -> str:
        return request.remote_addr if request else 'unknown'


def timed(func):
    """
    计时装饰器，用于记录函数执行时间
    
    Usage:
        @timed
        def my_function():
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = (time.time() - start) * 1000
            logger.debug(f"[{get_request_id()}] {func.__name__} 耗时: {duration:.2f}ms")
    return wrapper
