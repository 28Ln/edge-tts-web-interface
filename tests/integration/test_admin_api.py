"""
Admin API 集成测试
"""

import pytest


class TestAdminUserAPI:
    """用户管理 API 测试"""

    def test_create_user(self, client, admin_headers):
        """测试创建用户"""
        import time
        username = f"testuser_{int(time.time())}"
        response = client.post('/admin/users', json={
            "username": username,
            "email": f"{username}@example.com"
        }, headers=admin_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['user']['username'] == username
        assert 'api_key' in data
        assert data['api_key'].startswith('etk_')

    def test_create_user_missing_fields(self, client, admin_headers):
        """测试缺少必填字段"""
        response = client.post('/admin/users', json={
            "username": "testuser2"
        }, headers=admin_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert data['error_code'] == 'VALIDATION_ERROR'

    def test_create_duplicate_user(self, client, admin_headers):
        """测试创建重复用户"""
        import time
        username = f"dupuser_{int(time.time())}"
        # 先创建一个用户
        client.post('/admin/users', json={
            "username": username,
            "email": f"{username}@example.com"
        }, headers=admin_headers)
        # 再次创建同名用户
        response = client.post('/admin/users', json={
            "username": username,
            "email": f"{username}2@example.com"
        }, headers=admin_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert data['error_code'] == 'USER_EXISTS'

    def test_get_user(self, client, admin_headers):
        """测试获取用户信息"""
        import time
        username = f"getuser_{int(time.time())}"
        # 先创建用户
        client.post('/admin/users', json={
            "username": username,
            "email": f"{username}@example.com"
        }, headers=admin_headers)
        # 获取用户
        response = client.get(f'/admin/users/{username}', headers=admin_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['user']['username'] == username
        assert 'quota' in data
        assert 'usage' in data

    def test_get_nonexistent_user(self, client, admin_headers):
        """测试获取不存在的用户"""
        response = client.get('/admin/users/nonexistent_xyz', headers=admin_headers)
        assert response.status_code == 404
        data = response.get_json()
        assert data['error_code'] == 'NOT_FOUND'

    def test_create_user_no_auth(self, client):
        """测试无认证创建用户"""
        response = client.post('/admin/users', json={
            "username": "noauth",
            "email": "noauth@example.com"
        })
        assert response.status_code == 401


class TestAdminAPIKeyAPI:
    """API Key 管理测试"""

    def test_create_api_key(self, client, admin_headers):
        """测试创建 API Key"""
        import time
        username = f"keyuser_{int(time.time())}"
        # 先创建用户
        client.post('/admin/users', json={
            "username": username,
            "email": f"{username}@example.com"
        }, headers=admin_headers)
        # 创建新 Key
        response = client.post(f'/admin/users/{username}/keys', json={
            "name": "test-key",
            "permissions": "stt,tts"
        }, headers=admin_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['api_key']['name'] == 'test-key'
        assert data['api_key']['key'].startswith('etk_')

    def test_list_api_keys(self, client, admin_headers):
        """测试列出 API Keys"""
        import time
        username = f"listuser_{int(time.time())}"
        # 先创建用户
        client.post('/admin/users', json={
            "username": username,
            "email": f"{username}@example.com"
        }, headers=admin_headers)
        # 列出 Keys
        response = client.get(f'/admin/users/{username}/keys', headers=admin_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'keys' in data
        assert len(data['keys']) >= 1  # 至少有默认 key

    def test_revoke_api_key(self, client, admin_headers):
        """测试撤销 API Key"""
        import time
        username = f"revokeuser_{int(time.time())}"
        # 先创建用户和 Key
        create_resp = client.post('/admin/users', json={
            "username": username,
            "email": f"{username}@example.com"
        }, headers=admin_headers)
        api_key = create_resp.get_json()['api_key']
        
        # 撤销 Key
        response = client.post(f'/admin/keys/{api_key}/revoke', headers=admin_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_revoke_nonexistent_key(self, client, admin_headers):
        """测试撤销不存在的 Key"""
        response = client.post('/admin/keys/etk_nonexistent/revoke', headers=admin_headers)
        assert response.status_code == 404


class TestV2AuthenticatedAPI:
    """v2 API 认证流程测试"""

    def test_full_auth_flow(self, client, admin_headers):
        """测试完整认证流程"""
        import time
        username = f"authuser_{int(time.time())}"
        # 1. 创建用户获取 API Key
        create_resp = client.post('/admin/users', json={
            "username": username,
            "email": f"{username}@example.com"
        }, headers=admin_headers)
        api_key = create_resp.get_json()['api_key']
        
        # 2. 使用 API Key 访问 v2 状态接口
        response = client.get('/v2/mcu/status', headers={
            'X-API-Key': api_key
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['authenticated'] is True
        assert 'quota' in data

    def test_bearer_auth(self, client, admin_headers):
        """测试 Bearer 认证方式"""
        import time
        username = f"beareruser_{int(time.time())}"
        # 创建用户
        create_resp = client.post('/admin/users', json={
            "username": username,
            "email": f"{username}@example.com"
        }, headers=admin_headers)
        api_key = create_resp.get_json()['api_key']
        
        # 使用 Bearer 方式
        response = client.get('/v2/mcu/status', headers={
            'Authorization': f'Bearer {api_key}'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['authenticated'] is True

    def test_query_param_auth(self, client, admin_headers):
        """测试 Query 参数认证方式"""
        import time
        username = f"queryuser_{int(time.time())}"
        # 创建用户
        create_resp = client.post('/admin/users', json={
            "username": username,
            "email": f"{username}@example.com"
        }, headers=admin_headers)
        api_key = create_resp.get_json()['api_key']
        
        # 使用 Query 参数方式
        response = client.get(f'/v2/mcu/status?api_key={api_key}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['authenticated'] is True
