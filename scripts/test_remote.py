#!/usr/bin/env python3
"""
远程测试脚本 - 用于从其他电脑测试 Edge TTS Web Interface

使用方法:
    python scripts/test_remote.py <服务器IP>
    
示例:
    python scripts/test_remote.py 192.168.0.2
"""

import sys
import requests

def test_server(server_ip, port=3003):
    base_url = f"http://{server_ip}:{port}"
    print(f"\n{'='*50}")
    print(f"测试服务器: {base_url}")
    print(f"{'='*50}\n")
    
    tests = [
        ("健康检查", "GET", "/health", None),
        ("Ping 测试", "GET", "/mcu/ping", None),
        ("状态检查", "GET", "/mcu/status", None),
        ("TTS 测试", "GET", "/mcu/tts?text=你好世界&voice=xiaoxiao&format=mp3", None),
    ]
    
    passed = 0
    failed = 0
    
    for name, method, path, data in tests:
        try:
            url = f"{base_url}{path}"
            if method == "GET":
                r = requests.get(url, timeout=30)
            else:
                r = requests.post(url, data=data, timeout=30)
            
            if r.status_code == 200:
                print(f"✓ {name}: 成功 (状态码: {r.status_code})")
                if "tts" in path.lower():
                    print(f"  音频大小: {len(r.content)} 字节")
                elif r.headers.get('content-type', '').startswith('application/json'):
                    print(f"  响应: {r.json()}")
                else:
                    print(f"  响应: {r.text[:100]}...")
                passed += 1
            else:
                print(f"✗ {name}: 失败 (状态码: {r.status_code})")
                print(f"  响应: {r.text[:200]}")
                failed += 1
        except Exception as e:
            print(f"✗ {name}: 错误 - {e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print(f"{'='*50}\n")
    
    return failed == 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/test_remote.py <服务器IP> [端口]")
        print("示例: python scripts/test_remote.py 192.168.0.2")
        print("      python scripts/test_remote.py 192.168.0.2 3003")
        sys.exit(1)
    
    server_ip = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 3003
    
    success = test_server(server_ip, port)
    sys.exit(0 if success else 1)
