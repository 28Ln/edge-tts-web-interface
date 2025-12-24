"""
Admin 认证服务
"""

import os
import secrets
import hashlib
from typing import Optional, Dict
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from flask import request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash

from ..billing.models import get_billing_db
from ..utils.logger import get_logger

logger = get_logger("auth.admin")

# Admin API Key 前缀
ADMIN_KEY_PREFIX = "adm_"


@dataclass
class Admin:
    """管理员"""
    id: int
    username: str
    password_hash: str
    api_key: Optional[str] = None
    is_super: bool = False
    is_active: bool = True
    created_at: datetime = None
    last_login: datetime = None


class AdminAuthService:
    """Admin 认证服务"""
    
    def __init__(self):
        self.db = get_billing_db()
        self._ensure_default_admin()
    
    def _ensure_default_admin(self):
        """确保存在默认管理员"""
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM admins WHERE is_super = 1"
            ).fetchone()
            
            if row[0] == 0:
                # 创建默认超级管理员
                default_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
                password_hash = self._hash_password(default_password)
                api_key = self._generate_api_key()
                
                conn.execute('''
                    INSERT INTO admins (username, password_hash, api_key, is_super, is_active)
                    VALUES (?, ?, ?, 1, 1)
                ''', ('admin', password_hash, api_key))
                
                logger.info(f"创建默认管理员: admin, API Key: {api_key}")
    
    def _hash_password(self, password: str) -> str:
        """
        安全密码哈希 - 使用pbkdf2算法和随机盐值
        """
        return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码是否匹配"""
        return check_password_hash(password_hash, password)
    
    def _generate_api_key(self) -> str:
        """生成 Admin API Key"""
        return f"{ADMIN_KEY_PREFIX}{secrets.token_hex(24)}"
    
    def verify_api_key(self, api_key: str) -> Optional[Admin]:
        """
        验证 Admin API Key
        
        Args:
            api_key: API Key
        
        Returns:
            Admin 对象，如果验证失败返回 None
        """
        if not api_key or not api_key.startswith(ADMIN_KEY_PREFIX):
            return None
        
        with self.db.get_connection() as conn:
            row = conn.execute('''
                SELECT * FROM admins WHERE api_key = ? AND is_active = 1
            ''', (api_key,)).fetchone()
            
            if row:
                return Admin(
                    id=row['id'],
                    username=row['username'],
                    password_hash=row['password_hash'],
                    api_key=row['api_key'],
                    is_super=bool(row['is_super']),
                    is_active=bool(row['is_active']),
                    created_at=row['created_at'],
                    last_login=row['last_login'] if 'last_login' in row.keys() else None
                )
        
        return None
    
    def verify_password(self, username: str, password: str) -> Optional[Admin]:
        """
        验证管理员密码
        
        Args:
            username: 用户名
            password: 密码
        
        Returns:
            Admin 对象，如果验证失败返回 None
        """
        with self.db.get_connection() as conn:
            row = conn.execute('''
                SELECT * FROM admins 
                WHERE username = ? AND is_active = 1
            ''', (username,)).fetchone()
            
            if row and self._verify_password(password, row['password_hash']):
                # 更新最后登录时间
                conn.execute(
                    "UPDATE admins SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                    (row['id'],)
                )
                
                return Admin(
                    id=row['id'],
                    username=row['username'],
                    password_hash=row['password_hash'],
                    api_key=row['api_key'],
                    is_super=bool(row['is_super']),
                    is_active=bool(row['is_active']),
                    created_at=row['created_at']
                )
        
        return None
    
    def create_admin(self, username: str, password: str, is_super: bool = False) -> Dict:
        """
        创建管理员
        
        Args:
            username: 用户名
            password: 密码
            is_super: 是否超级管理员
        
        Returns:
            {"success": bool, "admin": Admin, "api_key": str}
        """
        password_hash = self._hash_password(password)
        api_key = self._generate_api_key()
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO admins (username, password_hash, api_key, is_super, is_active)
                    VALUES (?, ?, ?, ?, 1)
                ''', (username, password_hash, api_key, is_super))
                
                admin_id = cursor.lastrowid
                
                logger.info(f"创建管理员: {username}")
                
                return {
                    "success": True,
                    "admin_id": admin_id,
                    "username": username,
                    "api_key": api_key,
                    "message": "管理员创建成功"
                }
        except Exception as e:
            logger.error(f"创建管理员失败: {e}")
            return {
                "success": False,
                "message": f"创建失败: {str(e)}"
            }
    
    def regenerate_api_key(self, admin_id: int) -> Dict:
        """重新生成 API Key"""
        new_api_key = self._generate_api_key()
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE admins SET api_key = ? WHERE id = ?",
                (new_api_key, admin_id)
            )
            
            if cursor.rowcount > 0:
                return {
                    "success": True,
                    "api_key": new_api_key,
                    "message": "API Key 已重新生成"
                }
        
        return {"success": False, "message": "管理员不存在"}
    
    def get_admin_by_id(self, admin_id: int) -> Optional[Admin]:
        """通过ID获取管理员"""
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM admins WHERE id = ?", (admin_id,)
            ).fetchone()
            
            if row:
                return Admin(
                    id=row['id'],
                    username=row['username'],
                    password_hash=row['password_hash'],
                    api_key=row['api_key'],
                    is_super=bool(row['is_super']),
                    is_active=bool(row['is_active']),
                    created_at=row['created_at']
                )
        return None
    
    def list_admins(self) -> list:
        """列出所有管理员"""
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT id, username, is_super, is_active, created_at, last_login FROM admins"
            ).fetchall()
            
            return [
                {
                    "id": row['id'],
                    "username": row['username'],
                    "is_super": bool(row['is_super']),
                    "is_active": bool(row['is_active']),
                    "created_at": str(row['created_at']),
                    "last_login": str(row['last_login']) if row['last_login'] else None
                }
                for row in rows
            ]


# 全局实例
_admin_auth_service: Optional[AdminAuthService] = None


def get_admin_auth_service() -> AdminAuthService:
    global _admin_auth_service
    if _admin_auth_service is None:
        _admin_auth_service = AdminAuthService()
    return _admin_auth_service


def require_admin_key():
    """
    Admin API Key 认证装饰器
    
    从请求头 X-Admin-Key 或 Authorization: Bearer 获取 API Key
    
    Usage:
        @app.route('/admin/users')
        @require_admin_key()
        def list_users():
            admin = g.current_admin
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取 API Key
            api_key = None
            
            # 从 X-Admin-Key header 获取
            api_key = request.headers.get('X-Admin-Key')
            
            # 从 Authorization header 获取
            if not api_key:
                auth_header = request.headers.get('Authorization')
                if auth_header and auth_header.startswith('Bearer '):
                    api_key = auth_header[7:]
            
            # 从 query 参数获取
            if not api_key:
                api_key = request.args.get('admin_key')
            
            if not api_key:
                return jsonify({
                    "success": False,
                    "error_code": "ADMIN_AUTH_REQUIRED",
                    "message": "需要管理员认证"
                }), 401
            
            # 验证 API Key
            service = get_admin_auth_service()
            admin = service.verify_api_key(api_key)
            
            if not admin:
                return jsonify({
                    "success": False,
                    "error_code": "INVALID_ADMIN_KEY",
                    "message": "无效的管理员 API Key"
                }), 401
            
            # 存储到 g 对象
            g.current_admin = admin
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_super_admin():
    """
    超级管理员认证装饰器
    
    必须是超级管理员才能访问
    """
    def decorator(f):
        @wraps(f)
        @require_admin_key()
        def decorated_function(*args, **kwargs):
            admin = g.current_admin
            
            if not admin.is_super:
                return jsonify({
                    "success": False,
                    "error_code": "SUPER_ADMIN_REQUIRED",
                    "message": "需要超级管理员权限"
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
