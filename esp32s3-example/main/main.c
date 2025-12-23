/**
 * ESP32-S3 EdgeTTS Client Example
 * 
 * 演示如何调用 EdgeTTS Web Interface API
 * 支持：语音识别、AI问答、语音合成、语音对话
 */

#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_http_client.h"
#include "cJSON.h"

static const char *TAG = "EdgeTTS_Client";

// WiFi事件组
static EventGroupHandle_t s_wifi_event_group;
#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT      BIT1

// 配置
#define WIFI_SSID      CONFIG_WIFI_SSID
#define WIFI_PASSWORD  CONFIG_WIFI_PASSWORD
#define SERVER_HOST    CONFIG_EDGETTS_SERVER_HOST
#define SERVER_PORT    CONFIG_EDGETTS_SERVER_PORT

// API端点
#define API_PING        "http://" SERVER_HOST ":%d/mcu/ping"
#define API_STATUS      "http://" SERVER_HOST ":%d/mcu/status"
#define API_ASK         "http://" SERVER_HOST ":%d/mcu/ask"
#define API_TTS         "http://" SERVER_HOST ":%d/mcu/tts?text=%s&voice=%s"
#define API_STT         "http://" SERVER_HOST ":%d/mcu/stt?engine=%s&format=%s"
#define API_VOICE_CHAT  "http://" SERVER_HOST ":%d/mcu/voice_chat?engine=%s&out=%s"

// HTTP响应缓冲区
#define MAX_HTTP_OUTPUT_BUFFER 4096
static char http_response_buffer[MAX_HTTP_OUTPUT_BUFFER];
static int http_response_len = 0;

// ==================== WiFi事件处理 ====================

static void wifi_event_handler(void* arg, esp_event_base_t event_base,
                               int32_t event_id, void* event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        ESP_LOGI(TAG, "WiFi断开，尝试重连...");
        esp_wifi_connect();
        xEventGroupClearBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        ESP_LOGI(TAG, "获得IP地址:" IPSTR, IP2STR(&event->ip_info.ip));
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

static void wifi_init_sta(void)
{
    s_wifi_event_group = xEventGroupCreate();

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    esp_event_handler_instance_t instance_any_id;
    esp_event_handler_instance_t instance_got_ip;
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                        ESP_EVENT_ANY_ID,
                                                        &wifi_event_handler,
                                                        NULL,
                                                        &instance_any_id));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT,
                                                        IP_EVENT_STA_GOT_IP,
                                                        &wifi_event_handler,
                                                        NULL,
                                                        &instance_got_ip));

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = WIFI_SSID,
            .password = WIFI_PASSWORD,
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,
        },
    };
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "WiFi初始化完成，等待连接...");

    EventBits_t bits = xEventGroupWaitBits(s_wifi_event_group,
            WIFI_CONNECTED_BIT | WIFI_FAIL_BIT,
            pdFALSE,
            pdFALSE,
            portMAX_DELAY);

    if (bits & WIFI_CONNECTED_BIT) {
        ESP_LOGI(TAG, "✅ WiFi连接成功: %s", WIFI_SSID);
    } else {
        ESP_LOGE(TAG, "❌ WiFi连接失败");
    }
}

// ==================== HTTP客户端 ====================

static esp_err_t http_event_handler(esp_http_client_event_t *evt)
{
    switch(evt->event_id) {
        case HTTP_EVENT_ON_DATA:
            if (http_response_len + evt->data_len < MAX_HTTP_OUTPUT_BUFFER) {
                memcpy(http_response_buffer + http_response_len, evt->data, evt->data_len);
                http_response_len += evt->data_len;
                http_response_buffer[http_response_len] = 0;
            }
            break;
        default:
            break;
    }
    return ESP_OK;
}

// ==================== EdgeTTS API 封装 ====================

/**
 * 测试连接
 */
static bool edgetts_ping(void)
{
    char url[128];
    snprintf(url, sizeof(url), API_PING, SERVER_PORT);
    
    http_response_len = 0;
    memset(http_response_buffer, 0, sizeof(http_response_buffer));
    
    esp_http_client_config_t config = {
        .url = url,
        .event_handler = http_event_handler,
        .timeout_ms = 5000,
    };
    
    esp_http_client_handle_t client = esp_http_client_init(&config);
    esp_err_t err = esp_http_client_perform(client);
    
    bool success = false;
    if (err == ESP_OK) {
        int status = esp_http_client_get_status_code(client);
        if (status == 200 && strcmp(http_response_buffer, "pong") == 0) {
            success = true;
        }
    }
    
    esp_http_client_cleanup(client);
    return success;
}

/**
 * 获取服务状态
 */
static bool edgetts_get_status(void)
{
    char url[128];
    snprintf(url, sizeof(url), API_STATUS, SERVER_PORT);
    
    http_response_len = 0;
    memset(http_response_buffer, 0, sizeof(http_response_buffer));
    
    esp_http_client_config_t config = {
        .url = url,
        .event_handler = http_event_handler,
        .timeout_ms = 5000,
    };
    
    esp_http_client_handle_t client = esp_http_client_init(&config);
    esp_err_t err = esp_http_client_perform(client);
    
    bool success = false;
    if (err == ESP_OK) {
        int status = esp_http_client_get_status_code(client);
        if (status == 200) {
            ESP_LOGI(TAG, "服务状态: %s", http_response_buffer);
            success = true;
        }
    }
    
    esp_http_client_cleanup(client);
    return success;
}

/**
 * AI问答
 */
static bool edgetts_ask(const char* question, char* answer, size_t answer_size)
{
    char url[128];
    snprintf(url, sizeof(url), API_ASK, SERVER_PORT);
    
    http_response_len = 0;
    memset(http_response_buffer, 0, sizeof(http_response_buffer));
    
    esp_http_client_config_t config = {
        .url = url,
        .method = HTTP_METHOD_POST,
        .event_handler = http_event_handler,
        .timeout_ms = 30000,
    };
    
    esp_http_client_handle_t client = esp_http_client_init(&config);
    esp_http_client_set_header(client, "Content-Type", "text/plain; charset=utf-8");
    esp_http_client_set_post_field(client, question, strlen(question));
    
    esp_err_t err = esp_http_client_perform(client);
    
    bool success = false;
    if (err == ESP_OK) {
        int status = esp_http_client_get_status_code(client);
        if (status == 200) {
            strncpy(answer, http_response_buffer, answer_size - 1);
            answer[answer_size - 1] = 0;
            success = true;
        }
    }
    
    esp_http_client_cleanup(client);
    return success;
}

/**
 * 文字转语音（获取音频数据大小）
 */
static int edgetts_tts_get_size(const char* text, const char* voice)
{
    char url[256];
    // URL编码文本（简化版，实际应该完整编码）
    snprintf(url, sizeof(url), API_TTS, SERVER_PORT, text, voice);
    
    esp_http_client_config_t config = {
        .url = url,
        .method = HTTP_METHOD_GET,
        .timeout_ms = 30000,
    };
    
    esp_http_client_handle_t client = esp_http_client_init(&config);
    esp_err_t err = esp_http_client_open(client, 0);
    
    int content_length = -1;
    if (err == ESP_OK) {
        content_length = esp_http_client_fetch_headers(client);
        ESP_LOGI(TAG, "TTS音频大小: %d bytes", content_length);
    }
    
    esp_http_client_cleanup(client);
    return content_length;
}

// ==================== 测试函数 ====================

static void test_edgetts_api(void)
{
    ESP_LOGI(TAG, "\n========== 开始测试 EdgeTTS API ==========\n");
    
    // 1. 测试连接
    ESP_LOGI(TAG, "1. 测试连接...");
    if (edgetts_ping()) {
        ESP_LOGI(TAG, "✅ Ping成功");
    } else {
        ESP_LOGE(TAG, "❌ Ping失败");
        return;
    }
    vTaskDelay(pdMS_TO_TICKS(1000));
    
    // 2. 获取服务状态
    ESP_LOGI(TAG, "\n2. 获取服务状态...");
    if (edgetts_get_status()) {
        ESP_LOGI(TAG, "✅ 状态获取成功");
    } else {
        ESP_LOGE(TAG, "❌ 状态获取失败");
    }
    vTaskDelay(pdMS_TO_TICKS(1000));
    
    // 3. AI问答测试
    ESP_LOGI(TAG, "\n3. AI问答测试...");
    char answer[512];
    if (edgetts_ask("你好，请介绍一下自己", answer, sizeof(answer))) {
        ESP_LOGI(TAG, "✅ AI问答成功");
        ESP_LOGI(TAG, "回答: %s", answer);
    } else {
        ESP_LOGE(TAG, "❌ AI问答失败");
    }
    vTaskDelay(pdMS_TO_TICKS(2000));
    
    // 4. 语音合成测试
    ESP_LOGI(TAG, "\n4. 语音合成测试...");
    int audio_size = edgetts_tts_get_size("你好，这是ESP32语音合成测试", "xiaoxiao");
    if (audio_size > 0) {
        ESP_LOGI(TAG, "✅ 语音合成成功，音频大小: %d bytes", audio_size);
    } else {
        ESP_LOGE(TAG, "❌ 语音合成失败");
    }
    
    ESP_LOGI(TAG, "\n========== 测试完成 ==========\n");
}

// ==================== 主函数 ====================

void app_main(void)
{
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "  ESP32-S3 EdgeTTS Client Example");
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "服务器: %s:%d", SERVER_HOST, SERVER_PORT);
    ESP_LOGI(TAG, "WiFi: %s", WIFI_SSID);
    ESP_LOGI(TAG, "========================================\n");
    
    // 初始化NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    
    // 初始化WiFi
    ESP_LOGI(TAG, "初始化WiFi...");
    wifi_init_sta();
    
    // 等待WiFi连接
    vTaskDelay(pdMS_TO_TICKS(2000));
    
    // 测试EdgeTTS API
    test_edgetts_api();
    
    // 主循环
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(10000));
        
        // 定期检查连接
        if (edgetts_ping()) {
            ESP_LOGI(TAG, "✅ 服务器连接正常");
        } else {
            ESP_LOGW(TAG, "⚠️ 服务器连接异常");
        }
    }
}
