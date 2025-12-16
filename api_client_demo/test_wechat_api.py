"""
微信 API 测试脚本
"""
import requests
import os

SERVER = os.environ.get('SERVER_URL', 'http://127.0.0.1:3003')

print("=" * 60)
print("微信 API 测试")
print("=" * 60)

# 1. 测试文字对话
print("\n1. 测试 /wechat/chat (文字对话)")
print("-" * 40)
r = requests.post(
    f"{SERVER}/wechat/chat",
    json={"message": "你好，请介绍一下自己", "session_id": "test123"}
)
if r.status_code == 200:
    data = r.json()
    print(f"成功: {data.get('success')}")
    print(f"回复: {data.get('reply')[:100]}...")
else:
    print(f"失败: {r.text}")

# 2. 测试语音转文字
print("\n2. 测试 /wechat/stt (语音转文字)")
print("-" * 40)
test_file = "static/测试.mp3"
if os.path.exists(test_file):
    with open(test_file, 'rb') as f:
        r = requests.post(
            f"{SERVER}/wechat/stt?format=mp3&engine=tencent",
            data=f.read(),
            headers={"Content-Type": "application/octet-stream"}
        )
    if r.status_code == 200:
        data = r.json()
        print(f"成功: {data.get('success')}")
        print(f"识别: {data.get('text')[:100]}...")
    else:
        print(f"失败: {r.text}")
else:
    print(f"测试文件不存在: {test_file}")

# 3. 测试语音对话
print("\n3. 测试 /wechat/voice (语音对话)")
print("-" * 40)
if os.path.exists(test_file):
    with open(test_file, 'rb') as f:
        r = requests.post(
            f"{SERVER}/wechat/voice?format=mp3&engine=tencent",
            data=f.read(),
            headers={"Content-Type": "application/octet-stream"}
        )
    if r.status_code == 200:
        data = r.json()
        print(f"成功: {data.get('success')}")
        print(f"识别: {data.get('question')[:50]}...")
        print(f"回答: {data.get('answer')[:100]}...")
    else:
        print(f"失败: {r.text}")
else:
    print(f"测试文件不存在: {test_file}")

print("\n" + "=" * 60)
print("测试完成!")
print("=" * 60)
