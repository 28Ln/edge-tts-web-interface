#!/usr/bin/env python3
"""
语音对话测试脚本 - 测试 voice_chat 接口

使用方法:
    python scripts/test_voice_chat.py
"""

import io
import wave
import requests

def test_voice_chat():
    # 1. 生成模拟ESP32的音频（静音WAV）
    silence = b'\x00\x00' * 16000
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(silence)

    audio_data = wav_buffer.getvalue()
    print(f'发送音频大小: {len(audio_data)} bytes')

    # 2. 调用 voice_chat，返回音频
    r = requests.post('http://127.0.0.1:3003/mcu/voice_chat?out=audio', data=audio_data)
    print(f'状态码: {r.status_code}')
    print(f'返回音频大小: {len(r.content)} bytes')

    # 3. 保存返回的音频
    with open('data/test_out/test_response.wav', 'wb') as f:
        f.write(r.content)
    print('返回音频已保存: data/test_out/test_response.wav')

    # 4. 用ASR识别返回的音频，验证内容
    try:
        from src.services.asr_service import get_asr_service
        service = get_asr_service()
        service.debug_skip_recognize = False
        text = service.recognize(r.content, engine='tencent')
        print(f'识别返回音频内容: {text}')
    except Exception as e:
        print(f'ASR识别跳过: {e}')

if __name__ == "__main__":
    test_voice_chat()
