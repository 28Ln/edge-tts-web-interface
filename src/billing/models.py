"""
计费系统数据模型
"""

import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict
from contextlib import contextmanager
import sqlite3

DB_PATH = os.environ.get('AUTH_DB_PATH', 'data/auth.db')


@dataclass
class Plan:
    """套餐"""
    id: int
    name: str                          # free, basic, pro, enterprise
    display_name: str                  # 显示名称
    description: str = ""
    monthly_price: Decimal = Decimal("0")
    
    # 配额限制
    daily_requests: int = 100
    daily_tokens: int = 10000
    daily_audio_seconds: int = 60
    
    # 按量计费价格
    price_per_request: Decimal = Decimal("0")
    price_per_1k_tokens: Decimal = Decimal("0")
    price_per_minute_audio: Decimal = Decimal("0")
    
    is_active: bool = True
    created_at: datetime = None


@dataclass
class Subscription:
    """订阅"""
    id: int
    user_id: int
    plan_id: int
    status: str = "active"             # active, expired, cancelled
    start_date: datetime = None
    end_date: datetime = None
    auto_renew: bool = False
    created_at: datetime = None
    
    # 关联数据
    plan: Plan = None


@dataclass
class Transaction:
    """交易记录"""
    id: int
    user_id: int
    type: str                          # recharge, consume, refund, subscribe
    amount: Decimal
    balance_after: Decimal = None
    description: str = ""
    reference_id: str = None           # 外部订单号
    created_at: datetime = None


class BillingDatabase:
    """计费数据库"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_tables()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_tables(self):
        """初始化计费相关表"""
        with self.get_connection() as conn:
            conn.executescript('''
                -- 套餐表
                CREATE TABLE IF NOT EXISTS plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    monthly_price REAL DEFAULT 0,
                    daily_requests INTEGER DEFAULT 100,
                    daily_tokens INTEGER DEFAULT 10000,
                    daily_audio_seconds INTEGER DEFAULT 60,
                    price_per_request REAL DEFAULT 0,
                    price_per_1k_tokens REAL DEFAULT 0,
                    price_per_minute_audio REAL DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- 订阅表
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    plan_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'active',
                    start_date TIMESTAMP NOT NULL,
                    end_date TIMESTAMP,
                    auto_renew BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (plan_id) REFERENCES plans(id)
                );
                
                -- 交易记录表
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    balance_after REAL,
                    description TEXT DEFAULT '',
                    reference_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                
                -- 管理员表
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    api_key TEXT UNIQUE,
                    is_super BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- 用户表扩展字段 (如果不存在)
                -- 注意: SQLite 不支持 IF NOT EXISTS for ALTER TABLE
                
                -- 索引
                CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
                CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
                CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);
                CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
            ''')
            
            # 检查并添加用户表扩展字段
            self._ensure_user_columns(conn)
            
            # 初始化默认套餐
            self._init_default_plans(conn)
    
    def _ensure_user_columns(self, conn):
        """确保用户表有必要的字段"""
        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'balance' not in columns:
            conn.execute('ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0')
        if 'email_verified' not in columns:
            conn.execute('ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT 0')
        if 'password_hash' not in columns:
            conn.execute('ALTER TABLE users ADD COLUMN password_hash TEXT')
    
    def _init_default_plans(self, conn):
        """初始化默认套餐"""
        plans = [
            ('free', '免费版', '基础功能，适合体验', 0, 100, 10000, 60, 0, 0, 0),
            ('basic', '基础版', '适合个人开发者', 29, 1000, 100000, 600, 0.001, 0.01, 0.1),
            ('pro', '专业版', '适合小型团队', 99, 10000, 1000000, 3600, 0.0008, 0.008, 0.08),
            ('enterprise', '企业版', '适合大型企业', 299, 100000, 10000000, 36000, 0.0005, 0.005, 0.05),
        ]
        
        for plan in plans:
            conn.execute('''
                INSERT OR IGNORE INTO plans 
                (name, display_name, description, monthly_price, 
                 daily_requests, daily_tokens, daily_audio_seconds,
                 price_per_request, price_per_1k_tokens, price_per_minute_audio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', plan)
    
    # ==================== 套餐操作 ====================
    
    def get_plans(self, active_only: bool = True) -> List[Plan]:
        """获取套餐列表"""
        with self.get_connection() as conn:
            if active_only:
                rows = conn.execute(
                    'SELECT * FROM plans WHERE is_active = 1 ORDER BY monthly_price'
                ).fetchall()
            else:
                rows = conn.execute('SELECT * FROM plans ORDER BY monthly_price').fetchall()
            return [self._row_to_plan(row) for row in rows]
    
    def get_plan(self, plan_id: int) -> Optional[Plan]:
        """获取套餐"""
        with self.get_connection() as conn:
            row = conn.execute('SELECT * FROM plans WHERE id = ?', (plan_id,)).fetchone()
            return self._row_to_plan(row) if row else None
    
    def get_plan_by_name(self, name: str) -> Optional[Plan]:
        """通过名称获取套餐"""
        with self.get_connection() as conn:
            row = conn.execute('SELECT * FROM plans WHERE name = ?', (name,)).fetchone()
            return self._row_to_plan(row) if row else None
    
    def create_plan(self, name: str, display_name: str, description: str = "",
                   monthly_price: float = 0, daily_requests: int = 100,
                   daily_tokens: int = 10000, daily_audio_seconds: int = 60,
                   price_per_request: float = 0, price_per_1k_tokens: float = 0,
                   price_per_minute_audio: float = 0) -> int:
        """创建套餐"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO plans (name, display_name, description, monthly_price,
                    daily_requests, daily_tokens, daily_audio_seconds,
                    price_per_request, price_per_1k_tokens, price_per_minute_audio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, display_name, description, monthly_price,
                  daily_requests, daily_tokens, daily_audio_seconds,
                  price_per_request, price_per_1k_tokens, price_per_minute_audio))
            return cursor.lastrowid
    
    def update_plan(self, plan_id: int, **kwargs) -> bool:
        """更新套餐"""
        allowed_fields = {
            'name', 'display_name', 'description', 'monthly_price',
            'daily_requests', 'daily_tokens', 'daily_audio_seconds',
            'price_per_request', 'price_per_1k_tokens', 'price_per_minute_audio',
            'is_active'
        }
        
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False
        
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [plan_id]
        
        with self.get_connection() as conn:
            # 检查 updated_at 列是否存在
            cursor = conn.execute("PRAGMA table_info(plans)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'updated_at' in columns:
                cursor = conn.execute(
                    f"UPDATE plans SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    values
                )
            else:
                cursor = conn.execute(
                    f"UPDATE plans SET {set_clause} WHERE id = ?",
                    values
                )
            return cursor.rowcount > 0
    
    def set_plan_active(self, plan_id: int, is_active: bool) -> bool:
        """启用/禁用套餐"""
        return self.update_plan(plan_id, is_active=is_active)
    
    def delete_plan(self, plan_id: int) -> bool:
        """删除套餐 (仅当没有订阅时)"""
        with self.get_connection() as conn:
            # 检查是否有订阅
            count = conn.execute(
                'SELECT COUNT(*) FROM subscriptions WHERE plan_id = ?',
                (plan_id,)
            ).fetchone()[0]
            
            if count > 0:
                return False
            
            cursor = conn.execute('DELETE FROM plans WHERE id = ?', (plan_id,))
            return cursor.rowcount > 0
    
    # ==================== 订阅操作 ====================
    
    def get_user_subscription(self, user_id: int) -> Optional[Subscription]:
        """获取用户当前订阅"""
        with self.get_connection() as conn:
            row = conn.execute('''
                SELECT s.*, p.name as plan_name, p.display_name, p.daily_requests,
                       p.daily_tokens, p.daily_audio_seconds
                FROM subscriptions s
                JOIN plans p ON s.plan_id = p.id
                WHERE s.user_id = ? AND s.status = 'active'
                ORDER BY s.created_at DESC LIMIT 1
            ''', (user_id,)).fetchone()
            
            if row:
                sub = self._row_to_subscription(row)
                sub.plan = Plan(
                    id=row['plan_id'],
                    name=row['plan_name'],
                    display_name=row['display_name'],
                    daily_requests=row['daily_requests'],
                    daily_tokens=row['daily_tokens'],
                    daily_audio_seconds=row['daily_audio_seconds']
                )
                return sub
        return None
    
    def create_subscription(self, user_id: int, plan_id: int, 
                           start_date: datetime, end_date: datetime = None) -> int:
        """创建订阅"""
        with self.get_connection() as conn:
            # 取消旧订阅
            conn.execute('''
                UPDATE subscriptions SET status = 'cancelled' 
                WHERE user_id = ? AND status = 'active'
            ''', (user_id,))
            
            # 创建新订阅
            cursor = conn.execute('''
                INSERT INTO subscriptions (user_id, plan_id, start_date, end_date)
                VALUES (?, ?, ?, ?)
            ''', (user_id, plan_id, start_date, end_date))
            return cursor.lastrowid
    
    def cancel_subscription(self, user_id: int) -> bool:
        """取消订阅"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                UPDATE subscriptions SET status = 'cancelled'
                WHERE user_id = ? AND status = 'active'
            ''', (user_id,))
            return cursor.rowcount > 0
    
    def expire_subscription(self, subscription_id: int) -> bool:
        """将订阅标记为过期"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                UPDATE subscriptions SET status = 'expired'
                WHERE id = ? AND status = 'active'
            ''', (subscription_id,))
            return cursor.rowcount > 0
    
    def get_expired_subscriptions(self) -> List[Subscription]:
        """获取所有已过期但状态仍为active的订阅"""
        with self.get_connection() as conn:
            rows = conn.execute('''
                SELECT * FROM subscriptions 
                WHERE status = 'active' 
                AND end_date IS NOT NULL 
                AND end_date < datetime('now')
            ''').fetchall()
            return [self._row_to_subscription(row) for row in rows]
    
    def atomic_upgrade_subscription(self, user_id: int, new_plan_id: int, 
                                     upgrade_cost: float, end_date, description: str) -> Dict:
        """
        原子性订阅升级 - 所有操作在单一事务中完成
        
        Args:
            user_id: 用户ID
            new_plan_id: 新套餐ID
            upgrade_cost: 升级费用
            end_date: 订阅结束日期
            description: 交易描述
        
        Returns:
            {"success": bool, "subscription_id": int, "new_balance": float}
        
        Raises:
            ValueError: 余额不足时
        """
        with self.get_connection() as conn:
            # 1. 原子扣款（如果有费用）
            new_balance = 0.0
            if upgrade_cost > 0:
                cursor = conn.execute(
                    'UPDATE users SET balance = balance - ? WHERE id = ? AND balance >= ?',
                    (upgrade_cost, user_id, upgrade_cost)
                )
                if cursor.rowcount == 0:
                    row = conn.execute('SELECT balance FROM users WHERE id = ?', (user_id,)).fetchone()
                    if not row:
                        raise ValueError(f"用户不存在: {user_id}")
                    raise ValueError(f"余额不足: 当前余额 {row['balance']}, 需要 {upgrade_cost}")
                
                # 获取新余额
                row = conn.execute('SELECT balance FROM users WHERE id = ?', (user_id,)).fetchone()
                new_balance = float(row['balance']) if row else 0.0
                
                # 2. 创建交易记录
                conn.execute('''
                    INSERT INTO transactions (user_id, type, amount, balance_after, description)
                    VALUES (?, 'subscribe', ?, ?, ?)
                ''', (user_id, -upgrade_cost, new_balance, description))
            
            # 3. 取消旧订阅
            conn.execute('''
                UPDATE subscriptions SET status = 'cancelled' 
                WHERE user_id = ? AND status = 'active'
            ''', (user_id,))
            
            # 4. 创建新订阅
            from datetime import datetime
            cursor = conn.execute('''
                INSERT INTO subscriptions (user_id, plan_id, start_date, end_date)
                VALUES (?, ?, ?, ?)
            ''', (user_id, new_plan_id, datetime.now(), end_date))
            
            return {
                "success": True,
                "subscription_id": cursor.lastrowid,
                "new_balance": new_balance
            }
    
    def get_subscription_by_id(self, subscription_id: int) -> Optional[Subscription]:
        """通过ID获取订阅"""
        with self.get_connection() as conn:
            row = conn.execute('''
                SELECT s.*, p.name as plan_name, p.display_name, p.daily_requests,
                       p.daily_tokens, p.daily_audio_seconds, p.monthly_price,
                       p.price_per_request, p.price_per_1k_tokens, p.price_per_minute_audio
                FROM subscriptions s
                JOIN plans p ON s.plan_id = p.id
                WHERE s.id = ?
            ''', (subscription_id,)).fetchone()
            
            if row:
                sub = self._row_to_subscription(row)
                sub.plan = self._row_to_plan_from_join(row)
                return sub
        return None
    
    # ==================== 交易操作 ====================
    
    def create_transaction(self, user_id: int, type: str, amount: float,
                          balance_after: float = None, description: str = "",
                          reference_id: str = None) -> int:
        """创建交易记录"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO transactions (user_id, type, amount, balance_after, description, reference_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, type, amount, balance_after, description, reference_id))
            return cursor.lastrowid
    
    def get_transactions(self, user_id: int, limit: int = 20, offset: int = 0) -> List[Transaction]:
        """获取交易记录"""
        with self.get_connection() as conn:
            rows = conn.execute('''
                SELECT * FROM transactions WHERE user_id = ?
                ORDER BY created_at DESC LIMIT ? OFFSET ?
            ''', (user_id, limit, offset)).fetchall()
            return [self._row_to_transaction(row) for row in rows]
    
    def get_transaction_count(self, user_id: int) -> int:
        """获取用户交易记录总数"""
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT COUNT(*) FROM transactions WHERE user_id = ?',
                (user_id,)
            ).fetchone()
            return row[0] if row else 0
    
    def get_transactions_by_type(self, user_id: int, trans_type: str, 
                                  limit: int = 20, offset: int = 0) -> List[Transaction]:
        """按类型获取交易记录"""
        with self.get_connection() as conn:
            rows = conn.execute('''
                SELECT * FROM transactions 
                WHERE user_id = ? AND type = ?
                ORDER BY created_at DESC LIMIT ? OFFSET ?
            ''', (user_id, trans_type, limit, offset)).fetchall()
            return [self._row_to_transaction(row) for row in rows]
    
    # ==================== 余额操作 ====================
    
    def get_balance(self, user_id: int) -> float:
        """获取用户余额"""
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT balance FROM users WHERE id = ?', (user_id,)
            ).fetchone()
            return float(row['balance']) if row and row['balance'] else 0.0
    
    def update_balance(self, user_id: int, amount: float, allow_negative: bool = False) -> float:
        """
        原子性更新余额 (正数增加，负数减少)
        
        使用单条SQL语句实现原子操作，防止竞态条件
        
        Args:
            user_id: 用户ID
            amount: 变动金额 (正数增加，负数减少)
            allow_negative: 是否允许余额变为负数，默认不允许
        
        Returns:
            更新后的余额
        
        Raises:
            ValueError: 当余额不足且不允许负数时
        """
        with self.get_connection() as conn:
            if allow_negative:
                # 允许负数：直接原子更新
                cursor = conn.execute(
                    'UPDATE users SET balance = balance + ? WHERE id = ?',
                    (amount, user_id)
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"用户不存在: {user_id}")
            else:
                # 不允许负数：原子更新并检查余额
                # 使用 WHERE 条件确保余额足够
                cursor = conn.execute(
                    'UPDATE users SET balance = balance + ? WHERE id = ? AND balance + ? >= 0',
                    (amount, user_id, amount)
                )
                if cursor.rowcount == 0:
                    # 检查是用户不存在还是余额不足
                    row = conn.execute(
                        'SELECT balance FROM users WHERE id = ?', (user_id,)
                    ).fetchone()
                    if not row:
                        raise ValueError(f"用户不存在: {user_id}")
                    current_balance = float(row['balance']) if row['balance'] else 0.0
                    raise ValueError(f"余额不足: 当前余额 {current_balance}, 需要扣除 {abs(amount)}")
            
            # 获取更新后的余额
            row = conn.execute(
                'SELECT balance FROM users WHERE id = ?', (user_id,)
            ).fetchone()
            
            return float(row['balance']) if row and row['balance'] else 0.0
    
    def set_balance(self, user_id: int, balance: float) -> float:
        """直接设置余额 (用于管理员操作)"""
        if balance < 0:
            raise ValueError("余额不能为负数")
        
        with self.get_connection() as conn:
            conn.execute(
                'UPDATE users SET balance = ? WHERE id = ?',
                (balance, user_id)
            )
            return balance
    
    def check_balance_sufficient(self, user_id: int, amount: float) -> bool:
        """检查余额是否足够"""
        return self.get_balance(user_id) >= amount
    
    # ==================== 辅助方法 ====================
    
    def _row_to_plan(self, row) -> Plan:
        return Plan(
            id=row['id'],
            name=row['name'],
            display_name=row['display_name'],
            description=row['description'] or "",
            monthly_price=Decimal(str(row['monthly_price'])),
            daily_requests=row['daily_requests'],
            daily_tokens=row['daily_tokens'],
            daily_audio_seconds=row['daily_audio_seconds'],
            price_per_request=Decimal(str(row['price_per_request'])),
            price_per_1k_tokens=Decimal(str(row['price_per_1k_tokens'])),
            price_per_minute_audio=Decimal(str(row['price_per_minute_audio'])),
            is_active=bool(row['is_active']),
            created_at=row['created_at']
        )
    
    def _row_to_subscription(self, row) -> Subscription:
        return Subscription(
            id=row['id'],
            user_id=row['user_id'],
            plan_id=row['plan_id'],
            status=row['status'],
            start_date=row['start_date'],
            end_date=row['end_date'],
            auto_renew=bool(row['auto_renew']),
            created_at=row['created_at']
        )
    
    def _row_to_transaction(self, row) -> Transaction:
        return Transaction(
            id=row['id'],
            user_id=row['user_id'],
            type=row['type'],
            amount=Decimal(str(row['amount'])),
            balance_after=Decimal(str(row['balance_after'])) if row['balance_after'] else None,
            description=row['description'] or "",
            reference_id=row['reference_id'],
            created_at=row['created_at']
        )
    
    def _row_to_plan_from_join(self, row) -> Plan:
        """从JOIN查询结果构建Plan对象"""
        return Plan(
            id=row['plan_id'],
            name=row['plan_name'],
            display_name=row['display_name'],
            daily_requests=row['daily_requests'],
            daily_tokens=row['daily_tokens'],
            daily_audio_seconds=row['daily_audio_seconds'],
            monthly_price=Decimal(str(row['monthly_price'])) if 'monthly_price' in row.keys() else Decimal("0"),
            price_per_request=Decimal(str(row['price_per_request'])) if 'price_per_request' in row.keys() else Decimal("0"),
            price_per_1k_tokens=Decimal(str(row['price_per_1k_tokens'])) if 'price_per_1k_tokens' in row.keys() else Decimal("0"),
            price_per_minute_audio=Decimal(str(row['price_per_minute_audio'])) if 'price_per_minute_audio' in row.keys() else Decimal("0")
        )


# 全局实例
_billing_db: Optional[BillingDatabase] = None


def get_billing_db() -> BillingDatabase:
    global _billing_db
    if _billing_db is None:
        _billing_db = BillingDatabase()
    return _billing_db
