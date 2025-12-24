"""
用户认证服务
"""

import os
import secrets
import hashlib
from typing import Optional, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash

from .models import get_db, User
from ..billing.models import get_billing_db
from ..utils.logger import get_logger

logger = get_logger("auth.service")

# 用户 API Key 前缀
USER_KEY_PREFIX = "etk_"

# JWT 配置
JWT_SECRET = os.environ.get('JWT_SECRET', os.environ.get('SECRET_KEY', 'default_jwt_secret'))
JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', '24'))

# 安全警告: 检查JWT密钥配置
if JWT_SECRET in ['default_jwt_secret', 'default_salt', 'secret', '']:
    logger.warning("⚠️ 安全警告: JWT使用默认密钥，生产环境请设置 JWT_SECRET 环境变量")


@dataclass
class AuthUser:
    """认证用户"""
    id: int
    username: str
    email: str
    password_hash: str
    email_verified: bool = False
    balance: float = 0.0
    created_at: datetime = None


class AuthService:
    """用户认证服务"""
    
    def __init__(self):
        self.user_db = get_db()
        self.billing_db = get_billing_db()
    
    def _hash_password(self, password: str) -> str:
        """
        安全密码哈希 - 使用pbkdf2算法和随机盐值
        
        每次调用都会生成不同的哈希值（因为使用随机盐）
        """
        return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """
        验证密码是否匹配
        
        Args:
            password: 明文密码
            password_hash: 存储的哈希值
        
        Returns:
            密码是否匹配
        """
        return check_password_hash(password_hash, password)
    
    def _generate_api_key(self) -> str:
        """生成用户 API Key"""
        return f"{USER_KEY_PREFIX}{secrets.token_hex(16)}"
    
    def _generate_jwt_token(self, user_id: int, username: str) -> str:
        """
        生成 JWT Token
        
        简单实现，生产环境建议使用 PyJWT 库
        """
        import base64
        import json
        import hmac
        
        # Header
        header = {"alg": "HS256", "typ": "JWT"}
        
        # Payload
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "username": username,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=JWT_EXPIRY_HOURS)).timestamp())
        }
        
        # Encode
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        
        # Sign
        message = f"{header_b64}.{payload_b64}"
        signature = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')
        
        return f"{header_b64}.{payload_b64}.{signature_b64}"
    
    def _verify_jwt_token(self, token: str) -> Optional[Dict]:
        """验证 JWT Token"""
        import base64
        import json
        import hmac
        
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            header_b64, payload_b64, signature_b64 = parts
            
            # 验证签名
            message = f"{header_b64}.{payload_b64}"
            expected_sig = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).digest()
            expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip('=')
            
            if signature_b64 != expected_sig_b64:
                return None
            
            # 解码 payload
            # 添加 padding
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += '=' * padding
            
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            
            # 检查过期
            if payload.get('exp', 0) < datetime.utcnow().timestamp():
                return None
            
            return payload
            
        except Exception as e:
            logger.debug(f"JWT 验证失败: {e}")
            return None
    
    def register(self, username: str, email: str, password: str) -> Dict:
        """
        用户注册
        
        Args:
            username: 用户名
            email: 邮箱
            password: 密码
        
        Returns:
            {"success": bool, "user": User, "api_key": str}
        """
        # 验证输入
        if not username or len(username) < 3:
            return {"success": False, "message": "用户名至少3个字符"}
        
        if not email or '@' not in email:
            return {"success": False, "message": "邮箱格式不正确"}
        
        if not password or len(password) < 6:
            return {"success": False, "message": "密码至少6个字符"}
        
        password_hash = self._hash_password(password)
        
        try:
            # 创建用户
            with self.user_db.get_connection() as conn:
                # 检查用户名是否存在
                existing = conn.execute(
                    "SELECT id FROM users WHERE username = ?", (username,)
                ).fetchone()
                if existing:
                    return {"success": False, "message": "用户名已存在"}
                
                # 检查邮箱是否存在
                existing = conn.execute(
                    "SELECT id FROM users WHERE email = ?", (email,)
                ).fetchone()
                if existing:
                    return {"success": False, "message": "邮箱已被注册"}
                
                # 创建用户
                cursor = conn.execute('''
                    INSERT INTO users (username, email, password_hash, balance, email_verified)
                    VALUES (?, ?, ?, 0, 0)
                ''', (username, email, password_hash))
                user_id = cursor.lastrowid
            
            # 生成 API Key
            api_key = self._generate_api_key()
            self.user_db.create_api_key(user_id, api_key, 'all')
            
            # 创建免费套餐订阅
            free_plan = self.billing_db.get_plan_by_name('free')
            if free_plan:
                self.billing_db.create_subscription(
                    user_id, free_plan.id, datetime.now(), None
                )
            
            logger.info(f"用户注册成功: {username}")
            
            return {
                "success": True,
                "user_id": user_id,
                "username": username,
                "email": email,
                "api_key": api_key,
                "message": "注册成功"
            }
            
        except Exception as e:
            logger.error(f"用户注册失败: {e}")
            return {"success": False, "message": f"注册失败: {str(e)}"}
    
    def login(self, username_or_email: str, password: str) -> Dict:
        """
        用户登录
        
        Args:
            username_or_email: 用户名或邮箱
            password: 密码
        
        Returns:
            {"success": bool, "token": str, "user": dict}
        """
        with self.user_db.get_connection() as conn:
            # 先通过用户名或邮箱查找用户
            row = conn.execute('''
                SELECT id, username, email, password_hash, balance, email_verified
                FROM users 
                WHERE (username = ? OR email = ?) AND is_active = 1
            ''', (username_or_email, username_or_email)).fetchone()
            
            if not row:
                return {"success": False, "message": "用户名/邮箱或密码错误"}
            
            # 使用安全的密码验证方法
            if not self._verify_password(password, row['password_hash']):
                return {"success": False, "message": "用户名/邮箱或密码错误"}
            
            user_id = row['id']
            username = row['username']
            
            # 生成 JWT Token
            token = self._generate_jwt_token(user_id, username)
            
            logger.info(f"用户登录成功: {username}")
            
            return {
                "success": True,
                "token": token,
                "user": {
                    "id": user_id,
                    "username": username,
                    "email": row['email'],
                    "balance": float(row['balance']) if row['balance'] else 0,
                    "email_verified": bool(row['email_verified'])
                },
                "expires_in": JWT_EXPIRY_HOURS * 3600,
                "message": "登录成功"
            }
    
    def verify_token(self, token: str) -> Optional[AuthUser]:
        """验证 Token 并返回用户"""
        payload = self._verify_jwt_token(token)
        if not payload:
            return None
        
        user_id = payload.get('sub')
        if not user_id:
            return None
        
        # 获取用户信息
        with self.user_db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ? AND is_active = 1",
                (user_id,)
            ).fetchone()
            
            if row:
                return AuthUser(
                    id=row['id'],
                    username=row['username'],
                    email=row['email'],
                    password_hash=row['password_hash'],
                    email_verified=bool(row['email_verified']) if 'email_verified' in row.keys() else False,
                    balance=float(row['balance']) if row['balance'] else 0,
                    created_at=row['created_at']
                )
        
        return None
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> Dict:
        """修改密码"""
        if len(new_password) < 6:
            return {"success": False, "message": "新密码至少6个字符"}
        
        with self.user_db.get_connection() as conn:
            # 获取当前密码哈希
            row = conn.execute(
                "SELECT password_hash FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()
            
            if not row:
                return {"success": False, "message": "用户不存在"}
            
            # 验证旧密码
            if not self._verify_password(old_password, row['password_hash']):
                return {"success": False, "message": "原密码错误"}
            
            # 生成新密码哈希并更新
            new_hash = self._hash_password(new_password)
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_hash, user_id)
            )
        
        logger.info(f"用户 {user_id} 修改密码成功")
        return {"success": True, "message": "密码修改成功"}
    
    def get_user_by_id(self, user_id: int) -> Optional[AuthUser]:
        """通过ID获取用户"""
        with self.user_db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            
            if row:
                return AuthUser(
                    id=row['id'],
                    username=row['username'],
                    email=row['email'],
                    password_hash=row['password_hash'],
                    email_verified=bool(row['email_verified']) if 'email_verified' in row.keys() else False,
                    balance=float(row['balance']) if row['balance'] else 0,
                    created_at=row['created_at']
                )
        return None


# 全局实例
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


def require_jwt_token():
    """
    JWT Token 认证装饰器
    
    从 Authorization: Bearer 获取 Token
    
    Usage:
        @app.route('/api/profile')
        @require_jwt_token()
        def get_profile():
            user = g.current_auth_user
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取 Token
            auth_header = request.headers.get('Authorization')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({
                    "success": False,
                    "error_code": "AUTH_REQUIRED",
                    "message": "需要认证"
                }), 401
            
            token = auth_header[7:]
            
            # 验证 Token
            service = get_auth_service()
            user = service.verify_token(token)
            
            if not user:
                return jsonify({
                    "success": False,
                    "error_code": "INVALID_TOKEN",
                    "message": "无效或过期的 Token"
                }), 401
            
            # 存储到 g 对象
            g.current_auth_user = user
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
