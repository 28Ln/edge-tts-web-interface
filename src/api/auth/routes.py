"""
认证 API 路由
"""

from flask import request, jsonify, g

from . import auth_bp
from ...auth.auth_service import get_auth_service, require_jwt_token
from ...utils.logger import get_logger

logger = get_logger("auth.api")


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    用户注册
    
    POST /auth/register
    {
        "username": "newuser",
        "email": "user@example.com",
        "password": "password123"
    }
    """
    data = request.get_json() or {}
    
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    if not username:
        return jsonify({
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "用户名不能为空"
        }), 400
    
    if not email:
        return jsonify({
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "邮箱不能为空"
        }), 400
    
    if not password:
        return jsonify({
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "密码不能为空"
        }), 400
    
    service = get_auth_service()
    result = service.register(username, email, password)
    
    if result['success']:
        logger.info(f"新用户注册: {username}")
        return jsonify(result), 201
    else:
        return jsonify({
            "success": False,
            "error_code": "REGISTER_FAILED",
            "message": result['message']
        }), 400


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    用户登录
    
    POST /auth/login
    {
        "username": "user@example.com",  // 用户名或邮箱
        "password": "password123"
    }
    """
    data = request.get_json() or {}
    
    username_or_email = data.get('username', '').strip() or data.get('email', '').strip()
    password = data.get('password', '')
    
    if not username_or_email:
        return jsonify({
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "用户名/邮箱不能为空"
        }), 400
    
    if not password:
        return jsonify({
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "密码不能为空"
        }), 400
    
    service = get_auth_service()
    result = service.login(username_or_email, password)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify({
            "success": False,
            "error_code": "LOGIN_FAILED",
            "message": result['message']
        }), 401


@auth_bp.route('/profile', methods=['GET'])
@require_jwt_token()
def get_profile():
    """
    获取当前用户信息
    
    GET /auth/profile
    Authorization: Bearer <token>
    """
    user = g.current_auth_user
    
    return jsonify({
        "success": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "balance": user.balance,
            "email_verified": user.email_verified,
            "created_at": str(user.created_at) if user.created_at else None
        }
    })


@auth_bp.route('/change-password', methods=['POST'])
@require_jwt_token()
def change_password():
    """
    修改密码
    
    POST /auth/change-password
    Authorization: Bearer <token>
    {
        "old_password": "oldpass",
        "new_password": "newpass"
    }
    """
    user = g.current_auth_user
    data = request.get_json() or {}
    
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    
    if not old_password or not new_password:
        return jsonify({
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "请提供原密码和新密码"
        }), 400
    
    service = get_auth_service()
    result = service.change_password(user.id, old_password, new_password)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify({
            "success": False,
            "error_code": "CHANGE_PASSWORD_FAILED",
            "message": result['message']
        }), 400


@auth_bp.route('/refresh', methods=['POST'])
@require_jwt_token()
def refresh_token():
    """
    刷新 Token
    
    POST /auth/refresh
    Authorization: Bearer <token>
    """
    user = g.current_auth_user
    service = get_auth_service()
    
    # 生成新 Token
    new_token = service._generate_jwt_token(user.id, user.username)
    
    return jsonify({
        "success": True,
        "token": new_token,
        "expires_in": 24 * 3600,
        "message": "Token 已刷新"
    })
