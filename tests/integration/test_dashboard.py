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
        assert 'sk-' in response.data.decode('utf-8')  # API Key

    def test_create_user_missing_fields(self, client):
        """测试创建用户缺少字段"""
        client.post('/dashboard/login', data={'password': 'admin123'})
        
        response = client.post('/dashboard/users/create', data={
            'username': 'testuser'
            # 缺少 email
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '不能为空' in response.data.decode('utf-8')


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
