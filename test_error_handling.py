#!/usr/bin/env python
"""
异常处理和日志测试脚本
测试所有 API 接口的错误处理和日志输出
"""

import requests
import json
import time

BASE_URL = "http://localhost:3003"

def print_test(name):
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print('='*60)

def test_mcu_api():
    """测试 MCU API v1"""
    
    # 1. 测试 ping
    print_test("MCU API - Ping")
    r = requests.get(f"{BASE_URL}/mcu/ping")
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.text}")
    
    # 2. 测试 status
    print_test("MCU API - Status")
    r = requests.get(f"{BASE_URL}/mcu/status")
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")
    
    # 3. 测试 STT - 空音频（应该返回 400）
    print_test("MCU API - STT 空音频")
    r = requests.post(f"{BASE_URL}/mcu/stt")
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")
    
    # 4. 测试 STT - 音频过大（应该返回 400）
    print_test("MCU API - STT 音频过大")
    large_audio = b'x' * (11 * 1024 * 1024)  # 11MB
    r = requests.post(f"{BASE_URL}/mcu/stt", data=large_audio)
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")
    
    # 5. 测试 Ask - 空问题（应该返回 400）
    print_test("MCU API - Ask 空问题")
    r = requests.post(f"{BASE_URL}/mcu/ask", data="")
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")
    
    # 6. 测试 Ask - 问题过长（应该返回 400）
    print_test("MCU API - Ask 问题过长")
    long_question = "x" * 1001
    r = requests.post(f"{BASE_URL}/mcu/ask", data=long_question)
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")
    
    # 7. 测试 Ask - JSON 格式错误（应该返回 400）
    print_test("MCU API - Ask JSON 格式错误")
    r = requests.post(
        f"{BASE_URL}/mcu/ask",
        data="{invalid json}",
        headers={"Content-Type": "application/json"}
    )
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")
    
    # 8. 测试 TTS - 空文本（应该返回 400）
    print_test("MCU API - TTS 空文本")
    r = requests.get(f"{BASE_URL}/mcu/tts")
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")
    
    # 9. 测试 TTS - 文本过长（应该返回 400）
    print_test("MCU API - TTS 文本过长")
    long_text = "x" * 5001
    r = requests.get(f"{BASE_URL}/mcu/tts?text={long_text}")
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")
    
    # 10. 测试 TTS - 不支持的格式（应该返回 400）
    print_test("MCU API - TTS 不支持的格式")
    r = requests.get(f"{BASE_URL}/mcu/tts?text=hello&format=ogg")
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")

def test_wechat_api():
    """测试微信 API"""
    
    # 1. 测试 Chat - 空消息（应该返回 400）
    print_test("微信 API - Chat 空消息")
    r = requests.post(
        f"{BASE_URL}/wechat/chat",
        json={"message": "", "session_id": "test"}
    )
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")
    
    # 2. 测试 Chat - JSON 格式错误（应该返回 400）
    print_test("微信 API - Chat JSON 格式错误")
    r = requests.post(
        f"{BASE_URL}/wechat/chat",
        data="{invalid json}",
        headers={"Content-Type": "application/json"}
    )
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")
    
    # 3. 测试 Chat - 消息过长（应该返回 400）
    print_test("微信 API - Chat 消息过长")
    long_message = "x" * 2001
    r = requests.post(
        f"{BASE_URL}/wechat/chat",
        json={"message": long_message}
    )
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")
    
    # 4. 测试 Voice - 空音频（应该返回 400）
    print_test("微信 API - Voice 空音频")
    r = requests.post(f"{BASE_URL}/wechat/voice")
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")
    
    # 5. 测试 Voice - 音频过大（应该返回 400）
    print_test("微信 API - Voice 音频过大")
    large_audio = b'x' * (11 * 1024 * 1024)  # 11MB
    r = requests.post(f"{BASE_URL}/wechat/voice", data=large_audio)
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")

def test_v2_api():
    """测试 MCU API v2 认证"""
    
    # 1. 测试无认证访问（应该返回 401）
    print_test("MCU API v2 - 无认证")
    r = requests.post(f"{BASE_URL}/v2/mcu/stt")
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")
    
    # 2. 测试无效 API Key（应该返回 401）
    print_test("MCU API v2 - 无效 API Key")
    r = requests.post(
        f"{BASE_URL}/v2/mcu/stt",
        headers={"X-API-Key": "invalid-key"}
    )
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")

def main():
    print("="*60)
    print("异常处理和日志测试")
    print("="*60)
    print(f"服务器: {BASE_URL}")
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 测试 MCU API
        test_mcu_api()
        
        # 测试微信 API
        test_wechat_api()
        
        # 测试 v2 API
        test_v2_api()
        
        print("\n" + "="*60)
        print("测试完成！请查看服务器日志验证：")
        print("1. 所有错误都有详细的日志记录")
        print("2. 所有请求都记录了耗时")
        print("3. 错误类型正确分类（ValidationError, ASRError 等）")
        print("4. 日志格式统一，包含模块、操作、参数、耗时")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 错误: 无法连接到服务器")
        print(f"请确保服务器运行在 {BASE_URL}")
        print("运行命令: python app.py")

if __name__ == "__main__":
    main()
