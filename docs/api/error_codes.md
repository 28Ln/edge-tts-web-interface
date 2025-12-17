# 错误码文档

本文档列出所有 API 可能返回的错误码及其含义。

## 错误响应格式

```json
{
    "success": false,
    "error_code": "ERROR_CODE",
    "message": "错误描述",
    "details": "详细信息（可选）"
}
```

## 通用错误码

| 错误码 | HTTP 状态码 | 描述 |
|--------|-------------|------|
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `VALIDATION_ERROR` | 400 | 参数验证失败 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `METHOD_NOT_ALLOWED` | 405 | 请求方法不允许 |

## 认证错误码

| 错误码 | HTTP 状态码 | 描述 |
|--------|-------------|------|
| `AUTH_FAILED` | 401 | 认证失败（缺少或无效的 API Key） |
| `PERMISSION_DENIED` | 403 | 权限不足 |
| `QUOTA_EXCEEDED` | 429 | 配额已用尽 |

## 语音识别错误码 (ASR)

| 错误码 | HTTP 状态码 | 描述 |
|--------|-------------|------|
| `ASR_ERROR` | 500 | 语音识别失败 |
| `ASR_ENGINE_UNAVAILABLE` | 503 | 语音识别引擎不可用 |
| `ASR_NO_SPEECH` | 400 | 未识别到语音内容 |

## AI 服务错误码

| 错误码 | HTTP 状态码 | 描述 |
|--------|-------------|------|
| `AI_ERROR` | 500 | AI 服务调用失败 |
| `AI_TIMEOUT` | 504 | AI 请求超时 |

## 语音合成错误码 (TTS)

| 错误码 | HTTP 状态码 | 描述 |
|--------|-------------|------|
| `TTS_ERROR` | 500 | 语音合成失败 |
| `TTS_VOICE_NOT_FOUND` | 400 | 指定的语音不存在 |

## 音频处理错误码

| 错误码 | HTTP 状态码 | 描述 |
|--------|-------------|------|
| `AUDIO_ERROR` | 500 | 音频处理失败 |
| `AUDIO_FORMAT_INVALID` | 400 | 音频格式无效 |
| `AUDIO_EMPTY` | 400 | 音频数据为空 |

## 用户管理错误码

| 错误码 | HTTP 状态码 | 描述 |
|--------|-------------|------|
| `USER_EXISTS` | 400 | 用户名已存在 |
| `USER_NOT_FOUND` | 404 | 用户不存在 |
| `USER_DISABLED` | 403 | 用户已被禁用 |

## API Key 错误码

| 错误码 | HTTP 状态码 | 描述 |
|--------|-------------|------|
| `API_KEY_INVALID` | 401 | API Key 无效 |
| `API_KEY_EXPIRED` | 401 | API Key 已过期 |
| `API_KEY_REVOKED` | 401 | API Key 已被撤销 |

## 错误处理示例

### Python

```python
import requests

response = requests.post('http://localhost:3003/v2/mcu/stt', 
                         headers={'X-API-Key': 'sk-xxx'},
                         data=audio_data)

if response.status_code != 200:
    error = response.json()
    print(f"错误: {error['error_code']} - {error['message']}")
    
    if error['error_code'] == 'QUOTA_EXCEEDED':
        print("配额已用尽，请明天再试")
    elif error['error_code'] == 'AUTH_FAILED':
        print("请检查 API Key 是否正确")
```

### JavaScript

```javascript
fetch('http://localhost:3003/v2/mcu/stt', {
    method: 'POST',
    headers: { 'X-API-Key': 'sk-xxx' },
    body: audioData
})
.then(response => {
    if (!response.ok) {
        return response.json().then(error => {
            throw new Error(`${error.error_code}: ${error.message}`);
        });
    }
    return response.json();
})
.catch(error => {
    console.error('请求失败:', error.message);
});
```
