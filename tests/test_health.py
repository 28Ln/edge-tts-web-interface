"""
健康检查接口测试
"""

import pytest


def test_health(client):
    """测试健康检查接口"""
    response = client.get('/health')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert 'timestamp' in data


def test_live(client):
    """测试存活检查接口"""
    response = client.get('/health/live')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['status'] == 'alive'
    assert 'pid' in data


def test_version(client):
    """测试版本接口"""
    response = client.get('/version')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'version' in data
    assert 'name' in data


def test_ping(client):
    """测试 MCU ping 接口"""
    response = client.get('/mcu/ping')
    assert response.status_code == 200
    assert response.data == b'pong'


def test_status(client):
    """测试 MCU 状态接口"""
    response = client.get('/mcu/status')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['success'] == True
    assert 'asr_engines' in data
