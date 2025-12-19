# Edge TTS Web Interface

**[中文](README.md)** | **[English](README.en.md)**

---

这是一个基于 Flask 的 Web 应用，使用 Microsoft Edge 的文本转语音（TTS）引擎生成音频文件，并支持语音转文本（STT）功能。

## 功能

- **文本转语音（TTS）**：
  - 将文本转换为语音
  - 支持多国语言（中文[包括普通话、粤语和台湾话]、英文、日文、西班牙语等）
  - 支持自定义语音参数（如语速、音调、音量）
  - 支持 SSML 输入
  - 生成的音频支持多种格式（默认 MP3，可转换为 WAV 等）
  - 可选生成字幕文件（SRT 格式）
  - 实时日志显示
  - 音频文件支持预览、在线播放和下载
  - 自动清理旧文件，只保留最新生成的音频和字幕
  - 支持通过 API 接口生成音频（`/api/tts`）

- **语音转文本（STT）**：
  - 支持上传音频文件并转换为文本（基于 Vosk 模型）
  - 要求音频为单声道 16kHz WAV 格式（非 WAV 文件会自动转换）

- **界面功能**：
  - 支持中英文切换
  - 支持深色模式

## 安装和运行

### 前置要求

- **FFmpeg**：用于音频处理和格式转换。代码会自动检测并尝试安装（Linux、macOS、Windows）。
- **Vosk 模型**：用于 STT 功能。需手动下载 `vosk-model-small-cn-0.22.zip` 并解压到项目根目录下的 `vosk-model-small-cn-0.22` 文件夹。
  - 下载地址：`https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip`

### 本地运行

1. 克隆仓库：
   ```sh
   git clone https://github.com/shuo0261/edge-tts-web-interface.git
   ```
2. 进入项目目录：
   ```sh
   cd edge-tts-web-interface
   ```
3. 安装依赖：
   ```sh
   python -m pip install --upgrade pip
   pip install -r requirements.txt --no-cache-dir
   ```
4. 下载并解压 Vosk 模型到 `vosk-model-small-cn-0.22` 文件夹。
5. 运行应用：
   ```sh
   python app.py
   ```
6. 在浏览器中访问 `http://localhost:2024`

### Docker 部署

1. 克隆仓库：
   ```sh
   git clone https://github.com/shuo0261/edge-tts-web-interface.git
   ```
2. 进入项目目录：
   ```sh
   cd edge-tts-web-interface
   ```
3. 构建 Docker 镜像：
   ```dockerfile
   docker build -t edge-tts-web .
   ```
4. 运行 Docker 容器：
   ```dockerfile
   docker run -d -p 2024:2024 --name edge-tts-web edge-tts-web
   ```
5. 在浏览器中访问 `http://localhost:2024`

**注意**：如果需要保存生成的音频文件到主机，可以使用卷挂载：
   ```dockerfile
   docker run -d -p 2024:2024 -v /path/on/host:/app/tts --name edge-tts-web edge-tts-web
   ```
   将 `/path/on/host` 替换为你主机上想要保存文件的路径。

## 使用

### API 接口请求

#### `/api/tts` - 文本转语音
- **方法**：POST
- **请求格式**：JSON
- **示例**：
  ```json
  {
      "text": "你好，世界",
      "file_name": "test",
      "voice": "xiaoxiao",
      "output_format": "mp3"
  }
  ```
- **参数说明**：
  - `text`（必需）：要转换的文本
  - `file_name`（可选）：输出文件名（默认 `output`）
  - `voice`（可选）：语音类型（默认 `xiaoxiao`，见下方支持的语音列表）
  - `output_format`（可选）：输出音频格式（默认 `mp3`）
- **返回格式**：
  - 成功：
    ```json
    {
        "result": "success",
        "file_url": "http://localhost:2024/download/test.mp3"
    }
    ```
  - 失败：
    ```json
    {
        "result": "error",
        "message": "错误信息"
    }
    ```

#### `/stt` - 语音转文本
- **方法**：POST
- **请求格式**：multipart/form-data，上传字段名为 `audio_file`
- **要求**：音频文件需为单声道 16kHz WAV 格式（其他格式会自动转换）
- **返回格式**：
  - 成功：
    ```json
    {
        "result": "success",
        "transcription": "转换后的文本",
        "console": "日志内容"
    }
    ```
  - 失败：
    ```json
    {
        "result": "error",
        "message": "错误信息",
        "console": "日志内容"
    }
    ```

### Web 使用

1. **文本转语音**：
   - 在文本框中输入要转换的文字（支持上传 `.txt` 文件）
   - 选择语音（如 `xiaoxiao`）
   - 输入文件名（不含扩展名）
   - 可选：调整语速（`rate`）、音调（`pitch`）、音量（`volume`）或输入 SSML
   - 可选：勾选生成字幕（SRT）
   - 点击“生成语音”按钮
   - 生成完成后，可播放或下载音频文件

2. **语音转文本**：
   - 上传音频文件到 `/stt` 页面
   - 等待处理完成，查看转换结果

### 支持的语音列表
| ID         | 语音名称                  | 语言       |
|------------|---------------------------|------------|
| xiaoxiao   | zh-CN-XiaoxiaoNeural      | 中文（普通话） |
| xiaoyi     | zh-CN-XiaoyiNeural        | 中文（普通话） |
| yunjian    | zh-CN-YunjianNeural       | 中文（普通话） |
| yunxi      | zh-CN-YunxiNeural         | 中文（普通话） |
| yunxia     | zh-CN-YunxiaNeural        | 中文（普通话） |
| yunyang    | zh-CN-YunyangNeural       | 中文（普通话） |
| xiaobei    | zh-CN-liaoning-XiaobeiNeural | 中文（辽宁话） |
| xiaoni     | zh-CN-shaanxi-XiaoniNeural | 中文（陕西话） |
| hiugaai    | zh-HK-HiuGaaiNeural       | 中文（粤语） |
| hiumaan    | zh-HK-HiuMaanNeural       | 中文（粤语） |
| wanlung    | zh-HK-WanLungNeural       | 中文（粤语） |
| hsiaochen  | zh-TW-HsiaoChenNeural     | 中文（台湾话） |
| hsioayu    | zh-TW-HsiaoYuNeural       | 中文（台湾话） |
| yunjhe     | zh-TW-YunJheNeural        | 中文（台湾话） |
| amy        | en-US-AmyNeural           | 英文       |
| nanami     | ja-JP-NanamiNeural        | 日文       |
| luna       | es-ES-LunaNeural          | 西班牙语   |

### 中英文切换
- 点击右上角语言切换按钮（中文或英文图标），切换页面语言。

### 深色模式
- 点击右上角主题切换按钮（太阳或月亮图标），切换深色或浅色模式。

## 📚 文档

- **[完整项目说明](PROJECT.md)** - 详细的项目文档
- **[测试指南](docs/testing.md)** - 测试运行和编写指南
- **[API 文档](docs/api/)** - API 接口说明
- **[架构说明](docs/architecture.md)** - 系统架构设计

## 测试

项目包含完整的测试套件，覆盖率达到 **70%+**。

### 运行测试
```bash
# 运行单元测试和集成测试（推荐）
py -m pytest tests/unit tests/integration -v

# 带覆盖率报告
py -m pytest tests/unit tests/integration --cov=src --cov-report=term-missing

# 运行所有测试（包括需要真实服务的 E2E 测试）
py -m pytest tests/ -v
```

### 测试统计
- **单元测试**: 66 个 - 测试独立模块和函数
- **集成测试**: 87 个 - 测试 API 接口
- **E2E 测试**: 13 个 - 测试完整业务流程（需要真实服务）
- **总计**: 166 个测试

详细测试指南请参考 [docs/testing.md](docs/testing.md)

## 依赖

- Flask
- edge-tts
- FFmpeg
- vosk
- werkzeug
- requests
- pytest (开发依赖)
- pytest-cov (开发依赖)

## 贡献

欢迎提交问题和拉取请求。对于重大更改，请先开 issue 讨论您想要更改的内容。

## 许可

此项目采用 MIT 许可证 - 详情请见 [LICENSE](LICENSE) 文件。