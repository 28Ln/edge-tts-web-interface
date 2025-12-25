#include <stdio.h>
#include <stdbool.h>
#include <unistd.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_log.h"
#include "esp_timer.h"

#include "lcd.h"
#include "lv_port_disp_template.h"
#include "gui_guider.h"
#include "custom.h"

#include "app_wifi.h"
#include "app_eth.h"
#include "app_sd_card.h"
#include "app_gpio.h"
#include "edgetts_client.h"

//#include "driver/i2c.h"
#include "driver/i2s_std.h"
#include "esp_system.h"
#include "esp_check.h"
#include "es8311.h"

#define CONFIG_EXAMPLE_MODE_MUSIC 1
#define CONFIG_EXAMPLE_VOICE_VOLUME 60

/* Example configurations */
#define EXAMPLE_RECV_BUF_SIZE   (2400)
#define EXAMPLE_SAMPLE_RATE     (16000)
#define EXAMPLE_MCLK_MULTIPLE   (384) // If not using 24-bit data width, 256 should be enough
#define EXAMPLE_MCLK_FREQ_HZ    (EXAMPLE_SAMPLE_RATE * EXAMPLE_MCLK_MULTIPLE)
#define EXAMPLE_VOICE_VOLUME    CONFIG_EXAMPLE_VOICE_VOLUME
#if CONFIG_EXAMPLE_MODE_ECHO
#define EXAMPLE_MIC_GAIN        CONFIG_EXAMPLE_MIC_GAIN
#endif

#if !defined(CONFIG_EXAMPLE_BSP)

/* I2C port and GPIOs */
#define I2C_NUM         (0)
#if CONFIG_IDF_TARGET_ESP32 || CONFIG_IDF_TARGET_ESP32S2 || CONFIG_IDF_TARGET_ESP32S3
#define I2C_SCL_IO      (GPIO_NUM_48)
#define I2C_SDA_IO      (GPIO_NUM_47)

#elif CONFIG_IDF_TARGET_ESP32H2
#define I2C_SCL_IO      (GPIO_NUM_8)
#define I2C_SDA_IO      (GPIO_NUM_9)
#else
#define I2C_SCL_IO      (GPIO_NUM_6)
#define I2C_SDA_IO      (GPIO_NUM_7)
#endif

/* I2S port and GPIOs */
#define I2S_NUM         (0)
#define I2S_MCK_IO      (GPIO_NUM_6)
#define I2S_BCK_IO      (GPIO_NUM_7)
#define I2S_WS_IO       (GPIO_NUM_5)
#if CONFIG_IDF_TARGET_ESP32 || CONFIG_IDF_TARGET_ESP32S2 || CONFIG_IDF_TARGET_ESP32S3
#define I2S_DO_IO       (GPIO_NUM_4)
#define I2S_DI_IO       (GPIO_NUM_19)
#else
#define I2S_DO_IO       (GPIO_NUM_2)
#define I2S_DI_IO       (GPIO_NUM_3)
#endif

#else // CONFIG_EXAMPLE_BSP
#include "bsp/esp-bsp.h"
#define I2C_NUM BSP_I2C_NUM
#endif // CONFIG_EXAMPLE_BSP

static const char *TAG = "main output";

TaskHandle_t  task_handle_gui;
esp_timer_create_args_t timer_args_gui;
esp_timer_handle_t timer_handle_gui;
lv_ui guider_ui;

extern MY_WIFI_INFO my_wifi_info;
extern MY_ETH_INFO my_eth_info;
extern MY_SDCARD_INFO my_SDcard_info;

static const char err_reason[][30] = {"input param is invalid",
                                      "operation timeout"
                                     };
static i2s_chan_handle_t tx_handle = NULL;
static i2s_chan_handle_t rx_handle = NULL;
static bool g_audio_ready = false;

/* Import music file as buffer */
#if CONFIG_EXAMPLE_MODE_MUSIC
extern const uint8_t music_pcm_start[] asm("_binary_canon_pcm_start");
extern const uint8_t music_pcm_end[]   asm("_binary_canon_pcm_end");
#endif

static esp_err_t es8311_codec_init(void)
{
    /* Initialize I2C peripheral */
#if !defined(CONFIG_EXAMPLE_BSP)
    const i2c_config_t es_i2c_cfg = {
        .sda_io_num = I2C_SDA_IO,
        .scl_io_num = I2C_SCL_IO,
        .mode = I2C_MODE_MASTER,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = 100000,
    };
    ESP_RETURN_ON_ERROR(i2c_param_config(I2C_NUM, &es_i2c_cfg), TAG, "config i2c failed");
    ESP_RETURN_ON_ERROR(i2c_driver_install(I2C_NUM, I2C_MODE_MASTER,  0, 0, 0), TAG, "install i2c driver failed");
#else
    ESP_ERROR_CHECK(bsp_i2c_init());
#endif

    /* Initialize es8311 codec */
    es8311_handle_t es_handle = es8311_create(I2C_NUM, ES8311_ADDRRES_0);
    ESP_RETURN_ON_FALSE(es_handle, ESP_FAIL, TAG, "es8311 create failed");
    const es8311_clock_config_t es_clk = {
        .mclk_inverted = false,
        .sclk_inverted = false,
        .mclk_from_mclk_pin = true,
        .mclk_frequency = EXAMPLE_MCLK_FREQ_HZ,
        .sample_frequency = EXAMPLE_SAMPLE_RATE
    };

    ESP_RETURN_ON_ERROR(es8311_init(es_handle, &es_clk, ES8311_RESOLUTION_16, ES8311_RESOLUTION_16), TAG, "es8311 init failed");
    ESP_RETURN_ON_ERROR(es8311_sample_frequency_config(es_handle, EXAMPLE_SAMPLE_RATE * EXAMPLE_MCLK_MULTIPLE, EXAMPLE_SAMPLE_RATE), TAG, "set es8311 sample frequency failed");
    ESP_RETURN_ON_ERROR(es8311_voice_volume_set(es_handle, EXAMPLE_VOICE_VOLUME, NULL), TAG, "set es8311 volume failed");
    ESP_RETURN_ON_ERROR(es8311_microphone_config(es_handle, false), TAG, "set es8311 microphone failed");
#if CONFIG_EXAMPLE_MODE_ECHO
    ESP_RETURN_ON_ERROR(es8311_microphone_gain_set(es_handle, EXAMPLE_MIC_GAIN), TAG, "set es8311 microphone gain failed");
#endif
    return ESP_OK;
}

static esp_err_t i2s_driver_init(void)
{
#if !defined(CONFIG_EXAMPLE_BSP)
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM, I2S_ROLE_MASTER);
    chan_cfg.auto_clear = true; // Auto clear the legacy data in the DMA buffer
    ESP_ERROR_CHECK(i2s_new_channel(&chan_cfg, &tx_handle, NULL));
    i2s_std_config_t std_cfg = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(EXAMPLE_SAMPLE_RATE),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_STEREO),
        .gpio_cfg = {
            .mclk = I2S_MCK_IO,
            .bclk = I2S_BCK_IO,
            .ws = I2S_WS_IO,
            .dout = I2S_DO_IO,
            .din = I2S_DI_IO,
            .invert_flags = {
                .mclk_inv = false,
                .bclk_inv = false,
                .ws_inv = false,
            },
        },
    };
    std_cfg.clk_cfg.mclk_multiple = EXAMPLE_MCLK_MULTIPLE;

    ESP_ERROR_CHECK(i2s_channel_init_std_mode(tx_handle, &std_cfg));
    ESP_ERROR_CHECK(i2s_channel_enable(tx_handle));
#else
    ESP_LOGI(TAG, "Using BSP for HW configuration");
    i2s_std_config_t std_cfg = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(EXAMPLE_SAMPLE_RATE),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_STEREO),
        .gpio_cfg = BSP_I2S_GPIO_CFG,
    };
    std_cfg.clk_cfg.mclk_multiple = EXAMPLE_MCLK_MULTIPLE;
    ESP_ERROR_CHECK(bsp_audio_init(&std_cfg, &tx_handle, &rx_handle));
    ESP_ERROR_CHECK(bsp_audio_poweramp_enable(true));
#endif
    return ESP_OK;
}

#if CONFIG_EXAMPLE_MODE_MUSIC
static void i2s_music(void *args)
{
    esp_err_t ret = ESP_OK;
    size_t bytes_write = 0;
    uint8_t *data_ptr = (uint8_t *)music_pcm_start;

    /* (Optional) Disable TX channel and preload the data before enabling the TX channel,
     * so that the valid data can be transmitted immediately */
    ESP_ERROR_CHECK(i2s_channel_disable(tx_handle));
    ESP_ERROR_CHECK(i2s_channel_preload_data(tx_handle, data_ptr, music_pcm_end - data_ptr, &bytes_write));
    data_ptr += bytes_write;  // Move forward the data pointer

    /* Enable the TX channel */
    ESP_ERROR_CHECK(i2s_channel_enable(tx_handle));
    while (1) {
        /* Write music to earphone */
        ret = i2s_channel_write(tx_handle, data_ptr, music_pcm_end - data_ptr, &bytes_write, portMAX_DELAY);
        if (ret != ESP_OK) {
            /* Since we set timeout to 'portMAX_DELAY' in 'i2s_channel_write'
               so you won't reach here unless you set other timeout value,
               if timeout detected, it means write operation failed. */
            ESP_LOGE(TAG, "[music] i2s write failed, %s", err_reason[ret == ESP_ERR_TIMEOUT]);
            break;
        }
        if (bytes_write > 0) {
            ESP_LOGI(TAG, "[music] i2s music played, %d bytes are written.", bytes_write);
        } else {
            ESP_LOGE(TAG, "[music] i2s music play failed.");
            break;
        }
        data_ptr = (uint8_t *)music_pcm_start;
        vTaskDelay(1000 / portTICK_PERIOD_MS);
    }
    vTaskDelete(NULL);
}

#else
static void i2s_echo(void *args)
{
    int *mic_data = malloc(EXAMPLE_RECV_BUF_SIZE);
    if (!mic_data) {
        ESP_LOGE(TAG, "[echo] No memory for read data buffer");
        vTaskDelete(NULL);
        return;
    }
    esp_err_t ret = ESP_OK;
    size_t bytes_read = 0;
    size_t bytes_write = 0;
    ESP_LOGI(TAG, "[echo] Echo start");

    while (1) {
        memset(mic_data, 0, EXAMPLE_RECV_BUF_SIZE);
        /* Read sample data from mic */
        ret = i2s_channel_read(rx_handle, mic_data, EXAMPLE_RECV_BUF_SIZE, &bytes_read, 1000);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "[echo] i2s read failed, %s", err_reason[ret == ESP_ERR_TIMEOUT]);
            break;
        }
        /* Write sample data to earphone */
        ret = i2s_channel_write(tx_handle, mic_data, EXAMPLE_RECV_BUF_SIZE, &bytes_write, 1000);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "[echo] i2s write failed, %s", err_reason[ret == ESP_ERR_TIMEOUT]);
            break;
        }
        if (bytes_read != bytes_write) {
            ESP_LOGW(TAG, "[echo] %d bytes read but only %d bytes are written", bytes_read, bytes_write);
        }
    }
    free(mic_data);
    vTaskDelete(NULL);
}
#endif

static bool play_wav_to_i2s(const uint8_t* wav, size_t wav_size)
{
    if (!g_audio_ready || !tx_handle) {
        ESP_LOGE(TAG, "Audio not ready");
        return false;
    }
    if (!wav || wav_size < 44) {
        ESP_LOGE(TAG, "Invalid WAV buffer");
        return false;
    }

    size_t offset = 12;
    while (offset + 8 <= wav_size) {
        uint32_t chunk_size = (uint32_t)wav[offset + 4] | ((uint32_t)wav[offset + 5] << 8) |
                              ((uint32_t)wav[offset + 6] << 16) | ((uint32_t)wav[offset + 7] << 24);
        if (offset + 8 + chunk_size > wav_size) {
            break;
        }
        if (memcmp(&wav[offset], "data", 4) == 0) {
            const uint8_t* pcm = &wav[offset + 8];
            size_t pcm_len = chunk_size;
            size_t wrote = 0;
            esp_err_t ret = i2s_channel_write(tx_handle, pcm, pcm_len, &wrote, portMAX_DELAY);
            if (ret != ESP_OK || wrote == 0) {
                ESP_LOGE(TAG, "TTS i2s write failed");
                return false;
            }
            return true;
        }
        offset += 8 + chunk_size + (chunk_size & 1);
    }

    ESP_LOGE(TAG, "WAV data chunk not found");
    return false;
}

void app_audio(void)
{
	printf("i2s es8311 codec example start\n-----------------------------\n");
    /* Initialize i2c peripheral and config es8311 codec by i2c */
    if (es8311_codec_init() != ESP_OK) {
        ESP_LOGE(TAG, "es8311 codec init failed");
        return;
    } else {
        ESP_LOGI(TAG, "es8311 codec init success");
    }
    /* Initialize i2s peripheral */
    if (i2s_driver_init() != ESP_OK) {
        ESP_LOGE(TAG, "i2s driver init failed");
        return;
    } else {
        ESP_LOGI(TAG, "i2s driver init success");
    }

    g_audio_ready = true;
}

static void lv_tick_task(void *arg)
{
    lv_tick_inc(1);
}
void lv_run_task(void *arg)
{
    while (true) {
        lv_task_handler();
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

// EdgeTTS测试任务
void edgetts_test_task(void *arg)
{
    uint32_t waited_ms = 0;
    while ((my_wifi_info.first != 1) && (my_eth_info.first != 1)) {
        vTaskDelay(pdMS_TO_TICKS(200));
        waited_ms += 200;
        if (waited_ms >= 60000) {
            ESP_LOGE(TAG, "Network not ready (WiFi/ETH), skip EdgeTTS test");
            vTaskDelete(NULL);
            return;
        }
    }
    
    ESP_LOGI(TAG, "========== EdgeTTS SDK Testing start ==========");
    
    // 创建客户端（修改为你的服务器地址）
    edgetts_client_t* client = edgetts_client_create("192.168.1.117", 3003);
    if (!client) {
        ESP_LOGE(TAG, "Fail to create EdgeTTS client");
        vTaskDelete(NULL);
        return;
    }
    
    // 设置超时
    edgetts_set_timeout(client, 120000);
    
    // 1. 测试连接
    ESP_LOGI(TAG, "1. Testing connect...");
    if (edgetts_ping(client)) {
        ESP_LOGI(TAG, "Ping succeed");
    } else {
        ESP_LOGE(TAG, "Ping fail: %s", edgetts_get_error(client));
        ESP_LOGE(TAG, "Please check:");
        ESP_LOGE(TAG, "  1. is server ready?");
        ESP_LOGE(TAG, "  2. is IP Add correct?");
        ESP_LOGE(TAG, "  3. does internet connnect?");
        edgetts_client_destroy(client);
        vTaskDelete(NULL);
        return;
    }
    
    // 2. 获取状态
    ESP_LOGI(TAG, "2. 获取服务状态...");
    char* status = NULL;
    if (edgetts_get_status(client, &status)) {
        ESP_LOGI(TAG, "✅ 状态: %s", status);
        free(status);
    } else {
        ESP_LOGW(TAG, "⚠️ 获取状态失败: %s", edgetts_get_error(client));
    }
    
    // 3. AI问答
    ESP_LOGI(TAG, "3. 测试AI问答...");
    char* answer = NULL;
    const char* question = "你好，请介绍一下自己";
    if (edgetts_ask(client, question, &answer, NULL)) {
        ESP_LOGI(TAG, "✅ AI回答: %s", answer);
    } else {
        ESP_LOGE(TAG, "❌ AI问答失败: %s", edgetts_get_error(client));
    }
    
    // 4. 语音合成
    ESP_LOGI(TAG, "4. 测试语音合成...");
    uint8_t* audio = NULL;
    size_t audio_size = 0;
    if (answer && edgetts_tts(client, answer, "xiaoxiao", "wav", &audio, &audio_size)) {
        ESP_LOGI(TAG, "✅ 语音合成成功");
        ESP_LOGI(TAG, "   音频大小: %zu bytes", audio_size);
        ESP_LOGI(TAG, "   音频格式: WAV");
        if (!play_wav_to_i2s(audio, audio_size)) {
            ESP_LOGE(TAG, "❌ 音频播放失败");
        } else {
            ESP_LOGI(TAG, "✅ 音频播放完成");
        }
        free(audio);
    } else {
        ESP_LOGE(TAG, "❌ 语音合成失败: %s", edgetts_get_error(client));
    }

    if (answer) {
        free(answer);
        answer = NULL;
    }

    // 5. 一体化问答转语音（后端 ask_tts）
    ESP_LOGI(TAG, "5. 测试 ask_tts 一体化接口...");
    audio = NULL;
    audio_size = 0;
    if (edgetts_ask_tts(client, question, "xiaoxiao", "wav", &audio, &audio_size, NULL)) {
        ESP_LOGI(TAG, "✅ ask_tts 成功");
        ESP_LOGI(TAG, "   音频大小: %zu bytes", audio_size);
        if (!play_wav_to_i2s(audio, audio_size)) {
            ESP_LOGE(TAG, "❌ 音频播放失败");
        } else {
            ESP_LOGI(TAG, "✅ 音频播放完成");
        }
        free(audio);
    } else {
        ESP_LOGE(TAG, "❌ ask_tts 失败: %s", edgetts_get_error(client));
    }
    
    ESP_LOGI(TAG, "========== EdgeTTS SDK 测试完成 ==========");
    
    // 清理
    edgetts_client_destroy(client);
    vTaskDelete(NULL);
}

void app_main(void)
{
	LCD_Init();
    lv_init();
    lv_port_disp_init();
    setup_ui(&guider_ui);
    timer_args_gui.callback = &lv_tick_task;
    timer_args_gui.name = "periodic_gui";
    ESP_ERROR_CHECK(esp_timer_create(&timer_args_gui, &timer_handle_gui));
    ESP_ERROR_CHECK(esp_timer_start_periodic(timer_handle_gui, 1 * 1000));

    BaseType_t status = xTaskCreate(lv_run_task, "lv_run_task", 4096, NULL, 2, &task_handle_gui);
    if (status == pdPASS) {
        ESP_LOGI(TAG,"Display xTaskCreate OK!");
    }
    //WIFI初始化
    app_wifi();
    //ETH(W5500)以太网初始化
    app_eth();
    //SD_CARD初始化
    app_sd_card();
    //剩余GPIO测试
    //app_gpio();
    app_audio();
    
    // 启动EdgeTTS测试任务
    xTaskCreate(edgetts_test_task, "edgetts_test", 8192, NULL, 3, NULL);
    
    while (true) {
        if(my_wifi_info.flag == 1){
            my_wifi_info.flag = 0;
            lv_obj_set_style_bg_color(guider_ui.counter_label_wifi_state,
                    lv_color_hex(0xff00), LV_PART_MAIN|LV_STATE_DEFAULT); // @suppress("Symbol is not resolved")
            lv_label_set_text(guider_ui.counter_label_wifi_state, "WIFI状态:OK");
            lv_label_set_text(guider_ui.counter_label_wifi_ip, my_wifi_info.ip_string);
        }
        if(my_eth_info.flag == 1){
            my_eth_info.flag = 0;
            lv_obj_set_style_bg_color(guider_ui.counter_label_eth_state,
                    lv_color_hex(0xff00), LV_PART_MAIN|LV_STATE_DEFAULT);// @suppress("Symbol is not resolved")
            lv_label_set_text(guider_ui.counter_label_eth_state, "ETH状态:OK");
            lv_label_set_text(guider_ui.counter_label_eth_ip, my_eth_info.ip_string);
        }
        if(my_SDcard_info.flag == 1){
            my_SDcard_info.flag = 0;
            lv_obj_set_style_bg_color(guider_ui.counter_label_tf_state,
                    lv_color_hex(0xff00), LV_PART_MAIN|LV_STATE_DEFAULT);// @suppress("Symbol is not resolved")
            lv_label_set_text(guider_ui.counter_label_tf_state, "TF卡状态:OK");
            lv_label_set_text(guider_ui.counter_label_tf_rw, my_SDcard_info.string);
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}
