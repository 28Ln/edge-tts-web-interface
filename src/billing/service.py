"""
计费服务
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict

from .models import Plan, Subscription, Transaction, get_billing_db
from ..auth.models import get_db, User
from ..utils.logger import get_logger

logger = get_logger("billing")


class BillingService:
    """计费服务"""
    
    def __init__(self):
        self.billing_db = get_billing_db()
        self.user_db = get_db()
    
    # ==================== 套餐管理 ====================
    
    def get_plans(self, active_only: bool = True) -> List[Plan]:
        """获取套餐列表"""
        return self.billing_db.get_plans(active_only)
    
    def get_plan(self, plan_id: int) -> Optional[Plan]:
        """获取套餐详情"""
        return self.billing_db.get_plan(plan_id)
    
    def get_plan_by_name(self, name: str) -> Optional[Plan]:
        """通过名称获取套餐"""
        return self.billing_db.get_plan_by_name(name)
    
    # ==================== 订阅管理 ====================
    
    def get_user_subscription(self, user_id: int) -> Optional[Subscription]:
        """获取用户当前订阅"""
        sub = self.billing_db.get_user_subscription(user_id)
        
        # 如果没有订阅，返回免费套餐
        if not sub:
            free_plan = self.billing_db.get_plan_by_name('free')
            if free_plan:
                sub = Subscription(
                    id=0,
                    user_id=user_id,
                    plan_id=free_plan.id,
                    status='active',
                    start_date=datetime.now(),
                    plan=free_plan
                )
        
        return sub
    
    def subscribe(self, user_id: int, plan_name: str, months: int = 1) -> Dict:
        """
        订阅套餐
        
        Returns:
            {"success": bool, "subscription": Subscription, "message": str}
        """
        plan = self.billing_db.get_plan_by_name(plan_name)
        if not plan:
            return {"success": False, "message": f"套餐不存在: {plan_name}"}
        
        if not plan.is_active:
            return {"success": False, "message": "该套餐已下架"}
        
        # 计算费用
        total_cost = float(plan.monthly_price) * months
        
        # 免费套餐直接订阅
        if total_cost == 0:
            start_date = datetime.now()
            sub_id = self.billing_db.create_subscription(
                user_id, plan.id, start_date, None
            )
            logger.info(f"用户 {user_id} 订阅免费套餐")
            return {
                "success": True,
                "subscription_id": sub_id,
                "message": "订阅成功"
            }
        
        # 检查余额
        balance = self.billing_db.get_balance(user_id)
        if balance < total_cost:
            return {
                "success": False,
                "message": f"余额不足，需要 ¥{total_cost}，当前余额 ¥{balance}"
            }
        
        # 扣除余额
        new_balance = self.billing_db.update_balance(user_id, -total_cost)
        
        # 创建交易记录
        self.billing_db.create_transaction(
            user_id=user_id,
            type='subscribe',
            amount=-total_cost,
            balance_after=new_balance,
            description=f"订阅{plan.display_name} {months}个月"
        )
        
        # 创建订阅
        start_date = datetime.now()
        end_date = start_date + timedelta(days=30 * months)
        sub_id = self.billing_db.create_subscription(
            user_id, plan.id, start_date, end_date
        )
        
        logger.info(f"用户 {user_id} 订阅 {plan.display_name}，费用 ¥{total_cost}")
        
        return {
            "success": True,
            "subscription_id": sub_id,
            "cost": total_cost,
            "new_balance": new_balance,
            "message": "订阅成功"
        }
    
    def cancel_subscription(self, user_id: int) -> Dict:
        """取消订阅"""
        if self.billing_db.cancel_subscription(user_id):
            logger.info(f"用户 {user_id} 取消订阅")
            return {"success": True, "message": "已取消订阅，将在到期后降级为免费版"}
        return {"success": False, "message": "没有活跃的订阅"}
    
    def check_subscription_expiry(self, user_id: int) -> Dict:
        """
        检查用户订阅是否过期，如果过期则自动降级到免费套餐
        
        Returns:
            {"expired": bool, "downgraded": bool, "subscription": Subscription}
        """
        sub = self.billing_db.get_user_subscription(user_id)
        
        if not sub:
            # 没有订阅，返回免费套餐状态
            return {
                "expired": False,
                "downgraded": False,
                "plan": "free"
            }
        
        # 检查是否过期
        if sub.end_date and sub.end_date < datetime.now():
            # 订阅已过期，标记为过期
            self.billing_db.expire_subscription(sub.id)
            
            # 自动创建免费套餐订阅
            free_plan = self.billing_db.get_plan_by_name('free')
            if free_plan:
                self.billing_db.create_subscription(
                    user_id, free_plan.id, datetime.now(), None
                )
            
            logger.info(f"用户 {user_id} 订阅已过期，自动降级为免费版")
            
            return {
                "expired": True,
                "downgraded": True,
                "plan": "free",
                "previous_plan": sub.plan.name if sub.plan else None
            }
        
        return {
            "expired": False,
            "downgraded": False,
            "plan": sub.plan.name if sub.plan else "free"
        }
    
    def process_expired_subscriptions(self) -> Dict:
        """
        处理所有过期订阅 (定时任务调用)
        
        Returns:
            {"processed": int, "downgraded": int}
        """
        expired_subs = self.billing_db.get_expired_subscriptions()
        processed = 0
        downgraded = 0
        
        free_plan = self.billing_db.get_plan_by_name('free')
        
        for sub in expired_subs:
            # 标记为过期
            self.billing_db.expire_subscription(sub.id)
            processed += 1
            
            # 创建免费套餐订阅
            if free_plan:
                self.billing_db.create_subscription(
                    sub.user_id, free_plan.id, datetime.now(), None
                )
                downgraded += 1
            
            logger.info(f"用户 {sub.user_id} 订阅过期，已降级为免费版")
        
        return {
            "processed": processed,
            "downgraded": downgraded
        }
    
    def upgrade_subscription(self, user_id: int, new_plan_name: str) -> Dict:
        """
        升级订阅 (立即生效) - 使用原子事务确保数据一致性
        
        Returns:
            {"success": bool, "message": str}
        """
        new_plan = self.billing_db.get_plan_by_name(new_plan_name)
        if not new_plan:
            return {"success": False, "message": f"套餐不存在: {new_plan_name}"}
        
        if not new_plan.is_active:
            return {"success": False, "message": "该套餐已下架"}
        
        current_sub = self.billing_db.get_user_subscription(user_id)
        
        # 检查是否是升级
        if current_sub and current_sub.plan:
            if float(new_plan.monthly_price) <= float(current_sub.plan.monthly_price):
                return {"success": False, "message": "只能升级到更高级的套餐"}
        
        # 计算升级费用 (按剩余天数折算)
        upgrade_cost = float(new_plan.monthly_price)
        
        if current_sub and current_sub.end_date:
            remaining_days = (current_sub.end_date - datetime.now()).days
            if remaining_days > 0:
                # 按剩余天数计算差价
                daily_diff = (float(new_plan.monthly_price) - float(current_sub.plan.monthly_price)) / 30
                upgrade_cost = daily_diff * remaining_days
        
        # 检查余额（预检查，实际扣款在原子操作中）
        if upgrade_cost > 0:
            balance = self.billing_db.get_balance(user_id)
            if balance < upgrade_cost:
                return {
                    "success": False,
                    "message": f"余额不足，升级需要 ¥{upgrade_cost:.2f}，当前余额 ¥{balance:.2f}"
                }
        
        # 计算结束日期
        end_date = current_sub.end_date if current_sub and current_sub.end_date else None
        if not end_date and float(new_plan.monthly_price) > 0:
            end_date = datetime.now() + timedelta(days=30)
        
        # 使用原子事务执行升级
        try:
            result = self.billing_db.atomic_upgrade_subscription(
                user_id=user_id,
                new_plan_id=new_plan.id,
                upgrade_cost=upgrade_cost if upgrade_cost > 0 else 0,
                end_date=end_date,
                description=f"升级到{new_plan.display_name}"
            )
            
            logger.info(f"用户 {user_id} 升级到 {new_plan.display_name}")
            
            return {
                "success": True,
                "subscription_id": result["subscription_id"],
                "plan": new_plan.name,
                "message": f"已升级到{new_plan.display_name}，新配额立即生效"
            }
        except ValueError as e:
            return {
                "success": False,
                "message": str(e)
            }
    
    # ==================== 余额管理 ====================
    
    def get_balance(self, user_id: int) -> float:
        """获取余额"""
        return self.billing_db.get_balance(user_id)
    
    def recharge(self, user_id: int, amount: float, reference_id: str = None) -> Dict:
        """
        充值
        
        Args:
            user_id: 用户ID
            amount: 充值金额
            reference_id: 外部订单号
        """
        if amount <= 0:
            return {"success": False, "message": "充值金额必须大于0"}
        
        new_balance = self.billing_db.update_balance(user_id, amount)
        
        self.billing_db.create_transaction(
            user_id=user_id,
            type='recharge',
            amount=amount,
            balance_after=new_balance,
            description=f"充值 ¥{amount}",
            reference_id=reference_id
        )
        
        logger.info(f"用户 {user_id} 充值 ¥{amount}，新余额 ¥{new_balance}")
        
        return {
            "success": True,
            "amount": amount,
            "new_balance": new_balance,
            "message": "充值成功"
        }
    
    def deduct_balance(self, user_id: int, amount: float, description: str) -> Dict:
        """
        扣除余额 (按量计费)
        
        Args:
            user_id: 用户ID
            amount: 扣除金额
            description: 描述
        
        Returns:
            {"success": bool, "deducted": float, "new_balance": float}
        """
        if amount <= 0:
            return {"success": True, "deducted": 0}
        
        # 使用安全的余额更新方法
        try:
            new_balance = self.billing_db.update_balance(user_id, -amount, allow_negative=False)
        except ValueError as e:
            return {
                "success": False, 
                "error_code": "INSUFFICIENT_BALANCE",
                "message": str(e)
            }
        
        self.billing_db.create_transaction(
            user_id=user_id,
            type='consume',
            amount=-amount,
            balance_after=new_balance,
            description=description
        )
        
        return {
            "success": True,
            "deducted": amount,
            "new_balance": new_balance
        }
    
    def refund(self, user_id: int, amount: float, description: str, reference_id: str = None) -> Dict:
        """
        退款
        
        Args:
            user_id: 用户ID
            amount: 退款金额
            description: 描述
            reference_id: 关联的原订单号
        
        Returns:
            {"success": bool, "amount": float, "new_balance": float}
        """
        if amount <= 0:
            return {"success": False, "message": "退款金额必须大于0"}
        
        new_balance = self.billing_db.update_balance(user_id, amount)
        
        self.billing_db.create_transaction(
            user_id=user_id,
            type='refund',
            amount=amount,
            balance_after=new_balance,
            description=description,
            reference_id=reference_id
        )
        
        logger.info(f"用户 {user_id} 退款 ¥{amount}，新余额 ¥{new_balance}")
        
        return {
            "success": True,
            "amount": amount,
            "new_balance": new_balance,
            "message": "退款成功"
        }
    
    # ==================== 配额检查 ====================
    
    # 有效的配额类型白名单
    VALID_QUOTA_TYPES = {'requests', 'tokens', 'audio_seconds'}
    
    def check_quota(self, user_id: int, quota_type: str = 'requests') -> Dict:
        """
        检查配额
        
        Returns:
            {"allowed": bool, "remaining": int, "limit": int, "can_pay": bool}
        """
        # 验证配额类型
        if quota_type not in self.VALID_QUOTA_TYPES:
            return {
                "allowed": False, 
                "message": f"无效的配额类型: {quota_type}，有效类型: {', '.join(self.VALID_QUOTA_TYPES)}"
            }
        
        sub = self.get_user_subscription(user_id)
        if not sub or not sub.plan:
            return {"allowed": False, "message": "无有效订阅"}
        
        # 获取今日用量
        usage = self.user_db.get_daily_usage(user_id)
        
        if quota_type == 'requests':
            used = usage.get('total_requests', 0)
            limit = sub.plan.daily_requests
        elif quota_type == 'tokens':
            used = usage.get('total_tokens', 0)
            limit = sub.plan.daily_tokens
        elif quota_type == 'audio_seconds':
            used = usage.get('total_audio_seconds', 0)
            limit = sub.plan.daily_audio_seconds
        
        remaining = limit - used
        
        if remaining > 0:
            return {
                "allowed": True,
                "remaining": remaining,
                "limit": limit,
                "used": used
            }
        
        # 配额用完，检查是否可以按量付费
        balance = self.billing_db.get_balance(user_id)
        can_pay = balance > 0
        
        return {
            "allowed": False,
            "remaining": 0,
            "limit": limit,
            "used": used,
            "can_pay": can_pay,
            "balance": balance
        }
    
    def calculate_cost(self, plan: Plan, usage_type: str, amount: float) -> float:
        """
        计算按量计费费用
        
        Args:
            plan: 套餐对象
            usage_type: 使用类型 (requests, tokens, audio_seconds)
            amount: 使用量
        
        Returns:
            费用 (元)
        """
        if amount <= 0:
            return 0.0
        
        if usage_type == 'requests':
            return float(plan.price_per_request) * amount
        elif usage_type == 'tokens':
            # 按每1000 Token计费
            return float(plan.price_per_1k_tokens) * (amount / 1000)
        elif usage_type == 'audio_seconds':
            # 按每分钟计费
            return float(plan.price_per_minute_audio) * (amount / 60)
        
        return 0.0
    
    def calculate_total_cost(self, plan: Plan, requests: int = 0, 
                            tokens: int = 0, audio_seconds: int = 0) -> Dict:
        """
        计算总费用
        
        Args:
            plan: 套餐对象
            requests: 请求数
            tokens: Token数
            audio_seconds: 音频秒数
        
        Returns:
            {
                "requests_cost": float,
                "tokens_cost": float,
                "audio_cost": float,
                "total_cost": float
            }
        """
        requests_cost = self.calculate_cost(plan, 'requests', requests)
        tokens_cost = self.calculate_cost(plan, 'tokens', tokens)
        audio_cost = self.calculate_cost(plan, 'audio_seconds', audio_seconds)
        
        return {
            "requests_cost": round(requests_cost, 4),
            "tokens_cost": round(tokens_cost, 4),
            "audio_cost": round(audio_cost, 4),
            "total_cost": round(requests_cost + tokens_cost + audio_cost, 4)
        }
    
    def get_pricing_info(self, plan_name: str = None) -> Dict:
        """
        获取定价信息
        
        Args:
            plan_name: 套餐名称，如果为空则返回所有套餐的定价
        
        Returns:
            定价信息
        """
        if plan_name:
            plan = self.billing_db.get_plan_by_name(plan_name)
            if not plan:
                return {"error": f"套餐不存在: {plan_name}"}
            
            return {
                "plan": plan.name,
                "display_name": plan.display_name,
                "monthly_price": float(plan.monthly_price),
                "pricing": {
                    "per_request": float(plan.price_per_request),
                    "per_1k_tokens": float(plan.price_per_1k_tokens),
                    "per_minute_audio": float(plan.price_per_minute_audio)
                }
            }
        
        # 返回所有套餐的定价
        plans = self.billing_db.get_plans(active_only=True)
        return {
            "plans": [
                {
                    "plan": p.name,
                    "display_name": p.display_name,
                    "monthly_price": float(p.monthly_price),
                    "pricing": {
                        "per_request": float(p.price_per_request),
                        "per_1k_tokens": float(p.price_per_1k_tokens),
                        "per_minute_audio": float(p.price_per_minute_audio)
                    }
                }
                for p in plans
            ]
        }
    
    # ==================== 交易记录 ====================
    
    def get_transactions(self, user_id: int, page: int = 1, limit: int = 20, 
                        trans_type: str = None) -> Dict:
        """
        获取交易记录 (带分页)
        
        Args:
            user_id: 用户ID
            page: 页码 (从1开始)
            limit: 每页数量
            trans_type: 交易类型筛选 (可选)
        
        Returns:
            {
                "transactions": [...],
                "page": int,
                "limit": int,
                "total": int,
                "total_pages": int
            }
        """
        offset = (page - 1) * limit
        
        if trans_type:
            transactions = self.billing_db.get_transactions_by_type(
                user_id, trans_type, limit, offset
            )
            # 获取该类型的总数
            total = len(self.billing_db.get_transactions_by_type(user_id, trans_type, 10000, 0))
        else:
            transactions = self.billing_db.get_transactions(user_id, limit, offset)
            total = self.billing_db.get_transaction_count(user_id)
        
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        
        return {
            "transactions": [
                {
                    "id": t.id,
                    "type": t.type,
                    "amount": float(t.amount),
                    "balance_after": float(t.balance_after) if t.balance_after else None,
                    "description": t.description,
                    "reference_id": t.reference_id,
                    "created_at": str(t.created_at)
                }
                for t in transactions
            ],
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages
        }
    
    def get_transaction_summary(self, user_id: int) -> Dict:
        """
        获取交易汇总
        
        Returns:
            {
                "total_recharge": float,
                "total_consume": float,
                "total_refund": float,
                "transaction_count": int
            }
        """
        recharges = self.billing_db.get_transactions_by_type(user_id, 'recharge', 10000, 0)
        consumes = self.billing_db.get_transactions_by_type(user_id, 'consume', 10000, 0)
        refunds = self.billing_db.get_transactions_by_type(user_id, 'refund', 10000, 0)
        
        total_recharge = sum(float(t.amount) for t in recharges)
        total_consume = sum(abs(float(t.amount)) for t in consumes)
        total_refund = sum(float(t.amount) for t in refunds)
        
        return {
            "total_recharge": total_recharge,
            "total_consume": total_consume,
            "total_refund": total_refund,
            "transaction_count": self.billing_db.get_transaction_count(user_id)
        }
    
    # ==================== 统计 ====================
    
    def get_user_billing_summary(self, user_id: int) -> Dict:
        """获取用户计费摘要"""
        sub = self.get_user_subscription(user_id)
        balance = self.billing_db.get_balance(user_id)
        usage = self.user_db.get_daily_usage(user_id)
        
        return {
            "subscription": {
                "plan": sub.plan.name if sub and sub.plan else "free",
                "display_name": sub.plan.display_name if sub and sub.plan else "免费版",
                "status": sub.status if sub else "active",
                "end_date": str(sub.end_date) if sub and sub.end_date else None
            },
            "balance": balance,
            "today_usage": {
                "requests": usage.get('total_requests', 0),
                "tokens": usage.get('total_tokens', 0),
                "audio_seconds": usage.get('total_audio_seconds', 0)
            },
            "quota": {
                "daily_requests": sub.plan.daily_requests if sub and sub.plan else 100,
                "daily_tokens": sub.plan.daily_tokens if sub and sub.plan else 10000,
                "daily_audio_seconds": sub.plan.daily_audio_seconds if sub and sub.plan else 60
            }
        }


# 全局实例
_billing_service: Optional[BillingService] = None


def get_billing_service() -> BillingService:
    global _billing_service
    if _billing_service is None:
        _billing_service = BillingService()
    return _billing_service
