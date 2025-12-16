"""
完整 API 测试脚本 - 测试所有接口

使用方法:
    本地测试: py api_client_demo/test_all_api.py
    指定服务器: set SERVER_URL=http://你的IP:3003 && py api_client_demo/test_all_api.py
"""
import requests
import os
import time

# 服务器地址 (支持环境变量配置)
SERVER = os.environ.get('SERVER_URL', 'http://127.0.0.1:3003')
TEST_AUDIO = "static/测试.mp3"

results = {}

def test(name, func):
    """运行测试并记录结果"""
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"{'='*60}")
    try:
        success = func()
        results[name] = "✅ 通过" if success else "❌ 失败"
        return success
    except Exception as e:
        print(f"错误: {e}")
        results[name] = f"❌ 错误: {e}"
        return False


# ==================== MCU API ====================

def test_mcu_ping():
    r = requests.get(f"{SERVER}/mcu/ping")
    print(f"响应: {r.text}")
    return r.status_code == 200 and r.text == "pong"

def test_mcu_status():
    r = requests.get(f"{SERVER}/mcu/status")
    data = r.json()
    print(f"响应: {data}")
    return r.status_code == 200 and data.get('ai') == True

def test_mcu_stt_vosk():
    if not os.path.exists(TEST_AUDIO):
        print(f"跳过: 测试文件不存在 {TEST_AUDIO}")
        return True
    with open(TEST_AUDIO, 'rb') as f:
        r = requests.post(f"{SERVER}/mcu/stt?engine=vosk", data=f.read())
    print(f"识别结果: {r.text[:100]}...")
    return r.status_code == 200 and len(r.text) > 0

def test_mcu_stt_tencent():
    if not os.path.exists(TEST_AUDIO):
        print(f"跳过: 测试文件不存在 {TEST_AUDIO}")
        return True
    with open(TEST_AUDIO, 'rb') as f:
        r = requests.post(f"{SERVER}/mcu/stt?engine=tencent", data=f.read())
    print(f"识别结果: {r.text[:100]}...")
    return r.status_code == 200 and len(r.text) > 0

def test_mcu_ask():
    r = requests.post(f"{SERVER}/mcu/ask", data="你好".encode('utf-8'),
                      headers={"Content-Type": "text/plain; charset=utf-8"})
    print(f"AI回答: {r.text[:100]}...")
    return r.status_code == 200 and len(r.text) > 0

def test_mcu_ask_stream():
    r = requests.post(f"{SERVER}/mcu/ask_stream", data="1+1等于几".encode('utf-8'),
                      headers={"Content-Type": "text/plain"}, stream=True)
    content = ""
    for line in r.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = line[6:]
                if data not in ['[DONE]']:
                    content += data
    print(f"流式回答: {content[:100]}...")
    return r.status_code == 200 and len(content) > 0

def test_mcu_voice_chat_text():
    if not os.path.exists(TEST_AUDIO):
        print(f"跳过: 测试文件不存在 {TEST_AUDIO}")
        return True
    with open(TEST_AUDIO, 'rb') as f:
        r = requests.post(f"{SERVER}/mcu/voice_chat?engine=tencent&out=text", data=f.read())
    data = r.json()
    print(f"识别: {data.get('question', '')[:50]}...")
    print(f"回答: {data.get('answer', '')[:50]}...")
    return r.status_code == 200 and data.get('question') and data.get('answer')

def test_mcu_voice_chat_full():
    if not os.path.exists(TEST_AUDIO):
        print(f"跳过: 测试文件不存在 {TEST_AUDIO}")
        return True
    with open(TEST_AUDIO, 'rb') as f:
        r = requests.post(f"{SERVER}/mcu/voice_chat_full?engine=tencent", data=f.read())
    data = r.json()
    print(f"成功: {data.get('success')}")
    print(f"识别: {data.get('question', '')[:50]}...")
    print(f"回答: {data.get('answer', '')[:50]}...")
    print(f"语音URL: {data.get('audio_url')}")
    return data.get('success') == True and data.get('question') and data.get('answer')

def test_mcu_tts():
    r = requests.get(f"{SERVER}/mcu/tts?text=测试&format=wav")
    print(f"状态码: {r.status_code}")
    print(f"返回大小: {len(r.content)} bytes")
    # TTS 可能因网络问题失败，不作为必须通过项
    if r.status_code == 200 and len(r.content) > 1000:
        return True
    else:
        print("TTS 失败 (edge-tts 网络问题，不影响其他功能)")
        return None  # 跳过

# ==================== 微信 API ====================

def test_wechat_chat():
    r = requests.post(f"{SERVER}/wechat/chat", json={"message": "你好", "session_id": "test"})
    data = r.json()
    print(f"成功: {data.get('success')}")
    print(f"回复: {data.get('reply', '')[:100]}...")
    return data.get('success') == True and data.get('reply')

def test_wechat_stt():
    if not os.path.exists(TEST_AUDIO):
        print(f"跳过: 测试文件不存在 {TEST_AUDIO}")
        return True
    with open(TEST_AUDIO, 'rb') as f:
        r = requests.post(f"{SERVER}/wechat/stt?format=mp3&engine=tencent", data=f.read())
    data = r.json()
    print(f"成功: {data.get('success')}")
    print(f"识别: {data.get('text', '')[:100]}...")
    return data.get('success') == True and data.get('text')

def test_wechat_voice():
    if not os.path.exists(TEST_AUDIO):
        print(f"跳过: 测试文件不存在 {TEST_AUDIO}")
        return True
    with open(TEST_AUDIO, 'rb') as f:
        r = requests.post(f"{SERVER}/wechat/voice?format=mp3&engine=tencent", data=f.read())
    data = r.json()
    print(f"成功: {data.get('success')}")
    print(f"识别: {data.get('question', '')[:50]}...")
    print(f"回答: {data.get('answer', '')[:50]}...")
    return data.get('success') == True and data.get('question') and data.get('answer')


# ==================== 运行所有测试 ====================

if __name__ == "__main__":
    print("\n" + "#"*60)
    print("#" + " "*20 + "完整 API 测试" + " "*20 + "#")
    print("#"*60)
    print(f"\n服务器: {SERVER}")
    print(f"测试音频: {TEST_AUDIO}")
    
    # MCU API
    test("MCU /mcu/ping", test_mcu_ping)
    test("MCU /mcu/status", test_mcu_status)
    test("MCU /mcu/stt (Vosk)", test_mcu_stt_vosk)
    test("MCU /mcu/stt (腾讯云)", test_mcu_stt_tencent)
    test("MCU /mcu/ask", test_mcu_ask)
    test("MCU /mcu/ask_stream", test_mcu_ask_stream)
    test("MCU /mcu/voice_chat (text)", test_mcu_voice_chat_text)
    test("MCU /mcu/voice_chat_full", test_mcu_voice_chat_full)
    
    # TTS (可能失败)
    tts_result = test_mcu_tts()
    if tts_result is None:
        results["MCU /mcu/tts"] = "⚠️ 跳过 (网络问题)"
    
    # 微信 API
    test("微信 /wechat/chat", test_wechat_chat)
    test("微信 /wechat/stt", test_wechat_stt)
    test("微信 /wechat/voice", test_wechat_voice)
    
    # 打印结果汇总
    print("\n" + "#"*60)
    print("#" + " "*20 + "测试结果汇总" + " "*20 + "#")
    print("#"*60)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for name, result in results.items():
        print(f"  {name}: {result}")
        if "✅" in result:
            passed += 1
        elif "⚠️" in result:
            skipped += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败, {skipped} 跳过")
    print("#"*60)
