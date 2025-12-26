"""
Pytest 配置和 fixtures
"""

import os
import sys
import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置测试环境变量
os.environ.setdefault('APP_ENV', 'testing')
os.environ.setdefault('AI_API_BASE', 'http://test.api')
os.environ.setdefault('AI_API_KEY', 'test_key')
os.environ.setdefault('AI_MODEL', 'test-model')
os.environ.setdefault('LOG_LEVEL', 'WARNING')
os.environ.setdefault('LOG_FORMAT', 'text')
os.environ.setdefault('ADMIN_PASSWORD', 'admin123')
# 测试环境使用较高的限流阈值
os.environ.setdefault('RATE_LIMIT_PER_MINUTE', '1000')


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """每个测试前重置限流器"""
    from src.utils.rate_limiter import reset_rate_limiter as _reset
    _reset()
    yield
    _reset()


@pytest.fixture(autouse=True)
def reset_metrics():
    """每个测试前重置指标收集器"""
    from src.utils.metrics import reset_metrics_collector
    reset_metrics_collector()
    yield
    reset_metrics_collector()


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


@pytest.fixture
def admin_key(app):
    """获取管理员 API Key"""
    from src.auth.admin_auth import get_admin_auth_service
    
    with app.app_context():
        service = get_admin_auth_service()
        # 获取默认管理员的 API Key
        admins = service.list_admins()
        if admins:
            admin = service.get_admin_by_id(admins[0]['id'])
            if admin:
                return admin.api_key
    return None


@pytest.fixture
def admin_headers(admin_key):
    """管理员认证头"""
    return {'X-Admin-Key': admin_key} if admin_key else {}
