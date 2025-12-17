# 项目问题清单 (50项)

> 为大型项目做准备，全面梳理目录结构、代码架构、命名规范等问题
> 更新时间: 2024-12-17

---

## 一、目录结构问题 (10项)

| # | 问题 | 当前状态 | 建议 | 优先级 | 状态 |
|---|------|----------|------|--------|------|
| 1 | **uploads/tts 临时目录在根目录** | `uploads/`, `tts/` 在根目录 | 移动到 `data/uploads/`, `data/tts/` | P1 | ⏳ 待处理 |
| 2 | **ffmpeg 二进制文件在项目中** | `ffmpeg/` 包含 Windows 二进制 | 通过 Docker 或系统安装，不纳入版本控制 | P2 | ⏳ 待处理 |
| 3 | **static 目录结构混乱** | `static/css/`, `static/js/`, `static/img/` | 考虑使用 `static/assets/` 统一管理 | P3 | ⏳ 待处理 |
| 4 | **templates 目录层级不清晰** | `templates/index.html` 和 `templates/dashboard/` 混合 | 按功能分组: `templates/web/`, `templates/dashboard/` | P2 | ⏳ 待处理 |
| 5 | **examples 缺少统一 README** | 每个示例目录无说明 | 每个示例添加独立 README.md | P2 | ⏳ 待处理 |
| 6 | **docs/api 文档分散** | 多个 API 文档文件 | 统一格式，添加版本说明 | P2 | ⏳ 待处理 |
| 7 | **缺少 logs 目录** | 日志输出到控制台 | 添加 `logs/` 目录，配置文件日志 | P2 | ⏳ 待处理 |
| 8 | **data 目录结构不完整** | 只有 `data/auth.db` | 添加 `data/uploads/`, `data/tts/`, `data/cache/` | P1 | ⏳ 待处理 |
| 9 | **scripts 目录不完整** | 只有测试脚本 | 添加 `setup.sh`, `deploy.sh`, `backup.sh` | P2 | ⏳ 待处理 |
| 10 | **缺少 migrations 目录** | 数据库无迁移管理 | 添加 `migrations/` 用于数据库版本控制 | P2 | ⏳ 待处理 |

---

## 二、文件命名问题 (5项)

| # | 问题 | 当前状态 | 建议 | 优先级 | 状态 |
|---|------|----------|------|--------|------|
| 11 | **双入口文件** | `app.py` 转发到 `src/main.py` | 删除 `app.py`，统一使用 `src/main.py` | P1 | ⏳ 待处理 |
| 12 | **README 多语言文件** | `README.md`, `README.en.md` 在根目录 | 移动到 `docs/README.zh.md`, `docs/README.en.md` | P3 | ⏳ 待处理 |
| 13 | **测试文件命名不一致** | `test_api_mcu.py` vs `test_admin_api.py` | 统一为 `test_<module>_<feature>.py` | P2 | ⏳ 待处理 |
| 14 | **服务文件命名不一致** | `ai_service.py`, `asr_service.py` vs `session_store.py` | 统一为 `<name>_service.py` 或 `<name>.py` | P2 | ⏳ 待处理 |
| 15 | **配置文件命名** | `.env.example` | 考虑添加 `.env.development`, `.env.production` 示例 | P3 | ⏳ 待处理 |

---

## 三、代码架构问题 (10项)

| # | 问题 | 当前状态 | 建议 | 优先级 | 状态 |
|---|------|----------|------|--------|------|
| 16 | **v1 API 未放入 v1 目录** | `src/api/mcu.py` 是 v1 | 移动到 `src/api/v1/mcu.py` | P1 | ⏳ 待处理 |
| 17 | **Dashboard 路由过长** | `dashboard.py` 超过 300 行 | 拆分为 `dashboard/routes.py`, `dashboard/views.py` | P2 | ⏳ 待处理 |
| 18 | **缺少依赖注入** | 服务通过 `get_xxx_service()` 获取 | 考虑使用 Flask-Injector 或自定义容器 | P3 | ⏳ 待处理 |
| 19 | **WebSocket 代码过长** | `websocket.py` 超过 200 行 | 拆分 SocketIO 和原生 WebSocket | P2 | ⏳ 待处理 |
| 20 | **缺少 Repository 层** | 直接在路由中操作数据库 | 添加 `src/repositories/` 数据访问层 | P2 | ⏳ 待处理 |
| 21 | **服务层缺少接口定义** | 只有 ASREngine 有抽象基类 | 为 AIService, TTSService 添加接口 | P2 | ⏳ 待处理 |
| 22 | **缺少事件系统** | 无 | 添加事件总线用于模块解耦 | P3 | ⏳ 待处理 |
| 23 | **缺少缓存层** | 无 | 添加 Redis 缓存支持 | P2 | ⏳ 待处理 |
| 24 | **配置类过于复杂** | `config.py` 超过 150 行 | 拆分为多个配置类 | P2 | ⏳ 待处理 |
| 25 | **全局状态管理** | 使用模块级全局变量 | 考虑使用 Flask 应用上下文 | P2 | ⏳ 待处理 |

---

## 四、日志架构问题 (5项)

| # | 问题 | 当前状态 | 建议 | 优先级 | 状态 |
|---|------|----------|------|--------|------|
| 26 | **日志级别使用不当** | 部分 INFO 应该是 DEBUG | 审查所有日志级别 | P2 | ⏳ 待处理 |
| 27 | **缺少结构化日志** | 文本格式日志 | 生产环境使用 JSON 格式 | P2 | ⏳ 待处理 |
| 28 | **缺少审计日志** | 无 | 添加用户操作审计日志表 | P2 | ⏳ 待处理 |
| 29 | **日志轮转未配置** | 无 | 添加日志轮转配置 | P2 | ⏳ 待处理 |
| 30 | **敏感信息过滤不完整** | 只过滤 API Key | 添加更多敏感字段过滤 | P1 | ⏳ 待处理 |

---

## 五、异常架构问题 (5项)

| # | 问题 | 当前状态 | 建议 | 优先级 | 状态 |
|---|------|----------|------|--------|------|
| 31 | **错误码不够细分** | 只有通用错误码 | 添加业务细分错误码 (如 ASR_ENGINE_UNAVAILABLE) | P2 | ⏳ 待处理 |
| 32 | **缺少错误码文档** | 无 | 添加 `docs/error_codes.md` | P2 | ⏳ 待处理 |
| 33 | **异常链丢失** | 部分异常未保留原始异常 | 使用 `raise ... from e` | P1 | ⏳ 待处理 |
| 34 | **缺少异常监控集成** | 无 | 集成 Sentry 或类似服务 | P3 | ⏳ 待处理 |
| 35 | **HTTP 状态码使用不一致** | 部分错误返回 500 应该是 400 | 审查所有错误响应状态码 | P1 | ⏳ 待处理 |

---

## 六、代码质量问题 (10项)

| # | 问题 | 当前状态 | 建议 | 优先级 | 状态 |
|---|------|----------|------|--------|------|
| 36 | **类型注解不完整** | 约 60% 函数有类型注解 | 添加完整类型注解，配置 mypy | P1 | ⏳ 待处理 |
| 37 | **文档字符串不完整** | 部分函数缺少 docstring | 补充所有公开函数文档 | P2 | ⏳ 待处理 |
| 38 | **魔法数字** | `16000`, `4000`, `600` 等硬编码 | 提取为常量或配置 | P2 | ⏳ 待处理 |
| 39 | **函数过长** | 部分函数超过 50 行 | 拆分为小函数 | P1 | ⏳ 待处理 |
| 40 | **重复代码** | 音频转换逻辑重复 | 提取到 `src/utils/audio.py` | P1 | ⏳ 待处理 |
| 41 | **缺少代码格式化配置** | 无 | 添加 `pyproject.toml` 中 black/ruff 配置 | P1 | ⏳ 待处理 |
| 42 | **缺少 lint 检查** | 无 | 添加 flake8/ruff lint 配置 | P1 | ⏳ 待处理 |
| 43 | **测试覆盖率** | 约 53% | 提高到 70%+ | P1 | ⏳ 待处理 |
| 44 | **缺少性能测试** | 无 | 添加 locust 压测脚本 | P3 | ⏳ 待处理 |
| 45 | **缺少安全扫描** | 无 | 添加 bandit 安全检查 | P2 | ⏳ 待处理 |

---

## 七、兼容性问题 (5项)

| # | 问题 | 当前状态 | 建议 | 优先级 | 状态 |
|---|------|----------|------|--------|------|
| 46 | **v1/v2 API 并存无迁移计划** | 两套 API 同时运行 | 制定 v1 废弃时间表，添加废弃警告 | P1 | ⏳ 待处理 |
| 47 | **环境变量兼容** | `GEMINI_*` 和 `AI_*` 并存 | 文档说明迁移，设置废弃警告 | P2 | ⏳ 待处理 |
| 48 | **Python 版本未指定** | 未指定最低版本 | 在 `pyproject.toml` 指定 `>=3.10` | P1 | ⏳ 待处理 |
| 49 | **依赖版本过于宽松** | `requirements.txt` 无版本锁定 | 使用 `poetry.lock` 或 `pip-tools` | P1 | ⏳ 待处理 |
| 50 | **缺少 API 版本头** | 无 | 添加 `X-API-Version` 响应头 | P2 | ⏳ 待处理 |

---

## 优先级说明

- **P0 (紧急)**: 影响功能或有安全风险，立即处理
- **P1 (高)**: 影响代码质量和可维护性，1 周内完成
- **P2 (中)**: 改进项，1 个月内完成
- **P3 (低)**: 优化项，按需完成

---

## 统计

| 优先级 | 数量 | 完成 | 待处理 |
|--------|------|------|--------|
| P0 | 0 | 0 | 0 |
| P1 | 15 | 0 | 15 |
| P2 | 27 | 0 | 27 |
| P3 | 8 | 0 | 8 |
| **总计** | **50** | **0** | **50** |

---

## 建议的目标目录结构

```
edge-tts-web-interface/
├── src/                          # 核心源码
│   ├── __init__.py
│   ├── main.py                   # 主入口
│   ├── config.py                 # 配置管理
│   ├── api/                      # API 路由
│   │   ├── __init__.py
│   │   ├── v1/                   # v1 API
│   │   │   ├── __init__.py
│   │   │   ├── mcu.py
│   │   │   └── wechat.py
│   │   ├── v2/                   # v2 API (带认证)
│   │   │   ├── __init__.py
│   │   │   └── mcu.py
│   │   ├── admin.py              # 管理 API
│   │   ├── health.py             # 健康检查
│   │   ├── openapi.py            # OpenAPI 文档
│   │   ├── websocket.py          # WebSocket
│   │   └── dashboard/            # Dashboard 模块
│   │       ├── __init__.py
│   │       ├── routes.py
│   │       └── views.py
│   ├── services/                 # 业务服务层
│   │   ├── __init__.py
│   │   ├── ai_service.py
│   │   ├── asr_service.py
│   │   ├── tts_service.py
│   │   ├── session_store.py
│   │   └── asr/                  # ASR 引擎
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── vosk.py
│   │       └── tencent.py
│   ├── auth/                     # 认证模块
│   │   ├── __init__.py
│   │   ├── api_key.py
│   │   ├── models.py
│   │   └── quota.py
│   ├── models/                   # 数据模型
│   │   ├── __init__.py
│   │   └── schemas.py
│   ├── repositories/             # 数据访问层 (NEW)
│   │   ├── __init__.py
│   │   ├── user_repo.py
│   │   └── usage_repo.py
│   ├── utils/                    # 工具函数
│   │   ├── __init__.py
│   │   ├── audio.py              # 音频处理 (NEW)
│   │   ├── cleanup.py
│   │   ├── logger.py
│   │   ├── middleware.py
│   │   └── retry.py
│   └── exceptions/               # 自定义异常
│       ├── __init__.py
│       └── errors.py
├── tests/                        # 测试代码
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/                         # 文档
│   ├── README.md
│   ├── api/
│   │   ├── v1.md
│   │   ├── v2.md
│   │   └── error_codes.md
│   ├── deployment.md
│   └── development.md
├── examples/                     # 示例代码
│   ├── README.md
│   ├── android/
│   ├── python/
│   └── esp32/
├── scripts/                      # 脚本
│   ├── setup.sh
│   ├── deploy.sh
│   ├── backup.sh
│   └── test.sh
├── data/                         # 数据目录 (gitignore)
│   ├── auth.db
│   ├── uploads/
│   ├── tts/
│   ├── cache/
│   └── logs/
├── static/                       # 静态文件
│   └── assets/
├── templates/                    # 模板文件
│   ├── web/
│   └── dashboard/
├── docker/                       # Docker 配置
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.prod.yml
├── migrations/                   # 数据库迁移 (NEW)
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## 下一步行动计划

### 第一阶段 (P1 - 本周)
1. [ ] 整理目录结构：移动 `uploads/`, `tts/` 到 `data/`
2. [ ] 删除 `app.py`，统一入口
3. [ ] 移动 v1 API 到 `src/api/v1/`
4. [ ] 添加代码格式化配置 (black/ruff)
5. [ ] 提高测试覆盖率到 70%

### 第二阶段 (P2 - 本月)
1. [ ] 拆分过长的模块
2. [ ] 添加 Repository 层
3. [ ] 完善类型注解
4. [ ] 添加审计日志
5. [ ] 添加安全扫描

### 第三阶段 (P3 - 长期)
1. [ ] 添加依赖注入
2. [ ] 添加事件系统
3. [ ] 添加缓存层
4. [ ] 添加性能测试
5. [ ] 集成异常监控
