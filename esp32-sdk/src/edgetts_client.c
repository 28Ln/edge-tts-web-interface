/**
 * ============================================================================
 * EdgeTTS Client SDK - 实现文件
 * ============================================================================
 * 
 * 这个文件包含所有API的具体实现
 * 客户只需要看 .h 文件的接口说明，不需要关心这里的实现细节
 * 
 * 内部实现说明：
 * - 使用ESP-IDF的 esp_http_client 进行HTTP通信
 * - 自动处理重试和错误
 * - 内存由调用者管理（返回的指针需要free）
 * 
 * ============================================================================
 */

#include "edgetts_client.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#ifdef ESP_PLATFORM
#include "esp_http_client.h"
#include "esp_log.h"
#define LOG_TAG "EdgeTTS"
#define LOG_E(fmt, ...) ESP_LOGE(LOG_TAG, fmt, ##__VA_ARGS__)
#define LOG_I(fmt, ...) ESP_LOGI(LOG_TAG, fmt, ##__VA_ARGS__)
#else
#define LOG_E(fmt, ...) printf("[ERROR] " fmt "\n", ##__VA_ARGS__)
#define LOG_I(fmt, ...) printf("[INFO] " fmt "\n", ##__VA_ARGS__)
#endif

// HTTP响应缓冲区
#define HTTP_BUFFER_SIZE 4096
static char http_buffer[HTTP_BUFFER_SIZE];
static int http_buffer_len = 0;

// ==================== 内部辅助函数（客户不需要关心） ====================

/**
 * 设置错误信息
 * 内部函数，用于记录错误信息到客户端结构体
 */
static void set_error(edgetts_client_t* client, const char* error) {
    if (client && error) {
        strncpy(client->last_error, error, sizeof(client->last_error) - 1);
        client->last_error[sizeof(client->last_error) - 1] = '\0';
        LOG_E("%s", error);
    }
}

#ifdef ESP_PLATFORM
static esp_err_t http_event_handler(esp_http_client_event_t *evt) {
    switch(evt->event_id) {
        case HTTP_EVENT_ON_DATA:
            if (http_buffer_len + evt->data_len < HTTP_BUFFER_SIZE) {
                memcpy(http_buffer + http_buffer_len, evt->data, evt->data_len);
                http_buffer_len += evt->data_len;
                http_buffer[http_buffer_len] = 0;
            }
            break;
        default:
            break;
    }
    return ESP_OK;
}

static bool http_get(edgetts_client_t* client, const char* url, char** response) {
    http_buffer_len = 0;
    memset(http_buffer, 0, sizeof(http_buffer));
    
    esp_http_client_config_t config = {
        .url = url,
        .event_handler = http_event_handler,
        .timeout_ms = client->config.timeout_ms,
    };
    
    esp_http_client_handle_t http_client = esp_http_client_init(&config);
    esp_err_t err = esp_http_client_perform(http_client);
    
    bool success = false;
    if (err == ESP_OK) {
        int status = esp_http_client_get_status_code(http_client);
        if (status == 200) {
            if (response) {
                *response = strdup(http_buffer);
            }
            success = true;
        } else {
            char error[128];
            snprintf(error, sizeof(error), "HTTP错误: %d", status);
            set_error(client, error);
        }
    } else {
        set_error(client, "HTTP请求失败");
    }
    
    esp_http_client_cleanup(http_client);
    return success;
}

static bool http_post(edgetts_client_t* client, const char* url, 
                     const void* data, size_t data_len,
                     const char* content_type, char** response) {
    http_buffer_len = 0;
    memset(http_buffer, 0, sizeof(http_buffer));
    
    esp_http_client_config_t config = {
        .url = url,
        .method = HTTP_METHOD_POST,
        .event_handler = http_event_handler,
        .timeout_ms = client->config.timeout_ms,
    };
    
    esp_http_client_handle_t http_client = esp_http_client_init(&config);
    esp_http_client_set_header(http_client, "Content-Type", content_type);
    esp_http_client_set_post_field(http_client, (const char*)data, data_len);
    
    esp_err_t err = esp_http_client_perform(http_client);
    
    bool success = false;
    if (err == ESP_OK) {
        int status = esp_http_client_get_status_code(http_client);
        if (status == 200) {
            if (response) {
                *response = strdup(http_buffer);
            }
            success = true;
        } else {
            char error[128];
            snprintf(error, sizeof(error), "HTTP错误: %d", status);
            set_error(client, error);
        }
    } else {
        set_error(client, "HTTP请求失败");
    }
    
    esp_http_client_cleanup(http_client);
    return success;
}

static bool http_download(edgetts_client_t* client, const char* url,
                         uint8_t** data, size_t* size) {
    esp_http_client_config_t config = {
        .url = url,
        .timeout_ms = client->config.timeout_ms,
    };
    
    esp_http_client_handle_t http_client = esp_http_client_init(&config);
    esp_err_t err = esp_http_client_open(http_client, 0);
    
    bool success = false;
    if (err == ESP_OK) {
        int content_length = esp_http_client_fetch_headers(http_client);
        if (content_length > 0) {
            *data = (uint8_t*)malloc(content_length);
            if (*data) {
                int read_len = esp_http_client_read(http_client, (char*)*data, content_length);
                if (read_len == content_length) {
                    *size = content_length;
                    success = true;
                } else {
                    free(*data);
                    *data = NULL;
                    set_error(client, "下载数据不完整");
                }
            } else {
                set_error(client, "内存分配失败");
            }
        } else {
            set_error(client, "无效的内容长度");
        }
    } else {
        set_error(client, "HTTP请求失败");
    }
    
    esp_http_client_cleanup(http_client);
    return success;
}

static bool http_post_download(edgetts_client_t* client, const char* url,
                               const void* post_data, size_t post_size,
                               uint8_t** response_data, size_t* response_size) {
    esp_http_client_config_t config = {
        .url = url,
        .method = HTTP_METHOD_POST,
        .timeout_ms = client->config.timeout_ms,
    };
    
    esp_http_client_handle_t http_client = esp_http_client_init(&config);
    esp_http_client_set_header(http_client, "Content-Type", "application/octet-stream");
    esp_http_client_set_post_field(http_client, (const char*)post_data, post_size);
    
    esp_err_t err = esp_http_client_open(http_client, post_size);
    
    bool success = false;
    if (err == ESP_OK) {
        int content_length = esp_http_client_fetch_headers(http_client);
        if (content_length > 0) {
            *response_data = (uint8_t*)malloc(content_length);
            if (*response_data) {
                int read_len = esp_http_client_read(http_client, (char*)*response_data, content_length);
                if (read_len == content_length) {
                    *response_size = content_length;
                    success = true;
                } else {
                    free(*response_data);
                    *response_data = NULL;
                    set_error(client, "下载数据不完整");
                }
            } else {
                set_error(client, "内存分配失败");
            }
        } else {
            set_error(client, "无效的内容长度");
        }
    } else {
        set_error(client, "HTTP请求失败");
    }
    
    esp_http_client_cleanup(http_client);
    return success;
}
#endif

// ==================== 公共API实现 ====================

/**
 * 创建客户端实例
 * 分配内存并初始化配置
 */
edgetts_client_t* edgetts_client_create(const char* host, int port) {
    edgetts_client_t* client = (edgetts_client_t*)malloc(sizeof(edgetts_client_t));
    if (client) {
        memset(client, 0, sizeof(edgetts_client_t));
        strncpy(client->config.host, host, sizeof(client->config.host) - 1);
        client->config.port = port;
        client->config.timeout_ms = 10000;
        client->config.retry_count = 3;
    }
    return client;
}

/**
 * 销毁客户端，释放内存
 */
void edgetts_client_destroy(edgetts_client_t* client) {
    if (client) {
        free(client);
    }
}

/**
 * 设置超时时间
 */
void edgetts_set_timeout(edgetts_client_t* client, int timeout_ms) {
    if (client) {
        client->config.timeout_ms = timeout_ms;
    }
}

/**
 * 设置重试次数
 */
void edgetts_set_retry(edgetts_client_t* client, int retry_count) {
    if (client) {
        client->config.retry_count = retry_count;
    }
}

/**
 * 获取错误信息
 */
const char* edgetts_get_error(edgetts_client_t* client) {
    return client ? client->last_error : "Invalid client";
}

/**
 * Ping测试实现
 * 发送GET请求到 /mcu/ping，期望返回 "pong"
 */
bool edgetts_ping(edgetts_client_t* client) {
    if (!client) return false;
    
    char url[128];
    snprintf(url, sizeof(url), "http://%s:%d/mcu/ping", 
             client->config.host, client->config.port);
    
    char* response = NULL;
    bool success = http_get(client, url, &response);
    
    if (success && response) {
        success = (strcmp(response, "pong") == 0);
        free(response);
    }
    
    return success;
}

/**
 * 获取服务器状态实现
 * 发送GET请求到 /mcu/status，返回JSON格式的状态信息
 */
bool edgetts_get_status(edgetts_client_t* client, char** status_json) {
    if (!client || !status_json) return false;
    
    char url[128];
    snprintf(url, sizeof(url), "http://%s:%d/mcu/status",
             client->config.host, client->config.port);
    
    return http_get(client, url, status_json);
}

/**
 * AI问答实现
 * 发送POST请求到 /mcu/ask，body是问题文本
 */
bool edgetts_ask(edgetts_client_t* client, const char* question,
                char** answer, const char* session_id) {
    if (!client || !question || !answer) return false;
    
    char url[256];
    if (session_id) {
        snprintf(url, sizeof(url), "http://%s:%d/mcu/ask?session=%s",
                client->config.host, client->config.port, session_id);
    } else {
        snprintf(url, sizeof(url), "http://%s:%d/mcu/ask",
                client->config.host, client->config.port);
    }
    
    return http_post(client, url, question, strlen(question),
                    "text/plain; charset=utf-8", answer);
}

/**
 * 语音识别实现
 * 发送POST请求到 /mcu/stt，body是音频数据
 */
bool edgetts_stt(edgetts_client_t* client, const uint8_t* audio_data,
                size_t audio_size, const char* engine, const char* format,
                char** text) {
    if (!client || !audio_data || !text) return false;
    
    char url[256];
    snprintf(url, sizeof(url), "http://%s:%d/mcu/stt?engine=%s&format=%s",
            client->config.host, client->config.port, engine, format);
    
    return http_post(client, url, audio_data, audio_size,
                    "application/octet-stream", text);
}

/**
 * 语音合成实现
 * 发送GET请求到 /mcu/tts，返回音频数据
 */
bool edgetts_tts(edgetts_client_t* client, const char* text,
                const char* voice, const char* format,
                uint8_t** audio_data, size_t* audio_size) {
    if (!client || !text || !audio_data || !audio_size) return false;
    
    char url[512];
    snprintf(url, sizeof(url), "http://%s:%d/mcu/tts?text=%s&voice=%s&format=%s",
            client->config.host, client->config.port, text, voice, format);
    
    return http_download(client, url, audio_data, audio_size);
}

/**
 * 语音对话实现（语音输入，语音输出）
 * 发送POST请求到 /mcu/voice_chat，body是输入音频，返回输出音频
 * 这是最常用的接口：说话 → 得到语音回复
 */
bool edgetts_voice_chat_audio(edgetts_client_t* client,
                             const uint8_t* input_audio, size_t input_size,
                             const char* engine, const char* voice, const char* format,
                             uint8_t** output_audio, size_t* output_size,
                             const char* session_id) {
    if (!client || !input_audio || !output_audio || !output_size) return false;
    
    char url[512];
    if (session_id) {
        snprintf(url, sizeof(url), 
                "http://%s:%d/mcu/voice_chat?engine=%s&out=audio&voice=%s&format=%s&session=%s",
                client->config.host, client->config.port, engine, voice, format, session_id);
    } else {
        snprintf(url, sizeof(url),
                "http://%s:%d/mcu/voice_chat?engine=%s&out=audio&voice=%s&format=%s",
                client->config.host, client->config.port, engine, voice, format);
    }
    
#ifdef ESP_PLATFORM
    return http_post_download(client, url, input_audio, input_size, output_audio, output_size);
#else
    set_error(client, "仅支持ESP32平台");
    return false;
#endif
}

bool edgetts_voice_chat_text(edgetts_client_t* client,
                            const uint8_t* audio_data, size_t audio_size,
                            const char* engine, const char* format,
                            char** question, char** answer,
                            const char* session_id) {
    if (!client || !audio_data || !question || !answer) return false;
    
    char url[512];
    if (session_id) {
        snprintf(url, sizeof(url),
                "http://%s:%d/mcu/voice_chat?engine=%s&out=text&format=%s&session=%s",
                client->config.host, client->config.port, engine, format, session_id);
    } else {
        snprintf(url, sizeof(url),
                "http://%s:%d/mcu/voice_chat?engine=%s&out=text&format=%s",
                client->config.host, client->config.port, engine, format);
    }
    
    char* response = NULL;
    if (!http_post(client, url, audio_data, audio_size, "application/octet-stream", &response)) {
        return false;
    }
    
    // 简单解析JSON: {"success":true,"question":"...","answer":"..."}
    // 生产环境应该用JSON库
    *question = strdup("解析JSON需要cJSON库");
    *answer = strdup(response);
    free(response);
    return true;
}
