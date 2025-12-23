# ESP32-S3 EdgeTTS Client Example

这是一个完整的ESP32-S3项目示例，展示如何调用EdgeTTS Web Interface API。

## 📋 功能

- ✅ WiFi连接
- ✅ 连接测试 (`/mcu/ping`)
- ✅ 服务状态 (`/mcu/status`)
- ✅ AI问答 (`/mcu/ask`)
- ✅ 语音合成 (`/mcu/tts`)
- ✅ 语音识别 (`/mcu/stt`)
- ✅ 语音对话 (`/mcu/voice_chat`)

## 🛠️ 硬件要求

- ESP32-S3 开发板
- 8MB Flash（推荐）

## 📦 软件要求

- ESP-IDF v5.0 或更高版本

## 🚀 快速开始

### 1. 配置项目

```bash
# 进入项目目录
cd esp32s3-example

# 配置WiFi和服务器地址
idf.py menuconfig
# 进入: EdgeTTS Client Configuration
# 设置: WiFi SSID, WiFi Password, Server Host, Server Port
```

### 2. 编译项目

```bash
# 清理并编译
idf.py fullclean
idf.py build
```

### 3. 烧录和监控

```bash
# 烧录到设备
idf.py -p COM3 flash

# 查看串口输出
idf.py -p COM3 monitor
```

## 📝 配置说明

### WiFi配置
- SSID: 在 `menuconfig` 中设置
- Password: 在 `menuconfig` 中设置

### 服务器配置
- Host: EdgeTTS服务器IP地址（默认: 192.168.1.100）
- Port: EdgeTTS服务器端口（默认: 3003）

### 分区表
项目使用自定义分区表 `partitions.csv`：
- App分区: 3MB (足够大的空间)
- NVS: 24KB
- PHY: 4KB
- Storage: 960KB (可选，用于存储文件)

## 🔧 API使用示例

### 连接测试
```c
if (edgetts_ping()) {
    ESP_LOGI(TAG, "服务器连接正常");
}
```

### AI问答
```c
char answer[512];
if (edgetts_ask("你好", answer, sizeof(answer))) {
    ESP_LOGI(TAG, "回答: %s", answer);
}
```

### 语音合成
```c
int audio_size = edgetts_tts_get_size("你好世界", "xiaoxiao");
// 然后下载音频数据...
```

## 📊 内存使用

- 程序大小: ~1MB
- 运行时RAM: ~100KB
- HTTP缓冲区: 4KB

## 🐛 故障排除

### 编译错误: app partition too small
- 解决方案: 已使用3MB分区表，足够大

### WiFi连接失败
- 检查SSID和密码是否正确
- 检查WiFi信号强度

### 服务器连接失败
- 检查服务器IP和端口
- 确保ESP32和服务器在同一网络
- 检查防火墙设置

## 📚 相关文档

- [EdgeTTS API文档](../esp32/docs/API.md)
- [集成指南](../esp32/INTEGRATION_GUIDE.md)
- [ESP-IDF文档](https://docs.espressif.com/projects/esp-idf/)
