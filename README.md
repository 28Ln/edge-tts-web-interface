# Edge TTS Web Interface

基于 Flask 的语音服务平台，支持 TTS (语音合成)、ASR (语音识别)、AI 问答。

## ✨ 功能特性

- **TTS (语音合成)**: 基于 Microsoft Edge TTS，支持多种语音
- **ASR (语音识别)**: 支持腾讯云 ASR 和 Vosk 离线识别
- **AI 问答**: 支持 OpenAI 兼容接口 (DeepSeek, Gemini 等)
- **语音对话**: ASR + AI + TTS 一体化
- **用户管理**: API Key 认证和配额管理
- **管理面板**: Web 界面管理用户和查看统计
- **ESP32 支持**: 提供 ESP32 SDK 和示例

## 🚀 快速开始

### 1. 安装
```bash
git clone https://github.com/your-repo/edge-tts-web-interface.git
cd edge-tts-web-interface
pip install -r requirements.txt
```

### 2. 配置
```bash
cp .env.example .env
# 编辑 .env 配置 AI_API_BASE 和 AI_API_KEY
```

### 3. 启动
```bash
py -m src.main
```

### 4. 验证
```bash
curl http://localhost:3003/health
curl http://localhost:3003/mcu/ping
```

## 📡 API 端点

| 端点 | 说明 | 认证 |
|------|------|------|
| `/health` | 健康检查 | 无 |
| `/mcu/ping` | 连通测试 | 无 |
| `/mcu/status` | 服务状态 | 无 |
| `/mcu/tts` | 语音合成 | 无 |
| `/mcu/stt` | 语音识别 | 无 |
| `/mcu/ask` | AI问答 | 无 |
| `/v2/mcu/*` | v2 API | API Key |
| `/admin/*` | 管理API | 无 |
| `/dashboard` | 管理面板 | 密码 |
| `/docs` | API文档 | 无 |

## 🔧 配置

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `PORT` | 服务端口 | 3003 |
| `AI_API_BASE` | AI API地址 | - |
| `AI_API_KEY` | AI API密钥 | - |
| `ADMIN_PASSWORD` | 管理面板密码 | admin123 |

详见 [配置文档](docs/configuration.md)

## 📖 文档

| 文档 | 说明 |
|------|------|
| [快速开始](docs/QUICKSTART.md) | 安装和运行 |
| [API文档](docs/API.md) | 完整API接口 |
| [测试文档](docs/testing.md) | 测试指南 |
| [配置文档](docs/configuration.md) | 配置选项 |
| [架构文档](docs/architecture.md) | 项目架构 |
| [错误码](docs/error-codes.md) | 错误码说明 |

## 🧪 测试

```bash
# 运行所有测试
py -m pytest tests/ -v

# 查看覆盖率
py -m pytest tests/ --cov=src
```

**测试结果**: 163/166 通过 (98.2%)

详见 [测试文档](docs/TESTING.md)

## 📁 项目结构

```
├── src/                  # 源代码
│   ├── api/              # API路由
│   │   ├── admin/        # Admin API
│   │   ├── dashboard/    # 管理面板
│   │   ├── websocket/    # WebSocket
│   │   ├── v1/           # API v1
│   │   └── v2/           # API v2
│   ├── services/         # 业务服务
│   ├── repositories/     # 数据访问
│   ├── auth/             # 认证模块
│   └── utils/            # 工具函数
├── tests/                # 自动化测试
│   ├── unit/             # 单元测试
│   ├── integration/      # 集成测试
│   └── e2e/              # 端到端测试
├── scripts/              # 工具脚本
├── docs/                 # 文档
├── data/                 # 数据目录
├── docker/               # Docker配置
├── esp32-sdk/            # ESP32 SDK
├── examples/             # 示例代码
│   ├── android/          # Android示例
│   ├── esp32/            # ESP32示例
│   └── python/           # Python示例
└── static/               # 静态资源
```

## 🔌 ESP32 支持

提供 ESP32 SDK 用于嵌入式设备接入:

```c
#include "edgetts_client.h"

edgetts_client_t* client = edgetts_client_create("192.168.1.100", 3003);
edgetts_ping(client);
edgetts_tts(client, "你好", "xiaoxiao", "wav", &audio, &size);
```

详见 [ESP32 SDK](esp32-sdk/README.md)

## 📝 许可

MIT License - 详见 [LICENSE](LICENSE)
