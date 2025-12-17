"""
微信 API 集成测试
"""

import pytest


class TestWechatAPI:
    """微信 API 测试"""

    def test_chat_empty_message(self, client):
        """测试空消息"""
        response = client.post('/wechat/chat', json={
            "message": "",
            "session_id": "test"
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_chat_missing_message(self, client):
        """测试缺少消息字段"""
        response = client.post('/wechat/chat', json={
            "session_id": "test"
        })
        assert response.status_code == 400

    def test_stt_empty_audio(self, client):
        """测试空音频"""
        response = client.post('/wechat/stt')
        assert response.status_code == 400

    def test_voice_empty_audio(self, client):
        """测试空语音"""
        response = client.post('/wechat/voice')
        assert response.status_code == 400

    def test_callback_get_invalid_signature(self, client):
        """测试无效签名"""
        response = client.get('/wechat/callback?signature=invalid&timestamp=123&nonce=456&echostr=test')
        assert response.status_code == 403
