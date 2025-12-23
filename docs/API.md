# API 接口文档

## 基础信息

- **基础URL**: `http://localhost:3003`
- **默认端口**: `3003` (可通过 `PORT` 环境变量修改)
- **响应格式**: JSON

## API 版本

| 版本 | 路径前缀 | 认证 | 说明 |
|------|----------|------|------|
| v1 | `/mcu/*` | 无 | 兼容旧版，无需认证 |
| v2 | `/v2/mcu/*` | API Key | 带认证和配额管理 |

---

## 健康检查 API

### GET /health
健康检查

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-23T17:26:27.502634"
}
```

**测试命令**:
```bash
curl http://localhost:3003/health
```

### GET /health/live
存活检查

### GET /health/ready
就绪检查

### GET /health/version
版本信息

---

## MCU API v1 (无认证)

### GET /mcu/ping
连通性测试

**响应**: `pong`

**测试命令**:
```bash
curl http://localhost:3003/mcu/ping
```

### GET /mcu/status
服务状态

**响应示例**:
```json
{
  "success": true,
  "ai": true,
  "tts": true,
  "asr_engines": {
    "vosk": false,
    "tencent": true
  }
}
```

**测试命令**:
```bash
curl http://localhost:3003/mcu/status
```

### GET /mcu/tts
语音合成

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| text | string | 是 | 要合成的文本 |
| voice | string | 否 | 语音ID (默认: xiaoxiao) |
| format | string | 否 | 输出格式 (mp3/wav, 默认: mp3) |

**可用语音**:
- `xiaoxiao` - 晓晓 (女声)
- `yunxi` - 云希 (男声)
- `xiaoyi` - 晓艺 (女声)
- `yunjian` - 云健 (男声)

**测试命令**:
```bash
# 基础测试
curl "http://localhost:3003/mcu/tts?text=你好世界" -o test.mp3

# 指定语音和格式
curl "http://localhost:3003/mcu/tts?text=测试&voice=yunxi&format=wav" -o test.wav
```

### POST /mcu/tts
语音合成 (POST方式)

**请求体**: 纯文本
**Content-Type**: `text/plain; charset=utf-8`

**测试命令**:
```bash
curl -X POST http://localhost:3003/mcu/tts \
  -H "Content-Type: text/plain; charset=utf-8" \
  -d "你好世界" -o test.mp3
```

### POST /mcu/stt
语音识别

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| engine | string | 否 | 引擎 (tencent/vosk, 默认: tencent) |

**请求体**: 音频二进制数据 (WAV/PCM/AMR)

**响应**: 识别的文本

**测试命令**:
```bash
curl -X POST http://localhost:3003/mcu/stt \
  --data-binary @audio.wav
```

### POST /mcu/ask
AI问答

**请求体**: 问题文本
**Content-Type**: `text/plain; charset=utf-8`

**响应**: AI回答文本

**测试命令**:
```bash
curl -X POST http://localhost:3003/mcu/ask \
  -H "Content-Type: text/plain; charset=utf-8" \
  -d "你好，请介绍一下自己"
```

### POST /mcu/ask/stream
AI问答 (流式)

**测试命令**:
```bash
curl -X POST http://localhost:3003/mcu/ask/stream \
  -H "Content-Type: text/plain; charset=utf-8" \
  -d "讲一个故事"
```

### POST /mcu/voice_chat
语音对话 (ASR + AI + TTS)

**请求体**: 音频二进制数据

**响应**: AI回答的音频

**测试命令**:
```bash
curl -X POST http://localhost:3003/mcu/voice_chat \
  --data-binary @audio.wav -o response.mp3
```

---

## MCU API v2 (带认证)

### 认证方式

支持三种认证方式:

1. **Header**: `X-API-Key: your_api_key`
2. **Bearer Token**: `Authorization: Bearer your_api_key`
3. **Query参数**: `?api_key=your_api_key`

### GET /v2/mcu/ping
连通性测试 (无需认证)

### GET /v2/mcu/status
服务状态

**测试命令**:
```bash
# 匿名访问
curl http://localhost:3003/v2/mcu/status

# 带认证
curl http://localhost:3003/v2/mcu/status \
  -H "X-API-Key: your_api_key"
```

### POST /v2/mcu/stt
语音识别 (需认证)

**测试命令**:
```bash
curl -X POST http://localhost:3003/v2/mcu/stt \
  -H "X-API-Key: your_api_key" \
  --data-binary @audio.wav
```

### POST /v2/mcu/ask
AI问答 (需认证)

**测试命令**:
```bash
curl -X POST http://localhost:3003/v2/mcu/ask \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: text/plain; charset=utf-8" \
  -d "你好"
```

### GET /v2/mcu/tts
语音合成 (需认证)

**测试命令**:
```bash
curl "http://localhost:3003/v2/mcu/tts?text=你好&api_key=your_api_key" -o test.mp3
```

---

## Admin API

### POST /admin/users
创建用户

**请求体**:
```json
{
  "username": "testuser",
  "email": "test@example.com",
  "daily_requests": 1000,
  "daily_tokens": 100000,
  "daily_audio_seconds": 600
}
```

**响应**:
```json
{
  "success": true,
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com"
  },
  "api_key": "etk_xxxxxxxxxxxxxxxx"
}
```

**测试命令**:
```bash
curl -X POST http://localhost:3003/admin/users \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com"}'
```

### GET /admin/users/{username}
获取用户信息

**测试命令**:
```bash
curl http://localhost:3003/admin/users/testuser
```

### POST /admin/users/{username}/keys
创建API Key

**测试命令**:
```bash
curl -X POST http://localhost:3003/admin/users/testuser/keys \
  -H "Content-Type: application/json" \
  -d '{"name":"my-key"}'
```

### GET /admin/users/{username}/keys
获取用户的API Key列表

### POST /admin/keys/{key}/revoke
撤销API Key

---

## 微信 API

### POST /wechat/chat
微信聊天

**请求体**:
```json
{
  "message": "你好"
}
```

### POST /wechat/stt
微信语音识别

### POST /wechat/voice
微信语音对话

### GET/POST /wechat/callback
微信公众号回调

---

## Dashboard 管理面板

访问地址: `http://localhost:3003/dashboard`

默认密码: `admin123` (通过 `ADMIN_PASSWORD` 环境变量修改)

### 功能
- 用户管理 (创建/编辑/启用/禁用)
- API Key 管理 (创建/撤销)
- 用量统计
- 系统状态

---

## WebSocket API

### SocketIO: /realtime
实时语音识别 (SocketIO)

### 原生WebSocket: /ws/realtime
实时语音识别 (原生WebSocket，兼容Android OkHttp)

### 测试页面
访问 `http://localhost:3003/realtime` 可打开WebSocket测试页面

---

## 错误响应格式

```json
{
  "success": false,
  "error_code": "ERROR_CODE",
  "message": "错误描述"
}
```

详见 [错误码文档](error-codes.md)
