# 测试指南

## 测试概览

本项目采用三层测试架构：
- **单元测试** (`tests/unit/`) - 测试独立模块和函数
- **集成测试** (`tests/integration/`) - 测试 API 接口和模块集成
- **端到端测试** (`tests/e2e/`) - 测试完整业务流程（需要真实服务）

## 快速开始

### 运行所有测试（推荐）
```bash
# 运行单元测试和集成测试
py -m pytest tests/unit tests/integration -v

# 带覆盖率报告
py -m pytest tests/unit tests/integration --cov=src --cov-report=term-missing
```

### 运行特定测试
```bash
# 只运行单元测试
py -m pytest tests/unit -v

# 只运行集成测试
py -m pytest tests/integration -v

# 运行特定测试文件
py -m pytest tests/unit/test_services.py -v

# 运行特定测试类
py -m pytest tests/unit/test_services.py::TestAIService -v

# 运行特定测试方法
py -m pytest tests/unit/test_services.py::TestAIService::test_ask_success -v
```

### 端到端测试（需要启动服务）
```bash
# 1. 先启动服务
py app.py

# 2. 在另一个终端运行 E2E 测试
py -m pytest tests/e2e -v

# 或指定服务器地址
SERVER_URL=http://192.168.1.100:3003 py -m pytest tests/e2e -v
```

## 测试覆盖情况

### 当前覆盖率: 70%+

| 模块 | 覆盖率 | 说明 |
|------|--------|------|
| 配置模块 | 89% | ✅ 良好 |
| 异常处理 | 100% | ✅ 完整 |
| 数据模型 | 95% | ✅ 良好 |
| 认证模块 | 78-93% | ✅ 良好 |
| AI 服务 | 80% | ✅ 良好 |
| TTS 服务 | 72% | ✅ 可接受 |
| ASR 服务 | 60% | ⚠️ 需外部服务 |
| MCU API v1 | 85% | ✅ 良好 |
| MCU API v2 | 73% | ✅ 良好 |
| 微信 API | 71% | ✅ 良好 |
| Dashboard | 93% | ✅ 良好 |
| 音频工具 | 94% | ✅ 良好 |

### 测试统计
- 单元测试: 66 个
- 集成测试: 87 个
- E2E 测试: 13 个（需要真实服务）
- **总计: 166 个测试**

## 测试文件说明

### 单元测试 (`tests/unit/`)
```
tests/unit/
├── test_audio.py       # 音频处理工具测试
├── test_config.py      # 配置、日志、会话存储测试
├── test_exceptions.py  # 异常类测试
├── test_health.py      # 健康检查测试
└── test_services.py    # 服务层测试（AI/ASR/TTS/认证）
```

### 集成测试 (`tests/integration/`)
```
tests/integration/
├── test_admin_api.py   # Admin API 测试
├── test_api_mcu.py     # MCU API v1/v2 测试
├── test_dashboard.py   # Dashboard 管理面板测试
└── test_wechat_api.py  # 微信 API 测试
```

### E2E 测试 (`tests/e2e/`)
```
tests/e2e/
└── test_full_api.py    # 完整 API 端到端测试
```

## 编写测试

### Mock 外部服务
```python
from unittest.mock import patch, Mock

def test_ai_ask_success(self, client):
    """测试 AI 问答成功"""
    with patch('src.api.v1.mcu.get_ai_service') as mock_ai:
        mock_service = Mock()
        mock_service.ask.return_value = 'AI回答'
        mock_ai.return_value = mock_service
        
        response = client.post('/mcu/ask', data='你好')
        
        assert response.status_code == 200
        assert response.data.decode('utf-8') == 'AI回答'
```

### 使用 Fixtures
```python
# tests/conftest.py 中定义的 fixtures
def test_example(client):
    """client fixture 自动创建测试客户端"""
    response = client.get('/health')
    assert response.status_code == 200
```

## 常见问题

### E2E 测试失败
E2E 测试需要真实的外部服务（AI API、腾讯云 ASR 等），在没有配置这些服务时会失败，这是正常的。

### 临时文件权限错误（Windows）
在 Windows 上运行 TTS 测试时可能遇到文件锁定问题，测试已做兼容处理。

### 测试数据库
测试使用独立的 SQLite 数据库，不会影响生产数据。

## CI/CD 集成

```yaml
# GitHub Actions 示例
- name: Run Tests
  run: |
    pip install -r requirements.txt
    py -m pytest tests/unit tests/integration --cov=src --cov-fail-under=50
```
