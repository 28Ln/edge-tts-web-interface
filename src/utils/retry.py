"""
重试机制
"""

import time
from functools import wraps
from typing import Tuple, Type
from .logger import get_logger

logger = get_logger("retry")


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 延迟倍数
        exceptions: 需要重试的异常类型
    
    Usage:
        @retry(max_attempts=3, delay=1.0)
        def call_external_api():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"{func.__name__} 第 {attempt} 次失败: {e}, "
                            f"{current_delay:.1f}s 后重试..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"{func.__name__} 重试 {max_attempts} 次后仍失败: {e}"
                        )
            
            raise last_exception
        return wrapper
    return decorator


class RetryableError(Exception):
    """可重试的错误"""
    pass
