"""
快速测试脚本 - 最简单的 MCU API 调用示例

运行: python api_client_demo/quick_test.py
"""

import requests

SERVER = "http://127.0.0.1:2024"

# 1. 测试连接
print("1. 测试连接...")
r = requests.get(f"{SERVER}/mcu/ping")
print(f"   结果: {r.text}\n")

# 2. 文字转语音
print("2. 文字转语音...")
r = requests.get(f"{SERVER}/mcu/tts?text=你好世界&format=wav")
with open("test_output.wav", "wb") as f:
    f.write(r.content)
print(f"   已保存: test_output.wav ({len(r.content)} bytes)\n")

# 3. 语音转文字
print("3. 语音转文字...")
with open("test_output.wav", "rb") as f:
    r = requests.post(f"{SERVER}/mcu/stt", data=f.read(),
                      headers={"Content-Type": "application/octet-stream"})
print(f"   识别结果: {r.text}\n")

# 4. AI 问答
print("4. AI 问答...")
r = requests.post(f"{SERVER}/mcu/ask", data="你好".encode(),
                  headers={"Content-Type": "text/plain"})
print(f"   AI回答: {r.text[:100]}...\n")

print("✅ 测试完成!")
