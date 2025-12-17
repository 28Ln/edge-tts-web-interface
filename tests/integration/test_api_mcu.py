"""
MCU API 集成测试
"""

import pytest
import io


class TestMCUAPI:
    """MCU API v1 测试"""

    def test_ping(self, client):
        """测试 ping 接口"""
        response = client.get('/mcu/ping')
        assert response.status_code == 200
        assert response.data == b'pong'

    def test_status(self, client):
        """测试状态接口"""
        response = client.get('/mcu/status')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'asr_engines' in data
        assert 'ai' in data
        assert 'tts' in data

    def test_stt_empty_audio(self, client):
        """测试空音频"""
        response = client.post('/mcu/stt')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error_code'] == 'VALIDATION_ERROR'

    def test_stt_with_engine_param(self, client):
        """测试 STT 引擎参数"""
        response = client.post('/mcu/stt?engine=vosk')
        assert response.status_code == 400  # 空音频

    def test_ask_empty_question(self, client):
        """测试空问题"""
        response = client.post('/mcu/ask')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_ask_with_session(self, client):
        """测试带会话的问答"""
        response = client.post('/mcu/ask?session=test123', data='')
        assert response.status_code == 400

    def test_tts_empty_text(self, client):
        """测试空文本"""
        response = client.get('/mcu/tts')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_tts_with_params(self, client):
        """测试 TTS 参数"""
        response = client.get('/mcu/tts?voice=yunxi&format=mp3')
        assert response.status_code == 400  # 空文本

    def test_voice_chat_empty(self, client):
        """测试空语音对话"""
        response = client.post('/mcu/voice_chat')
        assert response.status_code == 400


class TestMCUAPIV2:
    """MCU API v2 测试"""

    def test_v2_ping(self, client):
        """测试 v2 ping 接口"""
        response = client.get('/v2/mcu/ping')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['message'] == 'pong'

    def test_v2_status_anonymous(self, client):
        """测试 v2 状态接口（匿名）"""
        response = client.get('/v2/mcu/status')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['authenticated'] is False
        assert data['version'] == '2.0.0'

    def test_v2_stt_requires_auth(self, client):
        """测试 v2 STT 需要认证"""
        response = client.post('/v2/mcu/stt')
        assert response.status_code == 401
        data = response.get_json()
        assert data['error_code'] == 'AUTH_FAILED'

    def test_v2_ask_requires_auth(self, client):
        """测试 v2 问答需要认证"""
        response = client.post('/v2/mcu/ask', data='test question')
        assert response.status_code == 401

    def test_v2_tts_requires_auth(self, client):
        """测试 v2 TTS 需要认证"""
        response = client.get('/v2/mcu/tts?text=hello')
        assert response.status_code == 401

    def test_v2_voice_chat_requires_auth(self, client):
        """测试 v2 语音对话需要认证"""
        response = client.post('/v2/mcu/voice_chat')
        assert response.status_code == 401

    def test_v2_invalid_api_key(self, client):
        """测试无效 API Key"""
        response = client.post(
            '/v2/mcu/stt',
            headers={'X-API-Key': 'invalid-key'}
        )
        assert response.status_code == 401

    def test_v2_wrong_format_api_key(self, client):
        """测试格式错误的 API Key"""
        response = client.post(
            '/v2/mcu/stt',
            headers={'Authorization': 'Bearer wrong-format'}
        )
        assert response.status_code == 401


class TestHealthAPI:
    """健康检查 API 测试"""

    def test_health(self, client):
        """测试健康检查"""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'

    def test_health_ready(self, client):
        """测试就绪检查"""
        response = client.get('/health/ready')
        assert response.status_code == 200

    def test_health_live(self, client):
        """测试存活检查"""
        response = client.get('/health/live')
        assert response.status_code == 200


class TestOpenAPI:
    """OpenAPI 文档测试"""

    def test_openapi_json(self, client):
        """测试 OpenAPI JSON"""
        response = client.get('/openapi.json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['openapi'] == '3.0.3'
        assert 'paths' in data
        assert 'info' in data

    def test_swagger_ui(self, client):
        """测试 Swagger UI"""
        response = client.get('/docs')
        assert response.status_code == 200
        assert b'swagger-ui' in response.data


class TestErrorHandling:
    """错误处理测试"""

    def test_404(self, client):
        """测试 404"""
        response = client.get('/nonexistent')
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert data['error_code'] == 'NOT_FOUND'

    def test_method_not_allowed(self, client):
        """测试方法不允许"""
        response = client.delete('/mcu/ping')
        assert response.status_code == 405
