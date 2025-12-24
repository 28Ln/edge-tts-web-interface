# 计费系统设计文档

## Overview

本设计实现一个完整的计费系统，支持套餐订阅、按量计费、余额管理、账单记录等功能。

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      API Layer                          │
│  /auth/*  /billing/*  /admin/*  /v2/mcu/*              │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                   Service Layer                         │
│  AuthService  BillingService  SubscriptionService      │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                  Repository Layer                       │
│  UserRepo  PlanRepo  SubscriptionRepo  TransactionRepo │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                    Database                             │
│  users  plans  subscriptions  transactions  usage      │
└─────────────────────────────────────────────────────────┘
```

## Data Models

### Plan (套餐)
```sql
CREATE TABLE plans (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,        -- free, basic, pro, enterprise
    display_name TEXT NOT NULL,       -- 免费版, 基础版, 专业版, 企业版
    description TEXT,
    monthly_price DECIMAL(10,2) DEFAULT 0,
    
    -- 配额限制
    daily_requests INTEGER DEFAULT 100,
    daily_tokens INTEGER DEFAULT 10000,
    daily_audio_seconds INTEGER DEFAULT 60,
    
    -- 按量计费价格 (元)
    price_per_request DECIMAL(10,4) DEFAULT 0,
    price_per_1k_tokens DECIMAL(10,4) DEFAULT 0,
    price_per_minute_audio DECIMAL(10,4) DEFAULT 0,
    
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### User (扩展)
```sql
ALTER TABLE users ADD COLUMN balance DECIMAL(10,2) DEFAULT 0;
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT 0;
ALTER TABLE users ADD COLUMN password_hash TEXT;
```

### Subscription (订阅)
```sql
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    plan_id INTEGER NOT NULL,
    status TEXT DEFAULT 'active',     -- active, expired, cancelled
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    auto_renew BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (plan_id) REFERENCES plans(id)
);
```

### Transaction (交易记录)
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL,               -- recharge, consume, refund, subscribe
    amount DECIMAL(10,2) NOT NULL,
    balance_after DECIMAL(10,2),
    description TEXT,
    reference_id TEXT,                -- 外部订单号
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Admin (管理员)
```sql
CREATE TABLE admins (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    api_key TEXT UNIQUE,
    is_super BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Components and Interfaces

### BillingService
```python
class BillingService:
    def get_plans() -> List[Plan]
    def get_user_subscription(user_id) -> Subscription
    def subscribe(user_id, plan_id, months=1) -> Subscription
    def cancel_subscription(user_id) -> bool
    def check_and_deduct(user_id, usage_type, amount) -> bool
    def recharge(user_id, amount, reference_id) -> Transaction
    def get_transactions(user_id, page, limit) -> List[Transaction]
    def get_invoice(user_id, month) -> Invoice
```

### AuthService
```python
class AuthService:
    def register(username, email, password) -> User
    def login(email, password) -> (User, Token)
    def verify_email(token) -> bool
    def reset_password(email) -> bool
    def change_password(user_id, old_pwd, new_pwd) -> bool
```

### AdminAuthService
```python
class AdminAuthService:
    def verify_admin_key(api_key) -> Admin
    def create_admin(username, password) -> Admin
    def generate_admin_key(admin_id) -> str
```

## API Endpoints

### Auth API
```
POST /auth/register     - 用户注册
POST /auth/login        - 用户登录
POST /auth/verify-email - 邮箱验证
POST /auth/forgot-password - 忘记密码
POST /auth/reset-password  - 重置密码
```

### Billing API
```
GET  /billing/plans           - 获取套餐列表
GET  /billing/subscription    - 获取当前订阅
POST /billing/subscribe       - 订阅套餐
POST /billing/cancel          - 取消订阅
GET  /billing/balance         - 获取余额
POST /billing/recharge        - 充值
GET  /billing/transactions    - 交易记录
GET  /billing/invoice/{month} - 月度账单
```

### Admin API (需认证)
```
# 需要 X-Admin-Key header
GET  /admin/stats             - 系统统计
GET  /admin/users             - 用户列表
POST /admin/users             - 创建用户
PUT  /admin/users/{id}        - 更新用户
GET  /admin/plans             - 套餐列表
POST /admin/plans             - 创建套餐
PUT  /admin/plans/{id}        - 更新套餐
```

## Default Plans

| 套餐 | 月费 | 日请求 | 日Token | 日音频 |
|------|------|--------|---------|--------|
| free | ¥0 | 100 | 10,000 | 1分钟 |
| basic | ¥29 | 1,000 | 100,000 | 10分钟 |
| pro | ¥99 | 10,000 | 1,000,000 | 60分钟 |
| enterprise | ¥299 | 100,000 | 10,000,000 | 600分钟 |

## Pay-as-you-go Pricing

| 类型 | 价格 |
|------|------|
| 每次请求 | ¥0.001 |
| 每1000 Token | ¥0.01 |
| 每分钟音频 | ¥0.1 |

## Quota Check Flow

```
请求 → API Key验证 → 获取用户订阅 → 检查配额
                                    ↓
                              配额充足? 
                              ↓      ↓
                             是      否
                              ↓      ↓
                          处理请求  检查余额
                              ↓      ↓
                          记录用量  余额充足?
                                    ↓      ↓
                                   是      否
                                    ↓      ↓
                                扣除余额  拒绝请求
                                    ↓
                                处理请求
```

## Error Handling

| 错误码 | HTTP | 说明 |
|--------|------|------|
| QUOTA_EXCEEDED | 429 | 配额超限 |
| INSUFFICIENT_BALANCE | 402 | 余额不足 |
| SUBSCRIPTION_EXPIRED | 403 | 订阅已过期 |
| PLAN_NOT_FOUND | 404 | 套餐不存在 |
| ADMIN_AUTH_REQUIRED | 401 | 需要管理员认证 |

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. 
Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Plan CRUD Round-Trip
*For any* valid plan data (name, description, price, quota limits), creating a plan and then retrieving it should return the same data unchanged.
**Validates: Requirements 1.1, 1.3**

### Property 2: Plan Enable/Disable Preserves Data
*For any* plan, disabling and then re-enabling it should preserve all plan data (name, price, quotas) unchanged.
**Validates: Requirements 1.4**

### Property 3: Subscription Creates Valid Record
*For any* user and valid plan, subscribing should create a subscription record with correct start_date, end_date, and plan association.
**Validates: Requirements 2.1**

### Property 4: Expired Subscription Downgrades to Free
*For any* user with an expired subscription, checking their subscription status should return the free plan.
**Validates: Requirements 2.2**

### Property 5: Quota Uses Active Subscription Limits
*For any* user with an active subscription, quota checks should use that subscription's plan limits, not default limits.
**Validates: Requirements 2.4**

### Property 6: Daily Usage Reset Preserves History
*For any* user with usage records, after daily reset, today's usage should be zero but historical records should be preserved.
**Validates: Requirements 3.1, 3.2**

### Property 7: Plan Upgrade Immediately Applies
*For any* user upgrading from a lower plan to a higher plan, the new quota limits should be immediately available.
**Validates: Requirements 3.3**

### Property 8: Balance Operations Consistency
*For any* sequence of recharge and deduction operations, the final balance should equal initial balance plus sum of all operations, and each operation should create a transaction record.
**Validates: Requirements 4.1, 4.2, 4.3, 5.1**

### Property 9: Insufficient Balance Rejects Request
*For any* user with balance less than required amount, attempting to deduct should fail with INSUFFICIENT_BALANCE error and balance should remain unchanged.
**Validates: Requirements 4.4**

### Property 10: Transaction Pagination Correctness
*For any* user with N transactions, paginating through all pages should return exactly N unique transactions in chronological order.
**Validates: Requirements 5.3**

### Property 11: Admin Endpoints Require Authentication
*For any* admin endpoint, requests without valid admin authentication should return 401 Unauthorized.
**Validates: Requirements 6.1**

### Property 12: New User Gets Free Plan and API Key
*For any* successful user registration, the user should have a free plan subscription and at least one valid API key.
**Validates: Requirements 7.2, 7.4**

### Property 13: Cost Calculation Uses Current Pricing
*For any* API usage, the calculated cost should match the current plan's pricing rates multiplied by usage amount.
**Validates: Requirements 8.3**

## Error Handling

| 错误码 | HTTP | 说明 |
|--------|------|------|
| QUOTA_EXCEEDED | 429 | 配额超限 |
| INSUFFICIENT_BALANCE | 402 | 余额不足 |
| SUBSCRIPTION_EXPIRED | 403 | 订阅已过期 |
| PLAN_NOT_FOUND | 404 | 套餐不存在 |
| ADMIN_AUTH_REQUIRED | 401 | 需要管理员认证 |

## Testing Strategy

### Unit Tests
- Plan CRUD operations
- Subscription lifecycle
- Balance operations
- Quota calculations

### Integration Tests
- Registration flow
- Subscription flow
- Billing flow
- Admin operations

### Property-Based Testing
- Use `hypothesis` library for Python property-based testing
- Configure minimum 100 iterations per property test
- Each property test must reference the correctness property it implements using format: `**Feature: billing-system, Property {number}: {property_text}**`
