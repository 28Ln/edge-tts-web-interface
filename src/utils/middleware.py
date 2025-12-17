"""
Flask 中间件
- 请求 ID 追踪
- 性能监控
- 请求日志
"""

import time
import uuid
from functools import wraps
from flask import Flask, request, g
from .logger import get_logger

logger = get_logger("middleware")


def generate_request_id() -> str:
    """生成请求 ID"""
    return str(uuid.uuid4())[:8]


def register_middleware(app: Flask):
    """注册中间件"""
    
    @app.before_request
    def before_request():
        """请求前处理"""
        # 生成请求 ID
        g.request_id = request.headers.get('X-Request-ID') or generate_request_id()
        g.start_time = time.time()
        
        # 记录请求日志
        logger.info(
            f"[{g.request_id}] --> {request.method} {request.path} "
            f"| client={request.remote_addr}"
        )
    
    @app.after_request
    def after_request(response):
        """请求后处理"""
        # 计算耗时
        duration = (time.time() - g.start_time) * 1000  # 毫秒
        
        # 添加响应头
        response.headers['X-Request-ID'] = g.request_id
        response.headers['X-Response-Time'] = f"{duration:.2f}ms"
        
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
