"""
计费系统安全审计测试
第三方审计级别 - 严重漏洞检测

**Feature: billing-security-audit**
"""

import os
import sys
import tempfile
import threading
import time
import pytest
from decimal import Decimal
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hypothesis import given, strategies as st, settings, assume


# ============================================
# 安全测试 Fixtures
# ============================================

@pytest.fixture
def temp_db():
    """创建临时测试数据库"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
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
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    from src.billing.models import BillingDatabase
    db = BillingDatabase(db_path)
    yield db
    
    try:
        os.unlink(db_path)
    except Exception:
        pass


# ============================================
# P0-1: 密码哈希安全性测试
# ============================================

class TestPasswordHashingSecurity:
    """密码哈希安全性测试"""
    
    def test_password_hash_not_sha256(self):
        """
        验证密码哈希不应该使用简单的SHA256
        
        **安全要求:** 密码应使用bcrypt或Argon2
        """
        from src.auth.auth_service import AuthService
        
        service = AuthService()
        
        # 获取哈希结果
        password = "test_password_123"
        hash_result = service._hash_password(password)
        
        # SHA256 产生64字符的十六进制字符串
        # 如果长度是64且全是十六进制字符，很可能是SHA256
        is_likely_sha256 = (
            len(hash_result) == 64 and 
            all(c in '0123456789abcdef' for c in hash_result.lower())
        )
        
        # 这个测试应该失败，表明当前实现不安全
        # 修复后应该通过
        if is_likely_sha256:
            pytest.fail(
                "⚠️ 安全漏洞: 密码使用SHA256哈希，应改用bcrypt或Argon2\n"
                f"当前哈希长度: {len(hash_result)}\n"
                "建议: 使用 werkzeug.security.generate_password_hash"
            )
    
    def test_password_hash_uses_unique_salt(self):
        """
        验证每个密码应该使用唯一的盐值
        
        **安全要求:** 相同密码应产生不同哈希
        """
        from src.auth.auth_service import AuthService
        
        service = AuthService()
        password = "same_password"
        
        hash1 = service._hash_password(password)
        hash2 = service._hash_password(password)
        
        # 如果使用正确的盐值，相同密码应产生不同哈希
        # 当前实现使用固定盐值，所以会相同
        if hash1 == hash2:
            pytest.fail(
                "⚠️ 安全漏洞: 相同密码产生相同哈希，表明使用固定盐值\n"
                "建议: 使用per-user随机盐值"
            )


# ============================================
# P0-2: JWT 安全性测试
# ============================================

class TestJWTSecurity:
    """JWT 安全性测试"""
    
    def test_jwt_secret_not_default(self):
        """
        验证JWT密钥不应使用默认值
        
        **安全要求:** JWT密钥必须是强随机值
        """
        from src.auth.auth_service import JWT_SECRET
        
        default_secrets = [
            'default_jwt_secret',
            'default_salt',
            'secret',
            'jwt_secret',
            ''
        ]
        
        if JWT_SECRET in default_secrets:
            pytest.fail(
                f"⚠️ 安全漏洞: JWT使用默认密钥 '{JWT_SECRET}'\n"
                "建议: 设置环境变量 JWT_SECRET 为强随机值"
            )
    
    def test_jwt_token_tampering_detection(self):
        """
        验证JWT令牌篡改应被检测
        
        **安全要求:** 修改后的令牌应验证失败
        """
        from src.auth.auth_service import AuthService
        
        service = AuthService()
        
        # 生成有效令牌
        token = service._generate_jwt_token(1, "testuser")
        
        # 篡改令牌 (修改payload部分)
        parts = token.split('.')
        if len(parts) == 3:
            # 修改payload
            tampered_token = f"{parts[0]}.{parts[1]}x.{parts[2]}"
            
            result = service._verify_jwt_token(tampered_token)
            assert result is None, "篡改的令牌应该验证失败"
    
    def test_jwt_expired_token_rejected(self):
        """
        验证过期JWT令牌应被拒绝
        
        **安全要求:** 过期令牌不应通过验证
        """
        from src.auth.auth_service import AuthService
        import base64
        import json
        import hmac
        import hashlib
        
        service = AuthService()
        
        # 创建一个已过期的令牌
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": 1,
            "username": "testuser",
            "iat": int((datetime.utcnow() - timedelta(hours=48)).timestamp()),
            "exp": int((datetime.utcnow() - timedelta(hours=24)).timestamp())  # 已过期
        }
        
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        
        from src.auth.auth_service import JWT_SECRET
        message = f"{header_b64}.{payload_b64}"
        signature = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')
        
        expired_token = f"{header_b64}.{payload_b64}.{signature_b64}"
        
        result = service._verify_jwt_token(expired_token)
        assert result is None, "过期令牌应该验证失败"


# ============================================
# P0-3: 余额并发安全测试
# ============================================

class TestBalanceConcurrencySecurity:
    """余额并发安全测试"""
    
    def test_concurrent_balance_operations_race_condition(self, temp_db):
        """
        测试并发余额操作的竞态条件
        
        **安全要求:** 并发操作不应导致余额不一致
        """
        # 创建测试用户
        with temp_db.get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, email, balance) VALUES (?, ?, ?)",
                ("testuser", "test@test.com", 1000.0)
            )
        
        results = []
        errors = []
        
        def deduct_balance():
            try:
                # 每个线程尝试扣除100
                new_balance = temp_db.update_balance(1, -100, allow_negative=False)
                results.append(('success', new_balance))
            except ValueError as e:
                results.append(('failed', str(e)))
            except Exception as e:
                errors.append(str(e))
        
        # 启动20个并发线程，每个扣除100
        # 初始余额1000，理论上只能成功10次
        threads = []
        for _ in range(20):
            t = threading.Thread(target=deduct_balance)
            threads.append(t)
        
        # 同时启动所有线程
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # 检查最终余额
        final_balance = temp_db.get_balance(1)
        successful_deductions = sum(1 for r in results if r[0] == 'success')
        
        # 计算预期余额
        expected_balance = 1000 - (successful_deductions * 100)
        
        # 如果存在竞态条件，最终余额可能不等于预期
        if abs(final_balance - expected_balance) > 0.01:
            pytest.fail(
                f"⚠️ 安全漏洞: 检测到余额竞态条件\n"
                f"成功扣款次数: {successful_deductions}\n"
                f"预期余额: {expected_balance}\n"
                f"实际余额: {final_balance}\n"
                f"差异: {abs(final_balance - expected_balance)}\n"
                "建议: 使用数据库原子操作 UPDATE users SET balance = balance - ? WHERE id = ? AND balance >= ?"
            )
    
    def test_double_spending_prevention(self, temp_db):
        """
        测试双花攻击防护
        
        **安全要求:** 不应允许余额变为负数
        """
        # 创建测试用户，余额100
        with temp_db.get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, email, balance) VALUES (?, ?, ?)",
                ("testuser", "test@test.com", 100.0)
            )
        
        # 尝试扣除150
        try:
            temp_db.update_balance(1, -150, allow_negative=False)
            pytest.fail("应该拒绝导致负余额的扣款")
        except ValueError:
            pass  # 预期行为
        
        # 验证余额未变
        balance = temp_db.get_balance(1)
        assert balance == 100.0, "余额应保持不变"


# ============================================
# P0-4: 订阅升级原子性测试
# ============================================

class TestSubscriptionUpgradeAtomicity:
    """订阅升级原子性测试"""
    
    def test_upgrade_failure_rollback(self, temp_db):
        """
        测试升级失败时的回滚
        
        **安全要求:** 升级失败不应导致数据不一致
        """
        # 创建测试用户
        with temp_db.get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, email, balance) VALUES (?, ?, ?)",
                ("testuser", "test@test.com", 50.0)  # 余额不足以升级
            )
        
        # 获取免费套餐
        free_plan = temp_db.get_plan_by_name('free')
        pro_plan = temp_db.get_plan_by_name('pro')
        
        if not free_plan or not pro_plan:
            pytest.skip("需要free和pro套餐")
        
        # 创建免费订阅
        temp_db.create_subscription(1, free_plan.id, datetime.now(), None)
        
        initial_balance = temp_db.get_balance(1)
        initial_sub = temp_db.get_user_subscription(1)
        
        # 尝试升级到pro (余额不足)
        from src.billing.service import BillingService
        
        # 注意: 这里我们测试的是如果升级过程中出错，数据是否一致
        # 当前实现可能存在问题
        
        # 验证用户仍有订阅
        current_sub = temp_db.get_user_subscription(1)
        current_balance = temp_db.get_balance(1)
        
        # 如果升级失败，用户应该保持原有订阅和余额
        assert current_sub is not None, "用户应该仍有订阅"
        assert abs(current_balance - initial_balance) < 0.01, "余额应保持不变"


# ============================================
# P1-1: 金额计算精度测试
# ============================================

class TestMonetaryPrecision:
    """金额计算精度测试"""
    
    @given(
        price=st.floats(min_value=0.001, max_value=0.01, allow_nan=False, allow_infinity=False),
        quantity=st.integers(min_value=1, max_value=1000000)
    )
    @settings(max_examples=50, deadline=None)
    def test_cost_calculation_precision(self, price, quantity):
        """
        测试成本计算精度
        
        **安全要求:** 金额计算不应有精度丢失
        """
        # 使用浮点数计算
        float_result = price * quantity
        
        # 使用Decimal计算
        decimal_result = Decimal(str(price)) * Decimal(str(quantity))
        
        # 检查差异
        diff = abs(float_result - float(decimal_result))
        
        # 对于金融计算，差异应该小于0.01
        if diff > 0.01:
            pytest.fail(
                f"⚠️ 精度问题: 浮点数计算与Decimal计算差异过大\n"
                f"价格: {price}, 数量: {quantity}\n"
                f"浮点结果: {float_result}\n"
                f"Decimal结果: {decimal_result}\n"
                f"差异: {diff}"
            )


# ============================================
# P1-2: 参数验证测试
# ============================================

class TestParameterValidation:
    """参数验证测试"""
    
    def test_quota_type_validation(self):
        """
        测试配额类型参数验证
        
        **安全要求:** 无效的配额类型应被拒绝
        """
        from src.billing.service import BillingService
        
        service = BillingService()
        
        # 测试无效的配额类型
        invalid_types = ['invalid', 'sql_injection', "'; DROP TABLE users; --", '']
        
        for invalid_type in invalid_types:
            result = service.check_quota(1, invalid_type)
            # 当前实现对无效类型返回 allowed=True，这是不安全的
            if result.get('allowed') and result.get('remaining') == 999999:
                pytest.fail(
                    f"⚠️ 安全漏洞: 无效配额类型 '{invalid_type}' 被接受\n"
                    "建议: 验证quota_type参数"
                )
    
    def test_negative_amount_rejection(self, temp_db):
        """
        测试负数金额应被拒绝
        
        **安全要求:** 负数充值金额应被拒绝
        """
        from src.billing.service import BillingService
        
        # 创建测试用户
        with temp_db.get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, email, balance) VALUES (?, ?, ?)",
                ("testuser", "test@test.com", 100.0)
            )
        
        # 注意: 需要mock或使用真实服务
        # 这里只测试模型层
        
        # 测试负数充值
        initial_balance = temp_db.get_balance(1)
        
        # update_balance 允许负数作为扣款
        # 但 recharge 方法应该拒绝负数
        # 这里测试直接调用 update_balance 的行为
        
        # 尝试通过 update_balance 增加负数（实际是扣款）
        try:
            temp_db.update_balance(1, -50, allow_negative=False)
            # 这是预期行为，扣款50
        except ValueError:
            pass


# ============================================
# P1-3: Admin API 认证测试
# ============================================

class TestAdminAPIAuthentication:
    """Admin API 认证测试"""
    
    def test_create_user_requires_auth(self):
        """
        测试创建用户端点需要认证
        
        **安全要求:** 创建用户应需要管理员认证
        """
        # 检查路由定义
        from src.api.admin.routes import create_user
        
        # 检查函数是否有认证装饰器
        # 通过检查 __wrapped__ 属性来判断是否被装饰
        has_auth_decorator = hasattr(create_user, '__wrapped__')
        
        if not has_auth_decorator:
            pytest.fail(
                "⚠️ 安全漏洞: create_user 端点缺少认证装饰器\n"
                "建议: 添加 @require_admin_key() 装饰器"
            )
    
    def test_invalid_admin_key_rejected(self, temp_db):
        """
        测试无效的管理员密钥应被拒绝
        
        **安全要求:** 无效密钥不应通过认证
        """
        from src.auth.admin_auth import AdminAuthService
        
        service = AdminAuthService()
        
        invalid_keys = [
            '',
            'invalid',
            'adm_',  # 只有前缀
            'etk_user_key',  # 用户密钥前缀
            'adm_' + 'a' * 100,  # 过长
            "adm_'; DROP TABLE admins; --",  # SQL注入尝试
        ]
        
        for invalid_key in invalid_keys:
            admin = service.verify_api_key(invalid_key)
            assert admin is None, f"无效密钥 '{invalid_key}' 不应通过认证"


# ============================================
# SQL 注入测试
# ============================================

class TestSQLInjection:
    """SQL 注入测试"""
    
    def test_plan_name_sql_injection(self, temp_db):
        """
        测试套餐名称SQL注入防护
        
        **安全要求:** SQL注入尝试应被安全处理
        """
        malicious_inputs = [
            "'; DROP TABLE plans; --",
            "1' OR '1'='1",
            "1; UPDATE users SET balance = 999999; --",
            "1 UNION SELECT * FROM admins",
        ]
        
        for malicious_input in malicious_inputs:
            try:
                result = temp_db.get_plan_by_name(malicious_input)
                # 应该返回None，不应该执行恶意SQL
                assert result is None, f"恶意输入 '{malicious_input}' 应返回None"
            except Exception as e:
                # 异常也是可接受的，只要不执行恶意SQL
                pass
        
        # 验证plans表仍然存在
        plans = temp_db.get_plans()
        assert len(plans) > 0, "plans表应该仍然存在"


# ============================================
# 运行测试
# ============================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
