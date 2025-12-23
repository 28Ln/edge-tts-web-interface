# 配置文档

## 环境变量

### 基础配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `APP_ENV` | `development` | 环境类型: development/testing/production |
| `FLASK_DEBUG` | `0` | 调试模式: 0=关闭, 1=开启 |
| `PORT` | `3003` | 服务端口 |
| `SECRET_KEY` | - | Session密钥，生产环境必须设置 |

### AI 服务配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `AI_API_BASE` | - | AI API 地址 (支持 OpenAI 兼容接口) |
| `AI_API_KEY` | - | AI API 密钥 |
| `AI_MODEL` | `deepseek-r1-search` | 模型名称 |

> 兼容旧变量名: `GEMINI_API_BASE`, `GEMINI_API_KEY`, `GEMINI_MODEL`

### 腾讯云 ASR 配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `TENCENT_SECRET_ID` | - | 腾讯云 SecretId |
| `TENCENT_SECRET_KEY` | - | 腾讯云 SecretKey |
| `TENCENT_APPID` | - | 腾讯云 AppId |

### 日志配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `LOG_LEVEL` | 按环境 | 日志级别: DEBUG/INFO/WARNING/ERROR |
| `LOG_FORMAT` | 按环境 | 日志格式: text/json |
| `LOG_FILE` | - | 日志文件路径 (可选) |

默认日志级别:
- development: DEBUG
- testing: INFO
- production: WARNING

### 可选配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `REDIS_URL` | - | Redis 连接地址 |
| `AUTH_DB_PATH` | `data/auth.db` | 认证数据库路径 |
| `ADMIN_PASSWORD` | `admin123` | 管理面板密码 |
| `VOSK_MODEL_PATH` | - | Vosk 离线模型路径 |

## 超时配置

配置类中的超时设置 (单位: 秒):

```python
# AI 服务
ai.timeout = 30           # 普通请求超时
ai.stream_timeout = 60    # 流式响应超时
ai.max_retries = 3        # 最大重试次数

# ASR 服务
asr.timeout = 60          # ASR 请求超时
asr.convert_timeout = 30  # 音频转换超时

# TTS 服务
tts.timeout = 30          # TTS 请求超时
tts.ffmpeg_timeout = 10   # FFmpeg 转换超时
```

## 配置验证

启动时会自动验证必要配置:

```python
from src.config import get_config, validate_config

config = get_config()
errors = validate_config(config)
if errors:
    print("配置错误:", errors)
```

## 多环境配置

1. 复制 `.env.example` 为 `.env`
2. 设置 `APP_ENV` 为对应环境
3. 填写必要的 API 密钥

生产环境建议:
- 设置 `APP_ENV=production`
- 使用强随机 `SECRET_KEY`
- 设置 `LOG_FORMAT=json`
- 配置 `REDIS_URL` 用于分布式部署
