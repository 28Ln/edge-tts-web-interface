# 计费系统需求文档

## Introduction

本文档定义了 Edge TTS Web Interface 的计费系统需求，包括套餐管理、用户订阅、配额控制、支付集成等功能。

## Glossary

- **Plan (套餐)**: 预定义的服务等级，包含配额限制和价格
- **Subscription (订阅)**: 用户购买的套餐实例
- **Quota (配额)**: 用户可使用的资源限制
- **Usage (用量)**: 用户实际消耗的资源
- **Balance (余额)**: 用户账户余额（按量计费模式）
- **Invoice (账单)**: 用户的消费记录

---

## Requirements

### Requirement 1: 套餐管理

**User Story:** As a 系统管理员, I want to 定义和管理服务套餐, so that 用户可以选择适合的服务等级。

#### Acceptance Criteria

1. THE System SHALL support creating plans with name, description, price, and quota limits
2. THE System SHALL support four plan types: free, basic, pro, enterprise
3. WHEN a plan is created THEN THE System SHALL store monthly_price, daily_requests, daily_tokens, daily_audio_seconds
4. THE System SHALL support enabling/disabling plans without deleting them

### Requirement 2: 用户订阅

**User Story:** As a 用户, I want to 订阅服务套餐, so that 我可以获得相应的配额。

#### Acceptance Criteria

1. WHEN a user subscribes to a plan THEN THE System SHALL create a subscription record with start_date and end_date
2. WHEN a subscription expires THEN THE System SHALL downgrade user to free plan
3. THE System SHALL support subscription status: active, expired, cancelled
4. WHEN checking quota THEN THE System SHALL use the user's active subscription plan limits

### Requirement 3: 配额重置

**User Story:** As a 用户, I want to 每日自动重置配额, so that 我可以持续使用服务。

#### Acceptance Criteria

1. WHEN a new day starts (00:00 UTC+8) THEN THE System SHALL reset daily usage counters
2. THE System SHALL maintain usage history for billing and analytics
3. WHEN user upgrades plan mid-cycle THEN THE System SHALL immediately apply new quota limits

### Requirement 4: 余额系统

**User Story:** As a 用户, I want to 充值账户余额, so that 我可以按量付费使用服务。

#### Acceptance Criteria

1. THE System SHALL support user balance for pay-as-you-go billing
2. WHEN user makes a payment THEN THE System SHALL increase user balance
3. WHEN user uses API THEN THE System SHALL deduct from balance based on usage
4. IF balance is insufficient THEN THE System SHALL reject the request with INSUFFICIENT_BALANCE error

### Requirement 5: 账单记录

**User Story:** As a 用户, I want to 查看消费记录, so that 我可以了解我的使用情况。

#### Acceptance Criteria

1. THE System SHALL record all transactions (recharge, consumption, refund)
2. THE System SHALL generate monthly invoices for subscribed users
3. WHEN user queries billing THEN THE System SHALL return transaction history with pagination

### Requirement 6: Admin API 保护

**User Story:** As a 系统管理员, I want to Admin API 需要认证, so that 防止未授权访问。

#### Acceptance Criteria

1. THE System SHALL require admin authentication for /admin/* endpoints
2. THE System SHALL support admin API key separate from user API key
3. WHEN admin authentication fails THEN THE System SHALL return 401 Unauthorized

### Requirement 7: 用户自助注册

**User Story:** As a 新用户, I want to 自助注册账号, so that 我可以开始使用服务。

#### Acceptance Criteria

1. THE System SHALL provide /auth/register endpoint for user registration
2. WHEN user registers THEN THE System SHALL create account with free plan
3. THE System SHALL require email verification before activating account
4. THE System SHALL generate initial API key upon successful registration

### Requirement 8: 价格配置

**User Story:** As a 系统管理员, I want to 配置服务价格, so that 可以灵活调整计费策略。

#### Acceptance Criteria

1. THE System SHALL support configurable pricing per API call type
2. THE System SHALL support pricing: per_request, per_1k_tokens, per_minute_audio
3. WHEN calculating cost THEN THE System SHALL use the pricing at time of request
