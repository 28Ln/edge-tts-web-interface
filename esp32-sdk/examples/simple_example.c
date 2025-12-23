/**
 * ============================================================================
 * EdgeTTS SDK 使用示例
 * ============================================================================
 * 
 * 这个示例展示了如何使用EdgeTTS SDK的基本功能
 * 包括：连接测试、AI问答、语音合成
 * 
 * 使用前请确保：
 * 1. EdgeTTS服务器已启动
 * 2. 修改下面的服务器地址和端口
 * 3. ESP32已连接WiFi
 * 
 * ============================================================================
 */

#include "edgetts_client.h"
#include <stdio.h>
#include <stdlib.h>

int main() {
    printf("========================================\n");
    printf("  EdgeTTS SDK 使用示例\n");
    printf("========================================\n\n");
    
    // ==================== 步骤1：创建客户端 ====================
    // 参数：服务器IP地址，端口号
    // 注意：请修改为你的服务器地址
    edgetts_client_t* client = edgetts_client_create("192.168.1.100", 3003);
    if (!client) {
        printf("❌ 创建客户端失败\n");
        return -1;
    }
    printf("✅ 客户端创建成功\n\n");
    
    // 可选：设置超时和重试
    edgetts_set_timeout(client, 15000);  // 15秒超时
    edgetts_set_retry(client, 3);        // 失败重试3次
    
    // ==================== 步骤2：测试连接 ====================
    printf("测试服务器连接...\n");
    if (edgetts_ping(client)) {
        printf("✅ 服务器连接正常\n\n");
    } else {
        printf("❌ 服务器连接失败: %s\n", edgetts_get_error(client));
        printf("请检查：\n");
        printf("  1. 服务器是否启动\n");
        printf("  2. IP地址和端口是否正确\n");
        printf("  3. 网络是否连通\n\n");
        edgetts_client_destroy(client);
        return -1;
    }
    
    // ==================== 步骤3：AI问答 ====================
    printf("测试AI问答...\n");
    char* answer = NULL;
    
    // 调用AI问答接口
    // 参数：客户端、问题、答案指针、会话ID(NULL表示单次问答)
    if (edgetts_ask(client, "你好，请介绍一下自己", &answer, NULL)) {
        printf("✅ AI回答: %s\n\n", answer);
        free(answer);  // 重要：使用完必须释放内存
    } else {
        printf("❌ AI问答失败: %s\n\n", edgetts_get_error(client));
    }
    
    // ==================== 步骤4：语音合成 ====================
    printf("测试语音合成...\n");
    uint8_t* audio = NULL;
    size_t audio_size = 0;
    
    // 调用语音合成接口
    // 参数：客户端、文字、语音类型、格式、音频数据指针、音频大小指针
    // 语音类型：xiaoxiao(女声)、yunxi(男声)、xiaoyi(女声)、yunjian(男声)
    if (edgetts_tts(client, "你好世界，这是语音合成测试", "xiaoxiao", "wav", 
                    &audio, &audio_size)) {
        printf("✅ 语音合成成功\n");
        printf("   音频大小: %zu bytes\n", audio_size);
        printf("   音频格式: WAV\n");
        printf("   语音类型: 晓晓(女声)\n\n");
        
        // 这里可以：
        // 1. 播放音频：play_audio(audio, audio_size);
        // 2. 保存到文件：save_to_file("output.wav", audio, audio_size);
        // 3. 通过I2S输出：i2s_write(audio, audio_size);
        
        free(audio);  // 重要：使用完必须释放内存
    } else {
        printf("❌ 语音合成失败: %s\n\n", edgetts_get_error(client));
    }
    
    // ==================== 步骤5：清理资源 ====================
    edgetts_client_destroy(client);
    printf("✅ 客户端已销毁\n");
    
    printf("========================================\n");
    printf("  示例运行完成\n");
    printf("========================================\n");
    
    return 0;
}

/**
 * 更多示例：
 * 
 * 1. 多轮对话：
 *    char* session = "user123";
 *    edgetts_ask(client, "我叫小明", &answer1, session);
 *    edgetts_ask(client, "我叫什么名字？", &answer2, session);  // AI会记住
 * 
 * 2. 语音识别：
 *    uint8_t* audio = ...; // 你录制的音频
 *    char* text = NULL;
 *    edgetts_stt(client, audio, size, "tencent", "wav", &text);
 *    printf("识别结果: %s\n", text);
 *    free(text);
 * 
 * 3. 语音对话（最简单）：
 *    uint8_t* my_voice = record_audio();  // 录音
 *    uint8_t* ai_voice = NULL;
 *    size_t ai_size = 0;
 *    edgetts_voice_chat_audio(client, my_voice, my_size,
 *                             "tencent", "xiaoxiao", "wav",
 *                             &ai_voice, &ai_size, NULL);
 *    play_audio(ai_voice, ai_size);  // 播放AI回复
 *    free(ai_voice);
 */
