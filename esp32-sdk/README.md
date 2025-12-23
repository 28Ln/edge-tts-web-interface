# EdgeTTS Client SDK for ESP32

**独立的、零依赖的C语言HTTP客户端库**

## 🎯 特点

- ✅ **独立使用** - 只需2个文件：`.h` + `.c`
- ✅ **零耦合** - 不依赖任何其他代码
- ✅ **跨项目** - 可以复制到任何ESP32项目
- ✅ **纯C语言** - 兼容C和C++项目
- ✅ **简单API** - 函数式调用，易于使用

## 📦 文件结构

```
esp32-sdk/
├── src/
│   ├── edgetts_client.h    # 头文件（复制这个）
│   └── edgetts_client.c    # 实现文件（复制这个）
└── examples/
    └── simple_example.c    # 使用示例
```

## 🚀 快速开始

### 1. 复制文件到你的项目

```bash
# 只需复制这2个文件
cp esp32-sdk/src/edgetts_client.h your_project/components/
cp esp32-sdk/src/edgetts_client.c your_project/components/
```

### 2. 在你的代码中使用

```c
#include "edgetts_client.h"

void app_main() {
    // 创建客户端
    edgetts_client_t* client = edgetts_client_create("192.168.1.100", 3003);
    
    // Ping测试
    if (edgetts_ping(client)) {
        printf("连接成功\n");
    }
    
    // AI问答
    char* answer = NULL;
    if (edgetts_ask(client, "你好", &answer, NULL)) {
        printf("回答: %s\n", answer);
        free(answer);  // 记得释放
    }
    
    // 销毁客户端
    edgetts_client_destroy(client);
}
```

## 📡 支持的API

| 函数 | 功能 | 说明 |
|------|------|------|
| `edgetts_ping()` | 连接测试 | 最简单 |
| `edgetts_ask()` | AI问答 | 核心功能 |
| `edgetts_stt()` | 语音识别 | 音频→文字 |
| `edgetts_tts()` | 语音合成 | 文字→音频 |
| `edgetts_voice_chat_audio()` | 语音对话 | 一站式 |

## 💻 完整示例

```c
#include "edgetts_client.h"
#include <stdio.h>
#include <stdlib.h>

void test_edgetts() {
    // 1. 创建
    edgetts_client_t* client = edgetts_client_create("192.168.1.100", 3003);
    
    // 2. 配置
    edgetts_set_timeout(client, 15000);  // 15秒超时
    edgetts_set_retry(client, 3);        // 重试3次
    
    // 3. 测试连接
    if (!edgetts_ping(client)) {
        printf("错误: %s\n", edgetts_get_error(client));
        goto cleanup;
    }
    
    // 4. AI问答
    char* answer = NULL;
    if (edgetts_ask(client, "你好", &answer, NULL)) {
        printf("AI: %s\n", answer);
        free(answer);
    }
    
    // 5. 语音合成
    uint8_t* audio = NULL;
    size_t size = 0;
    if (edgetts_tts(client, "你好世界", "xiaoxiao", "wav", &audio, &size)) {
        printf("音频大小: %zu bytes\n", size);
        // 播放或保存音频...
        free(audio);
    }
    
cleanup:
    // 6. 清理
    edgetts_client_destroy(client);
}
```

## 🔧 集成到ESP-IDF项目

### CMakeLists.txt

```cmake
idf_component_register(
    SRCS "main.c" "edgetts_client.c"
    INCLUDE_DIRS "."
    REQUIRES esp_http_client
)
```

### 或者创建独立组件

```
your_project/
├── main/
│   └── main.c
└── components/
    └── edgetts/
        ├── CMakeLists.txt
        ├── edgetts_client.h
        └── edgetts_client.c
```

`components/edgetts/CMakeLists.txt`:
```cmake
idf_component_register(
    SRCS "edgetts_client.c"
    INCLUDE_DIRS "."
    REQUIRES esp_http_client
)
```

## 📝 API参考

### 初始化

```c
// 创建客户端
edgetts_client_t* client = edgetts_client_create("192.168.1.100", 3003);

// 设置超时(毫秒)
edgetts_set_timeout(client, 10000);

// 设置重试次数
edgetts_set_retry(client, 3);

// 销毁客户端
edgetts_client_destroy(client);
```

### 基础功能

```c
// Ping测试
bool success = edgetts_ping(client);

// 获取状态
char* status = NULL;
edgetts_get_status(client, &status);
free(status);
```

### AI问答

```c
// 普通问答
char* answer = NULL;
edgetts_ask(client, "你好", &answer, NULL);
free(answer);

// 带会话ID的问答
edgetts_ask(client, "我叫小明", &answer, "session123");
free(answer);
```

### 语音识别

```c
uint8_t* audio_data = ...; // 你的音频数据
size_t audio_size = ...;

char* text = NULL;
edgetts_stt(client, audio_data, audio_size, "tencent", "wav", &text);
printf("识别结果: %s\n", text);
free(text);
```

### 语音合成

```c
uint8_t* audio = NULL;
size_t size = 0;
edgetts_tts(client, "你好世界", "xiaoxiao", "wav", &audio, &size);
// 播放音频...
free(audio);
```

### 语音对话

```c
uint8_t* input_audio = ...;
size_t input_size = ...;

uint8_t* output_audio = NULL;
size_t output_size = 0;

edgetts_voice_chat_audio(client, 
    input_audio, input_size,
    "tencent", "xiaoxiao", "wav",
    &output_audio, &output_size,
    NULL);

// 播放output_audio...
free(output_audio);
```

## ⚠️ 注意事项

### 内存管理

所有返回的指针（`char*`, `uint8_t*`）都需要调用者释放：

```c
char* answer = NULL;
if (edgetts_ask(client, "你好", &answer, NULL)) {
    // 使用answer...
    free(answer);  // ✅ 必须释放
}
```

### 错误处理

```c
if (!edgetts_ping(client)) {
    printf("错误: %s\n", edgetts_get_error(client));
}
```

### 线程安全

当前实现**不是线程安全的**，如果需要多线程使用，请：
1. 每个线程创建独立的client
2. 或者使用互斥锁保护

## 🎯 使用场景

### 场景1: 简单问答机器人
```c
edgetts_client_t* client = edgetts_client_create(HOST, PORT);
char* answer = NULL;
edgetts_ask(client, "今天天气怎么样？", &answer, NULL);
printf("%s\n", answer);
free(answer);
edgetts_client_destroy(client);
```

### 场景2: 语音助手
```c
// 录音 → 识别 → 问答 → 合成 → 播放
uint8_t* recorded_audio = record_audio();
char* text = NULL;
edgetts_stt(client, recorded_audio, size, "tencent", "wav", &text);

char* answer = NULL;
edgetts_ask(client, text, &answer, NULL);

uint8_t* tts_audio = NULL;
size_t tts_size = 0;
edgetts_tts(client, answer, "xiaoxiao", "wav", &tts_audio, &tts_size);
play_audio(tts_audio, tts_size);

free(text);
free(answer);
free(tts_audio);
```

### 场景3: 一站式语音对话
```c
// 最简单：一次调用完成所有
uint8_t* input = record_audio();
uint8_t* output = NULL;
size_t output_size = 0;

edgetts_voice_chat_audio(client, input, input_size,
    "tencent", "xiaoxiao", "wav",
    &output, &output_size, NULL);

play_audio(output, output_size);
free(output);
```

## 📚 更多信息

- 服务端API文档: `../API_INVENTORY.md`
- 完整项目示例: `../esp32s3-example/`
