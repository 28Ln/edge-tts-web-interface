/**
 * ============================================================================
 * EdgeTTS Client SDK for ESP32
 * ============================================================================
 * 
 * 这是一个独立的、零依赖的EdgeTTS HTTP客户端库
 * 只需复制 .h 和 .c 两个文件到你的项目即可使用
 * 
 * 快速开始：
 * 1. 复制 edgetts_client.h 和 edgetts_client.c 到你的项目
 * 2. 在你的代码中 #include "edgetts_client.h"
 * 3. 创建客户端：edgetts_client_t* client = edgetts_client_create("192.168.1.100", 3003);
 * 4. 调用API：edgetts_ask(client, "你好", &answer, NULL);
 * 5. 释放资源：edgetts_client_destroy(client);
 * 
 * 注意事项：
 * - 所有返回的字符串和数据需要调用者用 free() 释放
 * - 出错时通过 edgetts_get_error() 获取错误信息
 * - 不是线程安全的，多线程使用请创建多个客户端实例
 * 
 * 作者：EdgeTTS Team
 * 版本：1.0.0
 * ============================================================================
 */

#ifndef EDGETTS_CLIENT_H
#define EDGETTS_CLIENT_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// ==================== 数据结构 ====================

/**
 * 客户端配置结构体
 * 包含服务器连接信息和超时设置
 */
typedef struct {
    char host[64];          // 服务器地址，例如："192.168.1.100"
    int port;               // 服务器端口，默认：3003
    int timeout_ms;         // HTTP请求超时时间(毫秒)，默认：10000
    int retry_count;        // 请求失败重试次数，默认：3
} edgetts_config_t;

/**
 * EdgeTTS客户端结构体
 * 不要直接访问内部字段，使用提供的API函数
 */
typedef struct {
    edgetts_config_t config;    // 配置信息
    char last_error[256];       // 最后一次错误信息
} edgetts_client_t;

// ==================== 初始化和配置 ====================

/**
 * 创建EdgeTTS客户端
 * 
 * 这是使用SDK的第一步，创建一个客户端实例
 * 
 * @param host 服务器IP地址或域名，例如："192.168.1.100"
 * @param port 服务器端口号，通常是 3003
 * @return 返回客户端指针，失败返回NULL
 * 
 * 示例：
 *   edgetts_client_t* client = edgetts_client_create("192.168.1.100", 3003);
 *   if (client == NULL) {
 *       printf("创建客户端失败\n");
 *   }
 * 
 * 注意：使用完毕后必须调用 edgetts_client_destroy() 释放资源
 */
edgetts_client_t* edgetts_client_create(const char* host, int port);

/**
 * 销毁客户端，释放资源
 * 
 * 使用完客户端后必须调用此函数释放内存
 * 
 * @param client 客户端指针
 * 
 * 示例：
 *   edgetts_client_destroy(client);
 */
void edgetts_client_destroy(edgetts_client_t* client);

/**
 * 设置HTTP请求超时时间
 * 
 * 默认超时时间是10秒，如果网络较慢可以增加超时时间
 * 
 * @param client 客户端指针
 * @param timeout_ms 超时时间(毫秒)，例如：15000 表示15秒
 * 
 * 示例：
 *   edgetts_set_timeout(client, 15000);  // 设置15秒超时
 */
void edgetts_set_timeout(edgetts_client_t* client, int timeout_ms);

/**
 * 设置请求失败后的重试次数
 * 
 * 默认重试3次，网络不稳定时可以增加重试次数
 * 
 * @param client 客户端指针
 * @param retry_count 重试次数，例如：5 表示失败后重试5次
 * 
 * 示例：
 *   edgetts_set_retry(client, 5);  // 失败后重试5次
 */
void edgetts_set_retry(edgetts_client_t* client, int retry_count);

/**
 * 获取最后一次操作的错误信息
 * 
 * 当API调用返回false时，可以通过此函数获取详细错误信息
 * 
 * @param client 客户端指针
 * @return 返回错误信息字符串，不需要释放
 * 
 * 示例：
 *   if (!edgetts_ping(client)) {
 *       printf("错误: %s\n", edgetts_get_error(client));
 *   }
 */
const char* edgetts_get_error(edgetts_client_t* client);

// ==================== 基础接口 ====================

/**
 * 测试与服务器的连接
 * 
 * 这是最简单的测试接口，用于检查服务器是否可访问
 * 建议在使用其他功能前先调用此函数测试连接
 * 
 * @param client 客户端指针
 * @return true=连接正常, false=连接失败
 * 
 * 示例：
 *   if (edgetts_ping(client)) {
 *       printf("服务器连接正常\n");
 *   } else {
 *       printf("服务器连接失败: %s\n", edgetts_get_error(client));
 *   }
 */
bool edgetts_ping(edgetts_client_t* client);

/**
 * 获取服务器状态信息
 * 
 * 返回服务器的运行状态，包括可用的ASR引擎、AI服务等信息
 * 返回的是JSON格式字符串
 * 
 * @param client 客户端指针
 * @param status_json 输出参数，返回JSON字符串指针，使用完后必须用free()释放
 * @return true=成功, false=失败
 * 
 * 示例：
 *   char* status = NULL;
 *   if (edgetts_get_status(client, &status)) {
 *       printf("服务器状态: %s\n", status);
 *       free(status);  // 必须释放
 *   }
 */
bool edgetts_get_status(edgetts_client_t* client, char** status_json);

// ==================== AI问答 ====================

/**
 * AI问答接口
 * 
 * 向AI提问并获取回答，支持多轮对话（通过session_id）
 * 
 * @param client 客户端指针
 * @param question 问题文本，例如："今天天气怎么样？"
 * @param answer 输出参数，返回AI回答的字符串指针，使用完后必须用free()释放
 * @param session_id 会话ID，用于保持多轮对话上下文。传NULL表示单次问答
 * @return true=成功, false=失败
 * 
 * 单次问答示例：
 *   char* answer = NULL;
 *   if (edgetts_ask(client, "你好", &answer, NULL)) {
 *       printf("AI回答: %s\n", answer);
 *       free(answer);  // 必须释放
 *   }
 * 
 * 多轮对话示例：
 *   char* answer1 = NULL;
 *   char* answer2 = NULL;
 *   edgetts_ask(client, "我叫小明", &answer1, "session123");
 *   edgetts_ask(client, "我叫什么名字？", &answer2, "session123");  // AI会记住你叫小明
 *   free(answer1);
 *   free(answer2);
 */
bool edgetts_ask(edgetts_client_t* client, const char* question, 
                 char** answer, const char* session_id);

/**
 * 流式问答回调函数类型
 * 
 * 当使用流式问答时，AI的回答会分段实时返回，每收到一段就调用一次此回调
 * 
 * @param chunk 收到的文字片段
 * @param user_data 用户自定义数据，由 edgetts_ask_stream() 传入
 */
typedef void (*edgetts_stream_callback_t)(const char* chunk, void* user_data);

/**
 * 流式AI问答接口
 * 
 * 与普通问答不同，流式问答会实时返回AI的回答，不用等待全部生成完毕
 * 适合需要实时显示AI回答的场景
 * 
 * @param client 客户端指针
 * @param question 问题文本
 * @param callback 回调函数，每收到一段回答就调用一次
 * @param user_data 用户自定义数据，会传递给回调函数
 * @param session_id 会话ID，传NULL表示单次问答
 * @return true=成功, false=失败
 * 
 * 示例：
 *   void on_chunk(const char* chunk, void* user_data) {
 *       printf("%s", chunk);  // 实时打印每一段
 *   }
 *   
 *   edgetts_ask_stream(client, "讲个故事", on_chunk, NULL, NULL);
 */
bool edgetts_ask_stream(edgetts_client_t* client, const char* question,
                       edgetts_stream_callback_t callback, void* user_data,
                       const char* session_id);

// ==================== 语音识别 (STT: Speech To Text) ====================

/**
 * 语音识别接口 - 将音频转换为文字
 * 
 * 支持多种音频格式和识别引擎
 * 
 * @param client 客户端指针
 * @param audio_data 音频数据的字节数组
 * @param audio_size 音频数据的大小(字节数)
 * @param engine 识别引擎，可选值：
 *               - "tencent": 腾讯云ASR，准确率高，需要服务端配置密钥
 *               - "vosk": 本地离线识别，免费但准确率较低
 * @param format 音频格式，可选值：
 *               - "wav": WAV格式(推荐)
 *               - "pcm": 原始PCM格式
 *               - "mp3": MP3格式
 * @param text 输出参数，返回识别出的文字，使用完后必须用free()释放
 * @return true=成功, false=失败
 * 
 * 示例：
 *   uint8_t* audio = ...; // 你录制的音频数据
 *   size_t size = ...;    // 音频大小
 *   char* text = NULL;
 *   
 *   if (edgetts_stt(client, audio, size, "tencent", "wav", &text)) {
 *       printf("识别结果: %s\n", text);
 *       free(text);  // 必须释放
 *   }
 */
bool edgetts_stt(edgetts_client_t* client, const uint8_t* audio_data, 
                size_t audio_size, const char* engine, const char* format,
                char** text);

// ==================== 语音合成 (TTS: Text To Speech) ====================

/**
 * 语音合成接口 - 将文字转换为语音
 * 
 * 支持多种语音和音频格式
 * 
 * @param client 客户端指针
 * @param text 要转换的文字，例如："你好，欢迎使用语音助手"
 * @param voice 语音类型，可选值：
 *              - "xiaoxiao": 晓晓(女声，温柔)
 *              - "yunxi": 云希(男声，沉稳)
 *              - "xiaoyi": 晓伊(女声，甜美)
 *              - "yunjian": 云健(男声，活力)
 * @param format 输出音频格式，可选值：
 *               - "wav": WAV格式(推荐，兼容性好)
 *               - "mp3": MP3格式(体积小)
 * @param audio_data 输出参数，返回音频数据的字节数组，使用完后必须用free()释放
 * @param audio_size 输出参数，返回音频数据的大小(字节数)
 * @return true=成功, false=失败
 * 
 * 示例：
 *   uint8_t* audio = NULL;
 *   size_t size = 0;
 *   
 *   if (edgetts_tts(client, "你好世界", "xiaoxiao", "wav", &audio, &size)) {
 *       printf("音频大小: %zu bytes\n", size);
 *       // 播放或保存音频...
 *       play_audio(audio, size);
 *       free(audio);  // 必须释放
 *   }
 */
bool edgetts_tts(edgetts_client_t* client, const char* text, 
                const char* voice, const char* format,
                uint8_t** audio_data, size_t* audio_size);

// ==================== 语音对话 (一站式接口) ====================

/**
 * 语音对话接口 - 语音输入，文字输出
 * 
 * 一次调用完成：语音识别 → AI问答
 * 适合需要获取文字结果的场景
 * 
 * @param client 客户端指针
 * @param audio_data 输入的音频数据
 * @param audio_size 音频数据大小
 * @param engine ASR识别引擎，"tencent"或"vosk"
 * @param format 音频格式，"wav"、"pcm"或"mp3"
 * @param question 输出参数，返回识别出的问题文字，使用完后必须用free()释放
 * @param answer 输出参数，返回AI的回答文字，使用完后必须用free()释放
 * @param session_id 会话ID，传NULL表示单次对话
 * @return true=成功, false=失败
 * 
 * 示例：
 *   uint8_t* audio = ...; // 录制的音频
 *   char* question = NULL;
 *   char* answer = NULL;
 *   
 *   if (edgetts_voice_chat_text(client, audio, size, "tencent", "wav", 
 *                                &question, &answer, NULL)) {
 *       printf("你说: %s\n", question);
 *       printf("AI说: %s\n", answer);
 *       free(question);
 *       free(answer);
 *   }
 */
bool edgetts_voice_chat_text(edgetts_client_t* client,
                            const uint8_t* audio_data, size_t audio_size,
                            const char* engine, const char* format,
                            char** question, char** answer,
                            const char* session_id);

/**
 * 语音对话接口 - 语音输入，语音输出（最常用）
 * 
 * 一次调用完成：语音识别 → AI问答 → 语音合成
 * 这是最简单的语音对话方式，输入语音，直接得到语音回复
 * 
 * @param client 客户端指针
 * @param input_audio 输入的音频数据（你说的话）
 * @param input_size 输入音频大小
 * @param engine ASR识别引擎，"tencent"(推荐)或"vosk"
 * @param voice TTS语音类型，"xiaoxiao"、"yunxi"、"xiaoyi"或"yunjian"
 * @param format 音频格式，"wav"(推荐)或"mp3"
 * @param output_audio 输出参数，返回AI回复的音频数据，使用完后必须用free()释放
 * @param output_size 输出参数，返回输出音频大小
 * @param session_id 会话ID，传NULL表示单次对话
 * @return true=成功, false=失败
 * 
 * 示例（最简单的语音对话）：
 *   // 1. 录音
 *   uint8_t* my_voice = record_audio();  // 你的录音函数
 *   size_t my_voice_size = get_audio_size();
 *   
 *   // 2. 发送并获取回复
 *   uint8_t* ai_voice = NULL;
 *   size_t ai_voice_size = 0;
 *   
 *   if (edgetts_voice_chat_audio(client, my_voice, my_voice_size,
 *                                 "tencent", "xiaoxiao", "wav",
 *                                 &ai_voice, &ai_voice_size, NULL)) {
 *       // 3. 播放AI的语音回复
 *       play_audio(ai_voice, ai_voice_size);
 *       free(ai_voice);  // 必须释放
 *   }
 * 
 * 多轮对话示例：
 *   char* session = "user123";
 *   // 第一轮
 *   edgetts_voice_chat_audio(client, audio1, size1, "tencent", "xiaoxiao", "wav",
 *                            &reply1, &reply1_size, session);
 *   // 第二轮（AI会记住第一轮的内容）
 *   edgetts_voice_chat_audio(client, audio2, size2, "tencent", "xiaoxiao", "wav",
 *                            &reply2, &reply2_size, session);
 */
bool edgetts_voice_chat_audio(edgetts_client_t* client,
                             const uint8_t* input_audio, size_t input_size,
                             const char* engine, const char* voice, const char* format,
                             uint8_t** output_audio, size_t* output_size,
                             const char* session_id);

#ifdef __cplusplus
}
#endif

#endif // EDGETTS_CLIENT_H
