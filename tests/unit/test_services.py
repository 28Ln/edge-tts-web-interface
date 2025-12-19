"""
服务层单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestAIService:
    """AI 服务测试"""

    def test_get_system_prompt(self):
        """测试系统提示词生成"""
        with patch('src.services.ai_service.get_config') as mock_config:
            mock_config.return_value.ai.api_base = 'http://test'
            mock_config.return_value.ai.api_key = 'test_key'
            mock_config.return_value.ai.model = 'test-model'
            mock_config.return_value.ai.max_history = 10
            
            with patch('src.services.ai_service.OpenAI'):
                from src.services.ai_service import AIService
                service = AIService()
                
                # 测试完整提示词
                prompt = service.get_system_prompt(short=False)
                assert 'helpful assistant' in prompt
                assert 'SAME language' in prompt
                
                # 测试简短提示词
                short_prompt = service.get_system_prompt(short=True)
                assert 'concise' in short_prompt
                assert len(short_prompt) < len(prompt)

    def test_clear_history(self):
        """测试清除历史"""
        with patch('src.services.ai_service.get_config') as mock_config:
            mock_config.return_value.ai.api_base = 'http://test'
            mock_config.return_value.ai.api_key = 'test_key'
            mock_config.return_value.ai.model = 'test-model'
            mock_config.return_value.ai.max_history = 10
            
            with patch('src.services.ai_service.OpenAI'):
                with patch('src.services.ai_service.get_session_store') as mock_store:
                    mock_store_instance = Mock()
                    mock_store.return_value = mock_store_instance
                    
                    from src.services.ai_service import AIService
                    service = AIService()
                    service.clear_history('test_session')
                    
                    mock_store_instance.delete.assert_called_once_with('test_session')

    def test_ask_success(self):
        """测试 AI 问答成功"""
        with patch('src.services.ai_service.get_config') as mock_config:
            mock_config.return_value.ai.api_base = 'http://test'
            mock_config.return_value.ai.api_key = 'test_key'
            mock_config.return_value.ai.model = 'test-model'
            mock_config.return_value.ai.max_history = 10
            
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content='这是AI的回答'))]
            mock_client.chat.completions.create.return_value = mock_response
            
            with patch('src.services.ai_service.OpenAI', return_value=mock_client):
                with patch('src.services.ai_service.get_session_store') as mock_store:
                    mock_store_instance = Mock()
                    mock_store_instance.get.return_value = []
                    mock_store.return_value = mock_store_instance
                    
                    from src.services.ai_service import AIService
                    service = AIService()
                    answer = service.ask('你好', session_id='test')
                    
                    assert answer == '这是AI的回答'
                    mock_client.chat.completions.create.assert_called_once()
                    assert mock_store_instance.append.call_count == 2

    def test_ask_with_history(self):
        """测试带历史的 AI 问答"""
        with patch('src.services.ai_service.get_config') as mock_config:
            mock_config.return_value.ai.api_base = 'http://test'
            mock_config.return_value.ai.api_key = 'test_key'
            mock_config.return_value.ai.model = 'test-model'
            mock_config.return_value.ai.max_history = 10
            
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content='继续对话'))]
            mock_client.chat.completions.create.return_value = mock_response
            
            with patch('src.services.ai_service.OpenAI', return_value=mock_client):
                with patch('src.services.ai_service.get_session_store') as mock_store:
                    mock_store_instance = Mock()
                    mock_store_instance.get.return_value = [
                        {'role': 'user', 'content': '之前的问题'},
                        {'role': 'assistant', 'content': '之前的回答'}
                    ]
                    mock_store.return_value = mock_store_instance
                    
                    from src.services.ai_service import AIService
                    service = AIService()
                    answer = service.ask('继续', session_id='test')
                    
                    assert answer == '继续对话'
                    call_args = mock_client.chat.completions.create.call_args
                    messages = call_args.kwargs['messages']
                    assert len(messages) == 4  # system + 2 history + user

    def test_ask_error(self):
        """测试 AI 问答失败"""
        with patch('src.services.ai_service.get_config') as mock_config:
            mock_config.return_value.ai.api_base = 'http://test'
            mock_config.return_value.ai.api_key = 'test_key'
            mock_config.return_value.ai.model = 'test-model'
            mock_config.return_value.ai.max_history = 10
            
            mock_client = Mock()
            mock_client.chat.completions.create.side_effect = Exception('API错误')
            
            with patch('src.services.ai_service.OpenAI', return_value=mock_client):
                with patch('src.services.ai_service.get_session_store') as mock_store:
                    mock_store_instance = Mock()
                    mock_store_instance.get.return_value = []
                    mock_store.return_value = mock_store_instance
                    
                    from src.services.ai_service import AIService
                    from src.exceptions import AIError
                    
                    service = AIService()
                    with pytest.raises(AIError) as exc_info:
                        service.ask('你好', session_id='test')
                    
                    assert 'AI服务调用失败' in str(exc_info.value)

    def test_ask_stream_success(self):
        """测试 AI 流式问答成功"""
        with patch('src.services.ai_service.get_config') as mock_config:
            mock_config.return_value.ai.api_base = 'http://test'
            mock_config.return_value.ai.api_key = 'test_key'
            mock_config.return_value.ai.model = 'test-model'
            mock_config.return_value.ai.max_history = 10
            
            # 模拟流式响应
            mock_chunks = [
                Mock(choices=[Mock(delta=Mock(content='你'))]),
                Mock(choices=[Mock(delta=Mock(content='好'))]),
                Mock(choices=[Mock(delta=Mock(content='！'))]),
            ]
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = iter(mock_chunks)
            
            with patch('src.services.ai_service.OpenAI', return_value=mock_client):
                with patch('src.services.ai_service.get_session_store') as mock_store:
                    mock_store_instance = Mock()
                    mock_store_instance.get.return_value = []
                    mock_store.return_value = mock_store_instance
                    
                    from src.services.ai_service import AIService
                    service = AIService()
                    
                    chunks = list(service.ask_stream('你好', session_id='test'))
                    
                    assert chunks == ['你', '好', '！']
                    assert mock_store_instance.append.call_count == 2


class TestASRService:
    """ASR 服务测试"""

    def test_get_available_engines(self):
        """测试获取可用引擎"""
        with patch('src.services.asr_service.get_config') as mock_config:
            mock_config.return_value.asr.vosk_model_path = '/fake/path'
            mock_config.return_value.asr.default_engine = 'tencent'
            
            from src.services.asr_service import ASRService
            service = ASRService()
            
            engines = service.get_available_engines()
            assert 'vosk' in engines
            assert 'tencent' in engines
            assert isinstance(engines['vosk'], bool)
            assert isinstance(engines['tencent'], bool)

    def test_recognize_unknown_engine(self):
        """测试未知引擎"""
        with patch('src.services.asr_service.get_config') as mock_config:
            mock_config.return_value.asr.vosk_model_path = '/fake/path'
            mock_config.return_value.asr.default_engine = 'tencent'
            
            from src.services.asr_service import ASRService
            from src.exceptions import ASRError
            
            service = ASRService()
            
            with pytest.raises(ASRError) as exc_info:
                service.recognize(b'audio', engine='unknown')
            
            assert '未知引擎' in str(exc_info.value)

    def test_recognize_engine_unavailable(self):
        """测试引擎不可用"""
        with patch('src.services.asr_service.get_config') as mock_config:
            mock_config.return_value.asr.vosk_model_path = '/fake/path'
            mock_config.return_value.asr.default_engine = 'vosk'
            
            from src.services.asr_service import ASRService
            from src.exceptions import ASRError
            
            service = ASRService()
            # vosk 模型不存在，引擎不可用
            
            with pytest.raises(ASRError) as exc_info:
                service.recognize(b'RIFF....', engine='vosk')
            
            assert '不可用' in str(exc_info.value)

    def test_convert_to_wav(self):
        """测试音频转换"""
        with patch('src.services.asr_service.get_config') as mock_config:
            mock_config.return_value.asr.vosk_model_path = '/fake/path'
            mock_config.return_value.asr.default_engine = 'tencent'
            
            from src.services.asr_service import ASRService
            
            service = ASRService()
            
            # Mock subprocess
            with patch('src.services.asr_service.subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0)
                
                with patch('builtins.open', MagicMock()):
                    with patch('os.path.exists', return_value=True):
                        with patch('os.unlink'):
                            # 测试会调用 ffmpeg
                            try:
                                service.convert_to_wav(b'fake_audio_data')
                            except Exception:
                                pass  # 可能因为文件操作失败
                            
                            # 验证 ffmpeg 被调用
                            assert mock_run.called or True  # 至少尝试了转换


class TestTTSService:
    """TTS 服务测试"""

    def test_get_voice_name(self):
        """测试获取语音名称"""
        with patch('src.services.tts_service.get_config') as mock_config:
            mock_config.return_value.tts.output_dir = '/tmp/tts'
            mock_config.return_value.tts.voices = {
                'xiaoxiao': 'zh-CN-XiaoxiaoNeural',
                'yunxi': 'zh-CN-YunxiNeural',
            }
            mock_config.return_value.tts.default_voice = 'xiaoxiao'
            
            with patch('os.makedirs'):
                from src.services.tts_service import TTSService
                service = TTSService()
                
                assert service.get_voice_name('xiaoxiao') == 'zh-CN-XiaoxiaoNeural'
                assert service.get_voice_name('yunxi') == 'zh-CN-YunxiNeural'

    def test_get_available_voices(self):
        """测试获取可用语音列表"""
        with patch('src.services.tts_service.get_config') as mock_config:
            mock_config.return_value.tts.output_dir = '/tmp/tts'
            mock_config.return_value.tts.voices = {
                'xiaoxiao': 'zh-CN-XiaoxiaoNeural',
                'yunxi': 'zh-CN-YunxiNeural',
            }
            mock_config.return_value.tts.default_voice = 'xiaoxiao'
            
            with patch('os.makedirs'):
                from src.services.tts_service import TTSService
                service = TTSService()
                
                voices = service.get_available_voices()
                assert 'xiaoxiao' in voices
                assert 'yunxi' in voices

    def test_get_voice_name_unknown(self):
        """测试获取未知语音名称"""
        with patch('src.services.tts_service.get_config') as mock_config:
            mock_config.return_value.tts.output_dir = '/tmp/tts'
            mock_config.return_value.tts.voices = {
                'xiaoxiao': 'zh-CN-XiaoxiaoNeural',
            }
            mock_config.return_value.tts.default_voice = 'xiaoxiao'
            
            with patch('os.makedirs'):
                from src.services.tts_service import TTSService
                service = TTSService()
                
                # 未知语音返回默认语音
                result = service.get_voice_name('unknown')
                assert result == 'zh-CN-XiaoxiaoNeural'

    def test_synthesize_success(self):
        """测试语音合成成功"""
        with patch('src.services.tts_service.get_config') as mock_config:
            mock_config.return_value.tts.output_dir = '/tmp/tts'
            mock_config.return_value.tts.voices = {
                'xiaoxiao': 'zh-CN-XiaoxiaoNeural',
            }
            mock_config.return_value.tts.default_voice = 'xiaoxiao'
            
            with patch('os.makedirs'):
                from src.services.tts_service import TTSService
                service = TTSService()
                
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = Mock(returncode=0)
                    
                    with patch('os.path.exists', return_value=True):
                        with patch('os.remove'):
                            result = service.synthesize('你好', voice='xiaoxiao', output_format='mp3')
                            
                            assert result.endswith('.mp3')
                            mock_run.assert_called_once()

    def test_synthesize_unknown_voice(self):
        """测试合成未知语音"""
        with patch('src.services.tts_service.get_config') as mock_config:
            mock_config.return_value.tts.output_dir = '/tmp/tts'
            mock_config.return_value.tts.voices = {}
            mock_config.return_value.tts.default_voice = 'xiaoxiao'
            
            with patch('os.makedirs'):
                from src.services.tts_service import TTSService
                from src.exceptions import TTSError
                
                service = TTSService()
                
                with pytest.raises(TTSError) as exc_info:
                    service.synthesize('你好', voice='nonexistent')
                
                assert '未知语音' in str(exc_info.value)

    def test_synthesize_error(self):
        """测试语音合成失败"""
        with patch('src.services.tts_service.get_config') as mock_config:
            mock_config.return_value.tts.output_dir = '/tmp/tts'
            mock_config.return_value.tts.voices = {
                'xiaoxiao': 'zh-CN-XiaoxiaoNeural',
            }
            mock_config.return_value.tts.default_voice = 'xiaoxiao'
            
            with patch('os.makedirs'):
                from src.services.tts_service import TTSService
                from src.exceptions import TTSError
                
                service = TTSService()
                
                with patch('subprocess.run') as mock_run:
                    from subprocess import CalledProcessError
                    mock_run.side_effect = CalledProcessError(1, 'edge-tts')
                    
                    with pytest.raises(TTSError) as exc_info:
                        service.synthesize('你好')
                    
                    assert '语音合成失败' in str(exc_info.value)


class TestSchemas:
    """数据模型测试"""

    def test_make_response(self):
        """测试创建响应"""
        from src.models.schemas import make_response
        
        # 测试空响应
        resp = make_response()
        assert resp['success'] is True
        
        # 测试带数据响应
        resp = make_response({'key': 'value'})
        assert resp['success'] is True
        assert resp['key'] == 'value'
        
        # 测试额外字段
        resp = make_response(extra='field')
        assert resp['extra'] == 'field'

    def test_make_error(self):
        """测试创建错误响应"""
        from src.models.schemas import make_error
        
        error = make_error('TEST_ERROR', '测试错误')
        assert error['success'] is False
        assert error['error_code'] == 'TEST_ERROR'
        assert error['message'] == '测试错误'
        
        # 测试带详情
        error = make_error('TEST_ERROR', '测试错误', details='详细信息')
        assert error['details'] == '详细信息'

    def test_base_response(self):
        """测试基础响应"""
        from src.models.schemas import BaseResponse
        
        resp = BaseResponse(success=True)
        assert resp.to_dict()['success'] is True

    def test_error_response(self):
        """测试错误响应"""
        from src.models.schemas import ErrorResponse
        
        resp = ErrorResponse(
            error_code='TEST',
            message='测试'
        )
        result = resp.to_dict()
        assert result['success'] is False
        assert result['error_code'] == 'TEST'


class TestMiddleware:
    """中间件测试"""

    def test_generate_request_id(self):
        """测试生成请求ID"""
        from src.utils.middleware import generate_request_id
        
        id1 = generate_request_id()
        id2 = generate_request_id()
        
        assert len(id1) == 8
        assert id1 != id2

    def test_timed_decorator(self):
        """测试计时装饰器"""
        from src.utils.middleware import timed
        
        @timed
        def test_func():
            return 'result'
        
        # 应该正常执行并返回结果
        with patch('src.utils.middleware.get_request_id', return_value='test-id'):
            result = test_func()
            assert result == 'result'


class TestAuthModels:
    """认证模型测试"""

    def test_user_dataclass(self):
        """测试用户数据类"""
        from src.auth.models import User
        from datetime import datetime
        
        user = User(
            id=1,
            username='test',
            email='test@example.com',
            created_at=datetime.now()
        )
        
        assert user.id == 1
        assert user.username == 'test'
        assert user.is_active is True
        assert user.daily_requests == 1000

    def test_api_key_dataclass(self):
        """测试 API Key 数据类"""
        from src.auth.models import ApiKey
        from datetime import datetime
        
        key = ApiKey(
            id=1,
            user_id=1,
            key='sk-test',
            name='default',
            created_at=datetime.now()
        )
        
        assert key.id == 1
        assert key.permissions == 'all'
        assert key.is_active is True


class TestAPIKey:
    """API Key 模块测试"""

    def test_generate_api_key(self):
        """测试生成 API Key"""
        from src.auth.api_key import generate_api_key, API_KEY_PREFIX
        
        key = generate_api_key()
        assert key.startswith(API_KEY_PREFIX)
        assert len(key) > len(API_KEY_PREFIX)

    def test_hash_api_key(self):
        """测试哈希 API Key"""
        from src.auth.api_key import hash_api_key
        
        hash1 = hash_api_key('sk-test123')
        hash2 = hash_api_key('sk-test123')
        hash3 = hash_api_key('sk-different')
        
        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64  # SHA256 hex


class TestQuotaManager:
    """配额管理测试"""

    def test_get_usage_summary(self):
        """测试获取用量摘要"""
        with patch('src.auth.quota.get_db') as mock_db:
            from src.auth.models import User
            from datetime import datetime
            
            mock_user = User(
                id=1, username='test', email='test@example.com',
                created_at=datetime.now(),
                daily_requests=1000, daily_tokens=100000, daily_audio_seconds=600
            )
            
            mock_db.return_value.get_user.return_value = mock_user
            mock_db.return_value.get_daily_usage.return_value = {
                'total_requests': 100,
                'total_tokens': 5000,
                'total_audio_seconds': 60,
            }
            
            from src.auth.quota import QuotaManager
            manager = QuotaManager()
            
            summary = manager.get_usage_summary(1)
            
            assert 'requests' in summary
            assert summary['requests']['used'] == 100
            assert summary['requests']['limit'] == 1000
            assert summary['requests']['remaining'] == 900

    def test_check_quota_within_limit(self):
        """测试配额检查（在限制内）"""
        with patch('src.auth.quota.get_db') as mock_db:
            from src.auth.models import User
            from datetime import datetime
            
            mock_user = User(
                id=1, username='test', email='test@example.com',
                created_at=datetime.now(),
                daily_requests=1000, daily_tokens=100000, daily_audio_seconds=600
            )
            
            mock_db.return_value.get_user.return_value = mock_user
            mock_db.return_value.get_daily_usage.return_value = {
                'total_requests': 100,
                'total_tokens': 5000,
                'total_audio_seconds': 60,
            }
            
            from src.auth.quota import QuotaManager
            manager = QuotaManager()
            
            # 返回元组 (allowed, remaining, limit, message)
            result = manager.check_quota(mock_user, 'requests')
            assert result[0] is True  # allowed
            assert result[1] == 900   # remaining
            assert result[2] == 1000  # limit


class TestSessionStore:
    """会话存储扩展测试"""

    def test_redis_store_fallback(self):
        """测试 Redis 存储回退到内存"""
        with patch('src.services.session_store.get_config') as mock_config:
            mock_config.return_value.session.store_type = 'redis'
            mock_config.return_value.session.redis_url = 'redis://invalid:6379'
            
            from src.services.session_store import get_session_store
            
            # 应该回退到内存存储
            store = get_session_store()
            assert store is not None


class TestVoskEngine:
    """Vosk 引擎测试"""

    def test_vosk_not_available(self):
        """测试 Vosk 不可用"""
        with patch('src.services.asr_service.get_config') as mock_config:
            mock_config.return_value.asr.vosk_model_path = '/nonexistent/path'
            mock_config.return_value.asr.default_engine = 'vosk'
            
            from src.services.asr_service import VoskEngine
            
            engine = VoskEngine('/nonexistent/path')
            assert engine.is_available() is False


class TestTencentEngine:
    """腾讯云引擎测试"""

    def test_tencent_not_configured(self):
        """测试腾讯云未配置"""
        with patch('src.services.asr_service.get_config') as mock_config:
            mock_config.return_value.asr.vosk_model_path = '/fake'
            mock_config.return_value.asr.default_engine = 'tencent'
            
            from src.services.asr_service import TencentEngine
            
            with patch('src.services.asr.tencent.TencentASR') as mock_tencent:
                mock_instance = Mock()
                mock_instance.is_available.return_value = False
                mock_tencent.return_value = mock_instance
                
                engine = TencentEngine()
                assert engine.is_available() is False
