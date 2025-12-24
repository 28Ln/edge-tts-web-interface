# 计费系统安全审计设计文档

## Overview

本文档详细描述了计费系统安全审计中发现的问题及修复方案。审计通过自动化安全测试验证了6个严重安全漏洞。

## 审计测试结果摘要

```
测试执行: 14个安全测试
通过: 8个 (57%)
失败: 6个 (43%) - 均为已确认的安全漏洞
```

## Architecture

### 当前系统架构问题

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ auth/routes │  │billing/routes│  │ admin/routes ❌无认证   │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
┌─────────┼────────────────┼─────────────────────┼────────────────┐
│         ▼                ▼                     ▼                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ AuthService │  │BillingService│  │ AdminAuthService        │  │
│  │ ❌SHA256密码│  │ ❌竞态条件  │  │                         │  │
│  │ ❌默认JWT   │  │ ❌非原子升级│  │                         │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                     │                │
│         ▼                ▼                     ▼                │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    SQLite Database                          ││
│  │  users | plans | subscriptions | transactions | admins      ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## 已确认的安全漏洞详情

### 漏洞 1: 密码使用SHA256哈希 (P0)

**测试结果:**
```
FAILED test_password_hash_not_sha256
⚠️ 安全漏洞: 密码使用SHA256哈希，应改用bcrypt或Argon2
当前哈希长度: 64
```

**问题代码:**
```python
# src/auth/auth_service.py:35-37
def _hash_password(self, password: str) -> str:
    salt = os.environ.get('SECRET_KEY', 'default_salt')
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
```

**修复方案:**
```python
from werkzeug.security import generate_password_hash, check_password_hash

def _hash_password(self, password: str) -> str:
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

def _verify_password(self, password: str, hash: str) -> bool:
    return check_password_hash(hash, password)
```

---

### 漏洞 2: 相同密码产生相同哈希 (P0)

**测试结果:**
```
FAILED test_password_hash_uses_unique_salt
⚠️ 安全漏洞: 相同密码产生相同哈希，表明使用固定盐值
```

**影响:** 彩虹表攻击可以一次性破解所有使用相同密码的用户

---

### 漏洞 3: JWT使用默认密钥 (P0)

**测试结果:**
```
FAILED test_jwt_secret_not_default
⚠️ 安全漏洞: JWT使用默认密钥 'default_jwt_secret'
```

**问题代码:**
```python
# src/auth/auth_service.py:20
JWT_SECRET = os.environ.get('JWT_SECRET', os.environ.get('SECRET_KEY', 'default_jwt_secret'))
```

**修复方案:**
1. 移除默认值，强制要求配置
2. 启动时检查密钥强度
3. 使用标准PyJWT库

---

### 漏洞 4: 余额竞态条件 (P0 - 最严重)

**测试结果:**
```
FAILED test_concurrent_balance_operations_race_condition
⚠️ 安全漏洞: 检测到余额竞态条件
成功扣款次数: 20
预期余额: -1000
实际余额: 800.0
差异: 1800.0
```

**问题分析:**
- 初始余额: 1000
- 20个并发线程各扣100
- 理论上只能成功10次 (1000/100)
- 实际成功20次，导致余额应为-1000
- 但由于竞态条件，实际余额为800 (数据不一致)

**问题代码:**
```python
# src/billing/models.py:285-305
def update_balance(self, user_id: int, amount: float, allow_negative: bool = False) -> float:
    with self.get_connection() as conn:
        # 步骤1: 读取余额
        row = conn.execute('SELECT balance FROM users WHERE id = ?', (user_id,)).fetchone()
        current_balance = float(row['balance'])
        new_balance = current_balance + amount
        
        # ❌ TOCTOU漏洞: 在步骤1和步骤2之间，其他线程可能已修改余额
        
        # 步骤2: 更新余额
        conn.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, user_id))
```

**修复方案:**
```python
def update_balance(self, user_id: int, amount: float, allow_negative: bool = False) -> float:
    with self.get_connection() as conn:
        if allow_negative:
            # 原子更新，不检查余额
            conn.execute(
                'UPDATE users SET balance = balance + ? WHERE id = ?',
                (amount, user_id)
            )
        else:
            # 原子更新，同时检查余额
            cursor = conn.execute(
                '''UPDATE users SET balance = balance + ? 
                   WHERE id = ? AND balance + ? >= 0''',
                (amount, user_id, amount)
            )
            if cursor.rowcount == 0:
                raise ValueError("余额不足")
        
        # 返回更新后的余额
        row = conn.execute('SELECT balance FROM users WHERE id = ?', (user_id,)).fetchone()
        return float(row['balance'])
```

---

### 漏洞 5: 无效配额类型被接受 (P1)

**测试结果:**
```
FAILED test_quota_type_validation
⚠️ 安全漏洞: 无效配额类型 'invalid' 被接受
```

**问题代码:**
```python
# src/billing/service.py:295-310
def check_quota(self, user_id: int, quota_type: str = 'requests') -> Dict:
    # ...
    else:
        return {"allowed": True, "remaining": 999999, "limit": 999999}  # ❌ 无效类型返回无限配额
```

**修复方案:**
```python
VALID_QUOTA_TYPES = {'requests', 'tokens', 'audio_seconds'}

def check_quota(self, user_id: int, quota_type: str = 'requests') -> Dict:
    if quota_type not in VALID_QUOTA_TYPES:
        return {"allowed": False, "message": f"无效的配额类型: {quota_type}"}
    # ...
```

---

### 漏洞 6: Admin API缺少认证 (P1)

**测试结果:**
```
FAILED test_create_user_requires_auth
⚠️ 安全漏洞: create_user 端点缺少认证装饰器
```

**问题代码:**
```python
# src/api/admin/routes.py:85
@admin_bp.route('/users', methods=['POST'])
def create_user():  # ❌ 没有 @require_admin_key() 装饰器
```

**修复方案:**
```python
@admin_bp.route('/users', methods=['POST'])
@require_admin_key()  # 添加认证
def create_user():
```

---

## Components and Interfaces

### 需要修改的组件

| 组件 | 文件 | 修改内容 |
|------|------|----------|
| AuthService | src/auth/auth_service.py | 密码哈希、JWT实现 |
| BillingDatabase | src/billing/models.py | 原子余额操作 |
| BillingService | src/billing/service.py | 参数验证、事务升级 |
| Admin Routes | src/api/admin/routes.py | 添加认证装饰器 |

## Data Models

无需修改数据模型，但需要注意:
- 密码哈希格式将改变，需要迁移策略
- 建议添加 `password_version` 字段支持渐进式迁移

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: 密码哈希唯一性
*For any* two identical passwords, hashing them should produce different hash values due to unique per-hash salts.
**Validates: Requirements 1.1, 1.2**

### Property 2: JWT令牌不可伪造
*For any* modified JWT token, verification should fail and return None.
**Validates: Requirements 2.1, 2.2**

### Property 3: 余额操作原子性
*For any* sequence of concurrent balance operations, the final balance should equal the sum of all successful operations.
**Validates: Requirements 3.1, 3.2**

### Property 4: 配额类型验证
*For any* invalid quota type, the system should reject the request with an error.
**Validates: Requirements 7.1**

### Property 5: Admin端点认证
*For any* admin endpoint, requests without valid admin authentication should return 401.
**Validates: Requirements 8.1**

## Error Handling

### 安全相关错误码

| 错误码 | HTTP状态 | 描述 |
|--------|----------|------|
| AUTH_FAILED | 401 | 认证失败 |
| INVALID_TOKEN | 401 | 无效或过期的Token |
| ADMIN_AUTH_REQUIRED | 401 | 需要管理员认证 |
| INSUFFICIENT_BALANCE | 400 | 余额不足 |
| INVALID_QUOTA_TYPE | 400 | 无效的配额类型 |
| RACE_CONDITION_DETECTED | 500 | 检测到竞态条件 |

## Testing Strategy

### 安全测试覆盖

1. **密码安全测试**
   - 验证不使用SHA256
   - 验证使用唯一盐值
   - 验证密码强度要求

2. **JWT安全测试**
   - 验证不使用默认密钥
   - 验证令牌篡改检测
   - 验证过期令牌拒绝

3. **并发安全测试**
   - 验证余额操作原子性
   - 验证双花攻击防护
   - 验证订阅升级原子性

4. **输入验证测试**
   - 验证配额类型验证
   - 验证金额范围验证
   - 验证SQL注入防护

5. **认证测试**
   - 验证Admin端点认证
   - 验证无效密钥拒绝
   - 验证权限检查

### 测试框架

- **pytest**: 测试框架
- **hypothesis**: 属性测试
- **threading**: 并发测试

### 运行安全测试

```bash
py -m pytest tests/security/test_billing_security_audit.py -v
```

## 修复优先级

### P0 - 立即修复 (本周)
1. ❌ 密码哈希安全性 - 使用bcrypt
2. ❌ JWT默认密钥 - 强制配置
3. ❌ 余额竞态条件 - 原子操作
4. ❌ 订阅升级原子性 - 事务处理

### P1 - 尽快修复 (下周)
1. ❌ 配额类型验证
2. ❌ Admin API认证
3. ⚠️ 金额计算精度

### P2 - 计划修复
1. ⚠️ 充值金额限制
2. ⚠️ 支付幂等性
3. ⚠️ API Key哈希存储
