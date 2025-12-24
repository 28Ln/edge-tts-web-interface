"""
配额管理服务
"""

from typing import Dict, Optional
from functools import wraps
from flask import g, jsonify

from .service import get_billing_service
from ..utils.logger import get_logger

logger = get_logger("billing.quota")


class QuotaService:
    """配额管理服务"""
    
    def __init__(self):
        self.billing_service = get_billing_service()
    
    def check_and_consume(self, user_id: int, quota_type: str, amount: int = 1) -> Dict:
        """
        检查配额并消费
        
        Args:
            user_id: 用户ID
            quota_type: 配额类型 (requests, tokens, audio_seconds)
            amount: 消费数量
        
        Returns:
            {
                "allowed": bool,
                "remaining": int,
                "limit": int,
                "used_balance": bool,
                "cost": float,
                "error_code": str (if not allowed)
            }
        """
        # 先检查订阅是否过期
        self.billing_service.check_subscription_expiry(user_id)
        
        # 检查配额
        quota_result = self.billing_service.check_quota(user_id, quota_type)
        
        if quota_result.get('allowed'):
            return {
                "allowed": True,
                "remaining": quota_result.get('remaining', 0) - amount,
                "limit": quota_result.get('limit', 0),
                "used_balance": False,
                "cost": 0
            }
        
        # 配额用完，尝试按量计费
        if quota_result.get('can_pay'):
            sub = self.billing_service.get_user_subscription(user_id)
            if sub and sub.plan:
                cost = self.billing_service.calculate_cost(sub.plan, quota_type, amount)
                
                if cost > 0:
                    deduct_result = self.billing_service.deduct_balance(
                        user_id, cost, f"按量计费: {quota_type} x {amount}"
                    )
                    
                    if deduct_result.get('success'):
                        return {
                            "allowed": True,
                            "remaining": 0,
                            "limit": quota_result.get('limit', 0),
                            "used_balance": True,
                            "cost": cost,
                            "new_balance": deduct_result.get('new_balance')
                        }
        
        # 无法使用
        return {
            "allowed": False,
            "remaining": 0,
            "limit": quota_result.get('limit', 0),
            "error_code": "QUOTA_EXCEEDED",
            "message": f"配额已用完，余额不足以按量计费",
            "can_pay": quota_result.get('can_pay', False),
            "balance": quota_result.get('balance', 0)
        }
    
    def get_quota_status(self, user_id: int) -> Dict:
        """
        获取用户配额状态
        
        Returns:
            {
                "plan": str,
                "quotas": {
                    "requests": {"used": int, "limit": int, "remaining": int},
                    "tokens": {...},
                    "audio_seconds": {...}
                },
                "balance": float,
                "can_pay_as_you_go": bool
            }
        """
        sub = self.billing_service.get_user_subscription(user_id)
        balance = self.billing_service.get_balance(user_id)
        
        quotas = {}
        for quota_type in ['requests', 'tokens', 'audio_seconds']:
            result = self.billing_service.check_quota(user_id, quota_type)
            quotas[quota_type] = {
                "used": result.get('used', 0),
                "limit": result.get('limit', 0),
                "remaining": result.get('remaining', 0)
            }
        
        return {
            "plan": sub.plan.name if sub and sub.plan else "free",
            "plan_display_name": sub.plan.display_name if sub and sub.plan else "免费版",
            "quotas": quotas,
            "balance": balance,
            "can_pay_as_you_go": balance > 0
        }


# 全局实例
_quota_service: Optional[QuotaService] = None


def get_quota_service() -> QuotaService:
    global _quota_service
    if _quota_service is None:
        _quota_service = QuotaService()
    return _quota_service


def require_quota(quota_type: str = 'requests', amount: int = 1):
    """
    配额检查装饰器
    
    用于保护需要配额的 API 端点
    
    Usage:
        @app.route('/api/tts')
        @require_api_key()
        @require_quota('requests', 1)
        def tts():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = getattr(g, 'current_user', None)
            if not user:
                return jsonify({
                    "success": False,
                    "error_code": "AUTH_REQUIRED",
                    "message": "需要认证"
                }), 401
            
            quota_service = get_quota_service()
            result = quota_service.check_and_consume(user.id, quota_type, amount)
            
            if not result.get('allowed'):
                return jsonify({
                    "success": False,
                    "error_code": result.get('error_code', 'QUOTA_EXCEEDED'),
                    "message": result.get('message', '配额不足'),
                    "quota": {
                        "type": quota_type,
                        "limit": result.get('limit', 0),
                        "remaining": result.get('remaining', 0)
                    }
                }), 429
            
            # 将配额信息存储到 g 对象，供后续使用
            g.quota_result = result
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
