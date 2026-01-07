# 项目架构

## 目录结构

```
edge-tts-web-interface/
├── src/                      # 核心源码
│   ├── api/                  # API 路由
│   │   ├── admin/            # Admin API 模块
│   │   ├── dashboard/        # Dashboard 管理面板
│   │   ├── websocket/        # WebSocket 模块
│   │   ├── v1/               # API v1 (兼容)
│   │   ├── v2/               # API v2 (带认证)
│   │   ├── health.py         # 健康检查
│   │   └── openapi.py        # API 文档
│   ├── services/             # 业务服务层
│   │   ├── asr/              # ASR 引擎
│   │   ├── ai_service.py     # AI 服务
│   │   ├── asr_service.py    # 语音识别服务
│   │   ├── tts_service.py    # 语音合成服务
│   │   └── session_store.py  # 会话存储
│   ├── repositories/         # 数据访问层
│   ├── auth/                 # 认证模块
│   ├── exceptions/           # 异常处理
│   ├── utils/                # 工具函数
│   ├── models/               # 数据模型
│   ├── config.py             # 配置管理
│   ├── constants.py          # 常量定义
│   └── main.py               # 应用入口
├── data/                     # 数据目录
├── docs/                     # 文档
├── esp32-sdk/                # ESP32 SDK
├── examples/                 # 示例代码
│   ├── android/
│   ├── esp32/
│   └── python/
├── tests/                    # 测试
│   ├── unit/                 # 单元测试
│   ├── integration/          # 集成测试
│   ├── e2e/                  # 端到端测试
│   └── security/             # 安全测试
├── scripts/                  # 脚本工具
├── static/                   # 静态文件
├── templates/                # 模板文件
├── docker/                   # Docker 配置
└── migrations/               # 数据库迁移
```

## 分层架构

```
┌─────────────────────────────────────┐
│           API Layer (路由层)         │
│  - 请求解析、参数验证、响应格式化      │
│  - admin/, dashboard/, v1/, v2/     │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│        Service Layer (服务层)        │
│  - 业务逻辑、多引擎管理、上下文管理    │
│  - ai_service, asr_service, tts     │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│      Repository Layer (数据层)       │
│  - 数据访问、CRUD 操作               │
│  - user, api_key, quota             │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│       External Services (外部服务)   │
│  - OpenAI API、腾讯云 ASR、Edge TTS  │
└─────────────────────────────────────┘
```

## API 端点

| 端点 | 说明 |
|------|------|
| `/health` | 健康检查 |
| `/mcu/*` | MCU API v1 (无认证) |
| `/v2/mcu/*` | MCU API v2 (带认证) |
| `/wechat/*` | 微信 API |
| `/admin/*` | 管理 API |
| `/dashboard/*` | 管理面板 |
| `/docs` | API 文档 |
| `/realtime` | WebSocket 测试 |

## 核心服务

### AIService
- 管理 AI 对话
- 维护对话历史上下文
- 支持流式和非流式响应

### ASRService
- 统一语音识别接口
- 支持多引擎 (Vosk/腾讯云)
- 自动音频格式转换

### TTSService
- 语音合成服务
- 基于 Edge TTS
- 支持多种语音和格式

## 异常处理

所有业务异常继承自 `AppError`:

```python
class AppError(Exception):
    code = 500
    error_code = "INTERNAL_ERROR"
    message = "服务器内部错误"
```

子类:
- `ValidationError` - 参数验证错误 (400)
- `AudioError` - 音频处理错误 (400)
- `ASRError` - 语音识别错误 (500)
- `AIError` - AI服务错误 (500)
- `TTSError` - 语音合成错误 (500)
- `AuthError` - 认证错误 (401)
- `QuotaExceededError` - 配额超限 (429)

## 配置管理

使用 dataclass 定义配置结构:

```python
@dataclass
class AppConfig:
    server: ServerConfig
    ai: AIConfig
    asr: ASRConfig
    tts: TTSConfig
```

配置来源:
1. 环境变量 (优先)
2. .env 文件
3. 默认值

详见 [配置文档](configuration.md)
