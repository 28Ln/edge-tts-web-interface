# 项目架构

## 目录结构

```
edge-tts-web-interface/
├── src/                      # 核心源码
│   ├── api/                  # API 路由
│   │   ├── __init__.py       # Flask 应用工厂
│   │   └── mcu.py            # MCU API
│   ├── services/             # 业务服务层
│   │   ├── ai_service.py     # AI 服务
│   │   ├── asr_service.py    # 语音识别服务
│   │   └── tts_service.py    # 语音合成服务
│   ├── exceptions/           # 自定义异常
│   │   └── errors.py         # 异常类定义
│   ├── utils/                # 工具函数
│   │   └── logger.py         # 日志配置
│   ├── config.py             # 配置管理
│   └── app.py                # 应用入口
├── docs/                     # 文档
├── examples/                 # 示例代码
│   ├── android/              # Android 示例
│   └── python/               # Python 示例
├── static/                   # 静态文件
├── templates/                # 模板文件
├── tencent_asr/              # 腾讯云 ASR 客户端
├── .env                      # 环境变量
└── requirements.txt          # 依赖
```

## 分层架构

```
┌─────────────────────────────────────┐
│           API Layer (路由层)         │
│  - 请求解析、参数验证、响应格式化      │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│        Service Layer (服务层)        │
│  - 业务逻辑、多引擎管理、上下文管理    │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│       External Services (外部服务)   │
│  - OpenAI API、腾讯云 ASR、Edge TTS  │
└─────────────────────────────────────┘
```

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
