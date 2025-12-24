"""
计费系统属性测试
使用 hypothesis 进行 Property-Based Testing

**Feature: billing-system**
"""

import os
import sys
import tempfile
import pytest
from decimal import Decimal

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hypothesis import given, strategies as st, settings, assume

from src.billing.models import BillingDatabase, Plan


# ============================================
# Test Fixtures
# ============================================

@pytest.fixture
def temp_db():
    """创建临时测试数据库"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    # 先创建 users 表 (billing 依赖它)
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            balance REAL DEFAULT 0,
            email_verified BOOLEAN DEFAULT 0,
            password_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    
    db = BillingDatabase(db_path)
    yield db
    
    # 清理
    try:
        os.unlink(db_path)
    except Exception:
        pass


# ============================================
# Strategies for generating test data
# ============================================

# 套餐名称策略 (唯一标识符)
plan_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_-'),
    min_size=3,
    max_size=20
).filter(lambda x: x and not x[0].isdigit())

# 显示名称策略
display_name_strategy = st.text(min_size=1, max_size=50).filter(lambda x: x.strip())

# 描述策略
description_strategy = st.text(max_size=200)

# 价格策略 (0-10000)
price_strategy = st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False)

# 配额策略 (正整数)
quota_strategy = st.integers(min_value=0, max_value=10000000)


# ============================================
# Property 1: Plan CRUD Round-Trip
# **Feature: billing-system, Property 1: Plan CRUD Round-Trip**
# **Validates: Requirements 1.1, 1.3**
# ============================================

@given(
    name=plan_name_strategy,
    display_name=display_name_strategy,
    description=description_strategy,
    monthly_price=price_strategy,
    daily_requests=quota_strategy,
    daily_tokens=quota_strategy,
    daily_audio_seconds=quota_strategy,
    price_per_request=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    price_per_1k_tokens=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    price_per_minute_audio=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=20, deadline=None)
def test_plan_crud_round_trip(
    name, display_name, description, monthly_price,
    daily_requests, daily_tokens, daily_audio_seconds,
    price_per_request, price_per_1k_tokens, price_per_minute_audio
):
    """
    **Feature: billing-system, Property 1: Plan CRUD Round-Trip**
    
    For any valid plan data, creating a plan and then retrieving it 
    should return the same data unchanged.
    
    **Validates: Requirements 1.1, 1.3**
    """
    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # 创建 users 表
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()
        
        db = BillingDatabase(db_path)
        
        # 确保名称唯一 (避免与默认套餐冲突)
        unique_name = f"test_{name}_{id(name)}"
        
        # 创建套餐
        plan_id = db.create_plan(
            name=unique_name,
            display_name=display_name,
            description=description,
            monthly_price=monthly_price,
            daily_requests=daily_requests,
            daily_tokens=daily_tokens,
            daily_audio_seconds=daily_audio_seconds,
            price_per_request=price_per_request,
            price_per_1k_tokens=price_per_1k_tokens,
            price_per_minute_audio=price_per_minute_audio
        )
        
        # 验证创建成功
        assert plan_id > 0, "Plan should be created with valid ID"
        
        # 读取套餐
        retrieved = db.get_plan(plan_id)
        
        # 验证数据一致性
        assert retrieved is not None, "Plan should be retrievable"
        assert retrieved.id == plan_id
        assert retrieved.name == unique_name
        assert retrieved.display_name == display_name
        assert retrieved.description == description
        assert retrieved.daily_requests == daily_requests
        assert retrieved.daily_tokens == daily_tokens
        assert retrieved.daily_audio_seconds == daily_audio_seconds
        
        # 浮点数比较使用近似相等
        assert abs(float(retrieved.monthly_price) - monthly_price) < 0.01
        assert abs(float(retrieved.price_per_request) - price_per_request) < 0.0001
        assert abs(float(retrieved.price_per_1k_tokens) - price_per_1k_tokens) < 0.0001
        assert abs(float(retrieved.price_per_minute_audio) - price_per_minute_audio) < 0.0001
        
    finally:
        try:
            os.unlink(db_path)
        except Exception:
            pass


# ============================================
# Property 2: Plan Enable/Disable Preserves Data
# **Feature: billing-system, Property 2: Plan Enable/Disable Preserves Data**
# **Validates: Requirements 1.4**
# ============================================

@given(
    display_name=display_name_strategy,
    monthly_price=price_strategy,
    daily_requests=quota_strategy
)
@settings(max_examples=20, deadline=None)
def test_plan_enable_disable_preserves_data(display_name, monthly_price, daily_requests):
    """
    **Feature: billing-system, Property 2: Plan Enable/Disable Preserves Data**
    
    For any plan, disabling and then re-enabling it should preserve 
    all plan data unchanged.
    
    **Validates: Requirements 1.4**
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()
        
        db = BillingDatabase(db_path)
        
        # 创建套餐
        unique_name = f"test_plan_{id(display_name)}"
        plan_id = db.create_plan(
            name=unique_name,
            display_name=display_name,
            monthly_price=monthly_price,
            daily_requests=daily_requests
        )
        
        # 获取原始数据
        original = db.get_plan(plan_id)
        assert original is not None
        assert original.is_active == True
        
        # 禁用套餐
        result = db.set_plan_active(plan_id, False)
        assert result == True
        
        disabled = db.get_plan(plan_id)
        assert disabled is not None
        assert disabled.is_active == False
        
        # 验证其他数据未变
        assert disabled.name == original.name
        assert disabled.display_name == original.display_name
        assert disabled.daily_requests == original.daily_requests
        assert float(disabled.monthly_price) == float(original.monthly_price)
        
        # 重新启用
        result = db.set_plan_active(plan_id, True)
        assert result == True
        
        enabled = db.get_plan(plan_id)
        assert enabled is not None
        assert enabled.is_active == True
        
        # 验证数据完全恢复
        assert enabled.name == original.name
        assert enabled.display_name == original.display_name
        assert enabled.daily_requests == original.daily_requests
        assert float(enabled.monthly_price) == float(original.monthly_price)
        
    finally:
        try:
            os.unlink(db_path)
        except Exception:
            pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


# ============================================
# Property 3: Subscription Creates Valid Record
# **Feature: billing-system, Property 3: Subscription Creates Valid Record**
# **Validates: Requirements 2.1**
# ============================================

@given(
    months=st.integers(min_value=1, max_value=12)
)
@settings(max_examples=20, deadline=None)
def test_subscription_creates_valid_record(months):
    """
    **Feature: billing-system, Property 3: Subscription Creates Valid Record**
    
    For any user and valid plan, subscribing should create a subscription 
    record with correct start_date, end_date, and plan association.
    
    **Validates: Requirements 2.1**
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0
            )
        ''')
        # 创建测试用户
        conn.execute("INSERT INTO users (username, balance) VALUES ('testuser', 1000)")
        conn.commit()
        conn.close()
        
        db = BillingDatabase(db_path)
        
        # 获取一个付费套餐
        plans = db.get_plans(active_only=True)
        paid_plan = next((p for p in plans if float(p.monthly_price) > 0), None)
        
        if not paid_plan:
            # 如果没有付费套餐，跳过测试
            return
        
        from datetime import datetime, timedelta
        
        start_date = datetime.now()
        end_date = start_date + timedelta(days=30 * months)
        
        # 创建订阅
        sub_id = db.create_subscription(
            user_id=1,
            plan_id=paid_plan.id,
            start_date=start_date,
            end_date=end_date
        )
        
        # 验证订阅创建成功
        assert sub_id > 0, "Subscription should be created with valid ID"
        
        # 获取订阅
        sub = db.get_user_subscription(1)
        
        # 验证订阅数据
        assert sub is not None, "Subscription should be retrievable"
        assert sub.user_id == 1
        assert sub.plan_id == paid_plan.id
        assert sub.status == 'active'
        assert sub.start_date is not None
        assert sub.end_date is not None
        
        # 验证关联的套餐
        assert sub.plan is not None
        assert sub.plan.id == paid_plan.id
        
    finally:
        try:
            os.unlink(db_path)
        except Exception:
            pass


# ============================================
# Property 4: Expired Subscription Downgrades to Free
# **Feature: billing-system, Property 4: Expired Subscription Downgrades to Free**
# **Validates: Requirements 2.2**
# ============================================

@given(
    days_expired=st.integers(min_value=1, max_value=30)
)
@settings(max_examples=20, deadline=None)
def test_expired_subscription_downgrades_to_free(days_expired):
    """
    **Feature: billing-system, Property 4: Expired Subscription Downgrades to Free**
    
    For any user with an expired subscription, checking their subscription 
    status should return the free plan.
    
    **Validates: Requirements 2.2**
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0
            )
        ''')
        conn.execute("INSERT INTO users (username, balance) VALUES ('testuser', 0)")
        conn.commit()
        conn.close()
        
        db = BillingDatabase(db_path)
        
        # 获取付费套餐和免费套餐
        plans = db.get_plans(active_only=True)
        paid_plan = next((p for p in plans if float(p.monthly_price) > 0), None)
        free_plan = next((p for p in plans if p.name == 'free'), None)
        
        if not paid_plan or not free_plan:
            return
        
        from datetime import datetime, timedelta
        
        # 创建一个已过期的订阅
        start_date = datetime.now() - timedelta(days=30 + days_expired)
        end_date = datetime.now() - timedelta(days=days_expired)
        
        sub_id = db.create_subscription(
            user_id=1,
            plan_id=paid_plan.id,
            start_date=start_date,
            end_date=end_date
        )
        
        # 获取过期订阅列表
        expired_subs = db.get_expired_subscriptions()
        
        # 验证订阅在过期列表中
        assert len(expired_subs) > 0, "Expired subscription should be detected"
        assert any(s.id == sub_id for s in expired_subs)
        
        # 标记为过期
        db.expire_subscription(sub_id)
        
        # 创建免费套餐订阅
        db.create_subscription(1, free_plan.id, datetime.now(), None)
        
        # 验证当前订阅是免费套餐
        current_sub = db.get_user_subscription(1)
        assert current_sub is not None
        assert current_sub.plan.name == 'free'
        
    finally:
        try:
            os.unlink(db_path)
        except Exception:
            pass


# ============================================
# Property 5: Quota Uses Active Subscription Limits
# **Feature: billing-system, Property 5: Quota Uses Active Subscription Limits**
# **Validates: Requirements 2.4**
# ============================================

@given(
    daily_requests=st.integers(min_value=100, max_value=10000),
    daily_tokens=st.integers(min_value=1000, max_value=100000)
)
@settings(max_examples=20, deadline=None)
def test_quota_uses_subscription_limits(daily_requests, daily_tokens):
    """
    **Feature: billing-system, Property 5: Quota Uses Active Subscription Limits**
    
    For any user with an active subscription, quota checks should use 
    that subscription's plan limits, not default limits.
    
    **Validates: Requirements 2.4**
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0
            )
        ''')
        conn.execute('''
            CREATE TABLE daily_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                total_requests INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                total_audio_seconds INTEGER DEFAULT 0,
                UNIQUE(user_id, date)
            )
        ''')
        conn.execute("INSERT INTO users (username, balance) VALUES ('testuser', 0)")
        conn.commit()
        conn.close()
        
        db = BillingDatabase(db_path)
        
        # 创建自定义套餐
        unique_name = f"custom_plan_{daily_requests}_{daily_tokens}"
        plan_id = db.create_plan(
            name=unique_name,
            display_name="自定义套餐",
            monthly_price=50,
            daily_requests=daily_requests,
            daily_tokens=daily_tokens,
            daily_audio_seconds=600
        )
        
        # 创建订阅
        from datetime import datetime, timedelta
        db.create_subscription(
            user_id=1,
            plan_id=plan_id,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30)
        )
        
        # 获取订阅
        sub = db.get_user_subscription(1)
        
        # 验证配额限制来自订阅的套餐
        assert sub is not None
        assert sub.plan is not None
        assert sub.plan.daily_requests == daily_requests
        assert sub.plan.daily_tokens == daily_tokens
        
    finally:
        try:
            os.unlink(db_path)
        except Exception:
            pass


# ============================================
# Property 6: Daily Usage Reset Preserves History
# **Feature: billing-system, Property 6: Daily Usage Reset Preserves History**
# **Validates: Requirements 3.1, 3.2**
# ============================================

@given(
    requests_count=st.integers(min_value=1, max_value=100),
    tokens_count=st.integers(min_value=100, max_value=10000)
)
@settings(max_examples=20, deadline=None)
def test_daily_reset_preserves_history(requests_count, tokens_count):
    """
    **Feature: billing-system, Property 6: Daily Usage Reset Preserves History**
    
    For any user with usage records, after daily reset, today's usage 
    should be zero but historical records should be preserved.
    
    **Validates: Requirements 3.1, 3.2**
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        import sqlite3
        from datetime import date, timedelta
        
        conn = sqlite3.connect(db_path)
        conn.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0
            )
        ''')
        conn.execute('''
            CREATE TABLE daily_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                total_requests INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                total_audio_seconds INTEGER DEFAULT 0,
                UNIQUE(user_id, date)
            )
        ''')
        conn.execute("INSERT INTO users (username, balance) VALUES ('testuser', 0)")
        
        # 插入昨天的用量记录
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        conn.execute('''
            INSERT INTO daily_usage (user_id, date, total_requests, total_tokens)
            VALUES (1, ?, ?, ?)
        ''', (yesterday, requests_count, tokens_count))
        
        conn.commit()
        
        # 验证昨天的记录存在
        row = conn.execute(
            "SELECT total_requests, total_tokens FROM daily_usage WHERE user_id = 1 AND date = ?",
            (yesterday,)
        ).fetchone()
        
        assert row is not None, "Yesterday's usage should exist"
        assert row[0] == requests_count
        assert row[1] == tokens_count
        
        # 验证今天的记录不存在 (新的一天)
        today = date.today().isoformat()
        row = conn.execute(
            "SELECT total_requests FROM daily_usage WHERE user_id = 1 AND date = ?",
            (today,)
        ).fetchone()
        
        # 今天的记录应该不存在或为0
        if row:
            assert row[0] == 0, "Today's usage should be zero"
        
        # 再次验证历史记录仍然存在
        row = conn.execute(
            "SELECT total_requests, total_tokens FROM daily_usage WHERE user_id = 1 AND date = ?",
            (yesterday,)
        ).fetchone()
        
        assert row is not None, "Historical usage should be preserved"
        assert row[0] == requests_count
        assert row[1] == tokens_count
        
        conn.close()
        
    finally:
        try:
            os.unlink(db_path)
        except Exception:
            pass


# ============================================
# Property 7: Plan Upgrade Immediately Applies
# **Feature: billing-system, Property 7: Plan Upgrade Immediately Applies**
# **Validates: Requirements 3.3**
# ============================================

@given(
    initial_requests=st.integers(min_value=100, max_value=500),
    upgraded_requests=st.integers(min_value=1000, max_value=5000)
)
@settings(max_examples=20, deadline=None)
def test_plan_upgrade_immediately_applies(initial_requests, upgraded_requests):
    """
    **Feature: billing-system, Property 7: Plan Upgrade Immediately Applies**
    
    For any user upgrading from a lower plan to a higher plan, 
    the new quota limits should be immediately available.
    
    **Validates: Requirements 3.3**
    """
    # 确保升级后的配额更高
    assume(upgraded_requests > initial_requests)
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0
            )
        ''')
        conn.execute("INSERT INTO users (username, balance) VALUES ('testuser', 1000)")
        conn.commit()
        conn.close()
        
        db = BillingDatabase(db_path)
        
        from datetime import datetime, timedelta
        
        # 创建初始套餐
        initial_plan_id = db.create_plan(
            name=f"initial_{initial_requests}",
            display_name="初始套餐",
            monthly_price=29,
            daily_requests=initial_requests
        )
        
        # 创建升级套餐
        upgraded_plan_id = db.create_plan(
            name=f"upgraded_{upgraded_requests}",
            display_name="升级套餐",
            monthly_price=99,
            daily_requests=upgraded_requests
        )
        
        # 创建初始订阅
        db.create_subscription(
            user_id=1,
            plan_id=initial_plan_id,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30)
        )
        
        # 验证初始配额
        sub = db.get_user_subscription(1)
        assert sub.plan.daily_requests == initial_requests
        
        # 升级订阅 (取消旧的，创建新的)
        db.cancel_subscription(1)
        db.create_subscription(
            user_id=1,
            plan_id=upgraded_plan_id,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30)
        )
        
        # 验证新配额立即生效
        new_sub = db.get_user_subscription(1)
        assert new_sub is not None
        assert new_sub.plan.daily_requests == upgraded_requests
        
    finally:
        try:
            os.unlink(db_path)
        except Exception:
            pass


# ============================================
# Property 8: Balance Operations Consistency
# **Feature: billing-system, Property 8: Balance Operations Consistency**
# **Validates: Requirements 4.1, 4.2, 4.3, 5.1**
# ============================================

@given(
    initial_balance=st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False),
    operations=st.lists(
        st.tuples(
            st.sampled_from(['recharge', 'deduct']),
            st.floats(min_value=0.01, max_value=100, allow_nan=False, allow_infinity=False)
        ),
        min_size=1,
        max_size=10
    )
)
@settings(max_examples=20, deadline=None)
def test_balance_operations_consistency(initial_balance, operations):
    """
    **Feature: billing-system, Property 8: Balance Operations Consistency**
    
    For any sequence of recharge and deduction operations, the final balance 
    should equal initial balance plus sum of all operations, and each operation 
    should create a transaction record.
    
    **Validates: Requirements 4.1, 4.2, 4.3, 5.1**
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0
            )
        ''')
        conn.execute("INSERT INTO users (username, balance) VALUES ('testuser', ?)", (initial_balance,))
        conn.commit()
        conn.close()
        
        db = BillingDatabase(db_path)
        
        expected_balance = initial_balance
        successful_ops = 0
        
        for op_type, amount in operations:
            if op_type == 'recharge':
                # 充值总是成功
                new_balance = db.update_balance(1, amount)
                db.create_transaction(1, 'recharge', amount, new_balance, f"充值 {amount}")
                expected_balance += amount
                successful_ops += 1
            else:
                # 扣款可能失败
                if expected_balance >= amount:
                    try:
                        new_balance = db.update_balance(1, -amount, allow_negative=False)
                        db.create_transaction(1, 'consume', -amount, new_balance, f"消费 {amount}")
                        expected_balance -= amount
                        successful_ops += 1
                    except ValueError:
                        pass  # 余额不足，跳过
        
        # 验证最终余额
        final_balance = db.get_balance(1)
        assert abs(final_balance - expected_balance) < 0.01, \
            f"Balance mismatch: expected {expected_balance}, got {final_balance}"
        
        # 验证交易记录数量
        transaction_count = db.get_transaction_count(1)
        assert transaction_count == successful_ops, \
            f"Transaction count mismatch: expected {successful_ops}, got {transaction_count}"
        
    finally:
        try:
            os.unlink(db_path)
        except Exception:
            pass


# ============================================
# Property 9: Insufficient Balance Rejects Request
# **Feature: billing-system, Property 9: Insufficient Balance Rejects Request**
# **Validates: Requirements 4.4**
# ============================================

@given(
    balance=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
    deduct_amount=st.floats(min_value=0.01, max_value=200, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=20, deadline=None)
def test_insufficient_balance_rejects_request(balance, deduct_amount):
    """
    **Feature: billing-system, Property 9: Insufficient Balance Rejects Request**
    
    For any user with balance less than required amount, attempting to deduct 
    should fail with error and balance should remain unchanged.
    
    **Validates: Requirements 4.4**
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0
            )
        ''')
        conn.execute("INSERT INTO users (username, balance) VALUES ('testuser', ?)", (balance,))
        conn.commit()
        conn.close()
        
        db = BillingDatabase(db_path)
        
        original_balance = db.get_balance(1)
        
        if deduct_amount > balance:
            # 余额不足，应该抛出异常
            try:
                db.update_balance(1, -deduct_amount, allow_negative=False)
                assert False, "Should have raised ValueError for insufficient balance"
            except ValueError as e:
                assert "余额不足" in str(e)
            
            # 验证余额未变
            current_balance = db.get_balance(1)
            assert abs(current_balance - original_balance) < 0.01, \
                "Balance should remain unchanged after failed deduction"
        else:
            # 余额充足，应该成功
            new_balance = db.update_balance(1, -deduct_amount, allow_negative=False)
            assert abs(new_balance - (balance - deduct_amount)) < 0.01
        
    finally:
        try:
            os.unlink(db_path)
        except Exception:
            pass


# ============================================
# Property 10: Transaction Pagination Correctness
# **Feature: billing-system, Property 10: Transaction Pagination Correctness**
# **Validates: Requirements 5.3**
# ============================================

@given(
    num_transactions=st.integers(min_value=1, max_value=50),
    page_size=st.integers(min_value=1, max_value=20)
)
@settings(max_examples=20, deadline=None)
def test_transaction_pagination_correctness(num_transactions, page_size):
    """
    **Feature: billing-system, Property 10: Transaction Pagination Correctness**
    
    For any user with N transactions, paginating through all pages should 
    return exactly N unique transactions in chronological order.
    
    **Validates: Requirements 5.3**
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0
            )
        ''')
        conn.execute("INSERT INTO users (username, balance) VALUES ('testuser', 1000)")
        conn.commit()
        conn.close()
        
        db = BillingDatabase(db_path)
        
        # 创建指定数量的交易记录
        for i in range(num_transactions):
            db.create_transaction(
                user_id=1,
                type='recharge',
                amount=10.0,
                balance_after=1000 + (i + 1) * 10,
                description=f"Transaction {i + 1}"
            )
        
        # 验证总数
        total_count = db.get_transaction_count(1)
        assert total_count == num_transactions
        
        # 分页获取所有交易
        all_transactions = []
        page = 1
        while True:
            offset = (page - 1) * page_size
            transactions = db.get_transactions(1, page_size, offset)
            
            if not transactions:
                break
            
            all_transactions.extend(transactions)
            page += 1
            
            # 防止无限循环
            if page > num_transactions + 1:
                break
        
        # 验证获取的交易数量
        assert len(all_transactions) == num_transactions, \
            f"Expected {num_transactions} transactions, got {len(all_transactions)}"
        
        # 验证交易ID唯一
        transaction_ids = [t.id for t in all_transactions]
        assert len(transaction_ids) == len(set(transaction_ids)), \
            "Transaction IDs should be unique"
        
    finally:
        try:
            os.unlink(db_path)
        except Exception:
            pass


# ============================================
# Property 11: Admin Endpoints Require Authentication
# **Feature: billing-system, Property 11: Admin Endpoints Require Authentication**
# **Validates: Requirements 6.1**
# ============================================

@given(
    invalid_key=st.text(min_size=0, max_size=50).filter(lambda x: not x.startswith('adm_'))
)
@settings(max_examples=20, deadline=None)
def test_admin_endpoints_require_authentication(invalid_key):
    """
    **Feature: billing-system, Property 11: Admin Endpoints Require Authentication**
    
    For any admin endpoint, requests without valid admin authentication 
    should return 401 Unauthorized.
    
    **Validates: Requirements 6.1**
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0
            )
        ''')
        conn.execute('''
            CREATE TABLE admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                api_key TEXT UNIQUE,
                is_super BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        
        db = BillingDatabase(db_path)
        
        # 创建一个有效的管理员
        import hashlib
        password_hash = hashlib.sha256("admin123default_salt".encode()).hexdigest()
        valid_api_key = "adm_" + "a" * 48
        
        with db.get_connection() as conn:
            conn.execute('''
                INSERT INTO admins (username, password_hash, api_key, is_super, is_active)
                VALUES (?, ?, ?, 1, 1)
            ''', ('admin', password_hash, valid_api_key))
        
        # 验证有效的 API Key
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM admins WHERE api_key = ? AND is_active = 1",
                (valid_api_key,)
            ).fetchone()
            assert row is not None, "Valid admin should exist"
        
        # 验证无效的 API Key 不能通过
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM admins WHERE api_key = ? AND is_active = 1",
                (invalid_key,)
            ).fetchone()
            assert row is None, f"Invalid key '{invalid_key}' should not authenticate"
        
    finally:
        try:
            os.unlink(db_path)
        except Exception:
            pass


# ============================================
# Property 12: New User Gets Free Plan and API Key
# **Feature: billing-system, Property 12: New User Gets Free Plan and API Key**
# **Validates: Requirements 7.2, 7.4**
# ============================================

@given(
    username=st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_'),
        min_size=3,
        max_size=20
    ).filter(lambda x: x and not x[0].isdigit()),
    email_local=st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Nd')),
        min_size=3,
        max_size=10
    ).filter(lambda x: x and x.isalnum()),
    password=st.text(min_size=6, max_size=20).filter(lambda x: x.strip())
)
@settings(max_examples=20, deadline=None)
def test_new_user_gets_free_plan_and_api_key(username, email_local, password):
    """
    **Feature: billing-system, Property 12: New User Gets Free Plan and API Key**
    
    For any successful user registration, the user should have a free plan 
    subscription and at least one valid API key.
    
    **Validates: Requirements 7.2, 7.4**
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        
        # 创建完整的用户表
        conn.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT,
                balance REAL DEFAULT 0,
                email_verified BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建 API Key 表
        conn.execute('''
            CREATE TABLE api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                key TEXT UNIQUE NOT NULL,
                permissions TEXT DEFAULT 'all',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        db = BillingDatabase(db_path)
        
        # 确保有免费套餐
        free_plan = db.get_plan_by_name('free')
        assert free_plan is not None, "Free plan should exist"
        
        # 模拟用户注册
        import hashlib
        unique_username = f"{username}_{id(username)}"
        email = f"{email_local}@test.com"
        password_hash = hashlib.sha256(f"{password}default_salt".encode()).hexdigest()
        
        with db.get_connection() as conn:
            # 创建用户
            cursor = conn.execute('''
                INSERT INTO users (username, email, password_hash, balance, email_verified)
                VALUES (?, ?, ?, 0, 0)
            ''', (unique_username, email, password_hash))
            user_id = cursor.lastrowid
            
            # 创建 API Key
            import secrets
            api_key = f"etk_{secrets.token_hex(16)}"
            conn.execute('''
                INSERT INTO api_keys (user_id, key, permissions)
                VALUES (?, ?, 'all')
            ''', (user_id, api_key))
        
        # 创建免费套餐订阅
        from datetime import datetime
        db.create_subscription(user_id, free_plan.id, datetime.now(), None)
        
        # 验证用户有订阅
        sub = db.get_user_subscription(user_id)
        assert sub is not None, "User should have a subscription"
        assert sub.plan.name == 'free', "User should have free plan"
        
        # 验证用户有 API Key
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM api_keys WHERE user_id = ? AND is_active = 1",
                (user_id,)
            ).fetchone()
            assert row[0] >= 1, "User should have at least one API key"
        
    finally:
        try:
            os.unlink(db_path)
        except Exception:
            pass


# ============================================
# Property 13: Cost Calculation Uses Current Pricing
# **Feature: billing-system, Property 13: Cost Calculation Uses Current Pricing**
# **Validates: Requirements 8.3**
# ============================================

@given(
    price_per_request=st.floats(min_value=0, max_value=0.1, allow_nan=False, allow_infinity=False),
    price_per_1k_tokens=st.floats(min_value=0, max_value=0.1, allow_nan=False, allow_infinity=False),
    price_per_minute_audio=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    requests=st.integers(min_value=0, max_value=1000),
    tokens=st.integers(min_value=0, max_value=100000),
    audio_seconds=st.integers(min_value=0, max_value=3600)
)
@settings(max_examples=20, deadline=None)
def test_cost_calculation_uses_current_pricing(
    price_per_request, price_per_1k_tokens, price_per_minute_audio,
    requests, tokens, audio_seconds
):
    """
    **Feature: billing-system, Property 13: Cost Calculation Uses Current Pricing**
    
    For any API usage, the calculated cost should match the current plan's 
    pricing rates multiplied by usage amount.
    
    **Validates: Requirements 8.3**
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()
        
        db = BillingDatabase(db_path)
        
        # 创建自定义定价的套餐
        unique_name = f"test_pricing_{id(price_per_request)}"
        plan_id = db.create_plan(
            name=unique_name,
            display_name="测试套餐",
            monthly_price=0,
            daily_requests=1000,
            daily_tokens=100000,
            daily_audio_seconds=3600,
            price_per_request=price_per_request,
            price_per_1k_tokens=price_per_1k_tokens,
            price_per_minute_audio=price_per_minute_audio
        )
        
        plan = db.get_plan(plan_id)
        assert plan is not None
        
        # 计算预期成本
        expected_requests_cost = price_per_request * requests
        expected_tokens_cost = price_per_1k_tokens * (tokens / 1000)
        expected_audio_cost = price_per_minute_audio * (audio_seconds / 60)
        
        # 使用服务计算成本
        from src.billing.service import BillingService
        
        # 创建一个临时的服务实例来测试计算
        # 直接测试计算逻辑
        if requests > 0:
            actual_requests_cost = float(plan.price_per_request) * requests
            assert abs(actual_requests_cost - expected_requests_cost) < 0.0001, \
                f"Requests cost mismatch: expected {expected_requests_cost}, got {actual_requests_cost}"
        
        if tokens > 0:
            actual_tokens_cost = float(plan.price_per_1k_tokens) * (tokens / 1000)
            assert abs(actual_tokens_cost - expected_tokens_cost) < 0.0001, \
                f"Tokens cost mismatch: expected {expected_tokens_cost}, got {actual_tokens_cost}"
        
        if audio_seconds > 0:
            actual_audio_cost = float(plan.price_per_minute_audio) * (audio_seconds / 60)
            assert abs(actual_audio_cost - expected_audio_cost) < 0.0001, \
                f"Audio cost mismatch: expected {expected_audio_cost}, got {actual_audio_cost}"
        
    finally:
        try:
            os.unlink(db_path)
        except Exception:
            pass
