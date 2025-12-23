"""
Dashboard 管理面板测试
"""

import pytest


class TestDashboardAuth:
    """Dashboard 认证测试"""

    def test_login_page(self, client):
        """测试登录页面"""
        response = client.get('/dashboard/login')
        assert response.status_code == 200
        assert '管理面板登录' in response.data.decode('utf-8')

    def test_login_wrong_password(self, client):
        """测试错误密码"""
        response = client.post('/dashboard/login', data={
            'password': 'wrong_password'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert '密码错误' in response.data.decode('utf-8')

    def test_login_success(self, client):
        """测试登录成功"""
        response = client.post('/dashboard/login', data={
            'password': 'admin123'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert '仪表盘' in response.data.decode('utf-8')

    def test_protected_page_redirect(self, client):
        """测试未登录访问受保护页面"""
        response = client.get('/dashboard/')
        assert response.status_code == 302
        assert '/dashboard/login' in response.location

    def test_logout(self, client):
        """测试登出"""
        # 先登录
        client.post('/dashboard/login', data={'password': 'admin123'})
        
        # 登出
        response = client.get('/dashboard/logout', follow_redirects=True)
        assert response.status_code == 200
        assert '已退出登录' in response.data.decode('utf-8')


class TestDashboardIndex:
    """Dashboard 首页测试"""

    def test_index_page(self, client):
        """测试首页"""
        # 登录
        client.post('/dashboard/login', data={'password': 'admin123'})
        
        response = client.get('/dashboard/')
        assert response.status_code == 200
        assert '用户总数' in response.data.decode('utf-8')
        assert '今日请求' in response.data.decode('utf-8')


class TestDashboardUsers:
    """Dashboard 用户管理测试"""

    def test_users_list(self, client):
        """测试用户列表"""
        client.post('/dashboard/login', data={'password': 'admin123'})
        
        response = client.get('/dashboard/users')
        assert response.status_code == 200
        assert '用户管理' in response.data.decode('utf-8')

    def test_create_user_page(self, client):
        """测试创建用户页面"""
        client.post('/dashboard/login', data={'password': 'admin123'})
        
        response = client.get('/dashboard/users/create')
        assert response.status_code == 200
        assert '创建新用户' in response.data.decode('utf-8')

    def test_create_user(self, client):
        """测试创建用户"""
        import time
        client.post('/dashboard/login', data={'password': 'admin123'})
        
        username = f'dashuser_{int(time.time())}'
        response = client.post('/dashboard/users/create', data={
            'username': username,
            'email': f'{username}@example.com',
            'daily_requests': 500,
            'daily_tokens': 50000,
            'daily_audio_seconds': 300
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '用户创建成功' in response.data.decode('utf-8')
        assert 'etk_' in response.data.decode('utf-8')  # API Key

    def test_create_user_missing_fields(self, client):
        """测试创建用户缺少字段"""
        client.post('/dashboard/login', data={'password': 'admin123'})
        
        response = client.post('/dashboard/users/create', data={
            'username': 'testuser'
            # 缺少 email
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '不能为空' in response.data.decode('utf-8')

    def test_user_detail(self, client):
        """测试用户详情"""
        import time
        client.post('/dashboard/login', data={'password': 'admin123'})
        
        # 先创建用户
        username = f'detailuser_{int(time.time())}'
        client.post('/dashboard/users/create', data={
            'username': username,
            'email': f'{username}@example.com',
            'daily_requests': 500,
            'daily_tokens': 50000,
            'daily_audio_seconds': 300
        })
        
        # 获取用户 ID
        from src.auth.models import get_db
        db = get_db()
        user = db.get_user_by_username(username)
        
        response = client.get(f'/dashboard/users/{user.id}')
        assert response.status_code == 200
        assert username in response.data.decode('utf-8')
        assert 'API Key' in response.data.decode('utf-8')

    def test_user_detail_not_found(self, client):
        """测试用户详情不存在"""
        client.post('/dashboard/login', data={'password': 'admin123'})
        
        response = client.get('/dashboard/users/99999', follow_redirects=True)
        assert response.status_code == 200
        assert '用户不存在' in response.data.decode('utf-8')

    def test_edit_user(self, client):
        """测试编辑用户"""
        import time
        client.post('/dashboard/login', data={'password': 'admin123'})
        
        # 先创建用户
        username = f'edituser_{int(time.time())}'
        client.post('/dashboard/users/create', data={
            'username': username,
            'email': f'{username}@example.com',
            'daily_requests': 500,
            'daily_tokens': 50000,
            'daily_audio_seconds': 300
        })
        
        from src.auth.models import get_db
        db = get_db()
        user = db.get_user_by_username(username)
        
        # 编辑用户
        response = client.post(f'/dashboard/users/{user.id}/edit', data={
            'daily_requests': 1000,
            'daily_tokens': 200000,
            'daily_audio_seconds': 1200,
            'is_active': 'on'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '用户配置已更新' in response.data.decode('utf-8')

    def test_toggle_user(self, client):
        """测试启用/禁用用户"""
        import time
        client.post('/dashboard/login', data={'password': 'admin123'})
        
        # 先创建用户
        username = f'toggleuser_{int(time.time())}'
        client.post('/dashboard/users/create', data={
            'username': username,
            'email': f'{username}@example.com',
            'daily_requests': 500,
            'daily_tokens': 50000,
            'daily_audio_seconds': 300
        })
        
        from src.auth.models import get_db
        db = get_db()
        user = db.get_user_by_username(username)
        
        # 切换状态
        response = client.post(f'/dashboard/users/{user.id}/toggle', follow_redirects=True)
        assert response.status_code == 200
        assert '用户已' in response.data.decode('utf-8')


class TestDashboardAPIKeys:
    """Dashboard API Key 管理测试"""

    def test_create_api_key(self, client):
        """测试创建 API Key"""
        import time
        client.post('/dashboard/login', data={'password': 'admin123'})
        
        # 先创建用户
        username = f'keyuser_{int(time.time())}'
        client.post('/dashboard/users/create', data={
            'username': username,
            'email': f'{username}@example.com',
            'daily_requests': 500,
            'daily_tokens': 50000,
            'daily_audio_seconds': 300
        })
        
        from src.auth.models import get_db
        db = get_db()
        user = db.get_user_by_username(username)
        
        # 创建新 Key
        response = client.post(f'/dashboard/users/{user.id}/keys/create', data={
            'name': 'test-key',
            'permissions': 'stt,tts'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert 'API Key 创建成功' in response.data.decode('utf-8')

    def test_revoke_api_key(self, client):
        """测试撤销 API Key"""
        import time
        client.post('/dashboard/login', data={'password': 'admin123'})
        
        # 先创建用户
        username = f'revokeuser_{int(time.time())}'
        client.post('/dashboard/users/create', data={
            'username': username,
            'email': f'{username}@example.com',
            'daily_requests': 500,
            'daily_tokens': 50000,
            'daily_audio_seconds': 300
        })
        
        from src.auth.models import get_db
        db = get_db()
        user = db.get_user_by_username(username)
        keys = db.get_user_api_keys(user.id)
        
        if keys:
            api_key = keys[0].key
            response = client.post(f'/dashboard/keys/{api_key}/revoke', follow_redirects=True)
            assert response.status_code == 200
            assert 'API Key 已撤销' in response.data.decode('utf-8')

    def test_revoke_nonexistent_key(self, client):
        """测试撤销不存在的 Key"""
        client.post('/dashboard/login', data={'password': 'admin123'})
        
        response = client.post('/dashboard/keys/etk_nonexistent/revoke', follow_redirects=True)
        assert response.status_code == 200
        assert 'API Key 不存在' in response.data.decode('utf-8')


class TestDashboardUsage:
    """Dashboard 用量统计测试"""

    def test_usage_page(self, client):
        """测试用量统计页面"""
        client.post('/dashboard/login', data={'password': 'admin123'})
        
        response = client.get('/dashboard/usage')
        assert response.status_code == 200
        assert '用量统计' in response.data.decode('utf-8')

    def test_usage_with_days_param(self, client):
        """测试不同时间范围"""
        client.post('/dashboard/login', data={'password': 'admin123'})
        
        response = client.get('/dashboard/usage?days=30')
        assert response.status_code == 200
        assert '30天' in response.data.decode('utf-8')


class TestDashboardAPI:
    """Dashboard API 测试"""

    def test_stats_api(self, client):
        """测试统计 API"""
        client.post('/dashboard/login', data={'password': 'admin123'})
        
        response = client.get('/dashboard/api/stats')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'labels' in data
        assert 'requests' in data
        assert 'tokens' in data

    def test_stats_api_unauthorized(self, client):
        """测试未登录访问统计 API"""
        response = client.get('/dashboard/api/stats')
        assert response.status_code == 302  # 重定向到登录
