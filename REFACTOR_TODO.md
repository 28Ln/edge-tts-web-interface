# 项目重构优化清单

## 一、目录结构问题 (10个)

1. ✅ **根目录文件过多** - 已创建 `src/` 目录，新代码放在 src 下
2. ✅ **API 模块分散** - 已创建 `src/api/` 目录
3. ✅ **测试文件混乱** - 已移动到 `tests/` 目录
4. ✅ **配置文件分散** - 已创建 `src/config.py` 统一配置
5. ✅ **临时文件目录** - 已更新 `.gitignore`
6. ✅ **文档分散** - 已创建 `docs/` 目录
7. ✅ **Android 示例位置** - 已移动到 `examples/android/`
8. ✅ **FFmpeg 目录** - 已在 .gitignore 中排除，Docker 镜像自带 ffmpeg
9. ⏭️ **静态文件** - `static/测试.mp3` 中文文件名 (保留，不影响功能)
10. ✅ **缺少 src 目录** - 已创建 `src/` 目录

## 二、代码架构问题 (10个)

11. ✅ **单文件过大** - 已拆分为 services 层
12. ✅ **重复代码** - 已抽取到 AIService
13. ✅ **缺少服务层** - 已创建 `src/services/`
14. ✅ **缺少模型层** - 已创建 `src/models/schemas.py`
15. ✅ **全局变量滥用** - 已创建 SessionStore 抽象层 (支持内存/Redis)
16. ✅ **硬编码配置** - 已创建 `src/config.py`
17. ✅ **缺少依赖注入** - 已通过 get_xxx_service() 实现
18. ✅ **缺少接口抽象** - 已创建 ASREngine 抽象基类
19. ⏭️ **WebSocket 实现重复** - 保留两个版本 (socketio/native) 供不同场景使用
20. ✅ **缺少中间件** - 已添加全局错误处理器

## 三、日志架构问题 (8个)

21. ✅ **日志配置分散** - 已创建 `src/utils/logger.py`
22. ✅ **日志格式不统一** - 新代码使用统一格式
23. ✅ **缺少日志级别控制** - 支持 LOG_LEVEL 环境变量
24. ✅ **缺少请求 ID** - 已添加 `src/utils/middleware.py`
25. ✅ **日志输出位置** - 支持文件输出
26. ✅ **敏感信息泄露** - 已添加 SensitiveFilter 自动过滤敏感信息
27. ✅ **缺少结构化日志** - 已支持 JSON 格式 (LOG_FORMAT=json)
28. ✅ **缺少性能日志** - 已添加响应时间记录

## 四、异常处理问题 (8个)

29. ✅ **异常类型不明确** - 已创建 `src/exceptions/errors.py`
30. ✅ **错误响应不统一** - 新 API 使用统一 JSON 格式
31. ✅ **缺少全局异常处理** - 已添加 Flask 错误处理器
32. ✅ **异常信息暴露** - 已添加全局异常处理，仅调试模式返回详情
33. ✅ **缺少错误码** - 已定义错误码体系
34. ✅ **重试机制缺失** - 已添加 `src/utils/retry.py`
35. ✅ **超时处理不完善** - 已添加 timeout 和 retry_with_timeout 装饰器
36. ✅ **资源清理不完整** - 已添加 cleanup.py (temp_file 上下文管理器)

## 五、配置管理问题 (6个)

37. ✅ **环境变量命名混乱** - 已支持新变量名 AI_API_* (兼容旧名)
38. ✅ **缺少配置验证** - 已添加 validate_config()
39. ⏭️ **配置文件格式** - 当前使用环境变量，简单场景足够
40. ✅ **缺少多环境支持** - 已支持 APP_ENV (development/testing/production)
41. ⏭️ **密钥管理不安全** - 生产环境建议使用 Docker secrets 或云密钥服务
42. ⏭️ **配置热更新** - 当前需重启，可通过 Docker 滚动更新实现

## 六、测试问题 (4个)

43. ✅ **缺少单元测试** - 已添加 pytest 框架和基础测试
44. ✅ **测试脚本混乱** - 已整理到 `tests/` 目录
45. ✅ **缺少集成测试** - 已添加 tests/integration/test_api_mcu.py
46. ✅ **缺少测试覆盖率** - 已配置 pytest-cov (运行: pytest --cov)

## 七、其他问题 (4个)

47. ✅ **缺少 API 版本控制** - 已创建 `/v2/mcu/*` 带认证和计费的 API
48. ✅ **缺少健康检查** - 已添加 `/health`, `/health/ready`, `/health/live`
49. ✅ **缺少 API 文档自动生成** - 已添加 /docs (Swagger UI) 和 /openapi.json
50. ✅ **缺少 Docker Compose** - 已添加完整配置 (Redis + Nginx + 生产环境)

---

## 建议的目标目录结构

```
edge-tts-web-interface/
├── src/                          # 核心源码
│   ├── __init__.py
│   ├── app.py                    # Flask 应用入口
│   ├── config.py                 # 配置管理
│   ├── api/                      # API 路由
│   │   ├── __init__.py
│   │   ├── mcu.py
│   │   ├── wechat.py
│   │   └── websocket.py
│   ├── services/                 # 业务服务层
│   │   ├── __init__.py
│   │   ├── ai_service.py
│   │   ├── asr_service.py
│   │   └── tts_service.py
│   ├── models/                   # 数据模型
│   │   ├── __init__.py
│   │   └── schemas.py
│   ├── utils/                    # 工具函数
│   │   ├── __init__.py
│   │   ├── audio.py
│   │   └── logger.py
│   └── exceptions/               # 自定义异常
│       ├── __init__.py
│       └── errors.py
├── tests/                        # 测试代码
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/                         # 文档
│   ├── api.md
│   ├── deployment.md
│   └── development.md
├── examples/                     # 示例代码
│   ├── android/
│   ├── python/
│   └── esp32/
├── scripts/                      # 脚本
│   ├── setup.sh
│   └── deploy.sh
├── static/                       # 静态文件
├── templates/                    # 模板文件
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml               # 替代 requirements.txt
├── README.md
└── LICENSE
```

---

## 优先级建议

### P0 - 立即修复
- #29 异常类型不明确
- #30 错误响应不统一
- #21 日志配置分散

### P1 - 本周完成
- #1 根目录文件过多
- #11 单文件过大
- #12 重复代码

### P2 - 本月完成
- #13-18 架构层面优化
- #43-46 测试相关

### P3 - 长期优化
- #47-50 其他优化
