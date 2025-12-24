# 计费系统安全修复任务清单

## P0 - 立即修复 (严重安全漏洞)

- [x] 1. 修复密码哈希安全性





  - [ ] 1.1 替换SHA256为pbkdf2安全哈希
    - 修改 `src/auth/auth_service.py` 的 `_hash_password` 方法
    - 使用 `werkzeug.security.generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)`

    - 每次哈希使用随机盐值，相同密码产生不同哈希

    - _Requirements: 1.1, 1.2_
  - [x] 1.2 添加密码验证方法 `_verify_password`



    - 使用 `werkzeug.security.check_password_hash(hash, password)`
    - 返回布尔值表示密码是否匹配




    - _Requirements: 1.1_





  - [ ] 1.3 更新登录方法使用新的密码验证
    - 修改 `login` 方法，先查询用户再验证密码
    - 不再在SQL中比较password_hash
    - _Requirements: 1.1_






  - [ ] 1.4 同步更新 AdminAuthService 的密码哈希
    - 修改 `src/auth/admin_auth.py` 使用相同的安全哈希方法
    - _Requirements: 1.1, 1.2_







- [x] 2. 修复JWT安全性

  - [ ] 2.1 添加JWT密钥配置检查
    - 在 `src/auth/auth_service.py` 添加启动时检查
    - 如果使用默认密钥，记录警告日志

    - 生产环境应强制要求配置 JWT_SECRET 环境变量

    - _Requirements: 2.1, 2.3_

- [x] 3. 修复余额竞态条件 (最严重)

  - [ ] 3.1 实现原子余额更新操作
    - 修改 `src/billing/models.py` 的 `update_balance` 方法


    - 使用单条SQL原子更新: `UPDATE users SET balance = balance + ? WHERE id = ? AND balance + ? >= 0`

    - 通过 `cursor.rowcount` 判断是否成功

    - 如果 rowcount=0 且 allow_negative=False，抛出余额不足异常
    - _Requirements: 3.1, 3.2, 3.3_

- [ ] 4. 修复订阅升级原子性
  - [x] 4.1 重构 upgrade_subscription 使用单一事务

    - 修改 `src/billing/service.py` 的 `upgrade_subscription` 方法
    - 在 BillingDatabase 中添加 `atomic_upgrade_subscription` 方法
    - 所有操作（扣款、取消旧订阅、创建新订阅、记录交易）在同一个数据库连接中完成
    - 任何步骤失败自动回滚
    - _Requirements: 4.1, 4.2, 4.3_

- [ ] 5. Checkpoint - 验证P0修复
  - 运行安全测试: `py -m pytest tests/security/test_billing_security_audit.py -v -k "Password or JWT or Concurrency"`
  - 确保4个P0相关测试通过

## P1 - 尽快修复 (中等安全问题)

- [ ] 6. 修复配额类型验证
  - [ ] 6.1 添加配额类型白名单验证
    - 在 `src/billing/service.py` 顶部定义 `VALID_QUOTA_TYPES = {'requests', 'tokens', 'audio_seconds'}`
    - 修改 `check_quota` 方法，对无效类型返回 `{"allowed": False, "message": "无效的配额类型"}`
    - _Requirements: 7.1, 7.2_

- [ ] 7. 修复Admin API认证
  - [ ] 7.1 为 create_user 端点添加认证
    - 修改 `src/api/admin/routes.py`
    - 在 `create_user` 函数上添加 `@require_admin_key()` 装饰器
    - _Requirements: 8.1, 8.2_
  - [ ] 7.2 为其他用户管理端点添加认证
    - 为 `get_user` 添加 `@require_admin_key()` 装饰器
    - 为 `create_api_key` 添加 `@require_admin_key()` 装饰器
    - 为 `list_api_keys` 添加 `@require_admin_key()` 装饰器


    - 为 `revoke_api_key` 添加 `@require_admin_key()` 装饰器

    - _Requirements: 8.1, 8.3_


- [ ] 8. 修复金额计算精度
  - [x] 8.1 使用Decimal进行金额计算

    - 修改 `src/billing/service.py` 的 `calculate_cost` 方法
    - 将所有价格和数量转换为 Decimal 进行计算
    - 使用 `ROUND_HALF_UP` 舍入模式
    - 返回时转换为 float 保持API兼容
    - _Requirements: 5.1, 5.2_

- [ ] 9. Checkpoint - 验证P1修复
  - 运行安全测试: `py -m pytest tests/security/test_billing_security_audit.py -v -k "Validation or Admin"`
  - 确保P1相关测试通过

## P2 - 计划修复 (低优先级)

- [ ] 10. 添加充值金额限制
  - [ ] 10.1 添加充值金额范围验证
    - 修改 `src/billing/service.py` 的 `recharge` 方法
    - 添加最小金额限制 (如 0.01)
    - 添加最大金额限制 (如 100000)
    - _Requirements: 9.1, 9.2_

- [ ] 11. 实现支付幂等性
  - [ ] 11.1 检查 reference_id 重复
    - 修改 `src/billing/service.py` 的 `recharge` 方法
    - 如果 reference_id 已存在，返回已有交易结果而非重复充值
    - _Requirements: 10.1, 10.2_

- [ ]* 12. API Key哈希存储 (可选)
  - [ ]* 12.1 修改API Key存储为哈希
    - 修改 `src/auth/models.py`
    - 存储时只保存哈希值
    - 验证时比较哈希
    - _Requirements: 11.1, 11.2_

## 最终验证

- [ ] 13. 运行完整安全测试套件
  - [ ] 13.1 运行所有安全测试
    - `py -m pytest tests/security/test_billing_security_audit.py -v`
    - 目标: 14个测试全部通过
  - [ ] 13.2 运行属性测试确保无回归
    - `py -m pytest tests/unit/test_billing_properties.py -v`
    - 目标: 13个测试全部通过
  - [ ] 13.3 更新安全审计报告
    - 更新 `SECURITY_AUDIT_REPORT.md` 中的漏洞状态为已修复
