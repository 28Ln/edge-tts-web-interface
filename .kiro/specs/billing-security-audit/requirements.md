# 计费系统安全审计报告

## Introduction

本文档是对计费系统进行的第三方审计级别安全检查报告。审计范围包括：认证服务、计费服务、配额管理、API路由层。审计目标是识别严重安全漏洞、数据一致性问题和业务逻辑缺陷。

## Glossary

- **BillingService**: 计费服务核心类，处理订阅、余额、交易等业务逻辑
- **AuthService**: 用户认证服务，处理注册、登录、JWT Token
- **AdminAuthService**: 管理员认证服务，处理管理员API Key验证
- **QuotaService**: 配额管理服务，处理用量检查和按量计费
- **Race Condition**: 竞态条件，并发操作导致的数据不一致
- **TOCTOU**: Time-of-check to time-of-use，检查时间与使用时间之间的漏洞

---

## 🚨 严重安全问题 (P0 - 需立即修复)

### Requirement 1: 密码哈希安全性不足

**User Story:** As a security auditor, I want passwords to be securely hashed, so that user credentials are protected against brute-force and rainbow table attacks.

#### Acceptance Criteria

1. WHEN a user password is hashed THEN the system SHALL use bcrypt or Argon2 with per-user random salt
2. WHEN password hashing is performed THEN the system SHALL NOT use SHA256 with fixed salt
3. IF the current implementation uses weak hashing THEN the system SHALL migrate to secure hashing algorithm

**当前问题:**
```python
# src/auth/auth_service.py - 第35-37行
def _hash_password(self, password: str) -> str:
    salt = os.environ.get('SECRET_KEY', 'default_salt')  # ❌ 固定盐值
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()  # ❌ SHA256不适合密码
```

**风险等级:** 🔴 严重
- SHA256 计算速度过快，易受暴力破解
- 固定盐值使所有用户密码使用相同盐，易受彩虹表攻击
- 默认盐值 'default_salt' 可被猜测

---

### Requirement 2: JWT 实现存在安全漏洞

**User Story:** As a security auditor, I want JWT tokens to be securely implemented, so that authentication cannot be bypassed or forged.

#### Acceptance Criteria

1. WHEN JWT tokens are generated THEN the system SHALL use standard PyJWT library
2. WHEN JWT tokens are verified THEN the system SHALL validate algorithm header to prevent algorithm confusion attacks
3. WHEN JWT secret is configured THEN the system SHALL NOT use default secret value

**当前问题:**
```python
# src/auth/auth_service.py - 第39-65行
JWT_SECRET = os.environ.get('JWT_SECRET', os.environ.get('SECRET_KEY', 'default_jwt_secret'))
# ❌ 自制JWT实现，未使用标准库
# ❌ 默认密钥 'default_jwt_secret' 可被猜测
# ❌ 缺少算法验证，可能受算法混淆攻击
```

**风险等级:** 🔴 严重

---

### Requirement 3: 余额操作存在竞态条件

**User Story:** As a security auditor, I want balance operations to be atomic, so that concurrent requests cannot cause balance inconsistency or double-spending.

#### Acceptance Criteria

1. WHEN balance is updated THEN the system SHALL use database-level atomic operations
2. WHEN multiple concurrent balance operations occur THEN the system SHALL prevent race conditions
3. IF balance check and update are separate operations THEN the system SHALL use row-level locking

**当前问题:**
```python
# src/billing/models.py - 第285-305行
def update_balance(self, user_id: int, amount: float, allow_negative: bool = False) -> float:
    with self.get_connection() as conn:
        # ❌ 读取余额
        row = conn.execute('SELECT balance FROM users WHERE id = ?', (user_id,)).fetchone()
        current_balance = float(row['balance']) if row and row['balance'] else 0.0
        new_balance = current_balance + amount
        # ❌ 在这两步之间可能被其他请求修改 (TOCTOU漏洞)
        conn.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, user_id))
```

**风险等级:** 🔴 严重
- 并发充值可能导致余额丢失
- 并发扣款可能导致超额扣款
- 可被恶意利用进行双花攻击

---

### Requirement 4: 订阅升级操作非原子性

**User Story:** As a security auditor, I want subscription upgrades to be atomic, so that users cannot lose their subscription during upgrade failures.

#### Acceptance Criteria

1. WHEN a subscription is upgraded THEN the system SHALL perform all operations in a single transaction
2. IF any step of upgrade fails THEN the system SHALL rollback all changes
3. WHEN balance is deducted for upgrade THEN the system SHALL ensure subscription is created before commit

**当前问题:**
```python
# src/billing/service.py - 第185-220行
def upgrade_subscription(self, user_id: int, new_plan_name: str) -> Dict:
    # ❌ 扣除余额
    new_balance = self.billing_db.update_balance(user_id, -upgrade_cost)
    # ❌ 创建交易记录
    self.billing_db.create_transaction(...)
    # ❌ 取消当前订阅 - 如果这里成功
    self.billing_db.cancel_subscription(user_id)
    # ❌ 创建新订阅 - 但这里失败，用户就没有订阅了，钱也扣了
    sub_id = self.billing_db.create_subscription(...)
```

**风险等级:** 🔴 严重

---

## ⚠️ 中等安全问题 (P1 - 本周修复)

### Requirement 5: 浮点数精度问题导致金额计算错误

**User Story:** As a billing system user, I want monetary calculations to be precise, so that I am not overcharged or undercharged.

#### Acceptance Criteria

1. WHEN monetary amounts are calculated THEN the system SHALL use Decimal type with proper rounding
2. WHEN prices are multiplied by quantities THEN the system SHALL avoid floating-point precision loss
3. WHEN displaying amounts THEN the system SHALL round to appropriate decimal places

**当前问题:**
```python
# src/billing/service.py - 第315-325行
def calculate_cost(self, plan: Plan, usage_type: str, amount: float) -> float:
    if usage_type == 'tokens':
        return float(plan.price_per_1k_tokens) * (amount / 1000)  # ❌ 浮点数精度丢失
```

**风险等级:** 🟡 中等

---

### Requirement 6: 时区处理不一致

**User Story:** As a system administrator, I want subscription expiry to be checked correctly regardless of server timezone, so that users are not incorrectly downgraded.

#### Acceptance Criteria

1. WHEN subscription expiry is checked THEN the system SHALL use timezone-aware datetime comparison
2. WHEN dates are stored THEN the system SHALL use UTC or consistent timezone
3. WHEN displaying dates to users THEN the system SHALL convert to user's timezone

**当前问题:**
```python
# src/billing/service.py - 第130行
if sub.end_date and sub.end_date < datetime.now():  # ❌ 没有指定时区
```

**风险等级:** 🟡 中等

---

### Requirement 7: 配额检查参数验证不足

**User Story:** As a security auditor, I want quota parameters to be validated, so that malicious inputs cannot bypass quota limits.

#### Acceptance Criteria

1. WHEN quota_type parameter is received THEN the system SHALL validate against allowed values
2. WHEN amount parameter is received THEN the system SHALL reject negative or zero values
3. WHEN amount exceeds reasonable limits THEN the system SHALL reject the request

**当前问题:**
```python
# src/billing/quota.py - 第25-35行
def check_and_consume(self, user_id: int, quota_type: str, amount: int = 1) -> Dict:
    # ❌ 没有验证 amount 参数，可能传入负数
    # ❌ 没有验证 quota_type 参数，可能传入无效类型
```

**风险等级:** 🟡 中等

---

### Requirement 8: Admin API 缺少认证保护

**User Story:** As a security auditor, I want all admin endpoints to require authentication, so that unauthorized users cannot access administrative functions.

#### Acceptance Criteria

1. WHEN an admin endpoint is accessed THEN the system SHALL require valid admin API key
2. WHEN user creation endpoint is accessed THEN the system SHALL require admin authentication
3. WHEN API key management endpoints are accessed THEN the system SHALL require admin authentication

**当前问题:**
```python
# src/api/admin/routes.py - 第85行
@admin_bp.route('/users', methods=['POST'])
def create_user():  # ❌ 没有 @require_admin_key() 装饰器
```

**风险等级:** 🟡 中等 - 任何人可以创建用户

---

## 📋 低优先级问题 (P2 - 下周修复)

### Requirement 9: 缺少充值金额上限验证

**User Story:** As a system administrator, I want recharge amounts to be limited, so that fraudulent large transactions can be prevented.

#### Acceptance Criteria

1. WHEN a recharge request is received THEN the system SHALL validate amount is within allowed range
2. WHEN amount exceeds maximum limit THEN the system SHALL reject with appropriate error
3. WHEN amount is below minimum limit THEN the system SHALL reject with appropriate error

**当前问题:**
```python
# src/billing/service.py - 第240-250行
def recharge(self, user_id: int, amount: float, reference_id: str = None) -> Dict:
    if amount <= 0:
        return {"success": False, "message": "充值金额必须大于0"}
    # ❌ 没有最大金额限制
```

---

### Requirement 10: 缺少支付幂等性保护

**User Story:** As a billing system user, I want duplicate payment requests to be handled correctly, so that I am not charged multiple times.

#### Acceptance Criteria

1. WHEN a recharge request with reference_id is received THEN the system SHALL check for duplicate
2. IF duplicate reference_id exists THEN the system SHALL return existing transaction result
3. WHEN creating transaction THEN the system SHALL use reference_id as idempotency key

**当前问题:**
- 没有检查 reference_id 是否已存在
- 重复请求会导致重复充值

---

### Requirement 11: API Key 明文存储

**User Story:** As a security auditor, I want API keys to be securely stored, so that database compromise does not expose all API keys.

#### Acceptance Criteria

1. WHEN API key is stored THEN the system SHALL store only the hash
2. WHEN API key is verified THEN the system SHALL compare hash values
3. WHEN API key is displayed THEN the system SHALL show only prefix

**当前问题:**
```python
# src/auth/api_key.py - 第25-30行
# 注释说明应该存储哈希，但实际存储原文
```

---

## ✅ 良好实践

1. **参数化查询** - 所有SQL查询使用参数化，基本防止SQL注入
2. **事务处理** - 大部分数据库操作使用事务
3. **属性测试** - 13个Property-Based Tests覆盖核心逻辑，全部通过
4. **错误处理** - 有基本的异常处理机制
5. **日志记录** - 关键操作有日志记录
6. **权限检查** - 大部分API有认证装饰器

---

## 📊 测试覆盖率评估

| 测试类型 | 状态 | 数量 |
|---------|------|------|
| 属性测试 (PBT) | ✅ 通过 | 13个 |
| 单元测试 | ⚠️ 需补充 | - |
| 集成测试 | ⚠️ 需补充 | - |
| 安全测试 | ❌ 缺失 | - |
| 并发测试 | ❌ 缺失 | - |

---

## 🔧 修复优先级

### P0 (立即修复):
1. 密码哈希安全性 - 使用 bcrypt
2. JWT实现安全性 - 使用 PyJWT
3. 余额操作原子性 - 使用数据库原子操作
4. 订阅升级事务性 - 使用完整事务

### P1 (本周修复):
1. 金额计算精度 - 使用 Decimal
2. 时区处理 - 使用 UTC
3. 参数验证加强
4. Admin API 认证

### P2 (下周修复):
1. 充值金额限制
2. 支付幂等性
3. API Key 哈希存储
