"""
测试新增功能:
1. /mcu/voice_chat_full - 完整返回 (识别文字 + AI回答 + 语音URL)
2. /mcu/ask_stream - AI 流式回答
"""
import requests
import os

SERVER = "http://127.0.0.1:2024"

print("=" * 60)
print("新功能测试")
print("=" * 60)

# 测试文件
test_file = "static/测试.mp3"
if not os.path.exists(test_file):
    print(f"测试文件不存在: {test_file}")
    exit(1)

# 1. 测试完整语音对话接口
print("\n1. 测试 /mcu/voice_chat_full (完整返回)")
print("-" * 40)
with open(test_file, 'rb') as f:
    r = requests.post(
        f"{SERVER}/mcu/voice_chat_full?engine=tencent",
        data=f.read(),
        headers={"Content-Type": "application/octet-stream"}
    )

if r.status_code == 200:
    data = r.json()
    print(f"成功: {data.get('success')}")
    print(f"识别文字: {data.get('question')}")
    print(f"AI回答: {data.get('answer')}")
    print(f"语音URL: {data.get('audio_url')}")
    
    # 下载语音
    if data.get('audio_url'):
        audio_r = requests.get(f"{SERVER}{data['audio_url']}")
        if audio_r.status_code == 200:
            with open("test_reply.wav", 'wb') as f:
                f.write(audio_r.content)
            print(f"语音已保存: test_reply.wav ({len(audio_r.content)} bytes)")
else:
    print(f"失败: {r.text}")

# 2. 测试 AI 流式回答
print("\n2. 测试 /mcu/ask_stream (流式回答)")
print("-" * 40)
print("问题: 你好，请简单介绍一下自己")
print("AI回答: ", end="", flush=True)

r = requests.post(
    f"{SERVER}/mcu/ask_stream",
    data="你好，请简单介绍一下自己".encode('utf-8'),
    headers={"Content-Type": "text/plain; charset=utf-8"},
    stream=True
)

for line in r.iter_lines():
    if line:
        line = line.decode('utf-8')
        if line.startswith('data: '):
            content = line[6:]
            if content == '[DONE]':
                print("\n[完成]")
            elif content.startswith('[ERROR]'):
                print(f"\n错误: {content}")
            else:
                print(content, end="", flush=True)

print("\n" + "=" * 60)
print("测试完成!")
print("=" * 60)

# 3. 提示 WebSocket 测试
print("\n提示: 访问 http://127.0.0.1:2024/realtime 测试实时语音识别")
print("(需要先安装: pip install flask-socketio)")
