/**
 * ESP32 语音助手示例代码
 * 
 * 功能：录音 -> 上传服务器 -> 获取AI语音回复 -> 播放
 * 
 * 硬件需求：
 * - ESP32 开发板
 * - I2S 麦克风 (如 INMP441)
 * - I2S DAC/扬声器 (如 MAX98357A)
 * 
 * 服务器接口：
 * - /mcu/ping        - 测试连接
 * - /mcu/stt         - 语音转文字
 * - /mcu/tts         - 文字转语音
 * - /mcu/ask         - AI 文字问答
 * - /mcu/voice_chat  - 一站式语音对话
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <driver/i2s.h>

// ========== 配置区域 ==========
const char* WIFI_SSID = "your_wifi_ssid";
const char* WIFI_PASSWORD = "your_wifi_password";
const char* SERVER_URL = "http://192.168.1.100:2024";  // 服务器地址

// I2S 麦克风引脚配置 (INMP441)
#define I2S_MIC_WS   15
#define I2S_MIC_SD   13
#define I2S_MIC_SCK  2

// I2S 扬声器引脚配置 (MAX98357A)
#define I2S_SPK_BCLK  26
#define I2S_SPK_LRC   25
#define I2S_SPK_DOUT  22

// 录音配置
#define SAMPLE_RATE     16000
#define RECORD_SECONDS  5
#define BUFFER_SIZE     (SAMPLE_RATE * RECORD_SECONDS * 2)  // 16bit = 2 bytes

// 按钮引脚
#define BUTTON_PIN      0  // BOOT 按钮

// ========== 全局变量 ==========
uint8_t* audioBuffer = nullptr;
size_t audioBufferSize = 0;

// ========== I2S 初始化 ==========
void initI2SMic() {
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = 1024,
        .use_apll = false
    };
    
    i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_MIC_SCK,
        .ws_io_num = I2S_MIC_WS,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = I2S_MIC_SD
    };
    
    i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
    i2s_set_pin(I2S_NUM_0, &pin_config);
}

void initI2SSpk() {
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
        .sample_rate = SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = 1024,
        .use_apll = false
    };
    
    i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_SPK_BCLK,
        .ws_io_num = I2S_SPK_LRC,
        .data_out_num = I2S_SPK_DOUT,
        .data_in_num = I2S_PIN_NO_CHANGE
    };
    
    i2s_driver_install(I2S_NUM_1, &i2s_config, 0, NULL);
    i2s_set_pin(I2S_NUM_1, &pin_config);
}

// ========== 录音功能 ==========
bool recordAudio() {
    Serial.println("开始录音...");
    
    if (audioBuffer) free(audioBuffer);
    audioBuffer = (uint8_t*)malloc(BUFFER_SIZE);
    if (!audioBuffer) {
        Serial.println("内存分配失败!");
        return false;
    }
    
    size_t bytesRead = 0;
    size_t totalBytes = 0;
    
    while (totalBytes < BUFFER_SIZE) {
        i2s_read(I2S_NUM_0, audioBuffer + totalBytes, 
                 min((size_t)1024, BUFFER_SIZE - totalBytes), 
                 &bytesRead, portMAX_DELAY);
        totalBytes += bytesRead;
    }
    
    audioBufferSize = totalBytes;
    Serial.printf("录音完成，大小: %d bytes\n", audioBufferSize);
    return true;
}

// ========== 网络请求 ==========
bool testConnection() {
    HTTPClient http;
    String url = String(SERVER_URL) + "/mcu/ping";
    
    http.begin(url);
    int httpCode = http.GET();
    
    if (httpCode == 200) {
        String response = http.getString();
        Serial.println("服务器连接成功: " + response);
        http.end();
        return true;
    }
    
    Serial.printf("服务器连接失败: %d\n", httpCode);
    http.end();
    return false;
}

String speechToText() {
    HTTPClient http;
    String url = String(SERVER_URL) + "/mcu/stt?format=pcm&rate=16000";
    
    http.begin(url);
    http.addHeader("Content-Type", "application/octet-stream");
    
    int httpCode = http.POST(audioBuffer, audioBufferSize);
    
    if (httpCode == 200) {
        String text = http.getString();
        Serial.println("识别结果: " + text);
        http.end();
        return text;
    }
    
    Serial.printf("STT 请求失败: %d\n", httpCode);
    http.end();
    return "";
}

String askAI(String question) {
    HTTPClient http;
    String url = String(SERVER_URL) + "/mcu/ask";
    
    http.begin(url);
    http.addHeader("Content-Type", "text/plain; charset=utf-8");
    
    int httpCode = http.POST(question);
    
    if (httpCode == 200) {
        String answer = http.getString();
        Serial.println("AI 回答: " + answer);
        http.end();
        return answer;
    }
    
    Serial.printf("AI 请求失败: %d\n", httpCode);
    http.end();
    return "";
}

bool voiceChat() {
    // 一站式语音对话：上传录音，返回语音回复
    HTTPClient http;
    String url = String(SERVER_URL) + "/mcu/voice_chat?format=pcm&rate=16000&out=audio";
    
    http.begin(url);
    http.addHeader("Content-Type", "application/octet-stream");
    
    int httpCode = http.POST(audioBuffer, audioBufferSize);
    
    if (httpCode == 200) {
        // 获取返回的音频数据
        int len = http.getSize();
        Serial.printf("收到语音回复: %d bytes\n", len);
        
        // 跳过 WAV 头 (44 bytes)
        WiFiClient* stream = http.getStreamPtr();
        uint8_t wavHeader[44];
        stream->readBytes(wavHeader, 44);
        
        // 播放音频
        uint8_t buffer[1024];
        size_t bytesWritten;
        while (stream->available()) {
            int bytesRead = stream->readBytes(buffer, sizeof(buffer));
            i2s_write(I2S_NUM_1, buffer, bytesRead, &bytesWritten, portMAX_DELAY);
        }
        
        http.end();
        return true;
    }
    
    Serial.printf("语音对话请求失败: %d\n", httpCode);
    http.end();
    return false;
}

// ========== 主程序 ==========
void setup() {
    Serial.begin(115200);
    Serial.println("\n=== ESP32 语音助手 ===");
    
    // 初始化按钮
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    
    // 连接 WiFi
    Serial.print("连接 WiFi...");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi 已连接: " + WiFi.localIP().toString());
    
    // 初始化 I2S
    initI2SMic();
    initI2SSpk();
    
    // 测试服务器连接
    if (!testConnection()) {
        Serial.println("警告: 无法连接到服务器!");
    }
    
    Serial.println("按下 BOOT 按钮开始语音对话...");
}

void loop() {
    // 检测按钮按下
    if (digitalRead(BUTTON_PIN) == LOW) {
        delay(50);  // 消抖
        if (digitalRead(BUTTON_PIN) == LOW) {
            Serial.println("\n--- 开始语音对话 ---");
            
            // 录音
            if (recordAudio()) {
                // 方式1: 一站式语音对话 (推荐)
                voiceChat();
                
                // 方式2: 分步调用
                // String text = speechToText();
                // if (text.length() > 0) {
                //     String answer = askAI(text);
                //     // 然后调用 TTS 获取语音...
                // }
            }
            
            // 释放内存
            if (audioBuffer) {
                free(audioBuffer);
                audioBuffer = nullptr;
            }
            
            Serial.println("--- 对话结束 ---\n");
            
            // 等待按钮释放
            while (digitalRead(BUTTON_PIN) == LOW) {
                delay(10);
            }
        }
    }
    
    delay(10);
}
