# 错误码文档

## 错误响应格式

```json
{
  "success": false,
  "error_code": "ERROR_CODE",
  "message": "错误描述",
  "details": {}  // 可选，详细信息
}
```

## 错误码列表

### HTTP 错误 (HTTP_xxx)

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| `HTTP_400` | 400 | 请求参数错误 |
| `HTTP_401` | 401 | 未授权访问 |
| `HTTP_403` | 403 | 禁止访问 |
| `HTTP_404` | 404 | 资源不存在 |
| `HTTP_405` | 405 | 请求方法不允许 |
| `HTTP_429` | 429 | 请求过于频繁 |
| `HTTP_500` | 500 | 服务器内部错误 |

### 通用错误

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `VALIDATION_ERROR` | 400 | 参数验证失败 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `CONFIG_ERROR` | 500 | 配置错误 |

### 认证错误

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| `AUTH_FAILED` | 401 | 认证失败 |
| `QUOTA_EXCEEDED` | 429 | 配额已用尽 |

### 音频错误 (AUDIO_xxx)

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| `AUDIO_ERROR` | 500 | 音频处理失败 |
| `AUDIO_EMPTY` | 400 | 音频数据为空 |
| `AUDIO_FORMAT_ERROR` | 400 | 音频格式错误 |
| `AUDIO_CONVERT_ERROR` | 500 | 音频转换失败 |

### ASR 错误 (ASR_xxx)

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| `ASR_ERROR` | 500 | 语音识别失败 |
| `ASR_ENGINE_UNAVAILABLE` | 503 | 语音识别引擎不可用 |
| `ASR_FORMAT_ERROR` | 400 | 音频格式不支持 |
| `ASR_TIMEOUT` | 504 | 语音识别超时 |
| `ASR_NETWORK_ERROR` | 503 | 语音识别网络错误 |
| `ASR_NO_RESULT` | 400 | 未识别到语音内容 |

### AI 错误 (AI_xxx)

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| `AI_ERROR` | 500 | AI服务调用失败 |
| `AI_CONNECTION_ERROR` | 503 | AI服务连接失败 |
| `AI_TIMEOUT` | 504 | AI服务请求超时 |
| `AI_RATE_LIMIT` | 429 | AI服务请求过于频繁 |
| `AI_INVALID_KEY` | 401 | AI服务密钥无效 |

### TTS 错误 (TTS_xxx)

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| `TTS_ERROR` | 500 | 语音合成失败 |
| `TTS_VOICE_NOT_FOUND` | 400 | 语音不存在 |
| `TTS_TIMEOUT` | 504 | 语音合成超时 |
| `TTS_SERVICE_UNAVAILABLE` | 503 | 语音合成服务不可用 |

## 错误处理示例

### Python 客户端

```python
import requests

response = requests.post(url, json=data)
if not response.ok:
    error = response.json()
    print(f"错误: {error['error_code']} - {error['message']}")
```

### JavaScript 客户端

```javascript
try {
  const response = await fetch(url, { method: 'POST', body: JSON.stringify(data) });
  const result = await response.json();
  if (!result.success) {
    console.error(`错误: ${result.error_code} - ${result.message}`);
  }
} catch (error) {
  console.error('网络错误:', error);
}
```
