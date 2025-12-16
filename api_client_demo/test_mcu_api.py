"""
MCU API 测试脚本
用于在电脑上模拟 MCU 调用，测试所有接口

使用方法:
    1. 先启动服务器: python app.py
    2. 运行测试: python api_client_demo/test_mcu_api.py
"""

import requests
import os
import struct

# 服务器地址
BASE_URL = "http://127.0.0.1:2024"


def test_ping():
    """测试 1: 连接测试"""
    print("\n" + "=" * 50)
    print("测试 1: /mcu/ping - 连接测试")
    print("=" * 50)
    
    url = f"{BASE_URL}/mcu/ping"
    print(f"请求: GET {url}")
    
    try:
        resp = requests.get(url)
        print(f"状态码: {resp.status_code}")
        print(f"响应: {resp.text}")
        return resp.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_tts_get():
    """测试 2: TTS GET 方式"""
    print("\n" + "=" * 50)
    print("测试 2: /mcu/tts - 文字转语音 (GET)")
    print("=" * 50)
    
    text = "你好，我是语音助手"
    url = f"{BASE_URL}/mcu/tts?text={text}&format=wav"
    print(f"请求: GET {url}")
    
    try:
        resp = requests.get(url)
        print(f"状态码: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('Content-Type')}")
        print(f"音频大小: {len(resp.content)} bytes")
        
        if resp.status_code == 200:
            # 保存音频文件
            output_file = "api_client_demo/test_tts_output.wav"
            with open(output_file, 'wb') as f:
                f.write(resp.content)
            print(f"音频已保存: {output_file}")
            return True
    except Exception as e:
        print(f"错误: {e}")
    return False


def test_tts_post():
    """测试 3: TTS POST 方式"""
    print("\n" + "=" * 50)
    print("测试 3: /mcu/tts - 文字转语音 (POST JSON)")
    print("=" * 50)
    
    url = f"{BASE_URL}/mcu/tts"
    data = {"text": "这是POST方式的测试", "voice": "yunxi", "format": "wav"}
    print(f"请求: POST {url}")
    print(f"数据: {data}")
    
    try:
        resp = requests.post(url, json=data)
        print(f"状态码: {resp.status_code}")
        print(f"音频大小: {len(resp.content)} bytes")
        return resp.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
    return False


def test_stt_wav():
    """测试 4: STT 使用 WAV 文件"""
    print("\n" + "=" * 50)
    print("测试 4: /mcu/stt - 语音转文字 (WAV)")
    print("=" * 50)
    
    # 使用之前 TTS 生成的文件或项目中的测试文件
    test_files = [
        "api_client_demo/test_tts_output.wav",
        "uploads/input.wav",
        "static/测试.mp3"
    ]
    
    audio_file = None
    for f in test_files:
        if os.path.exists(f):
            audio_file = f
            break
    
    if not audio_file:
        print("未找到测试音频文件，跳过此测试")
        return False
    
    url = f"{BASE_URL}/mcu/stt?format=wav"
    print(f"请求: POST {url}")
    print(f"音频文件: {audio_file}")
    
    try:
        with open(audio_file, 'rb') as f:
            audio_data = f.read()
        
        resp = requests.post(
            url,
            data=audio_data,
            headers={"Content-Type": "application/octet-stream"}
        )
        print(f"状态码: {resp.status_code}")
        print(f"识别结果: {resp.text}")
        return resp.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
    return False


def test_stt_pcm():
    """测试 5: STT 使用 PCM 原始数据"""
    print("\n" + "=" * 50)
    print("测试 5: /mcu/stt - 语音转文字 (PCM)")
    print("=" * 50)
    
    # 生成一段静音 PCM 数据作为测试
    # 实际 MCU 会发送真实录音数据
    sample_rate = 16000
    duration = 1  # 1秒
    pcm_data = b'\x00\x00' * (sample_rate * duration)  # 16bit 静音
    
    url = f"{BASE_URL}/mcu/stt?format=pcm&rate=16000"
    print(f"请求: POST {url}")
    print(f"PCM 数据大小: {len(pcm_data)} bytes")
    
    try:
        resp = requests.post(
            url,
            data=pcm_data,
            headers={"Content-Type": "application/octet-stream"}
        )
        print(f"状态码: {resp.status_code}")
        print(f"识别结果: '{resp.text}' (静音数据，预期为空)")
        return resp.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
    return False


def test_ask_text():
    """测试 6: AI 文字问答 (纯文本)"""
    print("\n" + "=" * 50)
    print("测试 6: /mcu/ask - AI问答 (纯文本)")
    print("=" * 50)
    
    question = "你好，请用一句话介绍自己"
    url = f"{BASE_URL}/mcu/ask"
    print(f"请求: POST {url}")
    print(f"问题: {question}")
    
    try:
        resp = requests.post(
            url,
            data=question.encode('utf-8'),
            headers={"Content-Type": "text/plain; charset=utf-8"}
        )
        print(f"状态码: {resp.status_code}")
        print(f"AI回答: {resp.text[:200]}..." if len(resp.text) > 200 else f"AI回答: {resp.text}")
        return resp.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
    return False


def test_ask_json():
    """测试 7: AI 文字问答 (JSON)"""
    print("\n" + "=" * 50)
    print("测试 7: /mcu/ask - AI问答 (JSON)")
    print("=" * 50)
    
    url = f"{BASE_URL}/mcu/ask"
    data = {"question": "1+1等于几？"}
    print(f"请求: POST {url}")
    print(f"数据: {data}")
    
    try:
        resp = requests.post(url, json=data)
        print(f"状态码: {resp.status_code}")
        print(f"AI回答: {resp.text}")
        return resp.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
    return False


def test_voice_chat_text():
    """测试 8: 一站式语音对话 (返回文本)"""
    print("\n" + "=" * 50)
    print("测试 8: /mcu/voice_chat - 语音对话 (返回文本)")
    print("=" * 50)
    
    # 使用测试音频
    audio_file = "api_client_demo/test_tts_output.wav"
    if not os.path.exists(audio_file):
        audio_file = "uploads/input.wav"
    
    if not os.path.exists(audio_file):
        print("未找到测试音频文件，跳过此测试")
        return False
    
    url = f"{BASE_URL}/mcu/voice_chat?format=wav&out=text"
    print(f"请求: POST {url}")
    print(f"音频文件: {audio_file}")
    
    try:
        with open(audio_file, 'rb') as f:
            audio_data = f.read()
        
        resp = requests.post(
            url,
            data=audio_data,
            headers={"Content-Type": "application/octet-stream"}
        )
        print(f"状态码: {resp.status_code}")
        print(f"响应: {resp.text}")
        return resp.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
    return False


def test_voice_chat_audio():
    """测试 9: 一站式语音对话 (返回音频)"""
    print("\n" + "=" * 50)
    print("测试 9: /mcu/voice_chat - 语音对话 (返回音频)")
    print("=" * 50)
    
    audio_file = "api_client_demo/test_tts_output.wav"
    if not os.path.exists(audio_file):
        audio_file = "uploads/input.wav"
    
    if not os.path.exists(audio_file):
        print("未找到测试音频文件，跳过此测试")
        return False
    
    url = f"{BASE_URL}/mcu/voice_chat?format=wav&out=audio"
    print(f"请求: POST {url}")
    
    try:
        with open(audio_file, 'rb') as f:
            audio_data = f.read()
        
        resp = requests.post(
            url,
            data=audio_data,
            headers={"Content-Type": "application/octet-stream"}
        )
        print(f"状态码: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('Content-Type')}")
        print(f"音频大小: {len(resp.content)} bytes")
        
        if resp.status_code == 200 and len(resp.content) > 100:
            output_file = "api_client_demo/test_voice_chat_reply.wav"
            with open(output_file, 'wb') as f:
                f.write(resp.content)
            print(f"回复音频已保存: {output_file}")
            return True
    except Exception as e:
        print(f"错误: {e}")
    return False


def main():
    print("\n" + "#" * 60)
    print("#          MCU API 接口测试                              #")
    print("#" * 60)
    print(f"\n服务器地址: {BASE_URL}")
    print("请确保服务器已启动: python app.py\n")
    
    results = {}
    
    # 运行所有测试
    results["ping"] = test_ping()
    
    if not results["ping"]:
        print("\n❌ 服务器连接失败，请先启动服务器!")
        return
    
    results["tts_get"] = test_tts_get()
    results["tts_post"] = test_tts_post()
    results["stt_wav"] = test_stt_wav()
    results["stt_pcm"] = test_stt_pcm()
    results["ask_text"] = test_ask_text()
    results["ask_json"] = test_ask_json()
    results["voice_chat_text"] = test_voice_chat_text()
    results["voice_chat_audio"] = test_voice_chat_audio()
    
    # 打印结果汇总
    print("\n" + "#" * 60)
    print("#                    测试结果汇总                        #")
    print("#" * 60)
    
    passed = 0
    failed = 0
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败")


if __name__ == "__main__":
    main()
