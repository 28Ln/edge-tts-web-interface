"""
配额和用量管理
"""

from datetime import datetime
from functools import wraps
from flask import g, jsonify

from .models import get_db, User
from ..utils.logger import get_logger

logger = get_logger("quota")


class QuotaManager:
    """配额管理器"""
    
    def __init__(self):
        self.db = get_db()
    
    def check_quota(self, user: User, quota_type: str = 'requests') -> tuple:
        """
        检查配额
        
        Args:
            user: 用户对象
            quota_type: 配额类型 (requests, tokens, audio_seconds)
        
        Returns:
            (is_allowed, remaining, limit, error_message)
        """
        usage = self.db.get_daily_usage(user.id)
        
        if quota_type == 'requests':
            used = usage['total_requests']
            limit = user.daily_requests
        elif quota_type == 'tokens':
            used = usage['total_tokens']
            limit = user.daily_tokens
        elif quota_type == 'audio_seconds':
            used = usage['total_audio_seconds']
            limit = user.daily_audio_seconds
        else:
            return True, 0, 0, ""
        
        remaining = limit - used
        
        if remaining <= 0:
            return False, 0, limit, f"已达到每日{quota_type}配额上限"
        
        return True, remaining, limit, ""
    
    def record_usage(self, user_id: int, api_key_id: int, endpoint: str,
                     tokens: int = 0, audio_seconds: float = 0):
        """记录用量"""
        self.db.record_usage(user_id, api_key_id, endpoint, tokens, audio_seconds)
        logger.debug(f"记录用量 | user={user_id} | endpoint={endpoint} | tokens={tokens} | audio={audio_seconds}s")
    
    def get_usage_summary(self, user_id: int) -> dict:
        """获取用量摘要"""
        user = self.db.get_user(user_id)
        usage = self.db.get_daily_usage(user_id)
        
        return {
            "date": datetime.now().strftime('%Y-%m-%d'),
            "requests": {
                "used": usage['total_requests'],
                "limit": user.daily_requests,
                "remaining": user.daily_requests - usage['total_requests'],
            },
            "tokens": {
                "used": usage['total_tokens'],
                "limit": user.daily_tokens,
                "remaining": user.daily_tokens - usage['total_tokens'],
            },
            "audio_seconds": {
                "used": usage['total_audio_seconds'],
                "limit": user.daily_audio_seconds,
                "remaining": user.daily_audio_seconds - usage['total_audio_seconds'],
            },
        }


# 全局配额管理器
_quota_manager = None


def get_quota_manager() -> QuotaManager:
    """获取配额管理器"""
    global _quota_manager
    if _quota_manager is None:
        _quota_manager = QuotaManager()
    return _quota_manager


def check_quota(quota_type: str = 'requests'):
    """
    配额检查装饰器
    
    Usage:
        @app.route('/api/xxx')
        @require_api_key()
        @check_quota('requests')
        def xxx():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = getattr(g, 'current_user', None)
            if not user:
                # 未认证用户，跳过配额检查
                return f(*args, **kwargs)
            
            manager = get_quota_manager()
            is_allowed, remaining, limit, error = manager.check_quota(user, quota_type)
            
            if not is_allowed:
                logger.warning(f"配额超限 | user={user.username} | type={quota_type}")
                return jsonify({
                    "success": False,
                    "error_code": "QUOTA_EXCEEDED",
                    "message": error,
                    "quota": {
                        "type": quota_type,
                        "limit": limit,
                        "remaining": 0,
                    }
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def record_usage(endpoint: str, tokens: int = 0, audio_seconds: float = 0):
    """
    记录用量（在请求处理后调用）
    
    Usage:
        @app.route('/api/xxx')
        @require_api_key()
        def xxx():
            result = do_something()
            record_usage('/api/xxx', tokens=100)
            return result
    """
    user = getattr(g, 'current_user', None)
    api_key = getattr(g, 'current_api_key', None)
    
    if user and api_key:
        manager = get_quota_manager()
        manager.record_usage(user.id, api_key.id, endpoint, tokens, audio_seconds)
