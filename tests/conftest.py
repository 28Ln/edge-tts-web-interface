"""
Pytest 配置和 fixtures
"""

import os
import sys
import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置测试环境变量
os.environ.setdefault('GEMINI_API_BASE', 'http://test.api')
os.environ.setdefault('GEMINI_API_KEY', 'test_key')
os.environ.setdefault('GEMINI_MODEL', 'test-model')
os.environ.setdefault('LOG_LEVEL', 'WARNING')


@pytest.fixture
def app():
    """创建测试应用"""
    from src.api import create_app
    
    app = create_app()
    app.config['TESTING'] = True
    
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """创建 CLI 测试运行器"""
    return app.test_cli_runner()
