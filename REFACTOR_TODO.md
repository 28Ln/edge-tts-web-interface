# 项目重构优化清单

## 一、目录结构问题 (10个)

1. **根目录文件过多** - `api_mcu.py`, `api_websocket.py`, `api_wechat.py`, `app.py` 应该放到 `src/` 或 `app/` 目录
2. **API 模块分散** - 所有 API 蓝图应该统一放到 `api/` 目录下
3. **测试文件混乱** - `test_edge.mp3`, `test_output.wav` 应该放到 `tests/fixtures/` 目录
4. **配置文件分散** - `tencent_asr/config.py` 应该统一到根目录的配置管理
5. **临时文件目录** - `tts/`, `uploads/` 应该在 `.gitignore` 中，不应该有测试文件
6. **文档分散** - `README.md`, `README.en.md`, `api_client_demo/API_DOC.md` 应该统一到 `docs/` 目录
7. **Android 示例位置** - `android_demo/` 应该移到 `examples/android/` 或独立仓库
8. **FFmpeg 目录** - 不应该放在项目中，应该通过系统安装或 Docker
9. **静态文件** - `static/测试.mp3` 中文文件名不规范
10. **缺少 src 目录** - 核心代码应该放在 `src/` 下，便于打包发布

## 二、代码架构问题 (10个)

11. **单文件过大** - `api_mcu.py` 超过 700 行，应该拆分为多个模块
12. **重复代码** - `api_mcu.py` 和 `api_wechat.py` 有大量重复的 AI 调用逻辑
13. **缺少服务层** - 业务逻辑直接写在路由函数中，应该抽取到 `services/` 层
14. **缺少模型层** - 没有数据模型定义，请求/响应结构不清晰
15. **全局变量滥用** - `conversation_history` 等全局变量应该用 Redis 或数据库
16. **硬编码配置** - 很多配置直接写在代码中，应该统一到配置文件
17. **缺少依赖注入** - AI 客户端、ASR 客户端应该通过依赖注入
18. **缺少接口抽象** - ASR 引擎没有统一接口，切换引擎需要改代码
19. **WebSocket 实现重复** - `api_websocket.py` 和 `api_websocket_native.py` 功能重复
20. **缺少中间件** - 没有统一的请求日志、错误处理中间件

## 三、日志架构问题 (8个)

21. **日志配置分散** - 每个文件单独配置 logging，应该统一配置
22. **日志格式不统一** - 有的用 emoji，有的不用，格式混乱
23. **缺少日志级别控制** - 没有通过环境变量控制日志级别
24. **缺少请求 ID** - 无法追踪单个请求的完整日志链路
25. **日志输出位置** - 只输出到控制台，应该支持文件、远程日志服务
26. **敏感信息泄露** - API Key 等敏感信息可能被记录到日志
27. **缺少结构化日志** - 应该使用 JSON 格式便于日志分析
28. **缺少性能日志** - 没有记录接口响应时间等性能指标

## 四、异常处理问题 (8个)

29. **异常类型不明确** - 所有异常都用 `Exception`，应该定义业务异常类
30. **错误响应不统一** - 有的返回字符串，有的返回 JSON，格式不一致
31. **缺少全局异常处理** - 没有 Flask 的全局错误处理器
32. **异常信息暴露** - 直接返回 `str(e)` 可能暴露敏感信息
33. **缺少错误码** - 没有定义错误码体系，客户端难以处理
34. **重试机制缺失** - 外部服务调用失败没有重试逻辑
35. **超时处理不完善** - 长时间运行的任务没有超时控制
36. **资源清理不完整** - 临时文件在异常时可能没有被清理

## 五、配置管理问题 (6个)

37. **环境变量命名混乱** - `GEMINI_API_BASE` 实际上是通用 OpenAI 接口
38. **缺少配置验证** - 启动时不检查必要配置是否存在
39. **配置文件格式** - 应该支持 YAML/TOML 等更灵活的格式
40. **缺少多环境支持** - 没有 dev/test/prod 环境配置分离
41. **密钥管理不安全** - API Key 直接写在 `.env`，应该用密钥管理服务
42. **配置热更新** - 修改配置需要重启服务

## 六、测试问题 (4个)

43. **缺少单元测试** - 没有任何单元测试代码
44. **测试脚本混乱** - `api_client_demo/` 下有多个功能重复的测试脚本
45. **缺少集成测试** - 没有自动化的 API 集成测试
46. **缺少测试覆盖率** - 不知道代码测试覆盖情况

## 七、其他问题 (4个)

47. **缺少 API 版本控制** - 接口没有版本号，不利于迭代
48. **缺少健康检查** - 除了 `/mcu/ping` 没有完整的健康检查接口
49. **缺少 API 文档自动生成** - 应该用 OpenAPI/Swagger 自动生成文档
50. **缺少 Docker Compose** - 没有完整的容器化部署方案

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
