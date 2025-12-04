# 腾讯云语音识别 + AI 对话

基于腾讯云一句话语音识别 API，实现语音转文字后与 AI 对话。

## 配置

1. 登录腾讯云控制台：https://console.cloud.tencent.com
2. 开通语音识别服务：https://console.cloud.tencent.com/asr
3. 获取密钥：https://console.cloud.tencent.com/cam/capi
4. 编辑 `config.py`，填入你的密钥：

```python
TENCENT_SECRET_ID = "你的 SecretId"
TENCENT_SECRET_KEY = "你的 SecretKey"
TENCENT_APPID = "你的 AppId"
```

## 安装依赖

```bash
pip install requests openai
```

## 使用方式

### 1. 命令行测试

```bash
cd tencent_asr
python voice_chat.py your_audio.wav
```

### 2. 代码调用

```python
from voice_chat import VoiceChat

chat = VoiceChat()

# 语音对话（流式输出）
result = chat.voice_chat("question.wav", stream=True)
print(f"识别结果: {result['transcription']}")
for chunk in result["reply"]:
    print(chunk, end="", flush=True)

# 纯文字对话
reply = chat.chat("你好，介绍一下你自己", stream=False)
print(reply)
```

### 3. 单独使用语音识别

```python
from asr_client import TencentASR

asr = TencentASR()
result = asr.recognize("audio.wav")

if result["success"]:
    print(f"识别结果: {result['text']}")
else:
    print(f"识别失败: {result['error']}")
```

## 支持的音频格式

- wav, mp3, m4a, flac, ogg, amr
- 推荐：16kHz 采样率，单声道

## 文件说明

- `config.py` - 配置文件（密钥）
- `asr_client.py` - 腾讯云 ASR 客户端
- `voice_chat.py` - 语音对话（ASR + AI）

## 注意事项

1. 一句话识别限制音频时长 ≤ 60 秒
2. 首次使用需要在腾讯云开通语音识别服务
3. 有免费额度，超出后按量计费
