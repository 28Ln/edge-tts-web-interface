"""
微信 API 集成测试
"""

import pytest
import hashlib
import time
from unittest.mock import patch, Mock


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

    def test_chat_success(self, client):
        """测试文字对话成功"""
        with patch('src.api.v1.wechat.get_ai_service') as mock_ai:
            mock_service = Mock()
            mock_service.ask.return_value = '你好！有什么可以帮助你的？'
            mock_ai.return_value = mock_service
            
            response = client.post('/wechat/chat', json={
                "message": "你好",
                "session_id": "test_session"
            })
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['reply'] == '你好！有什么可以帮助你的？'
            assert data['session_id'] == 'test_session'

    def test_stt_empty_audio(self, client):
        """测试空音频"""
        response = client.post('/wechat/stt')
        assert response.status_code == 400

    def test_stt_success(self, client):
        """测试语音转文字成功"""
        with patch('src.api.v1.wechat.get_asr_service') as mock_asr:
            mock_service = Mock()
            mock_service.convert_to_wav.return_value = b'RIFF....WAVEfmt '
            mock_service.recognize.return_value = '识别的文字'
            mock_asr.return_value = mock_service
            
            response = client.post(
                '/wechat/stt?format=wav&engine=tencent',
                data=b'fake_audio_data',
                content_type='application/octet-stream'
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['text'] == '识别的文字'

    def test_voice_empty_audio(self, client):
        """测试空语音"""
        response = client.post('/wechat/voice')
        assert response.status_code == 400

    def test_voice_success(self, client):
        """测试语音对话成功"""
        with patch('src.api.v1.wechat.get_asr_service') as mock_asr:
            with patch('src.api.v1.wechat.get_ai_service') as mock_ai:
                mock_asr_service = Mock()
                mock_asr_service.convert_to_wav.return_value = b'RIFF....WAVEfmt '
                mock_asr_service.recognize.return_value = '你好'
                mock_asr.return_value = mock_asr_service
                
                mock_ai_service = Mock()
                mock_ai_service.ask.return_value = '你好！'
                mock_ai.return_value = mock_ai_service
                
                response = client.post(
                    '/wechat/voice?format=wav&engine=tencent',
                    data=b'fake_audio_data',
                    content_type='application/octet-stream'
                )
                
                assert response.status_code == 200
                data = response.get_json()
                assert data['success'] is True
                assert data['question'] == '你好'
                assert data['answer'] == '你好！'

    def test_voice_no_recognition(self, client):
        """测试语音未识别"""
        with patch('src.api.v1.wechat.get_asr_service') as mock_asr:
            mock_service = Mock()
            mock_service.convert_to_wav.return_value = b'RIFF....WAVEfmt '
            mock_service.recognize.return_value = ''
            mock_asr.return_value = mock_service
            
            response = client.post(
                '/wechat/voice?format=wav',
                data=b'fake_audio_data',
                content_type='application/octet-stream'
            )
            
            assert response.status_code == 400

    def test_callback_get_invalid_signature(self, client):
        """测试无效签名"""
        response = client.get('/wechat/callback?signature=invalid&timestamp=123&nonce=456&echostr=test')
        assert response.status_code == 403

    def test_callback_get_valid_signature(self, client):
        """测试有效签名验证"""
        timestamp = str(int(time.time()))
        nonce = '123456'
        echostr = 'test_echostr'
        
        # 使用默认 token 计算签名
        token = 'your_wechat_token'
        tmp_list = sorted([token, timestamp, nonce])
        tmp_str = ''.join(tmp_list)
        signature = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()
        
        response = client.get(
            f'/wechat/callback?signature={signature}&timestamp={timestamp}&nonce={nonce}&echostr={echostr}'
        )
        
        assert response.status_code == 200
        assert response.data.decode() == echostr

    def test_callback_post_text_message(self, client):
        """测试文本消息回调"""
        with patch('src.api.v1.wechat.get_ai_service') as mock_ai:
            mock_service = Mock()
            mock_service.ask.return_value = 'AI回复'
            mock_ai.return_value = mock_service
            
            xml_data = '''<xml>
                <ToUserName><![CDATA[gh_test]]></ToUserName>
                <FromUserName><![CDATA[user123]]></FromUserName>
                <CreateTime>1234567890</CreateTime>
                <MsgType><![CDATA[text]]></MsgType>
                <Content><![CDATA[你好]]></Content>
                <MsgId>1234567890</MsgId>
            </xml>'''
            
            response = client.post(
                '/wechat/callback',
                data=xml_data,
                content_type='application/xml'
            )
            
            assert response.status_code == 200
            assert 'AI回复' in response.data.decode('utf-8')

    def test_callback_post_voice_message(self, client):
        """测试语音消息回调（带识别结果）"""
        with patch('src.api.v1.wechat.get_ai_service') as mock_ai:
            mock_service = Mock()
            mock_service.ask.return_value = 'AI回复'
            mock_ai.return_value = mock_service
            
            xml_data = '''<xml>
                <ToUserName><![CDATA[gh_test]]></ToUserName>
                <FromUserName><![CDATA[user123]]></FromUserName>
                <CreateTime>1234567890</CreateTime>
                <MsgType><![CDATA[voice]]></MsgType>
                <Recognition><![CDATA[语音识别内容]]></Recognition>
                <MsgId>1234567890</MsgId>
            </xml>'''
            
            response = client.post(
                '/wechat/callback',
                data=xml_data,
                content_type='application/xml'
            )
            
            assert response.status_code == 200
            response_text = response.data.decode('utf-8')
            assert '语音' in response_text
            assert 'AI回复' in response_text

    def test_callback_post_unsupported_message(self, client):
        """测试不支持的消息类型"""
        xml_data = '''<xml>
            <ToUserName><![CDATA[gh_test]]></ToUserName>
            <FromUserName><![CDATA[user123]]></FromUserName>
            <CreateTime>1234567890</CreateTime>
            <MsgType><![CDATA[image]]></MsgType>
            <MsgId>1234567890</MsgId>
        </xml>'''
        
        response = client.post(
            '/wechat/callback',
            data=xml_data,
            content_type='application/xml'
        )
        
        assert response.status_code == 200
        assert '暂不支持' in response.data.decode('utf-8')


class TestWechatHelpers:
    """微信辅助函数测试"""

    def test_verify_signature(self):
        """测试签名验证"""
        from src.api.v1.wechat import verify_wechat_signature
        
        timestamp = '1234567890'
        nonce = 'test_nonce'
        token = 'your_wechat_token'
        
        tmp_list = sorted([token, timestamp, nonce])
        tmp_str = ''.join(tmp_list)
        valid_signature = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()
        
        assert verify_wechat_signature(valid_signature, timestamp, nonce) is True
        assert verify_wechat_signature('invalid', timestamp, nonce) is False

    def test_make_text_reply(self):
        """测试生成文本回复"""
        from src.api.v1.wechat import make_text_reply
        
        reply = make_text_reply('user', 'gh_test', '你好')
        
        assert '<ToUserName><![CDATA[user]]></ToUserName>' in reply
        assert '<FromUserName><![CDATA[gh_test]]></FromUserName>' in reply
        assert '<MsgType><![CDATA[text]]></MsgType>' in reply
        assert '<Content><![CDATA[你好]]></Content>' in reply
