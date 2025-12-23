# 快速开始

## 环境要求

- Python 3.10+
- FFmpeg (可选，用于音频转换)

## 安装

### 1. 克隆项目
```bash
git clone https://github.com/your-repo/edge-tts-web-interface.git
cd edge-tts-web-interface
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量
```bash
# 复制示例配置
cp .env.example .env

# 编辑配置
# 必须配置:
# - AI_API_BASE: AI API地址
# - AI_API_KEY: AI API密钥
```

### 4. 启动服务
```bash
py -m src.main
```

### 5. 验证
```bash
# 健康检查
curl http://localhost:3003/health

# Ping测试
curl http://localhost:3003/mcu/ping
```

## 端口配置

| 服务 | 默认端口 | 环境变量 |
|------|----------|----------|
| Web服务 | 3003 | `PORT` |

## 访问地址

| 功能 | 地址 |
|------|------|
| 健康检查 | http://localhost:3003/health |
| API文档 | http://localhost:3003/docs |
| 管理面板 | http://localhost:3003/dashboard |
| WebSocket测试 | http://localhost:3003/realtime |

## 快速测试

### TTS (语音合成)
```bash
curl "http://localhost:3003/mcu/tts?text=你好世界" -o hello.mp3
```

### AI问答
```bash
curl -X POST http://localhost:3003/mcu/ask \
  -H "Content-Type: text/plain; charset=utf-8" \
  -d "你好，请介绍一下自己"
```

### 创建用户和API Key
```bash
curl -X POST http://localhost:3003/admin/users \
  -H "Content-Type: application/json" \
  -d '{"username":"myuser","email":"my@email.com"}'
```

## 管理面板

1. 访问 http://localhost:3003/dashboard
2. 输入密码: `admin123` (可通过 `ADMIN_PASSWORD` 修改)
3. 功能:
   - 用户管理
   - API Key管理
   - 用量统计

## 下一步

- [API文档](API.md) - 完整API接口说明
- [配置文档](configuration.md) - 详细配置选项
- [测试文档](TESTING.md) - 如何运行测试
- [架构文档](architecture.md) - 项目架构说明

## 常见问题

### Q: 端口被占用
```bash
# 修改端口
export PORT=3004
py -m src.main
```

### Q: AI服务不可用
检查 `.env` 文件中的 `AI_API_BASE` 和 `AI_API_KEY` 配置

### Q: TTS生成失败
确保网络可以访问 Edge TTS 服务

### Q: ASR识别失败
- Vosk: 需要下载模型文件
- 腾讯云: 需要配置 `TENCENT_SECRET_ID`, `TENCENT_SECRET_KEY`, `TENCENT_APPID`
