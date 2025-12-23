# 测试文档

## 测试概览

| 类别 | 数量 | 位置 |
|------|------|------|
| 单元测试 | 66 | `tests/unit/` |
| 集成测试 | 87 | `tests/integration/` |
| E2E测试 | 13 | `tests/e2e/` |
| **总计** | **166** | |

## 运行测试

### 运行所有测试
```bash
py -m pytest tests/ -v
```

### 运行特定类别
```bash
# 单元测试
py -m pytest tests/unit/ -v

# 集成测试
py -m pytest tests/integration/ -v

# E2E测试
py -m pytest tests/e2e/ -v
```

### 运行特定文件
```bash
py -m pytest tests/unit/test_services.py -v
py -m pytest tests/integration/test_admin_api.py -v
```

### 运行特定测试
```bash
py -m pytest tests/unit/test_services.py::TestAIService::test_ask_success -v
```

### 查看覆盖率
```bash
py -m pytest tests/ --cov=src --cov-report=html
```

## 测试文件说明

### 单元测试 (tests/unit/)

| 文件 | 测试内容 |
|------|----------|
| `test_audio.py` | 音频处理 (PCM转WAV, 格式检测, 时长计算) |
| `test_config.py` | 配置加载, 会话存储, 日志, 重试机制 |
| `test_exceptions.py` | 异常类 |
| `test_health.py` | 健康检查API |
| `test_services.py` | AI/ASR/TTS服务, 认证, 配额 |

### 集成测试 (tests/integration/)

| 文件 | 测试内容 |
|------|----------|
| `test_admin_api.py` | Admin API (用户管理, API Key管理) |
| `test_api_mcu.py` | MCU API v1/v2 (ping, status, tts, stt, ask) |
| `test_dashboard.py` | Dashboard (登录, 用户管理, 用量统计) |
| `test_wechat_api.py` | 微信API (chat, stt, voice, callback) |

### E2E测试 (tests/e2e/)

| 文件 | 测试内容 |
|------|----------|
| `test_full_api.py` | 完整API流程测试 |

## 测试结果 (最新)

```
===== 测试结果 =====
总测试数: 166
通过: 163 ✅
跳过: 3 ⏭️
失败: 0

跳过的测试 (需要真实API配置):
- test_stt_tencent - 需要腾讯云ASR配置
- test_voice_chat_text - 需要ASR配置
- test_stt (wechat) - 测试音频不存在
```

## 手动API测试

### 1. 启动服务器
```bash
py -m src.main
```

### 2. 健康检查
```bash
curl http://localhost:3003/health
# 预期: {"status":"healthy","timestamp":"..."}
```

### 3. Ping测试
```bash
curl http://localhost:3003/mcu/ping
# 预期: pong
```

### 4. 状态检查
```bash
curl http://localhost:3003/mcu/status
# 预期: {"success":true,"ai":true,"tts":true,"asr_engines":{...}}
```

### 5. TTS测试
```bash
curl "http://localhost:3003/mcu/tts?text=你好世界" -o test.mp3
# 预期: 生成音频文件
```

### 6. AI问答测试
```bash
curl -X POST http://localhost:3003/mcu/ask \
  -H "Content-Type: text/plain; charset=utf-8" \
  -d "你好"
# 预期: AI回答文本
```

### 7. Admin API测试
```bash
# 创建用户
curl -X POST http://localhost:3003/admin/users \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@test.com"}'

# 获取用户
curl http://localhost:3003/admin/users/test
```

### 8. V2 API测试 (带认证)
```bash
# 先创建用户获取API Key
API_KEY="etk_xxxxxxxx"

# 带认证请求
curl http://localhost:3003/v2/mcu/status \
  -H "X-API-Key: $API_KEY"
```

### 9. Dashboard测试
```
浏览器访问: http://localhost:3003/dashboard
默认密码: admin123
```

## 测试配置

### conftest.py
测试配置文件位于 `tests/conftest.py`，提供:
- Flask测试客户端
- 测试数据库
- Mock服务

### 环境变量
测试时使用的环境变量:
```
FLASK_ENV=testing
AI_API_BASE=http://mock
AI_API_KEY=test_key
```

## 添加新测试

### 单元测试示例
```python
# tests/unit/test_example.py
import pytest

class TestExample:
    def test_something(self):
        assert 1 + 1 == 2
    
    def test_with_fixture(self, app):
        with app.test_client() as client:
            response = client.get('/health')
            assert response.status_code == 200
```

### 集成测试示例
```python
# tests/integration/test_example.py
import pytest

class TestExampleAPI:
    def test_endpoint(self, client):
        response = client.get('/mcu/ping')
        assert response.data == b'pong'
```

## CI/CD 集成

### GitHub Actions
```yaml
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest tests/ -v --cov=src
```

### 本地预提交检查
```bash
# 运行测试
py -m pytest tests/ -v

# 检查覆盖率
py -m pytest tests/ --cov=src --cov-fail-under=60
```
