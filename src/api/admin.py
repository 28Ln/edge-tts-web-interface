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
    import time
    import re
    start_time = time.time()
    
    try:
        # 解析 JSON
        try:
            data = request.get_json() or {}
        except Exception as e:
            logger.warning(f"[ADMIN] JSON 解析失败 | error={e}")
            return jsonify({
                "success": False,
                "error_code": "VALIDATION_ERROR",
                "message": f"JSON 解析失败: {e}",
            }), 400
        
        username = data.get('username', '').strip() if data.get('username') else None
        email = data.get('email', '').strip() if data.get('email') else None
        
        # 验证必填字段
        if not username or not email:
            return jsonify({
                "success": False,
                "error_code": "VALIDATION_ERROR",
                "message": "缺少 username 或 email",
            }), 400
        
        # 验证用户名格式（字母数字下划线，3-30字符）
        if not re.match(r'^[a-zA-Z0-9_]{3,30}$', username):
            return jsonify({
                "success": False,
                "error_code": "VALIDATION_ERROR",
                "message": "用户名格式错误，仅支持字母数字下划线，3-30字符",
            }), 400
        
        # 验证邮箱格式
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({
                "success": False,
                "error_code": "VALIDATION_ERROR",
                "message": "邮箱格式错误",
            }), 400
        
        # 验证配额参数
        daily_requests = data.get('daily_requests', 1000)
        daily_tokens = data.get('daily_tokens', 100000)
        daily_audio_seconds = data.get('daily_audio_seconds', 600)
        
        if not isinstance(daily_requests, int) or daily_requests < 0:
            return jsonify({
                "success": False,
                "error_code": "VALIDATION_ERROR",
                "message": "daily_requests 必须是非负整数",
            }), 400
        
        if not isinstance(daily_tokens, int) or daily_tokens < 0:
            return jsonify({
                "success": False,
                "error_code": "VALIDATION_ERROR",
                "message": "daily_tokens 必须是非负整数",
            }), 400
        
        if not isinstance(daily_audio_seconds, int) or daily_audio_seconds < 0:
            return jsonify({
                "success": False,
                "error_code": "VALIDATION_ERROR",
                "message": "daily_audio_seconds 必须是非负整数",
            }), 400
        
        logger.info(f"[ADMIN] 创建用户请求 | username={username} | email={email}")
        
        db = get_db()
        
        # 检查用户是否已存在
        if db.get_user_by_username(username):
            logger.warning(f"[ADMIN] 用户名已存在 | username={username}")
            return jsonify({
                "success": False,
                "error_code": "USER_EXISTS",
                "message": "用户名已存在",
            }), 400
        
        # 创建用户
        user_id = db.create_user(
            username=username,
            email=email,
            daily_requests=daily_requests,
            daily_tokens=daily_tokens,
            daily_audio_seconds=daily_audio_seconds,
        )
        
        # 自动生成一个 API Key
        api_key = generate_api_key()
        db.create_api_key(user_id, api_key, name='default')
        
        duration = (time.time() - start_time) * 1000
        logger.info(f"[ADMIN] 创建用户成功 | username={username} | id={user_id} | duration={duration:.2f}ms")
        
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
        duration = (time.time() - start_time) * 1000
        logger.error(f"[ADMIN] 创建用户失败 | error={e} | duration={duration:.2f}ms", exc_info=True)
        return jsonify({
            "success": False,
            "error_code": "CREATE_FAILED",
            "message": str(e),
        }), 500


@admin_bp.route('/users/<username>', methods=['GET'])
def get_user(username):
    """获取用户信息"""
    import time
    start_time = time.time()
    
    try:
        logger.info(f"[ADMIN] 获取用户信息 | username={username}")
        
        db = get_db()
        user = db.get_user_by_username(username)
        
        if not user:
            logger.warning(f"[ADMIN] 用户不存在 | username={username}")
            return jsonify({
                "success": False,
                "error_code": "NOT_FOUND",
                "message": "用户不存在",
            }), 404
        
        # 获取用量
        manager = get_quota_manager()
        usage = manager.get_usage_summary(user.id)
        
        duration = (time.time() - start_time) * 1000
        logger.info(f"[ADMIN] 获取用户信息成功 | username={username} | duration={duration:.2f}ms")
        
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
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"[ADMIN] 获取用户信息失败 | username={username} | error={e} | duration={duration:.2f}ms", exc_info=True)
        return jsonify({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
        }), 500


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
    import time
    start_time = time.time()
    
    try:
        logger.info(f"[ADMIN] 创建 API Key 请求 | username={username}")
        
        db = get_db()
        user = db.get_user_by_username(username)
        
        if not user:
            logger.warning(f"[ADMIN] 用户不存在 | username={username}")
            return jsonify({
                "success": False,
                "error_code": "NOT_FOUND",
                "message": "用户不存在",
            }), 404
        
        # 解析 JSON
        try:
            data = request.get_json() or {}
        except Exception as e:
            logger.warning(f"[ADMIN] JSON 解析失败 | error={e}")
            return jsonify({
                "success": False,
                "error_code": "VALIDATION_ERROR",
                "message": f"JSON 解析失败: {e}",
            }), 400
        
        name = data.get('name', 'default').strip()
        permissions = data.get('permissions', 'all')
        
        # 验证 name
        if not name or len(name) > 50:
            return jsonify({
                "success": False,
                "error_code": "VALIDATION_ERROR",
                "message": "name 不能为空且不超过50字符",
            }), 400
        
        api_key = generate_api_key()
        key_id = db.create_api_key(user.id, api_key, name=name, permissions=permissions)
        
        duration = (time.time() - start_time) * 1000
        logger.info(f"[ADMIN] 创建 API Key 成功 | user={username} | name={name} | duration={duration:.2f}ms")
        
        return jsonify({
            "success": True,
            "api_key": {
                "id": key_id,
                "key": api_key,  # 只返回一次
                "name": name,
                "permissions": permissions,
            }
        })
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"[ADMIN] 创建 API Key 失败 | username={username} | error={e} | duration={duration:.2f}ms", exc_info=True)
        return jsonify({
            "success": False,
            "error_code": "CREATE_FAILED",
            "message": str(e),
        }), 500


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
    import time
    start_time = time.time()
    
    try:
        logger.info(f"[ADMIN] 撤销 API Key 请求 | key={key[:12]}...")
        
        db = get_db()
        
        if db.revoke_api_key(key):
            duration = (time.time() - start_time) * 1000
            logger.info(f"[ADMIN] 撤销 API Key 成功 | key={key[:12]}... | duration={duration:.2f}ms")
            return jsonify({"success": True, "message": "API Key 已撤销"})
        else:
            logger.warning(f"[ADMIN] API Key 不存在 | key={key[:12]}...")
            return jsonify({
                "success": False,
                "error_code": "NOT_FOUND",
                "message": "API Key 不存在",
            }), 404
            
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"[ADMIN] 撤销 API Key 失败 | key={key[:12]}... | error={e} | duration={duration:.2f}ms", exc_info=True)
        return jsonify({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
        }), 500


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
