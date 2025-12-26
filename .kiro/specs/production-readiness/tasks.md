# Implementation Plan

## Phase 1: 测试修复与安全加固

- [x] 1. 修复失败的测试用例

  - [x] 1.1 修复 test_voice_chat_no_recognition 测试


    - 更新测试期望值：空 ASR 结果应返回 HTTP 200 + 友好提示




    - _Requirements: 2.1_



  - [x] 1.2 修复 test_stt_empty_audio 测试

    - 更新测试期望值：微信 STT 空音频应返回 HTTP 200 + 空文本
    - _Requirements: 2.2_
  - [x] 1.3 修复 test_ask_success 测试
    - 修复 Mock 配置，确保 AI 服务只被调用一次

    - _Requirements: 2.3_


- [ ] 2. 实现安全配置验证
  - [x] 2.1 创建 SecurityConfig 类

    - 在 src/config.py 中添加安全配置验证逻辑

    - 实现 SECRET_KEY 生成和验证
    - 实现 ADMIN_PASSWORD 安全检查
    - _Requirements: 1.1, 1.2, 1.4_
  - [x] 2.2 编写属性测试：SECRET_KEY 长度验证




    - **Property 2: SECRET_KEY 长度验证**
    - **Validates: Requirements 1.4**
  - [x] 2.3 更新敏感信息日志过滤器


    - 增强 SensitiveFilter 覆盖更多敏感字段

    - _Requirements: 1.3_
  - [x] 2.4 编写属性测试：敏感信息掩码


    - **Property 1: 敏感信息掩码**
    - **Validates: Requirements 1.3**


- [x] 3. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## Phase 2: IP 限流中间件

- [x] 4. 实现 IP 限流功能
  - [x] 4.1 创建 RateLimiter 类
    - 创建 src/utils/rate_limiter.py
    - 实现滑动窗口算法
    - 支持环境变量配置限流阈值
    - _Requirements: 3.1, 3.3_
  - [x] 4.2 编写属性测试：限流阈值执行
    - **Property 3: 限流阈值执行**
    - **Validates: Requirements 3.1**
  - [x] 4.3 编写属性测试：限流窗口重置
    - **Property 4: 限流窗口重置**
    - **Validates: Requirements 3.4**
  - [x] 4.4 集成限流中间件到 Flask
    - 在 src/utils/middleware.py 中注册限流中间件
    - 添加 429 响应和 Retry-After 头
    - _Requirements: 3.1, 3.2_

- [x] 5. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## Phase 3: Prometheus 监控

- [x] 6. 实现 Prometheus 指标收集
  - [x] 6.1 创建 MetricsCollector 类
    - 创建 src/utils/metrics.py
    - 定义 request_count Counter
    - 定义 request_latency Histogram
    - 定义 active_connections Gauge
    - 定义 service_status Gauge
    - _Requirements: 4.2, 4.3, 4.4, 4.5_
  - [x] 6.2 编写属性测试：请求计数准确性
    - **Property 5: 请求计数准确性**
    - **Validates: Requirements 4.2**
  - [x] 6.3 创建 /metrics 端点
    - 在 src/api/health.py 中添加 metrics 路由
    - 返回 Prometheus 格式的指标
    - _Requirements: 4.1_
  - [x] 6.4 集成指标收集到中间件
    - 在请求前后记录指标
    - _Requirements: 4.2, 4.3_

- [x] 7. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## Phase 4: 数据库连接池

- [x] 8. 实现数据库连接池
  - [x] 8.1 创建 ConnectionPool 类
    - 创建 src/utils/db_pool.py
    - 实现连接获取和释放
    - 实现队列等待机制
    - _Requirements: 6.1, 6.4_
  - [x] 8.2 编写属性测试：连接池大小限制
    - **Property 7: 连接池大小限制**
    - **Validates: Requirements 6.1**
  - [x] 8.3 编写属性测试：连接归还一致性
    - **Property 8: 连接归还一致性**
    - **Validates: Requirements 6.3**
  - [x] 8.4 编写属性测试：连接池队列行为
    - **Property 9: 连接池队列行为**
    - **Validates: Requirements 6.4**
  - [x] 8.5 实现连接重试机制
    - 添加指数退避重试逻辑
    - _Requirements: 6.2_
  - [x] 8.6 集成连接池到现有数据库模块
    - 更新 src/auth/models.py 使用连接池
    - 更新 src/billing/models.py 使用连接池
    - _Requirements: 6.1, 6.3_

- [x] 9. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## Phase 5: 健康检查增强

- [x] 10. 增强健康检查机制
  - [x] 10.1 实现连续失败计数器
    - 跟踪健康检查连续失败次数
    - 3 次失败后标记为 unhealthy
    - _Requirements: 5.4_
  - [x] 10.2 编写属性测试：健康检查状态转换
    - **Property 6: 健康检查状态转换**
    - **Validates: Requirements 5.4**

- [x] 11. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## Phase 6: 生产部署配置

- [x] 12. 创建生产部署配置文件
  - [x] 12.1 创建 Gunicorn 配置文件
    - 创建 gunicorn.conf.py
    - 配置 workers、timeout、日志等
    - _Requirements: 5.1_
  - [x] 12.2 更新 .env.example
    - 添加所有生产环境必需的变量
    - 添加安全配置说明注释
    - _Requirements: 5.2_
  - [x] 12.3 创建 Nginx 配置模板
    - 创建 docker/nginx/nginx.prod.conf
    - 配置反向代理、SSL、限流
    - _Requirements: 5.3_

- [x] 13. Final Checkpoint - 确保所有测试通过
  - ✅ 215 个测试全部通过
