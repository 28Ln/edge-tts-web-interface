"""
单独测试 STT (语音转文字) 功能
使用项目中已有的音频文件
"""
import requests
import os

SERVER = "http://127.0.0.1:2024"

# 测试文件列表 (优先使用有效的音频)
test_files = [
    "static/测试.mp3",
    "uploads/input.wav",
]

print("=" * 50)
print("STT 语音转文字测试")
print("=" * 50)

# 1. 查看状态
print("\n1. 查看引擎状态...")
r = requests.get(f"{SERVER}/mcu/status")
print(f"   {r.json()}")

# 2. 测试本地 Vosk
for f in test_files:
    if os.path.exists(f):
        print(f"\n2. 测试本地 Vosk - {f}")
        with open(f, 'rb') as audio:
            r = requests.post(
                f"{SERVER}/mcu/stt?engine=vosk",
                data=audio.read(),
                headers={"Content-Type": "application/octet-stream"}
            )
        print(f"   结果: {r.text}")
        break
else:
    print("   未找到测试音频文件")

# 3. 测试腾讯云 ASR
for f in test_files:
    if os.path.exists(f):
        print(f"\n3. 测试腾讯云 ASR - {f}")
        with open(f, 'rb') as audio:
            r = requests.post(
                f"{SERVER}/mcu/stt?engine=tencent",
                data=audio.read(),
                headers={"Content-Type": "application/octet-stream"}
            )
        print(f"   结果: {r.text}")
        break

# 4. 测试 AI 问答
print("\n4. 测试 AI 问答...")
r = requests.post(
    f"{SERVER}/mcu/ask",
    data="你好，请用一句话介绍自己".encode('utf-8'),
    headers={"Content-Type": "text/plain; charset=utf-8"}
)
print(f"   AI: {r.text[:200]}...")

print("\n" + "=" * 50)
print("测试完成!")
