# 计费系统实现任务列表

## Implementation Plan

- [x] 1. 完善数据库模型和迁移

  - [x] 1.1 创建完整的数据库迁移脚本



    - 确保 plans, subscriptions, transactions, admins 表结构完整
    - 添加必要的索引
    - _Requirements: 1.1, 1.3, 2.1, 5.1_
  - [x] 1.2 完善 BillingDatabase 类


    - 添加缺失的 CRUD 方法
    - 确保事务安全
    - _Requirements: 1.1, 1.4_
  - [x] 1.3 编写 Property Test: Plan CRUD Round-Trip


    - **Property 1: Plan CRUD Round-Trip**
    - **Validates: Requirements 1.1, 1.3**
  - [x] 1.4 编写 Property Test: Plan Enable/Disable

    - **Property 2: Plan Enable/Disable Preserves Data**
    - **Validates: Requirements 1.4**

- [x] 2. 实现订阅管理功能

  - [x] 2.1 完善 SubscriptionService


    - 实现订阅创建、取消、过期检查
    - 实现自动降级到免费套餐
    - _Requirements: 2.1, 2.2, 2.3_
  - [x] 2.2 实现订阅过期检查定时任务


    - 检查并更新过期订阅状态
    - _Requirements: 2.2_
  - [x] 2.3 编写 Property Test: Subscription Creates Valid Record


    - **Property 3: Subscription Creates Valid Record**
    - **Validates: Requirements 2.1**
  - [x] 2.4 编写 Property Test: Expired Subscription Downgrades

    - **Property 4: Expired Subscription Downgrades to Free**
    - **Validates: Requirements 2.2**

- [x] 3. 实现配额管理功能


  - [x] 3.1 完善 QuotaService

    - 实现配额检查逻辑
    - 集成到 API 请求流程
    - _Requirements: 2.4, 3.3_
  - [x] 3.2 实现每日配额重置


    - 创建定时任务重置每日用量
    - 保留历史记录
    - _Requirements: 3.1, 3.2_
  - [x] 3.3 编写 Property Test: Quota Uses Subscription Limits


    - **Property 5: Quota Uses Active Subscription Limits**
    - **Validates: Requirements 2.4**

  - [x] 3.4 编写 Property Test: Daily Reset Preserves History

    - **Property 6: Daily Usage Reset Preserves History**
    - **Validates: Requirements 3.1, 3.2**
  - [x] 3.5 编写 Property Test: Plan Upgrade Immediately Applies

    - **Property 7: Plan Upgrade Immediately Applies**
    - **Validates: Requirements 3.3**

- [x] 4. Checkpoint - 确保所有测试通过



  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. 实现余额和交易系统

  - [x] 5.1 完善余额管理功能


    - 实现充值、扣款、查询
    - 确保余额不会变为负数
    - _Requirements: 4.1, 4.2, 4.3_
  - [x] 5.2 完善交易记录功能


    - 记录所有交易类型
    - 实现分页查询
    - _Requirements: 5.1, 5.3_
  - [x] 5.3 编写 Property Test: Balance Operations Consistency


    - **Property 8: Balance Operations Consistency**
    - **Validates: Requirements 4.1, 4.2, 4.3, 5.1**

  - [x] 5.4 编写 Property Test: Insufficient Balance Rejects

    - **Property 9: Insufficient Balance Rejects Request**

    - **Validates: Requirements 4.4**

  - [x] 5.5 编写 Property Test: Transaction Pagination
    - **Property 10: Transaction Pagination Correctness**
    - **Validates: Requirements 5.3**


- [x] 6. 实现 Admin API 认证
  - [x] 6.1 创建 AdminAuthService

    - 实现 Admin API Key 验证
    - 与用户 API Key 分离
    - _Requirements: 6.1, 6.2_


  - [x] 6.2 添加 Admin 认证装饰器
    - 保护 /admin/* 端点
    - 返回正确的错误码
    - _Requirements: 6.1, 6.3_
  - [x] 6.3 编写 Property Test: Admin Authentication


    - **Property 11: Admin Endpoints Require Authentication**
    - **Validates: Requirements 6.1**

- [x] 7. 实现用户自助注册
  - [x] 7.1 创建 AuthService


    - 实现用户注册、登录
    - 密码哈希存储
    - _Requirements: 7.1, 7.2_
  - [x] 7.2 实现注册 API 端点


    - POST /auth/register
    - 自动分配免费套餐和 API Key
    - _Requirements: 7.1, 7.2, 7.4_

  - [x] 7.3 实现登录 API 端点
    - POST /auth/login
    - 返回 JWT Token
    - _Requirements: 7.1_
  - [x] 7.4 编写 Property Test: New User Gets Free Plan


    - **Property 12: New User Gets Free Plan and API Key**
    - **Validates: Requirements 7.2, 7.4**

- [x] 8. Checkpoint - 确保所有测试通过


  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. 实现计费计算

  - [x] 9.1 完善成本计算逻辑


    - 按请求、Token、音频时长计费
    - 使用当前套餐定价
    - _Requirements: 8.1, 8.2, 8.3_
  - [x] 9.2 集成计费到 API 请求流程


    - 配额用完后按量计费
    - 自动扣除余额
    - _Requirements: 4.3, 8.3_
  - [x] 9.3 编写 Property Test: Cost Calculation


    - **Property 13: Cost Calculation Uses Current Pricing**
    - **Validates: Requirements 8.3**

- [x] 10. 完善 Billing API 端点

  - [x] 10.1 完善套餐查询 API


    - GET /billing/plans
    - GET /billing/plans/{id}
    - _Requirements: 1.1, 1.2_

  - [x] 10.2 完善订阅管理 API
    - GET /billing/subscription
    - POST /billing/subscribe
    - POST /billing/cancel

    - _Requirements: 2.1, 2.3_
  - [x] 10.3 完善余额和交易 API
    - GET /billing/balance
    - POST /billing/recharge
    - GET /billing/transactions
    - _Requirements: 4.1, 4.2, 5.3_

- [x] 11. 完善 Admin API 端点

  - [x] 11.1 实现套餐管理 Admin API

    - POST /admin/plans
    - PUT /admin/plans/{id}
    - _Requirements: 1.1, 1.4_

  - [x] 11.2 实现用户管理 Admin API
    - GET /admin/users
    - POST /admin/users
    - PUT /admin/users/{id}
    - _Requirements: 6.1_

- [x] 12. Final Checkpoint - 确保所有测试通过



  - Ensure all tests pass, ask the user if questions arise.
