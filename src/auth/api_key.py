"""
API Key 认证
"""

import secrets
import hashlib
from functools import wraps
from datetime import datetime
from typing import Optional, Tuple
from flask import request, g, jsonify

from .models import get_db, ApiKey, User
from ..utils.logger import get_logger

logger = get_logger("auth")

# API Key 前缀
API_KEY_PREFIX = "sk-"


def generate_api_key(length: int = 32) -> str:
    """
    生成 API Key
    
    格式: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
    """
    random_part = secrets.token_hex(length // 2)
    return f"{API_KEY_PREFIX}{random_part}"


def hash_api_key(key: str) -> str:
    """
    哈希 API Key（用于存储）
    
    注意：实际存储时应该只存储哈希值，这里为了简化直接存储原文
    """
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(key: str) -> Tuple[bool, Optional[ApiKey], Optional[User], str]:
    """
    验证 API Key
    
    Returns:
        (is_valid, api_key, user, error_message)
    """
    if not key:
        return False, None, None, "缺少 API Key"
    
    # 检查格式
    if not key.startswith(API_KEY_PREFIX):
        return False, None, None, "API Key 格式错误"
    
    db = get_db()
    
    # 查找 API Key
    api_key = db.get_api_key(key)
    if not api_key:
        return False, None, None, "API Key 无效"
    
    # 检查是否过期
    if api_key.expires_at:
        if isinstance(api_key.expires_at, str):
            expires_at = datetime.fromisoformat(api_key.expires_at)
        else:
            expires_at = api_key.expires_at
        if expires_at < datetime.now():
            return False, None, None, "API Key 已过期"
    
    # 获取用户
    user = db.get_user(api_key.user_id)
    if not user:
        return False, None, None, "用户不存在"
    
    if not user.is_active:
        return False, None, None, "用户已禁用"
    
    return True, api_key, user, ""


def get_api_key_from_request() -> Optional[str]:
    """
    从请求中获取 API Key
    
    支持多种方式：
    1. Header: Authorization: Bearer sk-xxx
    2. Header: X-API-Key: sk-xxx
    3. Query: ?api_key=sk-xxx
    """
    # 方式1: Authorization Header
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    
    # 方式2: X-API-Key Header
    api_key = request.headers.get('X-API-Key')
    if api_key:
        return api_key
    
    # 方式3: Query Parameter
    api_key = request.args.get('api_key')
    if api_key:
        return api_key
    
    return None


def require_api_key(permissions: str = None):
    """
    API Key 认证装饰器
    
    Usage:
        @app.route('/api/xxx')
        @require_api_key()
        def xxx():
            user = g.current_user
            ...
    
    Args:
        permissions: 需要的权限，如 'stt', 'tts', 'ai'，None 表示任意权限
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取 API Key
            api_key = get_api_key_from_request()
            
            # 验证
            is_valid, key_obj, user, error = verify_api_key(api_key)
            
            if not is_valid:
                logger.warning(f"认证失败: {error} | key={api_key[:20]}..." if api_key else f"认证失败: {error}")
                return jsonify({
                    "success": False,
                    "error_code": "AUTH_FAILED",
                    "message": error,
                }), 401
            
            # 检查权限
            if permissions and key_obj.permissions != 'all':
                allowed = key_obj.permissions.split(',')
                if permissions not in allowed:
                    return jsonify({
                        "success": False,
                        "error_code": "PERMISSION_DENIED",
                        "message": f"缺少权限: {permissions}",
                    }), 403
            
            # 保存到 g 对象
            g.current_user = user
            g.current_api_key = key_obj
            
            logger.info(f"认证成功 | user={user.username} | key_name={key_obj.name}")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def optional_api_key():
    """
    可选的 API Key 认证装饰器
    
    如果提供了 API Key 则验证，否则允许匿名访问
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = get_api_key_from_request()
            
            if api_key:
                is_valid, key_obj, user, error = verify_api_key(api_key)
                if is_valid:
                    g.current_user = user
                    g.current_api_key = key_obj
                else:
                    g.current_user = None
                    g.current_api_key = None
            else:
                g.current_user = None
                g.current_api_key = None
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
