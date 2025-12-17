# 语音助手 API 文档

## 快速开始

### 1. 启动服务器
```bash
# 默认端口 3003
py app.py

# 指定端口
set PORT=3005
py app.py
```
服务器运行在 `http://0.0.0.0:3003` (本地和外网均可访问)

### 2. 测试连接
```bash
# 本地测试
curl http://127.0.0.1:3003/mcu/ping

# 外网测试
curl http://服务器IP:3003/mcu/ping
# 返回: pong
```

---

## API 接口总览

### MCU 专用接口 (轻量级，适合单片机)

| 接口 | 方法 | 功能 | 输入 | 输出 |
|------|------|------|------|------|
| `/mcu/ping` | GET | 连接测试 | 无 | `pong` |
| `/mcu/status` | GET | 查看引擎状态 | 无 | JSON |
| `/mcu/stt` | POST | 语音转文字 | 音频 | 纯文本 |
| `/mcu/tts` | GET/POST | 文字转语音 | 文字 | 音频文件 |
| `/mcu/ask` | POST | AI 问答 | 文字 | 纯文本 |
| `/mcu/ask_stream` | POST | AI 流式问答 | 文字 | SSE 流 |
| `/mcu/voice_chat` | POST | 一站式语音对话 | 音频 | 文本/音频 |
| `/mcu/voice_chat_full` | POST | 完整语音对话 | 音频 | JSON (文字+回答+音频URL) |

### 实时语音识别 (WebSocket)

| 接口 | 说明 |
|------|------|
| `/realtime` | 实时语音识别测试页面 |
| `ws://server/realtime` | WebSocket 连接地址 |

### Web 接口 (功能完整)

| 接口 | 方法 | 功能 |
|------|------|------|
| `/` | GET/POST | Web 界面 |
| `/api/tts` | POST | TTS API |
| `/stt` | POST | STT API |
| `/api/ask_ai` | POST | AI 语音问答 |

### 微信接口

| 接口 | 方法 | 功能 | 说明 |
|------|------|------|------|
| `/wechat/callback` | GET/POST | 公众号回调 | 验证+消息处理 |
| `/wechat/chat` | POST | 文字对话 | 小程序/H5 用 |
| `/wechat/voice` | POST | 语音对话 | 支持 AMR/SILK |
| `/wechat/stt` | POST | 语音转文字 | 支持 AMR/SILK |

---

## MCU 接口详细说明

### 1. 连接测试 `/mcu/ping`

```bash
curl http://服务器:3003/mcu/ping
```
返回: `pong`

---

### 2. 查看状态 `/mcu/status`

```bash
curl http://服务器:3003/mcu/status
```

返回:
```json
{
  "vosk": true,
  "tencent": true,
  "ai": true,
  "tts": true,
  "engines": {
    "vosk": "本地离线识别，速度快，准确率一般",
    "tencent": "腾讯云在线识别，准确率高，需要网络"
  }
}
```

---

### 3. 语音转文字 `/mcu/stt`

**请求:**
```
POST /mcu/stt?engine=vosk&format=wav
Content-Type: application/octet-stream

[音频二进制数据]
```

**参数:**
| 参数 | 说明 | 可选值 | 默认 |
|------|------|--------|------|
| engine | 识别引擎 | `vosk` (本地) / `tencent` (腾讯云) | vosk |
| format | 音频格式 | `wav` / `pcm` / `mp3` | wav |
| rate | 采样率 (PCM用) | 8000/16000 | 16000 |

**返回:** 纯文本识别结果

**示例:**
```bash
# 使用本地 Vosk
curl -X POST "http://服务器:3003/mcu/stt?engine=vosk" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @audio.wav

# 使用腾讯云 (更准确)
curl -X POST "http://服务器:3003/mcu/stt?engine=tencent" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @audio.mp3
```

---

### 4. 文字转语音 `/mcu/tts`

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
| 参数 | 说明 | 可选值 | 默认 |
|------|------|--------|------|
| text | 要转换的文字 | - | (必填) |
| voice | 语音角色 | `xiaoxiao` / `yunxi` | xiaoxiao |
| format | 输出格式 | `wav` / `mp3` | wav |

**返回:** 音频文件二进制数据

**示例:**
```bash
curl "http://服务器:3003/mcu/tts?text=你好世界&format=wav" -o output.wav
```

---

### 5. AI 问答 `/mcu/ask`

**纯文本请求:**
```
POST /mcu/ask
Content-Type: text/plain

你好，今天天气怎么样？
```

**JSON 请求:**
```
POST /mcu/ask
Content-Type: application/json

{"question": "你好，今天天气怎么样？"}
```

**返回:** AI 回答的纯文本

**示例:**
```bash
curl -X POST "http://服务器:3003/mcu/ask" \
  -H "Content-Type: text/plain" \
  -d "你好"
```

---

### 6. 一站式语音对话 `/mcu/voice_chat` ⭐推荐

上传录音 → 语音识别 → AI回答 → 返回语音

**请求:**
```
POST /mcu/voice_chat?engine=tencent&out=audio
Content-Type: application/octet-stream

[录音数据]
```

**参数:**
| 参数 | 说明 | 可选值 | 默认 |
|------|------|--------|------|
| engine | 识别引擎 | `vosk` / `tencent` | vosk |
| format | 输入音频格式 | `wav` / `pcm` / `mp3` | wav |
| rate | 采样率 | 8000/16000 | 16000 |
| out | 输出类型 | `text` / `audio` | audio |

**返回:**
- `out=text`: `{"question": "识别文字", "answer": "AI回答"}`
- `out=audio`: WAV 音频文件

**示例:**
```bash
# 返回文本
curl -X POST "http://服务器:3003/mcu/voice_chat?engine=tencent&out=text" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @question.wav

# 返回语音
curl -X POST "http://服务器:3003/mcu/voice_chat?engine=tencent&out=audio" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @question.wav -o reply.wav
```

---

## 对外提供服务

### 方式一：局域网访问

服务器默认监听 `0.0.0.0:2024`，局域网内设备可直接访问：
```
http://192.168.x.x:2024/mcu/...
```

### 方式二：公网访问 (内网穿透)

使用 ngrok、frp 等工具：
```bash
ngrok http 2024
```

### 方式三：Docker 部署

```bash
docker build -t voice-assistant .
docker run -p 2024:2024 voice-assistant
```

### 方式四：云服务器部署

1. 上传代码到云服务器
2. 安装依赖: `pip install -r requirements.txt`
3. 启动服务: `python app.py`
4. 开放防火墙端口 2024

---

## MCU (ESP32) 调用示例

```cpp
#include <HTTPClient.h>

// 语音转文字
String speechToText(uint8_t* audio, size_t len) {
    HTTPClient http;
    http.begin("http://192.168.1.100:2024/mcu/stt?engine=tencent");
    http.addHeader("Content-Type", "application/octet-stream");
    http.POST(audio, len);
    return http.getString();
}

// AI 问答
String askAI(String question) {
    HTTPClient http;
    http.begin("http://192.168.1.100:2024/mcu/ask");
    http.addHeader("Content-Type", "text/plain");
    http.POST(question);
    return http.getString();
}

// 一站式语音对话 (推荐)
void voiceChat(uint8_t* audio, size_t len) {
    HTTPClient http;
    http.begin("http://192.168.1.100:2024/mcu/voice_chat?engine=tencent&out=audio");
    http.addHeader("Content-Type", "application/octet-stream");
    http.POST(audio, len);
    // 播放返回的音频...
}
```

---

## Python 调用示例

```python
import requests

SERVER = "http://服务器:3003"

# 语音转文字
with open("audio.wav", "rb") as f:
    r = requests.post(f"{SERVER}/mcu/stt?engine=tencent", data=f.read())
    print(r.text)

# AI 问答
r = requests.post(f"{SERVER}/mcu/ask", data="你好".encode())
print(r.text)

# 一站式语音对话
with open("question.wav", "rb") as f:
    r = requests.post(f"{SERVER}/mcu/voice_chat?out=text", data=f.read())
    print(r.json())
```

---

## 当前状态

| 功能 | 状态 | 说明 |
|------|------|------|
| 本地 Vosk STT | ✅ 可用 | 离线，速度快 |
| 腾讯云 ASR | ✅ 可用 | 在线，准确率高 |
| AI 问答 | ✅ 可用 | Gemini API |
| TTS | ⚠️ 需网络 | edge-tts 需访问微软服务器 |

---

---

## 新增接口详细说明

### 7. 完整语音对话 `/mcu/voice_chat_full` 

同时返回识别文字、AI回答、语音URL

**请求:**
```
POST /mcu/voice_chat_full?engine=tencent
Content-Type: application/octet-stream

[音频数据]
```

**返回:**
```json
{
  "success": true,
  "question": "用户说的话",
  "answer": "AI的回答",
  "audio_url": "/mcu/audio/reply_xxx.wav"
}
```

**示例:**
```bash
curl -X POST "http://服务器:3003/mcu/voice_chat_full?engine=tencent" \
  --data-binary @audio.wav
```

---

### 8. AI 流式问答 `/mcu/ask_stream` 

实时返回 AI 回答 (SSE 格式)

**请求:**
```
POST /mcu/ask_stream
Content-Type: text/plain

你好
```

**返回 (SSE 流):**
```
data: 你好
data: ！
data: 有什么
data: 可以帮？
data: [DONE]
```

**Python 示例:**
```python
import requests

r = requests.post(
    "http://服务器:3003/mcu/ask_stream",
    data="你好".encode(),
    stream=True
)

for line in r.iter_lines():
    if line:
        line = line.decode('utf-8')
        if line.startswith('data: '):
            print(line[6:], end='', flush=True)
```

---

### 9. 实时语音识别 (WebSocket)

边说边识别，实时返回结果

**安装依赖:**
```bash
pip install flask-socketio
```

**测试页面:**
```
http://服务器:3003/realtime
```

**WebSocket 事件:**

| 事件 | 方向 | 说明 |
|------|------|------|
| `audio` | 客户端→服务器 | 发送音频数据 (PCM 16bit 16kHz) |
| `partial` | 服务器→客户端 | 中间识别结果 |
| `final` | 服务器→客户端 | 最终识别结果 |
| `reset` | 客户端→服务器 | 重置识别器 |
| `end` | 客户端→服务器 | 结束识别 |

**JavaScript 示例:**
```javascript
const socket = io('/realtime');

// 接收识别结果
socket.on('partial', (data) => {
    console.log('识别中:', data.text);
});

socket.on('final', (data) => {
    console.log('最终结果:', data.text);
});

// 发送音频数据
socket.emit('audio', pcmData);
```

---

---

## 微信接口详细说明

### 1. 公众号回调 `/wechat/callback`

用于微信公众号服务器配置验证和消息接收。

**配置步骤:**
1. 在 `api_wechat.py` 中设置 `WECHAT_TOKEN`
2. 在微信公众号后台配置服务器 URL: `http://域名/wechat/callback`
3. 开启"接收语音识别结果"功能

**支持的消息类型:**
- 文字消息 → AI 回答
- 语音消息 → 识别 + AI 回答

---

### 2. 文字对话 `/wechat/chat`

适用于微信小程序、H5 页面。

**请求:**
```
POST /wechat/chat
Content-Type: application/json

{
    "message": "你好",
    "session_id": "用户唯一标识"
}
```

**返回:**
```json
{
    "success": true,
    "reply": "AI的回答",
    "session_id": "用户唯一标识"
}
```

**小程序示例:**
```javascript
wx.request({
    url: 'https://域名/wechat/chat',
    method: 'POST',
    data: {
        message: '你好',
        session_id: wx.getStorageSync('openid')
    },
    success(res) {
        console.log('AI回复:', res.data.reply);
    }
});
```

---

### 3. 语音对话 `/wechat/voice`

上传语音，返回识别文字和 AI 回答。

**请求:**
```
POST /wechat/voice?format=amr&engine=tencent
Content-Type: application/octet-stream

[语音数据]
```

**参数:**
| 参数 | 说明 | 可选值 | 默认 |
|------|------|--------|------|
| format | 音频格式 | amr/silk/wav/mp3 | amr |
| engine | 识别引擎 | vosk/tencent | tencent |

**返回:**
```json
{
    "success": true,
    "question": "用户说的话",
    "answer": "AI的回答"
}
```

**小程序示例:**
```javascript
// 录音
const recorderManager = wx.getRecorderManager();
recorderManager.start({ format: 'mp3' });

// 上传
recorderManager.onStop((res) => {
    wx.uploadFile({
        url: 'https://域名/wechat/voice?format=mp3&engine=tencent',
        filePath: res.tempFilePath,
        name: 'file',
        success(res) {
            const data = JSON.parse(res.data);
            console.log('识别:', data.question);
            console.log('回答:', data.answer);
        }
    });
});
```

---

### 4. 语音转文字 `/wechat/stt`

仅做语音识别，不调用 AI。

**请求:**
```
POST /wechat/stt?format=amr&engine=tencent
Content-Type: application/octet-stream

[语音数据]
```

**返回:**
```json
{
    "success": true,
    "text": "识别结果"
}
```

---

## 微信小程序完整示例

```javascript
// pages/voice/voice.js
Page({
    data: {
        recording: false,
        result: ''
    },
    
    // 开始录音
    startRecord() {
        const recorderManager = wx.getRecorderManager();
        recorderManager.start({
            duration: 60000,
            sampleRate: 16000,
            numberOfChannels: 1,
            format: 'mp3'
        });
        this.setData({ recording: true });
        
        recorderManager.onStop((res) => {
            this.uploadVoice(res.tempFilePath);
        });
    },
    
    // 停止录音
    stopRecord() {
        wx.getRecorderManager().stop();
        this.setData({ recording: false });
    },
    
    // 上传语音
    uploadVoice(filePath) {
        wx.showLoading({ title: '识别中...' });
        
        wx.uploadFile({
            url: 'https://域名/wechat/voice?format=mp3&engine=tencent',
            filePath: filePath,
            name: 'file',
            success: (res) => {
                const data = JSON.parse(res.data);
                if (data.success) {
                    this.setData({
                        result: `你说: ${data.question}\n\nAI: ${data.answer}`
                    });
                } else {
                    wx.showToast({ title: data.error, icon: 'none' });
                }
            },
            complete: () => {
                wx.hideLoading();
            }
        });
    }
});
```

---

## 配置文件

| 文件 | 说明 |
|------|------|
| `tencent_asr/config.py` | 腾讯云密钥配置 |
| `api_mcu.py` | AI API 配置 (Gemini) |
| `api_wechat.py` | 微信公众号配置 (Token/AppID) |
