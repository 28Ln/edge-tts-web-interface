"""
管理员认证
"""

import os
import secrets
import hashlib
from functools import wraps
from typing import Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from flask import request, jsonify, g

from .models import get_db
from ..utils.logger import get_logger

logger = get_logger("admin.auth")

# 管理员 API Key 前缀
ADMIN_KEY_PREFIX = "adm_"

# 超级管理员密码 (环境变量)
SUPER_ADMIN_PASSWORD = os.environ.get('SUPER_ADMIN_PASSWORD', 'superadmin123')


@dataclass
class Admin:
    """管理员"""
    id: int
    username: str
    api_key: str = None
    is_super: bool = False
    created_at: datetime = None


def generate_admin_key() -> str:
    """生成管理员 API Key"""
    random_part = secrets.token_hex(24)
    return f"{ADMIN_KEY_PREFIX}{random_part}"


def hash_password(password: str) -> str:
    """哈希密码"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_admin_key(api_key: str) -> Tuple[bool, Optional[Admin], str]:
    """
    验证管理员 API Key
    
    Returns:
        (is_valid, admin, error_message)
    """
    if not api_key:
        return False, None, "缺少管理员 API Key"
    
    if not api_key.startswith(ADMIN_KEY_PREFIX):
        return False, None, "无效的管理员 API Key 格式"
    
    db = get_db()
    
    with db.get_connection() as conn:
        row = conn.execute(
            'SELECT * FROM admins WHERE api_key = ?', (api_key,)
        ).fetchone()
        
        if not row:
            return False, None, "管理员 API Key 无效"
        
        admin = Admin(
            id=row['id'],
            username=row['username'],
            api_key=row['api_key'],
            is_super=bool(row['is_super']),
            created_at=row['created_at']
        )
        
        return True, admin, ""


def get_admin_key_from_request() -> Optional[str]:
    """从请求中获取管理员 API Key"""
    # X-Admin-Key header
    admin_key = request.headers.get('X-Admin-Key')
    if admin_key:
        return admin_key
    
    # Authorization: Admin xxx
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Admin '):
        return auth_header[6:]
    
    return None


def require_admin():
    """
    管理员认证装饰器
    
    Usage:
        @app.route('/admin/xxx')
        @require_admin()
        def xxx():
            admin = g.current_admin
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = get_admin_key_from_request()
            
            is_valid, admin, error = verify_admin_key(api_key)
            
            if not is_valid:
                logger.warning(f"管理员认证失败: {error}")
                return jsonify({
                    "success": False,
                    "error_code": "ADMIN_AUTH_REQUIRED",
                    "message": error
                }), 401
            
            g.current_admin = admin
            logger.info(f"管理员认证成功: {admin.username}")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_super_admin():
    """超级管理员认证装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = get_admin_key_from_request()
            
            is_valid, admin, error = verify_admin_key(api_key)
            
            if not is_valid:
                return jsonify({
                    "success": False,
                    "error_code": "ADMIN_AUTH_REQUIRED",
                    "message": error
                }), 401
            
            if not admin.is_super:
                return jsonify({
                    "success": False,
                    "error_code": "SUPER_ADMIN_REQUIRED",
                    "message": "需要超级管理员权限"
                }), 403
            
            g.current_admin = admin
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def init_super_admin():
    """初始化超级管理员"""
    db = get_db()
    
    with db.get_connection() as conn:
        # 检查是否已存在超级管理员
        row = conn.execute(
            'SELECT * FROM admins WHERE is_super = 1'
        ).fetchone()
        
        if row:
            return row['api_key']
        
        # 创建超级管理员
        api_key = generate_admin_key()
        password_hash = hash_password(SUPER_ADMIN_PASSWORD)
        
        conn.execute('''
            INSERT INTO admins (username, password_hash, api_key, is_super)
            VALUES (?, ?, ?, 1)
        ''', ('superadmin', password_hash, api_key))
        
        logger.info(f"创建超级管理员，API Key: {api_key}")
        return api_key
