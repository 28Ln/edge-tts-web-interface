# MCU API 文档

适用于 ESP32、STM32 等嵌入式设备的轻量级 API。

## 基础信息

- 基础路径: `/mcu`
- 内容类型: `application/octet-stream` (音频) 或 `text/plain` (文本)

## 接口列表

### 1. 连接测试

```
GET /mcu/ping
```

**响应**: `pong`

### 2. 服务状态

```
GET /mcu/status
```

**响应**:
```json
{
  "success": true,
  "asr_engines": {
    "vosk": false,
    "tencent": true
  },
  "ai": true,
  "tts": true
}
```

### 3. 语音识别 (STT)

```
POST /mcu/stt?engine=tencent&format=wav
```

**参数**:
- `engine`: 识别引擎 (`tencent` 或 `vosk`)
- `format`: 音频格式 (`wav`, `mp3`, `pcm`)

**请求体**: 音频二进制数据

**响应**: 识别文本 (纯文本)

### 4. AI 问答

```
POST /mcu/ask?session=default
```

**参数**:
- `session`: 会话ID (用于保持上下文)

**请求体**: 问题文本

**响应**: AI 回答 (纯文本)

### 5. AI 流式问答

```
POST /mcu/ask_stream?session=default
```

**响应**: SSE 流
```
data: 你好
data: ！
data: [DONE]
```

### 6. 语音合成 (TTS)

```
GET /mcu/tts?text=你好&voice=xiaoxiao&format=wav
```

**参数**:
- `text`: 要合成的文本
- `voice`: 语音 (`xiaoxiao`, `yunxi`)
- `format`: 输出格式 (`wav`, `mp3`)

**响应**: 音频文件

### 7. 语音对话

```
POST /mcu/voice_chat?engine=tencent&out=text
```

**参数**:
- `engine`: ASR 引擎
- `out`: 输出类型 (`text` 或 `audio`)
- `session`: 会话ID

**请求体**: 音频二进制数据

**响应** (out=text):
```json
{
  "success": true,
  "question": "识别的问题",
  "answer": "AI 回答"
}
```

**响应** (out=audio): 音频文件

## 错误响应

```json
{
  "success": false,
  "error_code": "VALIDATION_ERROR",
  "message": "参数验证失败"
}
```

### 错误码

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| VALIDATION_ERROR | 400 | 参数验证失败 |
| AUDIO_ERROR | 400 | 音频处理失败 |
| ASR_ERROR | 500 | 语音识别失败 |
| AI_ERROR | 500 | AI服务失败 |
| TTS_ERROR | 500 | 语音合成失败 |
