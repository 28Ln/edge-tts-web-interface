"""
API 完整性测试 - 边界条件和异常处理
测试所有 API 接口的边界条件、异常处理和多设备访问场景

运行方式:
    py -m pytest tests/e2e/test_api_completeness.py -v
    或指定服务器: SERVER_URL=http://IP:3003 py -m pytest tests/e2e/test_api_completeness.py -v
"""

import os
import pytest
import requests
import threading
import time
import concurrent.futures
from typing import List, Dict

SERVER = os.environ.get('SERVER_URL', 'http://127.0.0.1:3003')
TEST_AUDIO = "static/test.mp3"


# ==================== 健康检查 API 测试 ====================

class TestHealthAPICompleteness:
    """健康检查 API 完整性测试"""

    def test_health_basic(self):
        """基础健康检查"""
        r = requests.get(f"{SERVER}/health")
        assert r.status_code == 200
        data = r.json()
        assert data['status'] == 'healthy'
        assert 'timestamp' in data

    def test_health_ready(self):
        """就绪检查"""
        r = requests.get(f"{SERVER}/health/ready")
        assert r.status_code in [200, 503]  # 可能部分服务未就绪
        data = r.json()
        assert 'status' in data
        assert 'checks' in data

    def test_health_live(self):
        """存活检查"""
        r = requests.get(f"{SERVER}/health/live")
        assert r.status_code == 200
        data = r.json()
        assert data['status'] == 'alive'
        assert 'pid' in data

    def test_version(self):
        """版本信息"""
        r = requests.get(f"{SERVER}/version")
        assert r.status_code == 200
        data = r.json()
        assert 'version' in data
        assert 'name' in data


# ==================== MCU API v1 边界测试 ====================

class TestMCUAPIBoundary:
    """MCU API v1 边界条件测试"""

    # --- ping/status ---
    def test_ping_method_not_allowed(self):
        """ping 不支持 POST"""
        r = requests.post(f"{SERVER}/mcu/ping")
        assert r.status_code == 405

    def test_status_method_not_allowed(self):
        """status 不支持 POST"""
        r = requests.post(f"{SERVER}/mcu/status")
        assert r.status_code == 405

    # --- STT 边界测试 ---
    def test_stt_empty_body(self):
        """STT 空请求体"""
        r = requests.post(f"{SERVER}/mcu/stt")
        assert r.status_code == 400
        data = r.json()
        assert data['success'] is False
        assert data['error_code'] == 'VALIDATION_ERROR'

    def test_stt_invalid_engine(self):
        """STT 无效引擎"""
        r = requests.post(
            f"{SERVER}/mcu/stt?engine=invalid_engine",
            data=b'fake_audio_data'
        )
        # 应该返回错误（引擎不可用或识别失败）
        assert r.status_code in [400, 500, 503]

    def test_stt_unsupported_format(self):
        """STT 不支持的格式"""
        r = requests.post(
            f"{SERVER}/mcu/stt?format=xyz",
            data=b'fake_audio_data'
        )
        # 可能返回格式错误或识别失败
        assert r.status_code in [400, 500]

    def test_stt_large_audio_rejection(self):
        """STT 超大音频拒绝（>10MB）"""
        # 生成 11MB 数据
        large_data = b'x' * (11 * 1024 * 1024)
        r = requests.post(f"{SERVER}/mcu/stt", data=large_data)
        assert r.status_code == 400
        data = r.json()
        assert 'error_code' in data

    # --- ASK 边界测试 ---
    def test_ask_empty_question(self):
        """ASK 空问题"""
        r = requests.post(f"{SERVER}/mcu/ask", data='')
        assert r.status_code == 400
        data = r.json()
        assert data['success'] is False

    def test_ask_whitespace_only(self):
        """ASK 仅空白字符"""
        r = requests.post(
            f"{SERVER}/mcu/ask",
            data='   \n\t  ',
            headers={"Content-Type": "text/plain; charset=utf-8"}
        )
        assert r.status_code == 400

    def test_ask_very_long_question(self):
        """ASK 超长问题（>1000字符）"""
        long_question = '测试' * 600  # 1200 字符
        r = requests.post(
            f"{SERVER}/mcu/ask",
            data=long_question.encode('utf-8'),
            headers={"Content-Type": "text/plain; charset=utf-8"}
        )
        assert r.status_code == 400
        data = r.json()
        assert 'error_code' in data

    def test_ask_json_format(self):
        """ASK JSON 格式"""
        r = requests.post(
            f"{SERVER}/mcu/ask",
            json={"question": "你好", "session": "test_session"}
        )
        assert r.status_code == 200
        assert len(r.text) > 0

    def test_ask_invalid_json(self):
        """ASK 无效 JSON"""
        r = requests.post(
            f"{SERVER}/mcu/ask",
            data='{invalid json}',
            headers={"Content-Type": "application/json"}
        )
        assert r.status_code == 400

    def test_ask_stream_empty(self):
        """ASK_STREAM 空问题"""
        r = requests.post(f"{SERVER}/mcu/ask_stream", data='')
        assert r.status_code == 400

    # --- TTS 边界测试 ---
    def test_tts_empty_text(self):
        """TTS 空文本"""
        r = requests.get(f"{SERVER}/mcu/tts")
        assert r.status_code == 400

    def test_tts_whitespace_only(self):
        """TTS 仅空白字符"""
        r = requests.get(f"{SERVER}/mcu/tts?text=%20%20%20")
        assert r.status_code == 400

    def test_tts_very_long_text(self):
        """TTS 超长文本（>5000字符）"""
        long_text = '测试' * 3000  # 6000 字符
        r = requests.post(
            f"{SERVER}/mcu/tts",
            json={"text": long_text}
        )
        assert r.status_code == 400

    def test_tts_invalid_format(self):
        """TTS 无效格式"""
        r = requests.get(f"{SERVER}/mcu/tts?text=hello&format=ogg")
        assert r.status_code == 400

    def test_tts_invalid_voice(self):
        """TTS 无效语音（应该有默认处理）"""
        r = requests.get(f"{SERVER}/mcu/tts?text=hello&voice=nonexistent")
        # 可能使用默认语音或返回错误
        assert r.status_code in [200, 400, 500]

    def test_tts_post_method(self):
        """TTS POST 方法"""
        r = requests.post(
            f"{SERVER}/mcu/tts",
            json={"text": "你好", "voice": "xiaoxiao", "format": "wav"}
        )
        assert r.status_code == 200
        assert r.headers.get('Content-Type') in ['audio/wav', 'audio/x-wav']

    def test_tts_with_rate_volume(self):
        """TTS 带语速和音量参数"""
        r = requests.post(
            f"{SERVER}/mcu/tts",
            json={"text": "你好", "rate": 10, "volume": 50}
        )
        assert r.status_code == 200

    # --- VOICE_CHAT 边界测试 ---
    def test_voice_chat_empty_audio(self):
        """VOICE_CHAT 空音频"""
        r = requests.post(f"{SERVER}/mcu/voice_chat")
        assert r.status_code == 400

    def test_voice_chat_invalid_output_type(self):
        """VOICE_CHAT 无效输出类型"""
        r = requests.post(
            f"{SERVER}/mcu/voice_chat?out=invalid",
            data=b'fake_audio'
        )
        assert r.status_code == 400

    def test_voice_chat_large_audio(self):
        """VOICE_CHAT 超大音频"""
        large_data = b'x' * (11 * 1024 * 1024)
        r = requests.post(f"{SERVER}/mcu/voice_chat", data=large_data)
        assert r.status_code == 400


# ==================== MCU API v2 认证测试 ====================

class TestMCUAPIV2Auth:
    """MCU API v2 认证测试"""

    def test_v2_ping_no_auth(self):
        """v2 ping 无需认证"""
        r = requests.get(f"{SERVER}/v2/mcu/ping")
        assert r.status_code == 200
        data = r.json()
        assert data['success'] is True

    def test_v2_status_no_auth(self):
        """v2 status 无需认证（匿名模式）"""
        r = requests.get(f"{SERVER}/v2/mcu/status")
        assert r.status_code == 200
        data = r.json()
        assert data['authenticated'] is False

    def test_v2_stt_requires_auth(self):
        """v2 STT 需要认证"""
        r = requests.post(f"{SERVER}/v2/mcu/stt", data=b'audio')
        assert r.status_code == 401
        data = r.json()
        assert data['error_code'] == 'AUTH_FAILED'

    def test_v2_ask_requires_auth(self):
        """v2 ASK 需要认证"""
        r = requests.post(f"{SERVER}/v2/mcu/ask", data='question')
        assert r.status_code == 401

    def test_v2_tts_requires_auth(self):
        """v2 TTS 需要认证"""
        r = requests.get(f"{SERVER}/v2/mcu/tts?text=hello")
        assert r.status_code == 401

    def test_v2_voice_chat_requires_auth(self):
        """v2 VOICE_CHAT 需要认证"""
        r = requests.post(f"{SERVER}/v2/mcu/voice_chat", data=b'audio')
        assert r.status_code == 401

    def test_v2_invalid_api_key(self):
        """v2 无效 API Key"""
        r = requests.post(
            f"{SERVER}/v2/mcu/stt",
            data=b'audio',
            headers={"X-API-Key": "invalid-key-12345"}
        )
        assert r.status_code == 401

    def test_v2_empty_api_key(self):
        """v2 空 API Key"""
        r = requests.post(
            f"{SERVER}/v2/mcu/stt",
            data=b'audio',
            headers={"X-API-Key": ""}
        )
        assert r.status_code == 401

    def test_v2_bearer_token_format(self):
        """v2 Bearer Token 格式"""
        r = requests.post(
            f"{SERVER}/v2/mcu/stt",
            data=b'audio',
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert r.status_code == 401


# ==================== 微信 API 测试 ====================

class TestWechatAPICompleteness:
    """微信 API 完整性测试"""

    def test_chat_empty_message(self):
        """chat 空消息"""
        r = requests.post(
            f"{SERVER}/wechat/chat",
            json={"message": "", "session_id": "test"}
        )
        assert r.status_code == 400

    def test_chat_missing_message(self):
        """chat 缺少消息字段"""
        r = requests.post(
            f"{SERVER}/wechat/chat",
            json={"session_id": "test"}
        )
        assert r.status_code == 400

    def test_chat_long_message(self):
        """chat 超长消息"""
        long_msg = '测试' * 1500  # 3000 字符，超过 2000 限制
        r = requests.post(
            f"{SERVER}/wechat/chat",
            json={"message": long_msg, "session_id": "test"}
        )
        assert r.status_code == 400

    def test_chat_invalid_json(self):
        """chat 无效 JSON"""
        r = requests.post(
            f"{SERVER}/wechat/chat",
            data='{invalid}',
            headers={"Content-Type": "application/json"}
        )
        assert r.status_code == 400

    def test_chat_success(self):
        """chat 成功"""
        r = requests.post(
            f"{SERVER}/wechat/chat",
            json={"message": "你好", "session_id": "test_session"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data['success'] is True
        assert 'reply' in data

    def test_stt_empty_audio(self):
        """STT 空音频"""
        r = requests.post(f"{SERVER}/wechat/stt")
        # 微信 STT 返回空文本而不是错误
        assert r.status_code == 200
        data = r.json()
        assert data['success'] is True
        assert data['text'] == ''

    def test_voice_empty_audio(self):
        """voice 空音频"""
        r = requests.post(f"{SERVER}/wechat/voice")
        assert r.status_code == 400


# ==================== 认证 API 测试 ====================

class TestAuthAPICompleteness:
    """认证 API 完整性测试"""

    def test_register_empty_username(self):
        """注册空用户名"""
        r = requests.post(
            f"{SERVER}/auth/register",
            json={"username": "", "email": "test@test.com", "password": "123456"}
        )
        assert r.status_code == 400

    def test_register_empty_email(self):
        """注册空邮箱"""
        r = requests.post(
            f"{SERVER}/auth/register",
            json={"username": "testuser", "email": "", "password": "123456"}
        )
        assert r.status_code == 400

    def test_register_empty_password(self):
        """注册空密码"""
        r = requests.post(
            f"{SERVER}/auth/register",
            json={"username": "testuser", "email": "test@test.com", "password": ""}
        )
        assert r.status_code == 400

    def test_login_empty_username(self):
        """登录空用户名"""
        r = requests.post(
            f"{SERVER}/auth/login",
            json={"username": "", "password": "123456"}
        )
        assert r.status_code == 400

    def test_login_empty_password(self):
        """登录空密码"""
        r = requests.post(
            f"{SERVER}/auth/login",
            json={"username": "testuser", "password": ""}
        )
        assert r.status_code == 400

    def test_login_invalid_credentials(self):
        """登录无效凭证"""
        r = requests.post(
            f"{SERVER}/auth/login",
            json={"username": "nonexistent_user_xyz", "password": "wrongpass"}
        )
        assert r.status_code == 401

    def test_profile_no_auth(self):
        """获取资料无认证"""
        r = requests.get(f"{SERVER}/auth/profile")
        assert r.status_code == 401

    def test_change_password_no_auth(self):
        """修改密码无认证"""
        r = requests.post(
            f"{SERVER}/auth/change-password",
            json={"old_password": "old", "new_password": "new"}
        )
        assert r.status_code == 401

    def test_refresh_no_auth(self):
        """刷新 Token 无认证"""
        r = requests.post(f"{SERVER}/auth/refresh")
        assert r.status_code == 401


# ==================== 计费 API 测试 ====================

class TestBillingAPICompleteness:
    """计费 API 完整性测试"""

    def test_plans_list(self):
        """获取套餐列表"""
        r = requests.get(f"{SERVER}/billing/plans")
        assert r.status_code == 200
        data = r.json()
        assert data['success'] is True
        assert 'plans' in data

    def test_plan_not_found(self):
        """获取不存在的套餐"""
        r = requests.get(f"{SERVER}/billing/plans/99999")
        assert r.status_code == 404

    def test_pricing_info(self):
        """获取定价信息"""
        r = requests.get(f"{SERVER}/billing/pricing")
        assert r.status_code == 200
        data = r.json()
        assert data['success'] is True

    def test_subscription_no_auth(self):
        """获取订阅无认证"""
        r = requests.get(f"{SERVER}/billing/subscription")
        assert r.status_code == 401

    def test_subscribe_no_auth(self):
        """订阅无认证"""
        r = requests.post(
            f"{SERVER}/billing/subscribe",
            json={"plan": "basic"}
        )
        assert r.status_code == 401

    def test_balance_no_auth(self):
        """获取余额无认证"""
        r = requests.get(f"{SERVER}/billing/balance")
        assert r.status_code == 401

    def test_quota_no_auth(self):
        """获取配额无认证"""
        r = requests.get(f"{SERVER}/billing/quota")
        assert r.status_code == 401


# ==================== 错误处理测试 ====================

class TestErrorHandling:
    """错误处理测试"""

    def test_404_not_found(self):
        """404 错误"""
        r = requests.get(f"{SERVER}/nonexistent/path")
        assert r.status_code == 404
        data = r.json()
        assert data['success'] is False
        assert data['error_code'] == 'NOT_FOUND'

    def test_405_method_not_allowed(self):
        """405 错误"""
        r = requests.delete(f"{SERVER}/mcu/ping")
        assert r.status_code == 405
        data = r.json()
        assert data['success'] is False
        assert data['error_code'] == 'METHOD_NOT_ALLOWED'

    def test_error_response_format(self):
        """错误响应格式一致性"""
        r = requests.post(f"{SERVER}/mcu/ask", data='')
        assert r.status_code == 400
        data = r.json()
        # 验证错误响应格式
        assert 'success' in data
        assert 'error_code' in data
        assert 'message' in data
        assert data['success'] is False


# ==================== 多设备并发访问测试 ====================

class TestConcurrentAccess:
    """多设备并发访问测试"""

    def test_concurrent_ping(self):
        """并发 ping 测试"""
        def ping():
            r = requests.get(f"{SERVER}/mcu/ping", timeout=10)
            return r.status_code == 200 and r.text == 'pong'
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(ping) for _ in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        assert all(results), "部分并发请求失败"

    def test_concurrent_status(self):
        """并发状态查询"""
        def get_status():
            r = requests.get(f"{SERVER}/mcu/status", timeout=10)
            return r.status_code == 200
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_status) for _ in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        assert all(results), "部分并发请求失败"

    def test_concurrent_health(self):
        """并发健康检查"""
        def health_check():
            r = requests.get(f"{SERVER}/health", timeout=10)
            return r.status_code == 200
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(health_check) for _ in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.95, f"并发成功率过低: {success_rate:.2%}"

    def test_concurrent_ask(self):
        """并发 AI 问答"""
        def ask_question(q):
            try:
                r = requests.post(
                    f"{SERVER}/mcu/ask",
                    data=q.encode('utf-8'),
                    headers={"Content-Type": "text/plain; charset=utf-8"},
                    timeout=30
                )
                return r.status_code == 200
            except:
                return False
        
        questions = [f"问题{i}" for i in range(10)]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(ask_question, q) for q in questions]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.8, f"并发问答成功率过低: {success_rate:.2%}"

    def test_different_sessions(self):
        """不同会话隔离测试"""
        sessions = ['session_a', 'session_b', 'session_c']
        results = {}
        
        def ask_with_session(session_id, question):
            r = requests.post(
                f"{SERVER}/mcu/ask?session={session_id}",
                data=question.encode('utf-8'),
                headers={"Content-Type": "text/plain; charset=utf-8"},
                timeout=30
            )
            return r.status_code == 200
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(ask_with_session, s, f"你好，我是{s}"): s 
                for s in sessions
            }
            for future in concurrent.futures.as_completed(futures):
                session = futures[future]
                results[session] = future.result()
        
        assert all(results.values()), "会话隔离测试失败"


# ==================== OpenAPI 文档测试 ====================

class TestOpenAPIDoc:
    """OpenAPI 文档测试"""

    def test_openapi_json(self):
        """OpenAPI JSON 可访问"""
        r = requests.get(f"{SERVER}/openapi.json")
        assert r.status_code == 200
        data = r.json()
        assert 'openapi' in data
        assert 'paths' in data
        assert 'info' in data

    def test_swagger_ui(self):
        """Swagger UI 可访问"""
        r = requests.get(f"{SERVER}/docs")
        assert r.status_code == 200
        assert 'swagger' in r.text.lower() or 'openapi' in r.text.lower()


# ==================== 超时和重试测试 ====================

class TestTimeoutAndRetry:
    """超时和重试测试"""

    def test_request_timeout_handling(self):
        """请求超时处理"""
        # 使用较短超时测试服务器响应
        try:
            r = requests.get(f"{SERVER}/health", timeout=1)
            assert r.status_code == 200
        except requests.exceptions.Timeout:
            pytest.fail("健康检查超时")

    def test_connection_refused_handling(self):
        """连接拒绝处理"""
        # 测试连接到不存在的端口
        with pytest.raises(requests.exceptions.ConnectionError):
            requests.get("http://127.0.0.1:59999/health", timeout=2)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
