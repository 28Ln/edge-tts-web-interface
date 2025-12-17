# 项目问题清单 (50项)

> 为大型项目做准备，全面梳理目录结构、代码架构、命名规范等问题

---

## 一、目录结构问题 (10项)

| # | 问题 | 当前状态 | 建议 | 优先级 | 状态 |
|---|------|----------|------|--------|------|
| 1 | **根目录 API 文件冗余** | 已删除 | - | P0 | ✅ 完成 |
| 2 | **双入口文件** | `app.py` 转发到 `src/main.py` | - | P0 | ✅ 完成 |
| 3 | **tencent_asr 目录位置** | 已移动到 `src/services/asr/` | - | P1 | ✅ 完成 |
| 4 | **ffmpeg 目录** | 二进制文件在项目中 | 应通过 Docker 或系统安装 | P2 | 保留 |
| 5 | **uploads/tts 临时目录** | 在根目录 | 移动到 `data/` | P1 | 待处理 |
| 6 | **examples 目录结构** | 缺少统一的 README | 每个示例添加独立 README | P2 | 待处理 |
| 7 | **docs 目录不完整** | API 文档分散 | 统一到 `docs/api/` | P1 | 待处理 |
| 8 | **缺少 scripts 目录** | 已创建 `scripts/` | - | P2 | ✅ 完成 |
| 9 | **static 中文文件名** | 已改为 `static/test.mp3` | - | P2 | ✅ 完成 |
| 10 | **__pycache__ 未完全忽略** | 已更新 .gitignore | - | P1 | ✅ 完成 |

---

## 二、文件命名问题 (5项)

| # | 问题 | 当前状态 | 建议 | 优先级 | 状态 |
|---|------|----------|------|--------|------|
| 11 | **API 文件命名不一致** | 已统一到 `src/api/` | - | P1 | ✅ 完成 |
| 12 | **测试文件命名混乱** | 已整理到 `tests/e2e/`, `tests/unit/`, `tests/integration/` | - | P1 | ✅ 完成 |
| 13 | **配置文件命名** | 已删除 `config.example.py` | - | P2 | ✅ 完成 |
| 14 | **中文文件名** | 已改为英文 | - | P2 | ✅ 完成 |
| 15 | **README 多语言** | `README.md`, `README.en.md` | 考虑使用 `docs/` 目录组织 | P3 | 待处理 |

---

## 三、代码架构问题 (10项)

| # | 问题 | 当前状态 | 建议 | 优先级 | 状态 |
|---|------|----------|------|--------|------|
| 16 | **重复的 API 实现** | 已删除旧版 | - | P0 | ✅ 完成 |
| 17 | **重复的 AI 客户端** | 已统一使用 `AIService` | - | P0 | ✅ 完成 |
| 18 | **全局变量** | 已使用 `SessionStore` | - | P0 | ✅ 完成 |
| 19 | **硬编码配置** | 已使用 `src/config.py` | - | P0 | ✅ 完成 |
| 20 | **缺少依赖注入容器** | 服务通过 `get_xxx_service()` 获取 | 考虑使用 Flask-Injector | P3 | 待处理 |
| 21 | **WebSocket 双实现** | 已整合到 `src/api/websocket.py` | - | P2 | ✅ 完成 |
| 22 | **缺少 DTO/VO 层** | 直接返回 dict | 使用 `src/models/schemas.py` 统一 | P2 | 待处理 |
| 23 | **服务层缺少接口** | 直接实现类 | 添加抽象基类 (已有 ASREngine) | P2 | 待处理 |
| 24 | **缺少事件系统** | 无 | 考虑添加事件总线用于解耦 | P3 | 待处理 |
| 25 | **缺少缓存层** | 无 | 添加 Redis 缓存支持 | P2 | 待处理 |

---

## 四、日志架构问题 (5项)

| # | 问题 | 当前状态 | 建议 | 优先级 | 状态 |
|---|------|----------|------|--------|------|
| 26 | **日志配置不统一** | 已统一使用 `src/utils/logger.py` | - | P0 | ✅ 完成 |
| 27 | **日志格式不一致** | 已统一格式 | - | P1 | ✅ 完成 |
| 28 | **缺少请求追踪** | 已添加 request_id 中间件 | - | P1 | ✅ 完成 |
| 29 | **日志级别混乱** | 有些 INFO 应该是 DEBUG | 审查日志级别 | P2 | 待处理 |
| 30 | **缺少审计日志** | 无 | 添加用户操作审计日志 | P2 | 待处理 |

---

## 五、异常架构问题 (5项)

| # | 问题 | 当前状态 | 建议 | 优先级 | 状态 |
|---|------|----------|------|--------|------|
| 31 | **旧 API 异常处理** | 已删除旧 API，统一使用异常类 | - | P0 | ✅ 完成 |
| 32 | **错误响应格式不一致** | 已统一 JSON 格式 | - | P0 | ✅ 完成 |
| 33 | **缺少业务异常码** | 只有通用错误码 | 添加细分错误码 | P2 | 待处理 |
| 34 | **异常信息暴露** | 已添加生产环境隐藏详情 | - | P1 | ✅ 完成 |
| 35 | **缺少异常监控** | 无 | 集成 Sentry 或类似服务 | P3 | 待处理 |

---

## 六、代码质量问题 (10项)

| # | 问题 | 当前状态 | 建议 | 优先级 |
|---|------|----------|------|--------|
| 36 | **类型注解不完整** | 部分函数缺少类型注解 | 添加完整类型注解 | P2 |
| 37 | **文档字符串不完整** | 部分函数缺少 docstring | 补充文档 | P2 |
| 38 | **魔法数字** | `16000`, `4000` 等硬编码 | 提取为常量 | P2 |
| 39 | **函数过长** | `mcu_voice_chat_full` 超过 80 行 | 拆分为小函数 | P1 |
| 40 | **重复代码** | PCM 转 WAV 逻辑重复 | 提取到工具函数 | P1 |
| 41 | **缺少代码格式化** | 无统一格式 | 添加 black/ruff 配置 | P1 |
| 42 | **缺少 lint 检查** | 无 | 添加 flake8/pylint | P1 |
| 43 | **测试覆盖率低** | 约 60% | 提高到 80%+ | P1 |
| 44 | **缺少性能测试** | 无 | 添加 locust 压测 | P3 |
| 45 | **缺少安全扫描** | 无 | 添加 bandit 安全检查 | P2 |

---

## 七、兼容性问题 (5项)

| # | 问题 | 当前状态 | 建议 | 优先级 | 状态 |
|---|------|----------|------|--------|------|
| 46 | **v1/v2 API 并存** | 两套 API 同时运行 | 制定迁移计划，设置 v1 废弃时间 | P1 | 待处理 |
| 47 | **旧入口文件** | `app.py` 转发到 `src/main.py` | - | P0 | ✅ 完成 |
| 48 | **环境变量兼容** | `GEMINI_*` 和 `AI_*` 并存 | 统一使用 `AI_*`，保留兼容 | P2 | 待处理 |
| 49 | **Python 版本** | 未指定最低版本 | 在 pyproject.toml 指定 `>=3.10` | P2 | 待处理 |
| 50 | **依赖版本** | requirements.txt 版本范围宽松 | 锁定主要版本 | P2 | 待处理 |

---

## 八、收费功能测试状态

### v2 API (带认证和计费)

| 功能 | 接口 | 测试状态 | 说明 |
|------|------|----------|------|
| 认证检查 | `/v2/mcu/*` | ✅ 已测试 | 无 API Key 返回 401 |
| 无效 Key | `/v2/mcu/*` | ✅ 已测试 | 格式错误返回 401 |
| 配额检查 | `@check_quota` | ⚠️ 未完整测试 | 需要创建用户后测试 |
| 用量记录 | `record_usage()` | ⚠️ 未完整测试 | 需要创建用户后测试 |
| 用户创建 | `/admin/users` | ❌ 未测试 | 需要添加测试 |
| API Key 管理 | `/admin/users/*/keys` | ❌ 未测试 | 需要添加测试 |
| 用量查询 | `/admin/usage/me` | ❌ 未测试 | 需要添加测试 |

### 需要补充的测试

```python
# tests/integration/test_admin_api.py - 需要创建
- test_create_user
- test_create_api_key
- test_list_api_keys
- test_revoke_api_key
- test_get_user_usage

# tests/integration/test_quota.py - 需要创建
- test_quota_check_pass
- test_quota_check_exceed
- test_usage_recording
```

---

## 九、建议的目标目录结构

```
edge-tts-web-interface/
├── src/                          # 核心源码 (唯一入口)
│   ├── __init__.py
│   ├── main.py                   # 主入口 (替代 app.py)
│   ├── config.py                 # 配置管理
│   ├── api/                      # API 路由
│   │   ├── __init__.py
│   │   ├── v1/                   # v1 API (兼容)
│   │   │   ├── mcu.py
│   │   │   └── wechat.py
│   │   ├── v2/                   # v2 API (带认证)
│   │   │   └── mcu.py
│   │   ├── admin.py
│   │   ├── health.py
│   │   └── websocket.py
│   ├── services/                 # 业务服务层
│   │   ├── __init__.py
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   └── ai_service.py
│   │   ├── asr/
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # ASREngine 基类
│   │   │   ├── vosk_engine.py
│   │   │   └── tencent_engine.py
│   │   ├── tts/
│   │   │   └── tts_service.py
│   │   └── session_store.py
│   ├── auth/                     # 认证模块
│   │   ├── __init__.py
│   │   ├── api_key.py
│   │   ├── models.py
│   │   └── quota.py
│   ├── models/                   # 数据模型
│   │   ├── __init__.py
│   │   └── schemas.py
│   ├── utils/                    # 工具函数
│   │   ├── __init__.py
│   │   ├── audio.py              # 音频处理工具
│   │   ├── cleanup.py
│   │   ├── logger.py
│   │   ├── middleware.py
│   │   └── retry.py
│   └── exceptions/               # 自定义异常
│       ├── __init__.py
│       └── errors.py
├── tests/                        # 测试代码
│   ├── conftest.py
│   ├── unit/                     # 单元测试
│   ├── integration/              # 集成测试
│   └── e2e/                      # 端到端测试
├── docs/                         # 文档
│   ├── README.md
│   ├── api/
│   │   ├── v1.md
│   │   └── v2.md
│   ├── deployment.md
│   └── development.md
├── examples/                     # 示例代码
│   ├── android/
│   ├── python/
│   └── esp32/
├── scripts/                      # 脚本
│   ├── setup.sh
│   ├── deploy.sh
│   └── test.sh
├── data/                         # 数据目录 (gitignore)
│   ├── uploads/
│   ├── tts/
│   └── auth.db
├── static/                       # 静态文件
├── templates/                    # 模板文件
├── docker/                       # Docker 配置
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.prod.yml
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## 十、优先级说明

- **P0 (立即)**: 影响功能或有安全风险，本周内完成
- **P1 (本周)**: 影响代码质量，1-2 周内完成
- **P2 (本月)**: 改进项，1 个月内完成
- **P3 (长期)**: 优化项，按需完成

---

## 十一、下一步行动

1. **P0 任务** (立即执行):
   - [ ] 删除根目录旧 API 文件，统一使用 `src/`
   - [ ] 修改入口为 `src/main.py`
   - [ ] 统一日志和异常处理

2. **P1 任务** (本周):
   - [ ] 整理测试文件结构
   - [ ] 添加代码格式化工具
   - [ ] 补充 Admin API 测试

3. **P2 任务** (本月):
   - [ ] 完善类型注解
   - [ ] 提高测试覆盖率
   - [ ] 添加安全扫描
