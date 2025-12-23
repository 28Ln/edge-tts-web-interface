# EdgeTTS SDK 快速上手

## 📦 只需2个文件

```
edgetts_client.h    # 复制这个
edgetts_client.c    # 复制这个
```

## 🚀 3步开始使用

### 1. 复制文件
```bash
cp edgetts_client.h your_project/
cp edgetts_client.c your_project/
```

### 2. 写代码
```c
#include "edgetts_client.h"

// 创建
edgetts_client_t* client = edgetts_client_create("192.168.1.100", 3003);

// 使用
char* answer = NULL;
edgetts_ask(client, "你好", &answer, NULL);
printf("%s\n", answer);
free(answer);  // 记得释放

// 销毁
edgetts_client_destroy(client);
```

### 3. 编译
```cmake
# CMakeLists.txt
idf_component_register(
    SRCS "main.c" "edgetts_client.c"
    INCLUDE_DIRS "."
    REQUIRES esp_http_client
)
```

## 📡 常用接口

### 测试连接
```c
if (edgetts_ping(client)) {
    printf("连接成功\n");
}
```

### AI问答
```c
char* answer = NULL;
edgetts_ask(client, "今天天气怎么样？", &answer, NULL);
printf("%s\n", answer);
free(answer);
```

### 语音合成
```c
uint8_t* audio = NULL;
size_t size = 0;
edgetts_tts(client, "你好世界", "xiaoxiao", "wav", &audio, &size);
play_audio(audio, size);  // 播放
free(audio);
```

### 语音识别
```c
uint8_t* recorded = record_audio();  // 你的录音
char* text = NULL;
edgetts_stt(client, recorded, size, "tencent", "wav", &text);
printf("你说: %s\n", text);
free(text);
```

### 语音对话（最简单）
```c
// 说话 → 得到语音回复
uint8_t* my_voice = record_audio();
uint8_t* ai_voice = NULL;
size_t ai_size = 0;

edgetts_voice_chat_audio(client, my_voice, my_size,
                         "tencent", "xiaoxiao", "wav",
                         &ai_voice, &ai_size, NULL);

play_audio(ai_voice, ai_size);  // 播放AI回复
free(ai_voice);
```

## ⚠️ 重要提醒

### 1. 内存管理
```c
// ✅ 正确
char* answer = NULL;
edgetts_ask(client, "你好", &answer, NULL);
free(answer);  // 必须释放

// ❌ 错误
char* answer = NULL;
edgetts_ask(client, "你好", &answer, NULL);
// 忘记free，内存泄漏！
```

### 2. 错误处理
```c
if (!edgetts_ping(client)) {
    printf("错误: %s\n", edgetts_get_error(client));
}
```

### 3. 参数说明

**语音类型：**
- `"xiaoxiao"` - 晓晓(女声，温柔)
- `"yunxi"` - 云希(男声，沉稳)
- `"xiaoyi"` - 晓伊(女声，甜美)
- `"yunjian"` - 云健(男声，活力)

**识别引擎：**
- `"tencent"` - 腾讯云(准确率高，推荐)
- `"vosk"` - 本地离线(免费)

**音频格式：**
- `"wav"` - WAV格式(推荐)
- `"mp3"` - MP3格式
- `"pcm"` - 原始PCM

## 🎯 完整示例

```c
#include "edgetts_client.h"

void voice_assistant() {
    // 1. 创建客户端
    edgetts_client_t* client = edgetts_client_create("192.168.1.100", 3003);
    
    // 2. 测试连接
    if (!edgetts_ping(client)) {
        printf("服务器连接失败\n");
        return;
    }
    
    // 3. 录音
    uint8_t* my_voice = record_audio();
    size_t my_size = get_audio_size();
    
    // 4. 语音对话（一次搞定）
    uint8_t* ai_voice = NULL;
    size_t ai_size = 0;
    
    if (edgetts_voice_chat_audio(client, my_voice, my_size,
                                 "tencent", "xiaoxiao", "wav",
                                 &ai_voice, &ai_size, NULL)) {
        // 5. 播放AI回复
        play_audio(ai_voice, ai_size);
        free(ai_voice);
    }
    
    // 6. 清理
    edgetts_client_destroy(client);
}
```

## 📚 更多信息

- 详细API文档：看 `edgetts_client.h` 的注释
- 完整示例：看 `examples/simple_example.c`
- 服务端配置：看 `../README.md`

就这么简单！复制2个文件，写几行代码，搞定！
