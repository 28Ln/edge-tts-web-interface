"""
管理员 API
用户管理、API Key 管理
"""

from flask import Blueprint, request, jsonify, g

from ..auth.models import get_db
from ..auth.api_key import generate_api_key, require_api_key
from ..auth.quota import get_quota_manager
from ..utils.logger import get_logger

logger = get_logger("admin")

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ==================== 用户管理 ====================

@admin_bp.route('/users', methods=['POST'])
def create_user():
    """
    创建用户
    
    POST /admin/users
    {
        "username": "user1",
        "email": "user1@example.com",
        "daily_requests": 1000,
        "daily_tokens": 100000,
        "daily_audio_seconds": 600
    }
    """
    data = request.get_json() or {}
    
    username = data.get('username')
    email = data.get('email')
    
    if not username or not email:
        return jsonify({
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "缺少 username 或 email",
        }), 400
    
    db = get_db()
    
    # 检查用户是否已存在
    if db.get_user_by_username(username):
        return jsonify({
            "success": False,
            "error_code": "USER_EXISTS",
            "message": "用户名已存在",
        }), 400
    
    # 创建用户
    try:
        user_id = db.create_user(
            username=username,
            email=email,
            daily_requests=data.get('daily_requests', 1000),
            daily_tokens=data.get('daily_tokens', 100000),
            daily_audio_seconds=data.get('daily_audio_seconds', 600),
        )
        
        # 自动生成一个 API Key
        api_key = generate_api_key()
        db.create_api_key(user_id, api_key, name='default')
        
        logger.info(f"创建用户成功 | username={username} | id={user_id}")
        
        return jsonify({
            "success": True,
            "user": {
                "id": user_id,
                "username": username,
                "email": email,
            },
            "api_key": api_key,  # 只在创建时返回一次
        })
    except Exception as e:
        logger.error(f"创建用户失败: {e}")
        return jsonify({
            "success": False,
            "error_code": "CREATE_FAILED",
            "message": str(e),
        }), 500


@admin_bp.route('/users/<username>', methods=['GET'])
def get_user(username):
    """获取用户信息"""
    db = get_db()
    user = db.get_user_by_username(username)
    
    if not user:
        return jsonify({
            "success": False,
            "error_code": "NOT_FOUND",
            "message": "用户不存在",
        }), 404
    
    # 获取用量
    manager = get_quota_manager()
    usage = manager.get_usage_summary(user.id)
    
    return jsonify({
        "success": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "created_at": str(user.created_at),
        },
        "quota": {
            "daily_requests": user.daily_requests,
            "daily_tokens": user.daily_tokens,
            "daily_audio_seconds": user.daily_audio_seconds,
        },
        "usage": usage,
    })


# ==================== API Key 管理 ====================

@admin_bp.route('/users/<username>/keys', methods=['POST'])
def create_api_key(username):
    """
    为用户创建新的 API Key
    
    POST /admin/users/{username}/keys
    {
        "name": "my-key",
        "permissions": "all"
    }
    """
    db = get_db()
    user = db.get_user_by_username(username)
    
    if not user:
        return jsonify({
            "success": False,
            "error_code": "NOT_FOUND",
            "message": "用户不存在",
        }), 404
    
    data = request.get_json() or {}
    name = data.get('name', 'default')
    permissions = data.get('permissions', 'all')
    
    api_key = generate_api_key()
    key_id = db.create_api_key(user.id, api_key, name=name, permissions=permissions)
    
    logger.info(f"创建 API Key | user={username} | name={name}")
    
    return jsonify({
        "success": True,
        "api_key": {
            "id": key_id,
            "key": api_key,  # 只返回一次
            "name": name,
            "permissions": permissions,
        }
    })


@admin_bp.route('/users/<username>/keys', methods=['GET'])
def list_api_keys(username):
    """获取用户的所有 API Key"""
    db = get_db()
    user = db.get_user_by_username(username)
    
    if not user:
        return jsonify({
            "success": False,
            "error_code": "NOT_FOUND",
            "message": "用户不存在",
        }), 404
    
    keys = db.get_user_api_keys(user.id)
    
    return jsonify({
        "success": True,
        "keys": [
            {
                "id": k.id,
                "name": k.name,
                "key_prefix": k.key[:12] + "...",  # 只显示前缀
                "permissions": k.permissions,
                "is_active": k.is_active,
                "created_at": str(k.created_at),
            }
            for k in keys
        ]
    })


@admin_bp.route('/keys/<key>/revoke', methods=['POST'])
def revoke_api_key(key):
    """撤销 API Key"""
    db = get_db()
    
    if db.revoke_api_key(key):
        logger.info(f"撤销 API Key | key={key[:12]}...")
        return jsonify({"success": True, "message": "API Key 已撤销"})
    else:
        return jsonify({
            "success": False,
            "error_code": "NOT_FOUND",
            "message": "API Key 不存在",
        }), 404


# ==================== 用量查询 ====================

@admin_bp.route('/usage/me', methods=['GET'])
@require_api_key()
def my_usage():
    """查询当前用户的用量"""
    user = g.current_user
    manager = get_quota_manager()
    usage = manager.get_usage_summary(user.id)
    
    return jsonify({
        "success": True,
        "user": user.username,
        "usage": usage,
    })
