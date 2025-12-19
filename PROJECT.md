# Edge TTS Web Interface - 项目说明文档

## 📖 项目概述

这是一个功能完整的**语音服务平台**，提供文本转语音（TTS）、语音识别（ASR）和 AI 对话功能，支持多种客户端接入（MCU/嵌入式设备、微信小程序、Web 应用）。

### 核心特性

- 🎤 **语音合成 (TTS)**: 基于 Microsoft Edge TTS，支持多语言多音色
- 🎧 **语音识别 (ASR)**: 支持 Vosk 本地识别和腾讯云 ASR
- 🤖 **AI 对话**: 集成 OpenAI 兼容 API，支持流式对话
- 🔐 **用户认证**: API Key 认证，配额管理，用量统计
- 📊 **管理后台**: 用户管理、API Key 管理、用量监控
- 🌐 **多端支持**: MCU API、微信 API、WebSocket 实时通信
- 📝 **完整文档**: API 文档、测试指南、部署文档

### 技术栈

- **后端框架**: Flask 3.0+
- **数据库**: SQLite (可扩展到 PostgreSQL/MySQL)
- **缓存**: Redis (可选)
- **语音服务**: edge-tts, Vosk, 腾讯云 ASR
- **AI 服务**: OpenAI 兼容 API
- **测试**: pytest, pytest-cov
- **部署**: Docker, Gunicorn

---

## 🏗️ 项目架构

```
edge-tts-web-interface/
├── src/                      # 源代码
│   ├── api/                  # API 路由
│   │   ├── v1/              # v1 API (无认证)
│   │   │   ├── mcu.py       # MCU 设备 API
│   │   │   └── wechat.py    # 微信小程序 API
│   │   ├── v2/              # v2 API (带认证)
│   │   │   └── mcu.py       # MCU 设备 API v2
│   │   ├── admin.py         # 管理 API
│   │   ├── dashboard.py     # Dashboard 面板
│   │   ├── health.py        # 健康检查
│   │   ├── openapi.py       # API 文档
│   │   └── websocket.py     # WebSocket 实时通信
│   ├── auth/                # 认证授权
│   │   ├── models.py        # 用户/API Key 模型
│   │   ├── api_key.py       # API Key 认证
│   │   └── quota.py         # 配额管理
│   ├── services/            # 业务服务
│   │   ├── ai_service.py    # AI 对话服务
│   │   ├── tts_service.py   # 语音合成服务
│   │   ├── asr_service.py   # 语音识别服务
│   │   └── session_store.py # 会话存储
│   ├── utils/               # 工具函数
│   │   ├── audio.py         # 音频处理
│   │   ├── logger.py        # 日志系统
│   │   ├── middleware.py    # 中间件
│   │   └── retry.py         # 重试机制
│   ├── models/              # 数据模型
│   ├── exceptions/          # 异常定义
│   ├── config.py            # 配置管理
│   └── main.py              # 应用入口
├── tests/                   # 测试代码
│   ├── unit/               # 单元测试 (66个)
│   ├── integration/        # 集成测试 (87个)
│   └── e2e/                # 端到端测试 (13个)
├── docs/                    # 文档
│   ├── api/                # API 文档
│   ├── testing.md          # 测试指南
│   └── architecture.md     # 架构说明
├── templates/              # HTML 模板
├── static/                 # 静态资源
├── data/                   # 数据目录
│   ├── auth.db            # 用户数据库
│   ├── logs/              # 日志文件
│   └── tts/               # TTS 音频文件
└── docker/                 # Docker 配置
```

---

## 🚀 快速开始

### 环境要求

- Python 3.9+
- FFmpeg (音频处理)
- Redis (可选，用于会话存储)

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/shuo0261/edge-tts-web-interface.git
cd edge-tts-web-interface

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置必要的参数

# 4. 初始化数据库（自动创建）
python app.py

# 5. 访问服务
# Web 界面: http://localhost:3003
# API 文档: http://localhost:3003/docs
# 管理后台: http://localhost:3003/dashboard
```

### 环境变量配置

```bash
# .env 文件示例

# 服务配置
APP_ENV=development
SERVER_PORT=3003
SECRET_KEY=your-secret-key-change-in-production

# AI 服务配置
AI_API_BASE=https://api.openai.com/v1
AI_API_KEY=sk-your-openai-api-key
AI_MODEL=gpt-3.5-turbo

# 腾讯云 ASR 配置（可选）
TENCENT_SECRET_ID=your-secret-id
TENCENT_SECRET_KEY=your-secret-key

# Redis 配置（可选）
SESSION_STORE_TYPE=memory  # 或 redis
REDIS_URL=redis://localhost:6379/0

# 管理员密码
ADMIN_PASSWORD=admin123
```

---

## 📡 API 接口

### MCU API v1 (无认证)

适用于嵌入式设备快速接入：

```bash
# 语音识别
POST /mcu/stt
Content-Type: application/octet-stream
Body: <audio_data>

# AI 问答
POST /mcu/ask
Content-Type: text/plain
Body: 你好

# 语音合成
GET /mcu/tts?text=你好&voice=xiaoxiao

# 语音对话（一站式）
POST /mcu/voice_chat?out=text
Content-Type: application/octet-stream
Body: <audio_data>
```

### MCU API v2 (带认证)

生产环境推荐使用，支持配额管理：

```bash
# 所有请求需要携带 API Key
# 方式1: Header
X-API-Key: sk-your-api-key

# 方式2: Bearer Token
Authorization: Bearer sk-your-api-key

# 方式3: Query 参数
?api_key=sk-your-api-key

# 接口路径
POST /v2/mcu/stt
POST /v2/mcu/ask
GET  /v2/mcu/tts
POST /v2/mcu/voice_chat
```

### 微信 API

```bash
# 文字对话
POST /wechat/chat
{
  "message": "你好",
  "session_id": "user123"
}

# 语音转文字
POST /wechat/stt?format=amr&engine=tencent
Content-Type: application/octet-stream

# 语音对话
POST /wechat/voice?format=amr
Content-Type: application/octet-stream
```

### Admin API

```bash
# 创建用户
POST /admin/users
{
  "username": "testuser",
  "email": "test@example.com"
}

# 获取用户信息
GET /admin/users/{username}

# 创建 API Key
POST /admin/users/{username}/keys
{
  "name": "my-key",
  "permissions": "all"
}

# 撤销 API Key
POST /admin/keys/{api_key}/revoke
```

---

## 🎯 核心功能

### 1. 语音合成 (TTS)

**支持的语音**:
- 中文普通话: xiaoxiao, xiaoyi, yunxi, yunyang
- 中文粤语: hiugaai, hiumaan, wanlung
- 中文台湾话: hsiaochen, hsioayu, yunjhe
- 英语: amy, jenny, guy
- 日语: nanami, keita
- 更多语言...

**特性**:
- 多种音色选择
- 支持 SSML 标记
- 自动格式转换 (MP3/WAV)
- 可选生成字幕

### 2. 语音识别 (ASR)

**支持的引擎**:
- **Vosk**: 本地识别，无需网络，免费
- **腾讯云 ASR**: 云端识别，准确率高

**特性**:
- 自动音频格式转换
- 支持多种音频格式
- 实时流式识别 (WebSocket)

### 3. AI 对话

**特性**:
- 支持 OpenAI 兼容 API
- 流式和非流式响应
- 会话历史管理
- 多语言自动识别
- 时间上下文感知

### 4. 用户管理

**功能**:
- 用户注册和管理
- API Key 生成和管理
- 配额限制 (请求数/Token数/音频时长)
- 用量统计和监控
- 权限控制

### 5. Dashboard 管理后台

**功能**:
- 用户列表和详情
- API Key 管理
- 用量统计图表
- 实时监控
- 配额调整

访问地址: `http://localhost:3003/dashboard`
默认密码: `admin123` (请在生产环境修改)

---

## 🧪 测试

### 测试覆盖

- **代码覆盖率**: 70.64%
- **测试总数**: 166 个
- **单元测试**: 66 个
- **集成测试**: 87 个
- **E2E 测试**: 13 个

### 运行测试

```bash
# 快速测试（推荐）
py -m pytest tests/unit tests/integration -v

# 带覆盖率报告
py -m pytest tests/unit tests/integration --cov=src --cov-report=html

# 运行特定测试
py -m pytest tests/unit/test_services.py -v
py -m pytest tests/integration/test_api_mcu.py::TestMCUAPI -v

# E2E 测试（需要启动服务）
python app.py  # 终端1
py -m pytest tests/e2e -v  # 终端2
```

详细测试指南: [docs/testing.md](docs/testing.md)

---

## 🐳 Docker 部署

### 快速部署

```bash
# 构建镜像
docker build -t edge-tts-web .

# 运行容器
docker run -d \
  -p 3003:3003 \
  -v $(pwd)/data:/app/data \
  -e AI_API_KEY=your-key \
  --name edge-tts \
  edge-tts-web

# 查看日志
docker logs -f edge-tts
```

### Docker Compose

```bash
# 启动所有服务（包括 Redis）
docker-compose -f docker/docker-compose.yml up -d

# 生产环境
docker-compose -f docker/docker-compose.prod.yml up -d
```

---

## 📊 性能指标

### 响应时间

| 接口 | 平均响应时间 |
|------|-------------|
| /mcu/ping | < 5ms |
| /mcu/status | < 10ms |
| /mcu/stt | 500-2000ms (取决于音频长度) |
| /mcu/ask | 1000-3000ms (取决于 AI 服务) |
| /mcu/tts | 500-1500ms (取决于文本长度) |

### 并发能力

- 单实例: 100+ 并发请求
- 使用 Gunicorn: 500+ 并发请求
- 使用负载均衡: 无限扩展

### 资源占用

- 内存: 100-300MB (空闲)
- CPU: < 5% (空闲)
- 磁盘: 取决于音频文件数量

---

## 🔒 安全建议

### 生产环境配置

1. **修改默认密码**
   ```bash
   ADMIN_PASSWORD=your-strong-password
   SECRET_KEY=your-random-secret-key
   ```

2. **使用 HTTPS**
   - 配置 Nginx 反向代理
   - 使用 Let's Encrypt 证书

3. **限制访问**
   - 配置防火墙规则
   - 使用 API Key 认证
   - 设置合理的配额限制

4. **日志监控**
   - 定期检查日志
   - 配置告警规则
   - 监控异常请求

5. **数据备份**
   - 定期备份数据库
   - 备份配置文件
   - 备份重要音频文件

---

## 🛠️ 故障排查

### 常见问题

**1. AI 服务连接失败**
```
错误: AI服务调用失败: Connection error
解决: 检查 AI_API_BASE 和 AI_API_KEY 配置
```

**2. 腾讯云 ASR 不可用**
```
错误: 引擎不可用: tencent
解决: 配置 TENCENT_SECRET_ID 和 TENCENT_SECRET_KEY
```

**3. Vosk 模型未安装**
```
警告: Vosk 模型未安装，本地语音识别不可用
解决: 下载并解压 vosk-model-small-cn-0.22.zip
```

**4. 端口被占用**
```
错误: Address already in use
解决: 修改 SERVER_PORT 或停止占用端口的进程
```

### 日志位置

```
data/logs/
├── app.log          # 应用日志
├── api.log          # API 请求日志
├── ai.log           # AI 服务日志
├── asr.log          # ASR 服务日志
└── tts.log          # TTS 服务日志
```

---

## 📚 相关文档

- [API 文档](docs/api/) - 详细的 API 接口说明
- [测试指南](docs/testing.md) - 测试运行和编写指南
- [架构说明](docs/architecture.md) - 系统架构设计
- [部署指南](docs/deployment.md) - 生产环境部署
- [错误码说明](docs/api/error_codes.md) - API 错误码参考

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发流程

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码规范

- 遵循 PEP 8 规范
- 添加必要的注释和文档
- 编写单元测试
- 确保测试通过

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 👥 联系方式

- 项目主页: https://github.com/shuo0261/edge-tts-web-interface
- 问题反馈: https://github.com/shuo0261/edge-tts-web-interface/issues

---

## 🙏 致谢

- [edge-tts](https://github.com/rany2/edge-tts) - Microsoft Edge TTS
- [Vosk](https://alphacephei.com/vosk/) - 离线语音识别
- [Flask](https://flask.palletsprojects.com/) - Web 框架
- [OpenAI](https://openai.com/) - AI 服务

---

**最后更新**: 2024-12-18
**版本**: 1.0.0
**状态**: ✅ 生产就绪
