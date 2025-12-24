"""
计费 API 路由
"""

from flask import request, jsonify, g

from . import billing_bp
from ...billing.service import get_billing_service
from ...auth.api_key import require_api_key, optional_api_key
from ...utils.logger import get_logger

logger = get_logger("billing.api")


@billing_bp.route('/plans', methods=['GET'])
def get_plans():
    """获取套餐列表"""
    service = get_billing_service()
    plans = service.get_plans()
    
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
                "price_per_minute_audio": float(p.price_per_minute_audio)
            }
            for p in plans
        ]
    })


@billing_bp.route('/plans/<int:plan_id>', methods=['GET'])
def get_plan(plan_id):
    """获取套餐详情"""
    service = get_billing_service()
    plan = service.get_plan(plan_id)
    
    if not plan:
        return jsonify({
            "success": False,
            "error_code": "NOT_FOUND",
            "message": "套餐不存在"
        }), 404
    
    return jsonify({
        "success": True,
        "plan": {
            "id": plan.id,
            "name": plan.name,
            "display_name": plan.display_name,
            "description": plan.description,
            "monthly_price": float(plan.monthly_price),
            "daily_requests": plan.daily_requests,
            "daily_tokens": plan.daily_tokens,
            "daily_audio_seconds": plan.daily_audio_seconds,
            "price_per_request": float(plan.price_per_request),
            "price_per_1k_tokens": float(plan.price_per_1k_tokens),
            "price_per_minute_audio": float(plan.price_per_minute_audio),
            "is_active": plan.is_active
        }
    })


@billing_bp.route('/pricing', methods=['GET'])
def get_pricing():
    """获取定价信息"""
    plan_name = request.args.get('plan')
    service = get_billing_service()
    result = service.get_pricing_info(plan_name)
    
    return jsonify({
        "success": True,
        **result
    })


@billing_bp.route('/subscription', methods=['GET'])
@require_api_key()
def get_subscription():
    """获取当前订阅"""
    user = g.current_user
    service = get_billing_service()
    sub = service.get_user_subscription(user.id)
    
    return jsonify({
        "success": True,
        "subscription": {
            "plan": sub.plan.name if sub and sub.plan else "free",
            "display_name": sub.plan.display_name if sub and sub.plan else "免费版",
            "status": sub.status if sub else "active",
            "start_date": str(sub.start_date) if sub else None,
            "end_date": str(sub.end_date) if sub and sub.end_date else None,
            "quota": {
                "daily_requests": sub.plan.daily_requests if sub and sub.plan else 100,
                "daily_tokens": sub.plan.daily_tokens if sub and sub.plan else 10000,
                "daily_audio_seconds": sub.plan.daily_audio_seconds if sub and sub.plan else 60
            }
        }
    })


@billing_bp.route('/subscribe', methods=['POST'])
@require_api_key()
def subscribe():
    """订阅套餐"""
    user = g.current_user
    data = request.get_json() or {}
    
    plan_name = data.get('plan')
    months = data.get('months', 1)
    
    if not plan_name:
        return jsonify({
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "缺少 plan 参数"
        }), 400
    
    service = get_billing_service()
    result = service.subscribe(user.id, plan_name, months)
    
    if result['success']:
        logger.info(f"用户 {user.username} 订阅 {plan_name}")
        return jsonify(result)
    else:
        return jsonify({
            "success": False,
            "error_code": "SUBSCRIBE_FAILED",
            "message": result['message']
        }), 400


@billing_bp.route('/cancel', methods=['POST'])
@require_api_key()
def cancel_subscription():
    """取消订阅"""
    user = g.current_user
    service = get_billing_service()
    result = service.cancel_subscription(user.id)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify({
            "success": False,
            "error_code": "CANCEL_FAILED",
            "message": result['message']
        }), 400


@billing_bp.route('/balance', methods=['GET'])
@require_api_key()
def get_balance():
    """获取余额"""
    user = g.current_user
    service = get_billing_service()
    balance = service.get_balance(user.id)
    
    return jsonify({
        "success": True,
        "balance": balance
    })


@billing_bp.route('/recharge', methods=['POST'])
@require_api_key()
def recharge():
    """
    充值 (模拟)
    
    实际生产环境需要对接支付网关
    """
    user = g.current_user
    data = request.get_json() or {}
    
    amount = data.get('amount')
    reference_id = data.get('reference_id')
    
    if not amount or amount <= 0:
        return jsonify({
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "充值金额必须大于0"
        }), 400
    
    service = get_billing_service()
    result = service.recharge(user.id, amount, reference_id)
    
    logger.info(f"用户 {user.username} 充值 ¥{amount}")
    return jsonify(result)


@billing_bp.route('/transactions', methods=['GET'])
@require_api_key()
def get_transactions():
    """获取交易记录"""
    user = g.current_user
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    trans_type = request.args.get('type')  # 可选: recharge, consume, refund, subscribe
    
    service = get_billing_service()
    result = service.get_transactions(user.id, page, limit, trans_type)
    
    return jsonify({
        "success": True,
        **result
    })


@billing_bp.route('/quota', methods=['GET'])
@require_api_key()
def get_quota():
    """获取配额状态"""
    user = g.current_user
    
    from ...billing.quota import get_quota_service
    quota_service = get_quota_service()
    result = quota_service.get_quota_status(user.id)
    
    return jsonify({
        "success": True,
        **result
    })


@billing_bp.route('/upgrade', methods=['POST'])
@require_api_key()
def upgrade_subscription():
    """升级订阅"""
    user = g.current_user
    data = request.get_json() or {}
    
    new_plan = data.get('plan')
    if not new_plan:
        return jsonify({
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "缺少 plan 参数"
        }), 400
    
    service = get_billing_service()
    result = service.upgrade_subscription(user.id, new_plan)
    
    if result['success']:
        logger.info(f"用户 {user.username} 升级到 {new_plan}")
        return jsonify(result)
    else:
        return jsonify({
            "success": False,
            "error_code": "UPGRADE_FAILED",
            "message": result['message']
        }), 400


@billing_bp.route('/summary', methods=['GET'])
@require_api_key()
def get_summary():
    """获取计费摘要"""
    user = g.current_user
    service = get_billing_service()
    summary = service.get_user_billing_summary(user.id)
    
    return jsonify({
        "success": True,
        **summary
    })
