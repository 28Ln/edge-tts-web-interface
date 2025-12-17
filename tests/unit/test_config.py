"""
配置模块单元测试
"""

import os
import pytest


class TestConfig:
    """配置测试"""

    def test_load_config(self):
        """测试加载配置"""
        from src.config import load_config
        config = load_config()
        assert config is not None
        assert config.server.port == 3003

    def test_env_detection(self):
        """测试环境检测"""
        from src.config import load_config, ENV_TESTING
        config = load_config(env=ENV_TESTING)
        assert config.env == ENV_TESTING
        assert config.is_testing is True
        assert config.is_production is False

    def test_ai_config_new_vars(self):
        """测试新 AI 环境变量"""
        os.environ['AI_API_BASE'] = 'http://new.api'
        os.environ['AI_API_KEY'] = 'new_key'
        
        from src.config import load_config, _config
        # 重置全局配置
        import src.config
        src.config._config = None
        
        config = load_config()
        assert config.ai.api_base == 'http://new.api'
        assert config.ai.api_key == 'new_key'

    def test_validate_config(self):
        """测试配置验证"""
        from src.config import load_config, validate_config
        config = load_config()
        errors = validate_config(config)
        # 测试环境可能缺少配置
        assert isinstance(errors, list)


class TestSessionStore:
    """会话存储测试"""

    def test_memory_store(self):
        """测试内存存储"""
        from src.services.session_store import MemorySessionStore
        
        store = MemorySessionStore()
        
        # 测试设置和获取
        store.set('test_session', [{'role': 'user', 'content': 'hello'}])
        messages = store.get('test_session')
        assert messages is not None
        assert len(messages) == 1
        assert messages[0]['content'] == 'hello'

    def test_memory_store_append(self):
        """测试追加消息"""
        from src.services.session_store import MemorySessionStore
        
        store = MemorySessionStore()
        store.append('test', {'role': 'user', 'content': 'msg1'})
        store.append('test', {'role': 'assistant', 'content': 'msg2'})
        
        messages = store.get('test')
        assert len(messages) == 2

    def test_memory_store_max_messages(self):
        """测试消息数量限制"""
        from src.services.session_store import MemorySessionStore
        
        store = MemorySessionStore()
        for i in range(15):
            store.append('test', {'role': 'user', 'content': f'msg{i}'}, max_messages=10)
        
        messages = store.get('test')
        assert len(messages) == 10

    def test_memory_store_delete(self):
        """测试删除会话"""
        from src.services.session_store import MemorySessionStore
        
        store = MemorySessionStore()
        store.set('test', [{'role': 'user', 'content': 'hello'}])
        store.delete('test')
        
        assert store.get('test') is None


class TestLogger:
    """日志模块测试"""

    def test_setup_logger(self):
        """测试设置日志器"""
        from src.utils.logger import setup_logger
        
        logger = setup_logger('test_logger', level='DEBUG')
        assert logger is not None
        assert logger.name == 'test_logger'

    def test_get_logger(self):
        """测试获取日志器"""
        from src.utils.logger import get_logger
        
        logger1 = get_logger('test')
        logger2 = get_logger('test')
        assert logger1 is logger2  # 应该是同一个实例

    def test_sensitive_filter(self):
        """测试敏感信息过滤"""
        from src.utils.logger import SensitiveFilter
        import logging
        
        filter = SensitiveFilter()
        record = logging.LogRecord(
            'test', logging.INFO, '', 0,
            'api_key=sk-1234567890abcdef1234567890abcdef', (), None
        )
        filter.filter(record)
        assert 'sk-1234567890' not in record.msg
        assert '***' in record.msg


class TestRetry:
    """重试模块测试"""

    def test_retry_success(self):
        """测试重试成功"""
        from src.utils.retry import retry
        
        call_count = 0
        
        @retry(max_attempts=3, delay=0.01)
        def succeed_on_second():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("fail")
            return "success"
        
        result = succeed_on_second()
        assert result == "success"
        assert call_count == 2

    def test_retry_all_fail(self):
        """测试全部失败"""
        from src.utils.retry import retry
        
        @retry(max_attempts=2, delay=0.01)
        def always_fail():
            raise ValueError("always fail")
        
        with pytest.raises(ValueError):
            always_fail()


class TestCleanup:
    """清理模块测试"""

    def test_temp_file(self):
        """测试临时文件"""
        import os
        from src.utils.cleanup import temp_file
        
        with temp_file(suffix='.txt') as filepath:
            assert os.path.exists(filepath)
            with open(filepath, 'w') as f:
                f.write('test')
        
        # 退出后应该被清理
        assert not os.path.exists(filepath)

    def test_register_temp_file(self):
        """测试注册临时文件"""
        from src.utils.cleanup import register_temp_file, unregister_temp_file, _temp_files
        
        register_temp_file('/tmp/test.txt')
        assert '/tmp/test.txt' in _temp_files
        
        unregister_temp_file('/tmp/test.txt')
        assert '/tmp/test.txt' not in _temp_files
