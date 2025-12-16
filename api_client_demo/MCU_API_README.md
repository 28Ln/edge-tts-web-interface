# MCU 语音助手 API 文档

专为单片机（ESP32、STM32等）设计的轻量级语音交互 API。

## 快速开始

### 1. 启动服务器

```bash
python app.py
```

服务器将在 `http://127.0.0.1:2024` 启动。

### 2. 测试 API

```bash
python api_client_demo/test_mcu_api.py
```

---

## API 接口列表

| 接口 | 方法 | 功能 | 输入 | 输出 |
|------|------|------|------|------|
| `/mcu/ping` | GET | 连接测试 | 无 | 文本 "pong" |
| `/mcu/stt` | POST | 语音转文字 | PCM/WAV 音频 | 纯文本 |
| `/mcu/tts` | GET/POST | 文字转语音 | 文字 | WAV/MP3 音频 |
| `/mcu/ask` | POST | AI 问答 | 文字 | 纯文本 |
| `/mcu/voice_chat` | POST | 一站式语音对话 | 音频 | 文本或音频 |

---

## 接口详细说明

### 1. 连接测试 `/mcu/ping`

测试服务器是否在线。

**请求:**
```
GET /mcu/ping
```

**响应:**
```
pong
```

**MCU 代码示例 (ESP32):**
```cpp
HTTPClient http;
http.begin("http://192.168.1.100:2024/mcu/ping");
int code = http.GET();
if (code == 200) {
    Serial.println("服务器在线");
}
```

---

### 2. 语音转文字 `/mcu/stt`

将录音转换为文字。

**请求:**
```
POST /mcu/stt?format=pcm&rate=16000
Content-Type: application/octet-stream

[音频二进制数据]
```

**参数:**
| 参数 | 说明 | 默认值 |
|------|------|--------|
| format | 音频格式: `pcm` 或 `wav` | wav |
| rate | 采样率 (仅 PCM 需要) | 16000 |

**响应:**
```
你好世界
```

**MCU 代码示例:**
```cpp
HTTPClient http;
http.begin("http://server:2024/mcu/stt?format=pcm&rate=16000");
http.addHeader("Content-Type", "application/octet-stream");
http.POST(audio_buffer, audio_length);
String text = http.getString();
Serial.println("识别结果: " + text);
```

**音频要求:**
- PCM: 16bit, 单声道, 16kHz
- WAV: 任意格式 (服务器自动转换)

---

### 3. 文字转语音 `/mcu/tts`

将文字转换为语音。

**GET 请求:**
```
GET /mcu/tts?text=你好&voice=xiaoxiao&format=wav
```

**POST 请求:**
```
POST /mcu/tts
Content-Type: application/json

{"text": "你好", "voice": "xiaoxiao", "format": "wav"}
```

**参数:**
| 参数 | 说明 | 默认值 |
|------|------|--------|
| text | 要转换的文字 | (必填) |
| voice | 语音: `xiaoxiao` 或 `yunxi` | xiaoxiao |
| format | 输出格式: `wav` 或 `mp3` | wav |

**响应:**
```
[WAV 音频二进制数据]
```

**MCU 代码示例:**
```cpp
HTTPClient http;
http.begin("http://server:2024/mcu/tts?text=你好&format=wav");
int code = http.GET();
if (code == 200) {
    WiFiClient* stream = http.getStreamPtr();
    // 读取音频数据并播放
}
```

---

### 4. AI 问答 `/mcu/ask`

向 AI 提问，获取文字回答。

**纯文本请求:**
```
POST /mcu/ask
Content-Type: text/plain

今天天气怎么样？
```

**JSON 请求:**
```
POST /mcu/ask
Content-Type: application/json

{"question": "今天天气怎么样？"}
```

**响应:**
```
我无法获取实时天气信息，建议您查看天气预报应用。
```

**MCU 代码示例:**
```cpp
HTTPClient http;
http.begin("http://server:2024/mcu/ask");
http.addHeader("Content-Type", "text/plain");
http.POST("你好");
String answer = http.getString();
Serial.println("AI: " + answer);
```

---

### 5. 一站式语音对话 `/mcu/voice_chat`

**最推荐的接口！** 上传录音，直接返回 AI 语音回复。

**请求:**
```
POST /mcu/voice_chat?format=pcm&rate=16000&out=audio
Content-Type: application/octet-stream

[录音数据]
```

**参数:**
| 参数 | 说明 | 默认值 |
|------|------|--------|
| format | 输入音频格式: `pcm` 或 `wav` | wav |
| rate | 采样率 | 16000 |
| out | 输出类型: `text` 或 `audio` | audio |

**响应 (out=text):**
```json
{"question": "你好", "answer": "你好！有什么可以帮助你的？"}
```

**响应 (out=audio):**
```
[WAV 音频二进制数据]
```

**MCU 代码示例:**
```cpp
HTTPClient http;
http.begin("http://server:2024/mcu/voice_chat?format=pcm&out=audio");
http.addHeader("Content-Type", "application/octet-stream");
http.POST(recorded_audio, length);

// 跳过 WAV 头 (44 bytes)
WiFiClient* stream = http.getStreamPtr();
uint8_t header[44];
stream->readBytes(header, 44);

// 播放音频
while (stream->available()) {
    uint8_t buf[1024];
    int len = stream->readBytes(buf, 1024);
    i2s_write(I2S_NUM_1, buf, len, &written, portMAX_DELAY);
}
```

---

## MCU 硬件接线参考 (ESP32)

### I2S 麦克风 (INMP441)

| INMP441 | ESP32 |
|---------|-------|
| VDD | 3.3V |
| GND | GND |
| WS | GPIO 15 |
| SCK | GPIO 2 |
| SD | GPIO 13 |

### I2S 扬声器 (MAX98357A)

| MAX98357A | ESP32 |
|-----------|-------|
| VIN | 5V |
| GND | GND |
| BCLK | GPIO 26 |
| LRC | GPIO 25 |
| DIN | GPIO 22 |

---

## 完整流程示例

### 流程图

```
┌─────────────┐     录音数据      ┌─────────────┐
│   ESP32     │ ───────────────> │   服务器     │
│   MCU       │                  │             │
│             │ <─────────────── │  语音识别    │
│  按下按钮    │     识别文字      │     ↓       │
│     ↓       │                  │  AI 处理    │
│  开始录音    │                  │     ↓       │
│     ↓       │ <─────────────── │  语音合成    │
│  上传音频    │     语音回复      │             │
│     ↓       │                  └─────────────┘
│  播放回复    │
└─────────────┘
```

### ESP32 代码流程

```cpp
void voiceAssistant() {
    // 1. 录音 (5秒)
    recordAudio(audio_buffer, 5);
    
    // 2. 上传并获取回复
    HTTPClient http;
    http.begin("http://server:2024/mcu/voice_chat?format=pcm&out=audio");
    http.addHeader("Content-Type", "application/octet-stream");
    http.POST(audio_buffer, audio_length);
    
    // 3. 播放回复
    playAudio(http.getStreamPtr());
}
```

---

## 常见问题

### Q: MCU 内存不够怎么办？

A: 可以分段录音上传，或降低采样率到 8kHz。

### Q: 网络延迟太高？

A: 
1. 使用 `/mcu/voice_chat` 减少请求次数
2. 服务器部署在局域网内
3. 使用更短的录音时长

### Q: 支持哪些音频格式？

A: 
- 输入: PCM (16bit/16kHz), WAV (任意格式)
- 输出: WAV (16bit/16kHz), MP3

---

## 文件说明

```
api_client_demo/
├── test_mcu_api.py          # Python 测试脚本
├── mcu_example_esp32.ino    # ESP32 完整示例
├── MCU_API_README.md        # 本文档
└── client.py                # 原有的 Python 客户端
```
