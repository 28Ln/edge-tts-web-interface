"""
多设备访问和负载测试
模拟多个设备同时访问 API 的场景

运行方式:
    py -m pytest tests/e2e/test_multidevice.py -v
    或指定服务器: SERVER_URL=http://IP:3003 py -m pytest tests/e2e/test_multidevice.py -v
"""

import os
import pytest
import requests
import threading
import time
import random
import concurrent.futures
from collections import Counter

SERVER = os.environ.get('SERVER_URL', 'http://127.0.0.1:3003')


class TestMultiDeviceAccess:
    """多设备访问测试"""

    def test_simultaneous_device_connections(self):
        """模拟多设备同时连接"""
        num_devices = 20
        results = []
        errors = []
        
        def device_connect(device_id):
            try:
                # 模拟设备连接流程
                # 1. 健康检查
                r1 = requests.get(f"{SERVER}/health", timeout=10)
                if r1.status_code != 200:
                    return False, f"Device {device_id}: health check failed"
                
                # 2. 获取状态
                r2 = requests.get(f"{SERVER}/mcu/status", timeout=10)
                if r2.status_code != 200:
                    return False, f"Device {device_id}: status check failed"
                
                # 3. ping 测试
                r3 = requests.get(f"{SERVER}/mcu/ping", timeout=10)
                if r3.status_code != 200 or r3.text != 'pong':
                    return False, f"Device {device_id}: ping failed"
                
                return True, f"Device {device_id}: connected successfully"
            except Exception as e:
                return False, f"Device {device_id}: {str(e)}"
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_devices) as executor:
            futures = [executor.submit(device_connect, i) for i in range(num_devices)]
            for future in concurrent.futures.as_completed(futures):
                success, msg = future.result()
                results.append(success)
                if not success:
                    errors.append(msg)
        
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.95, f"设备连接成功率过低: {success_rate:.2%}, 错误: {errors[:5]}"

    def test_mixed_api_calls(self):
        """混合 API 调用测试"""
        num_requests = 50
        results = Counter()
        
        def random_api_call():
            try:
                choice = random.choice(['ping', 'status', 'health', 'version'])
                
                if choice == 'ping':
                    r = requests.get(f"{SERVER}/mcu/ping", timeout=10)
                    return 'ping', r.status_code == 200
                elif choice == 'status':
                    r = requests.get(f"{SERVER}/mcu/status", timeout=10)
                    return 'status', r.status_code == 200
                elif choice == 'health':
                    r = requests.get(f"{SERVER}/health", timeout=10)
                    return 'health', r.status_code == 200
                else:
                    r = requests.get(f"{SERVER}/version", timeout=10)
                    return 'version', r.status_code == 200
            except Exception as e:
                return 'error', False
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(random_api_call) for _ in range(num_requests)]
            for future in concurrent.futures.as_completed(futures):
                api, success = future.result()
                results[f"{api}_{'success' if success else 'fail'}"] += 1
        
        total_success = sum(v for k, v in results.items() if 'success' in k)
        total = sum(results.values())
        success_rate = total_success / total
        
        assert success_rate >= 0.9, f"混合 API 调用成功率过低: {success_rate:.2%}, 详情: {dict(results)}"

    def test_session_isolation(self):
        """会话隔离测试 - 确保不同设备的会话互不影响"""
        num_sessions = 5
        session_data = {}
        
        def session_test(session_id):
            try:
                # 发送带会话的请求
                r = requests.post(
                    f"{SERVER}/mcu/ask?session={session_id}",
                    data=f"我是设备{session_id}".encode('utf-8'),
                    headers={"Content-Type": "text/plain; charset=utf-8"},
                    timeout=30
                )
                return session_id, r.status_code == 200, r.text
            except Exception as e:
                return session_id, False, str(e)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_sessions) as executor:
            futures = [executor.submit(session_test, f"device_{i}") for i in range(num_sessions)]
            for future in concurrent.futures.as_completed(futures):
                session_id, success, response = future.result()
                session_data[session_id] = {'success': success, 'response': response}
        
        # 验证所有会话都成功
        success_count = sum(1 for v in session_data.values() if v['success'])
        assert success_count >= num_sessions * 0.8, f"会话测试成功率过低: {success_count}/{num_sessions}"

    def test_rapid_reconnection(self):
        """快速重连测试"""
        num_reconnects = 10
        results = []
        
        for i in range(num_reconnects):
            try:
                r = requests.get(f"{SERVER}/mcu/ping", timeout=5)
                results.append(r.status_code == 200)
                time.sleep(0.1)  # 短暂间隔
            except:
                results.append(False)
        
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.9, f"快速重连成功率过低: {success_rate:.2%}"

    def test_burst_requests(self):
        """突发请求测试"""
        burst_size = 30
        results = []
        
        def burst_request():
            try:
                r = requests.get(f"{SERVER}/health", timeout=10)
                return r.status_code == 200
            except:
                return False
        
        # 同时发送大量请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=burst_size) as executor:
            futures = [executor.submit(burst_request) for _ in range(burst_size)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.85, f"突发请求成功率过低: {success_rate:.2%}"


class TestLoadHandling:
    """负载处理测试"""

    def test_sustained_load(self):
        """持续负载测试"""
        duration = 5  # 秒
        requests_per_second = 10
        results = []
        
        start_time = time.time()
        
        def make_request():
            try:
                r = requests.get(f"{SERVER}/mcu/ping", timeout=5)
                return r.status_code == 200
            except:
                return False
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            while time.time() - start_time < duration:
                futures = [executor.submit(make_request) for _ in range(requests_per_second)]
                for f in concurrent.futures.as_completed(futures):
                    results.append(f.result())
                time.sleep(1)
        
        success_rate = sum(results) / len(results) if results else 0
        assert success_rate >= 0.9, f"持续负载成功率过低: {success_rate:.2%}"

    def test_response_time_under_load(self):
        """负载下响应时间测试"""
        num_requests = 20
        response_times = []
        
        def timed_request():
            start = time.time()
            try:
                r = requests.get(f"{SERVER}/health", timeout=10)
                elapsed = time.time() - start
                return r.status_code == 200, elapsed
            except:
                return False, None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(timed_request) for _ in range(num_requests)]
            for f in concurrent.futures.as_completed(futures):
                success, elapsed = f.result()
                if success and elapsed:
                    response_times.append(elapsed)
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            
            # 平均响应时间应小于 2 秒
            assert avg_time < 2.0, f"平均响应时间过长: {avg_time:.2f}s"
            # 最大响应时间应小于 5 秒
            assert max_time < 5.0, f"最大响应时间过长: {max_time:.2f}s"


class TestErrorRecovery:
    """错误恢复测试"""

    def test_invalid_request_recovery(self):
        """无效请求后恢复"""
        # 发送无效请求
        r1 = requests.post(f"{SERVER}/mcu/stt", data=b'')
        assert r1.status_code == 400
        
        # 验证服务仍然正常
        r2 = requests.get(f"{SERVER}/mcu/ping")
        assert r2.status_code == 200
        assert r2.text == 'pong'

    def test_large_payload_recovery(self):
        """大负载请求后恢复"""
        # 发送超大请求（应被拒绝）
        large_data = b'x' * (11 * 1024 * 1024)
        r1 = requests.post(f"{SERVER}/mcu/stt", data=large_data)
        assert r1.status_code == 400
        
        # 验证服务仍然正常
        r2 = requests.get(f"{SERVER}/health")
        assert r2.status_code == 200

    def test_malformed_json_recovery(self):
        """畸形 JSON 后恢复"""
        # 发送畸形 JSON
        r1 = requests.post(
            f"{SERVER}/mcu/ask",
            data='{invalid json content',
            headers={"Content-Type": "application/json"}
        )
        assert r1.status_code == 400
        
        # 验证服务仍然正常
        r2 = requests.get(f"{SERVER}/mcu/status")
        assert r2.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
