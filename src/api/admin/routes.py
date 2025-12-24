"""
Admin API 路由
用户管理、API Key 管理、套餐管理
"""

from flask import request, jsonify, g

from . import admin_bp
from ...auth.models import get_db
from ...auth.api_key import generate_api_key, require_api_key
from ...auth.admin_auth import require_admin_key, get_admin_auth_service
from ...auth.quota import get_quota_manager
from ...billing.service import get_billing_service
from ...billing.models import get_billing_db
from ...utils.logger import get_logger

logger = get_logger("admin")


# ==================== 套餐管理 (需要 Admin 认证) ====================

@admin_bp.route('/plans', methods=['GET'])
@require_admin_key()
def admin_list_plans():
    """获取所有套餐 (包括禁用的)"""
    billing_db = get_billing_db()
    plans = billing_db.get_plans(active_only=False)
    
    return jsonify({
        "success": True,
        "plans": [
            {
                "id": p.id,
                "name": p.name,
                "display_name": p.display_name,
                "description": p.description,
                "monthly_price": float(p.monthly_price),
                "daily_requests": p.daily_requests,
                "daily_tokens": p.daily_tokens,
                "daily_audio_seconds": p.daily_audio_seconds,
                "price_per_request": float(p.price_per_request),
                "price_per_1k_tokens": float(p.price_per_1k_tokens),
                "price_per_minute_audio": float(p.price_per_minute_audio),
                "is_active": p.is_active,
                "created_at": str(p.created_at) if p.created_at else None
            }
            for p in plans
        ]
    })


@admin_bp.route('/plans', methods=['POST'])
@require_admin_key()
def admin_create_plan():
    """创建套餐"""
    data = request.get_json() or {}
    
    name = data.get('name', '').strip()
    display_name = data.get('display_name', '').strip()
    
    if not name or not display_name:
        return jsonify({
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "缺少 name 或 display_name"
        }), 400
    
    billing_db = get_billing_db()
    
    # 检查名称是否已存在
    if billing_db.get_plan_by_name(name):
        return jsonify({
            "success": False,
            "error_code": "PLAN_EXISTS",
            "message": "套餐名称已存在"
        }), 400
    
    try:
        plan_id = billing_db.create_plan(
            name=name,
            display_name=display_name,
            description=data.get('description', ''),
            monthly_price=float(data.get('monthly_price', 0)),
            daily_requests=int(data.get('daily_requests', 100)),
            daily_tokens=int(data.get('daily_tokens', 10000)),
            daily_audio_seconds=int(data.get('daily_audio_seconds', 60)),
            price_per_request=float(data.get('price_per_request', 0)),
            price_per_1k_tokens=float(data.get('price_per_1k_tokens', 0)),
            price_per_minute_audio=float(data.get('price_per_minute_audio', 0))
        )
        
        logger.info(f"Admin {g.current_admin.username} 创建套餐: {name}")
        
        return jsonify({
            "success": True,
            "plan_id": plan_id,
            "message": "套餐创建成功"
        }), 201
        
    except Exception as e:
        logger.error(f"创建套餐失败: {e}")
        return jsonify({
            "success": False,
            "error_code": "CREATE_FAILED",
            "message": str(e)
        }), 500


@admin_bp.route('/plans/<int:plan_id>', methods=['PUT'])
@require_admin_key()
def admin_update_plan(plan_id):
    """更新套餐"""
    data = request.get_json() or {}
    
    if not data:
        return jsonify({
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "请提供要更新的字段"
        }), 400
    
    billing_db = get_billing_db()
    
    # 检查套餐是否存在
    plan = billing_db.get_plan(plan_id)
    if not plan:
        return jsonify({
            "success": False,
            "error_code": "NOT_FOUND",
            "message": "套餐不存在"
        }), 404
    
    try:
        success = billing_db.update_plan(plan_id, **data)
        
        if success:
            logger.info(f"Admin {g.current_admin.username} 更新套餐: {plan_id}")
            return jsonify({
                "success": True,
                "message": "套餐更新成功"
            })
        else:
            return jsonify({
                "success": False,
                "error_code": "UPDATE_FAILED",
                "message": "更新失败"
            }), 400
            
    except Exception as e:
        logger.error(f"更新套餐失败: {e}")
        return jsonify({
            "success": False,
            "error_code": "UPDATE_FAILED",
            "message": str(e)
        }), 500


@admin_bp.route('/plans/<int:plan_id>/toggle', methods=['POST'])
@require_admin_key()
def admin_toggle_plan(plan_id):
    """启用/禁用套餐"""
    billing_db = get_billing_db()
    
    plan = billing_db.get_plan(plan_id)
    if not plan:
        return jsonify({
            "success": False,
            "error_code": "NOT_FOUND",
            "message": "套餐不存在"
        }), 404
    
    new_status = not plan.is_active
    billing_db.set_plan_active(plan_id, new_status)
    
    status_text = "启用" if new_status else "禁用"
    logger.info(f"Admin {g.current_admin.username} {status_text}套餐: {plan.name}")
    
    return jsonify({
        "success": True,
        "is_active": new_status,
        "message": f"套餐已{status_text}"
    })


# ==================== 用户管理 ====================

@admin_bp.route('/users', methods=['POST'])
@require_admin_key()
def create_user():
    """创建用户"""
    import time
    import re
    start_time = time.time()
    
    try:
        data = request.get_json() or {}
        username = data.get('username', '').strip() if data.get('username') else None
        email = data.get('email', '').strip() if data.get('email') else None
        
        if not username or not email:
            return jsonify({
                "success": False,
                "error_code": "VALIDATION_ERROR",
                "message": "缺少 username 或 email",
            }), 400
        
        if not re.match(r'^[a-zA-Z0-9_]{3,30}$', username):
            return jsonify({
                "success": False,
                "error_code": "VALIDATION_ERROR",
                "message": "用户名格式错误",
            }), 400
        
        db = get_db()
        
        if db.get_user_by_username(username):
            return jsonify({
                "success": False,
                "error_code": "USER_EXISTS",
                "message": "用户名已存在",
            }), 400
        
        user_id = db.create_user(
            username=username,
            email=email,
            daily_requests=data.get('daily_requests', 1000),
            daily_tokens=data.get('daily_tokens', 100000),
            daily_audio_seconds=data.get('daily_audio_seconds', 600),
        )
        
        api_key = generate_api_key()
        db.create_api_key(user_id, api_key, name='default')
        
        duration = (time.time() - start_time) * 1000
        logger.info(f"创建用户成功 | username={username} | duration={duration:.2f}ms")
        
        return jsonify({
            "success": True,
            "user": {"id": user_id, "username": username, "email": email},
            "api_key": api_key,
        })
        
    except Exception as e:
        logger.error(f"创建用户失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error_code": "CREATE_FAILED",
            "message": str(e),
        }), 500


@admin_bp.route('/users/<username>', methods=['GET'])
@require_admin_key()
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
@require_admin_key()
def create_api_key(username):
    """为用户创建 API Key"""
    db = get_db()
    user = db.get_user_by_username(username)
    
    if not user:
        return jsonify({
            "success": False,
            "error_code": "NOT_FOUND",
            "message": "用户不存在",
        }), 404
    
    data = request.get_json() or {}
    name = data.get('name', 'default').strip()
    permissions = data.get('permissions', 'all')
    
    api_key = generate_api_key()
    key_id = db.create_api_key(user.id, api_key, name=name, permissions=permissions)
    
    logger.info(f"创建 API Key | user={username} | name={name}")
    
    return jsonify({
        "success": True,
        "api_key": {"id": key_id, "key": api_key, "name": name, "permissions": permissions}
    })


@admin_bp.route('/users/<username>/keys', methods=['GET'])
@require_admin_key()
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
                "key_prefix": k.key[:12] + "...",
                "permissions": k.permissions,
                "is_active": k.is_active,
                "created_at": str(k.created_at),
            }
            for k in keys
        ]
    })


@admin_bp.route('/keys/<key>/revoke', methods=['POST'])
@require_admin_key()
def revoke_api_key(key):
    """撤销 API Key"""
    db = get_db()
    
    if db.revoke_api_key(key):
        logger.info(f"撤销 API Key: {key[:12]}...")
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


# ==================== Admin 管理 ====================

@admin_bp.route('/admins', methods=['GET'])
@require_admin_key()
def list_admins():
    """获取管理员列表"""
    service = get_admin_auth_service()
    admins = service.list_admins()
    
    return jsonify({
        "success": True,
        "admins": admins
    })


@admin_bp.route('/admins', methods=['POST'])
@require_admin_key()
def create_admin():
    """创建管理员"""
    # 只有超级管理员可以创建管理员
    if not g.current_admin.is_super:
        return jsonify({
            "success": False,
            "error_code": "FORBIDDEN",
            "message": "需要超级管理员权限"
        }), 403
    
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    is_super = data.get('is_super', False)
    
    if not username or not password:
        return jsonify({
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "缺少 username 或 password"
        }), 400
    
    service = get_admin_auth_service()
    result = service.create_admin(username, password, is_super)
    
    if result['success']:
        logger.info(f"Admin {g.current_admin.username} 创建管理员: {username}")
        return jsonify(result), 201
    else:
        return jsonify({
            "success": False,
            "error_code": "CREATE_FAILED",
            "message": result['message']
        }), 400


# ==================== 统计 ====================

@admin_bp.route('/stats', methods=['GET'])
@require_admin_key()
def get_stats():
    """获取系统统计"""
    db = get_db()
    billing_db = get_billing_db()
    
    with db.get_connection() as conn:
        # 用户统计
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active_user_count = conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_active = 1"
        ).fetchone()[0]
    
    with billing_db.get_connection() as conn:
        # 订阅统计
        sub_count = conn.execute(
            "SELECT COUNT(*) FROM subscriptions WHERE status = 'active'"
        ).fetchone()[0]
        
        # 交易统计
        total_recharge = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'recharge'"
        ).fetchone()[0]
    
    return jsonify({
        "success": True,
        "stats": {
            "users": {
                "total": user_count,
                "active": active_user_count
            },
            "subscriptions": {
                "active": sub_count
            },
            "transactions": {
                "total_recharge": float(total_recharge)
            }
        }
    })
