# Requirements Document

## Introduction

本文档定义了将 Edge TTS Web Interface 从开发阶段提升到生产就绪状态所需的改进。主要涵盖安全加固、测试修复、性能优化和运维支持等方面。

## Glossary

- **SECRET_KEY**: Flask 应用的会话加密密钥
- **ADMIN_PASSWORD**: 管理员默认密码
- **Rate Limiting**: 请求频率限制，防止滥用
- **Prometheus**: 开源监控系统
- **Gunicorn**: Python WSGI HTTP 服务器

## Requirements

### Requirement 1: 安全配置加固

**User Story:** As a system administrator, I want secure default configurations, so that the system is protected from common security vulnerabilities.

#### Acceptance Criteria

1. WHEN the application starts without SECRET_KEY environment variable THEN the system SHALL generate a random secure key and log a warning
2. WHEN the application starts with default ADMIN_PASSWORD THEN the system SHALL log a security warning recommending password change
3. WHEN sensitive configuration values are logged THEN the system SHALL mask the values to prevent credential exposure
4. IF a weak SECRET_KEY (less than 32 characters) is provided THEN the system SHALL reject it and raise a configuration error

### Requirement 2: 测试用例修复

**User Story:** As a developer, I want all tests to pass correctly, so that I can trust the test suite for regression detection.

#### Acceptance Criteria

1. WHEN test_voice_chat_no_recognition runs THEN the system SHALL expect HTTP 200 with fallback message for empty ASR result
2. WHEN test_stt_empty_audio runs THEN the system SHALL expect HTTP 200 with empty text for WeChat STT graceful degradation
3. WHEN test_ask_success runs THEN the system SHALL correctly mock AI service to be called once

### Requirement 3: IP 级别请求限流

**User Story:** As a system administrator, I want IP-based rate limiting, so that the system is protected from abuse and DDoS attacks.

#### Acceptance Criteria

1. WHEN a single IP exceeds 100 requests per minute THEN the system SHALL return HTTP 429 with retry-after header
2. WHEN rate limit is exceeded THEN the system SHALL log the blocked IP and request count
3. WHERE rate limiting is enabled THEN the system SHALL allow configuration of limits via environment variables
4. WHEN rate limit resets THEN the system SHALL allow the IP to make requests again

### Requirement 4: Prometheus 监控指标

**User Story:** As a DevOps engineer, I want Prometheus metrics endpoint, so that I can monitor system health and performance.

#### Acceptance Criteria

1. WHEN GET /metrics is called THEN the system SHALL return Prometheus-formatted metrics
2. THE metrics endpoint SHALL expose request count by endpoint and status code
3. THE metrics endpoint SHALL expose request latency histograms
4. THE metrics endpoint SHALL expose active connection count
5. THE metrics endpoint SHALL expose ASR/TTS/AI service availability status

### Requirement 5: 生产部署配置

**User Story:** As a DevOps engineer, I want production deployment configurations, so that I can deploy the system reliably.

#### Acceptance Criteria

1. THE system SHALL provide a production-ready Gunicorn configuration file
2. THE system SHALL provide an updated .env.example with all required production variables
3. THE system SHALL provide Nginx configuration template for reverse proxy
4. WHEN health check fails 3 consecutive times THEN the system SHALL be marked as unhealthy for load balancer

### Requirement 6: 数据库连接优化

**User Story:** As a developer, I want optimized database connections, so that the system can handle concurrent requests efficiently.

#### Acceptance Criteria

1. THE system SHALL use connection pooling for SQLite with configurable pool size
2. WHEN database connection fails THEN the system SHALL retry with exponential backoff
3. THE system SHALL implement proper connection cleanup on request completion
4. WHEN concurrent requests exceed pool size THEN the system SHALL queue requests rather than fail
