"""
完整 API 端到端测试
需要启动服务器后运行: py -m pytest tests/e2e/ -v

使用方法:
    1. 启动服务器: py app.py
    2. 运行测试: py -m pytest tests/e2e/test_full_api.py -v
    或指定服务器: SERVER_URL=http://IP:3003 py -m pytest tests/e2e/ -v
"""

import os
import pytest
import requests

SERVER = os.environ.get('SERVER_URL', 'http://127.0.0.1:3003')
TEST_AUDIO = "static/test.mp3"


class TestMCUAPI:
    """MCU API 端到端测试"""

    def test_ping(self):
        """测试连接"""
        r = requests.get(f"{SERVER}/mcu/ping")
        assert r.status_code == 200
        assert r.text == "pong"

    def test_status(self):
        """测试状态"""
        r = requests.get(f"{SERVER}/mcu/status")
        assert r.status_code == 200
        data = r.json()
        assert 'asr_engines' in data
        assert 'ai' in data

    @pytest.mark.skipif(not os.path.exists(TEST_AUDIO), reason="测试音频不存在")
    def test_stt_tencent(self):
        """测试腾讯云语音识别"""
        with open(TEST_AUDIO, 'rb') as f:
            r = requests.post(f"{SERVER}/mcu/stt?engine=tencent", data=f.read())
        assert r.status_code == 200
        assert len(r.text) > 0

    def test_ask(self):
        """测试 AI 问答"""
        r = requests.post(
            f"{SERVER}/mcu/ask",
            data="你好".encode('utf-8'),
            headers={"Content-Type": "text/plain; charset=utf-8"}
        )
        assert r.status_code == 200
        assert len(r.text) > 0

    def test_ask_stream(self):
        """测试 AI 流式问答"""
        r = requests.post(
            f"{SERVER}/mcu/ask_stream",
            data="1+1等于几".encode('utf-8'),
            headers={"Content-Type": "text/plain"},
            stream=True
        )
        assert r.status_code == 200
        content = ""
        for line in r.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]
                    if data not in ['[DONE]'] and not data.startswith('[ERROR]'):
                        content += data
        assert len(content) > 0

    @pytest.mark.skipif(not os.path.exists(TEST_AUDIO), reason="测试音频不存在")
    def test_voice_chat_text(self):
        """测试语音对话（返回文本）"""
        with open(TEST_AUDIO, 'rb') as f:
            r = requests.post(
                f"{SERVER}/mcu/voice_chat?engine=tencent&out=text",
                data=f.read()
            )
        assert r.status_code == 200
        data = r.json()
        assert data.get('question')
        assert data.get('answer')


class TestWechatAPI:
    """微信 API 端到端测试"""

    def test_chat(self):
        """测试文字对话"""
        r = requests.post(
            f"{SERVER}/wechat/chat",
            json={"message": "你好", "session_id": "test"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get('success') is True
        assert data.get('reply')

    @pytest.mark.skipif(not os.path.exists(TEST_AUDIO), reason="测试音频不存在")
    def test_stt(self):
        """测试语音转文字"""
        with open(TEST_AUDIO, 'rb') as f:
            r = requests.post(
                f"{SERVER}/wechat/stt?format=mp3&engine=tencent",
                data=f.read()
            )
        assert r.status_code == 200
        data = r.json()
        assert data.get('success') is True


class TestHealthAPI:
    """健康检查端到端测试"""

    def test_health(self):
        """测试健康检查"""
        r = requests.get(f"{SERVER}/health")
        assert r.status_code == 200
        data = r.json()
        assert data['status'] == 'healthy'

    def test_version(self):
        """测试版本接口"""
        r = requests.get(f"{SERVER}/version")
        assert r.status_code == 200
        data = r.json()
        assert 'version' in data


class TestV2API:
    """v2 API 端到端测试"""

    def test_v2_ping(self):
        """测试 v2 ping"""
        r = requests.get(f"{SERVER}/v2/mcu/ping")
        assert r.status_code == 200
        data = r.json()
        assert data['success'] is True

    def test_v2_requires_auth(self):
        """测试 v2 需要认证"""
        r = requests.post(f"{SERVER}/v2/mcu/stt")
        assert r.status_code == 401

    def test_v2_status_anonymous(self):
        """测试 v2 状态（匿名）"""
        r = requests.get(f"{SERVER}/v2/mcu/status")
        assert r.status_code == 200
        data = r.json()
        assert data['authenticated'] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
