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
#include "driver/i2c.h"
#include "driver/gpio.h"
#include "esp_system.h"
#include "esp_check.h"
#include "es8311.h"

#define ENABLE_BACKGROUND_I2S_TASKS 1

#define ENABLE_EDGETTS_TEST_TASK 0

#define ENABLE_MIC_VOICE_CHAT_TASK 0
#define MIC_RECORD_SECONDS 5

#define ENABLE_STARTUP_BEEP 0

#define CONFIG_EXAMPLE_MODE_MUSIC 0
#define CONFIG_EXAMPLE_MODE_ECHO (!CONFIG_EXAMPLE_MODE_MUSIC)
#define CONFIG_EXAMPLE_VOICE_VOLUME 60

#if CONFIG_EXAMPLE_MODE_ECHO
#ifndef CONFIG_EXAMPLE_MIC_GAIN
#define CONFIG_EXAMPLE_MIC_GAIN ES8311_MIC_GAIN_24DB
#endif
#endif

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
static es8311_handle_t g_es8311 = NULL;

static void mic_voice_chat_task(void *arg);

static bool record_wav_fixed_mono(uint32_t seconds, uint8_t** out_wav, size_t* out_size)
{
    if (!out_wav || !out_size) {
        return false;
    }
    *out_wav = NULL;
    *out_size = 0;
    if (!rx_handle) {
        return false;
    }

    if (g_es8311) {
        // 录音前打开 ES8311 MIC 通路
        (void)es8311_microphone_config(g_es8311, true);
    }

    if (seconds == 0) {
        return false;
    }
    const uint32_t sample_rate = EXAMPLE_SAMPLE_RATE;
    const uint16_t bits_per_sample = 16;
    const uint16_t channels = 1;
    const size_t mono_bytes = (size_t)sample_rate * (size_t)seconds * (bits_per_sample / 8);

    // WAV header (44 bytes) + mono PCM payload
    const size_t wav_size = 44 + mono_bytes;
    uint8_t* wav = (uint8_t*)malloc(wav_size);
    if (!wav) {
        ESP_LOGE(TAG, "❌ 录音内存不足(wav) | bytes=%u", (unsigned)wav_size);
        return false;
    }

    uint8_t* rx_buf = (uint8_t*)malloc(EXAMPLE_RECV_BUF_SIZE);
    if (!rx_buf) {
        ESP_LOGE(TAG, "❌ 录音内存不足(rx_buf) | bytes=%u", (unsigned)EXAMPLE_RECV_BUF_SIZE);
        free(wav);
        return false;
    }

    size_t mono_pos = 0;
    uint8_t* pcm_dst = wav + 44;
    while (mono_pos < mono_bytes) {
        size_t bytes_read = 0;
        esp_err_t ret = i2s_channel_read(rx_handle, rx_buf, EXAMPLE_RECV_BUF_SIZE, &bytes_read, portMAX_DELAY);
        if (ret != ESP_OK || bytes_read == 0) {
            if (g_es8311) {
                (void)es8311_microphone_config(g_es8311, false);
            }
            free(rx_buf);
            free(wav);
            return false;
        }

        // I2S 配置为 stereo 16-bit：每帧 4 字节(L,R)
        size_t frames = bytes_read / 4;
        for (size_t i = 0; i < frames && mono_pos + 2 <= mono_bytes; i++) {
            // 取左声道(前 2 字节)
            pcm_dst[mono_pos + 0] = rx_buf[i * 4 + 0];
            pcm_dst[mono_pos + 1] = rx_buf[i * 4 + 1];
            mono_pos += 2;
        }
    }

    free(rx_buf);

    if (g_es8311) {
        // 录音结束，关闭 MIC 通路避免噪声/回授
        (void)es8311_microphone_config(g_es8311, false);
    }

    uint32_t byte_rate = sample_rate * channels * (bits_per_sample / 8);
    uint16_t block_align = channels * (bits_per_sample / 8);
    uint32_t data_size = (uint32_t)mono_bytes;
    uint32_t riff_size = 36 + data_size;

    memcpy(wav + 0, "RIFF", 4);
    wav[4] = (uint8_t)(riff_size & 0xff);
    wav[5] = (uint8_t)((riff_size >> 8) & 0xff);
    wav[6] = (uint8_t)((riff_size >> 16) & 0xff);
    wav[7] = (uint8_t)((riff_size >> 24) & 0xff);
    memcpy(wav + 8, "WAVE", 4);
    memcpy(wav + 12, "fmt ", 4);
    wav[16] = 16; wav[17] = 0; wav[18] = 0; wav[19] = 0; // PCM fmt chunk size
    wav[20] = 1; wav[21] = 0; // PCM format
    wav[22] = (uint8_t)(channels & 0xff);
    wav[23] = (uint8_t)((channels >> 8) & 0xff);
    wav[24] = (uint8_t)(sample_rate & 0xff);
    wav[25] = (uint8_t)((sample_rate >> 8) & 0xff);
    wav[26] = (uint8_t)((sample_rate >> 16) & 0xff);
    wav[27] = (uint8_t)((sample_rate >> 24) & 0xff);
    wav[28] = (uint8_t)(byte_rate & 0xff);
    wav[29] = (uint8_t)((byte_rate >> 8) & 0xff);
    wav[30] = (uint8_t)((byte_rate >> 16) & 0xff);
    wav[31] = (uint8_t)((byte_rate >> 24) & 0xff);
    wav[32] = (uint8_t)(block_align & 0xff);
    wav[33] = (uint8_t)((block_align >> 8) & 0xff);
    wav[34] = (uint8_t)(bits_per_sample & 0xff);
    wav[35] = (uint8_t)((bits_per_sample >> 8) & 0xff);
    memcpy(wav + 36, "data", 4);
    wav[40] = (uint8_t)(data_size & 0xff);
    wav[41] = (uint8_t)((data_size >> 8) & 0xff);
    wav[42] = (uint8_t)((data_size >> 16) & 0xff);
    wav[43] = (uint8_t)((data_size >> 24) & 0xff);

    *out_wav = wav;
    *out_size = wav_size;
    return true;
}

static bool on_tts_pcm_chunk(const uint8_t* pcm, size_t len, void* user_data)
{
    (void)user_data;
    if (!tx_handle || !pcm || len == 0) {
        return false;
    }
    size_t total = 0;
    while (total < len) {
        size_t wrote = 0;
        esp_err_t ret = i2s_channel_write(tx_handle, pcm + total, len - total, &wrote, portMAX_DELAY);
        if (ret != ESP_OK) {
            return false;
        }
        if (wrote == 0) {
            return false;
        }
        total += wrote;
    }
    return true;
}

#if CONFIG_EXAMPLE_MODE_MUSIC
extern const uint8_t music_pcm_start[] asm("_binary_canon_pcm_start");
extern const uint8_t music_pcm_end[]   asm("_binary_canon_pcm_end");

static void play_canon_pcm_once(void)
{
    if (!tx_handle) {
        return;
    }
    size_t bytes_write = 0;
    uint8_t *data_ptr = (uint8_t *)music_pcm_start;

    ESP_ERROR_CHECK(i2s_channel_disable(tx_handle));
    ESP_ERROR_CHECK(i2s_channel_preload_data(tx_handle, data_ptr, music_pcm_end - data_ptr, &bytes_write));
    data_ptr += bytes_write;
    ESP_ERROR_CHECK(i2s_channel_enable(tx_handle));

    if (data_ptr < music_pcm_end) {
        esp_err_t ret = i2s_channel_write(tx_handle, data_ptr, music_pcm_end - data_ptr, &bytes_write, portMAX_DELAY);
        if (ret != ESP_OK || bytes_write == 0) {
            ESP_LOGE(TAG, "[canon] i2s write failed");
            return;
        }
    }

    ESP_LOGI(TAG, "[canon] startup pcm played once");
}
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
    g_es8311 = es_handle;
    const es8311_clock_config_t es_clk = {
        .mclk_inverted = false,
        .sclk_inverted = false,
        .mclk_from_mclk_pin = true,
        .mclk_frequency = EXAMPLE_MCLK_FREQ_HZ,
        .sample_frequency = EXAMPLE_SAMPLE_RATE
    };

    ESP_ERROR_CHECK(es8311_init(es_handle, &es_clk, ES8311_RESOLUTION_16, ES8311_RESOLUTION_16));
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
    ESP_ERROR_CHECK(i2s_new_channel(&chan_cfg, &tx_handle, &rx_handle));
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
    ESP_ERROR_CHECK(i2s_channel_init_std_mode(rx_handle, &std_cfg));
    ESP_ERROR_CHECK(i2s_channel_enable(tx_handle));
    ESP_ERROR_CHECK(i2s_channel_enable(rx_handle));
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
            abort();
        }
        if (bytes_write > 0) {
            ESP_LOGI(TAG, "[music] i2s music played, %d bytes are written.", bytes_write);
        } else {
            ESP_LOGE(TAG, "[music] i2s music play failed.");
            abort();
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
        abort();
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
            abort();
        }
        /* Write sample data to earphone */
        ret = i2s_channel_write(tx_handle, mic_data, EXAMPLE_RECV_BUF_SIZE, &bytes_write, 1000);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "[echo] i2s write failed, %s", err_reason[ret == ESP_ERR_TIMEOUT]);
            abort();
        }
        if (bytes_read != bytes_write) {
            ESP_LOGW(TAG, "[echo] %d bytes read but only %d bytes are written", bytes_read, bytes_write);
        }
    }
    vTaskDelete(NULL);
}
#endif

void app_audio(void)
{
	printf("i2s es8311 codec example start\n-----------------------------\n");
    /* Initialize i2c peripheral and config es8311 codec by i2c */
    if (es8311_codec_init() != ESP_OK) {
        ESP_LOGE(TAG, "es8311 codec init failed");
        abort();
    } else {
        ESP_LOGI(TAG, "es8311 codec init success");
    }
    /* Initialize i2s peripheral */
    if (i2s_driver_init() != ESP_OK) {
        ESP_LOGE(TAG, "i2s driver init failed");
        abort();
    } else {
        ESP_LOGI(TAG, "i2s driver init success");
    }

#if CONFIG_EXAMPLE_MODE_MUSIC && ENABLE_STARTUP_BEEP
    play_canon_pcm_once();
#endif
#if ENABLE_BACKGROUND_I2S_TASKS
    #if CONFIG_EXAMPLE_MODE_MUSIC
        xTaskCreate(i2s_music, "i2s_music", 4096, NULL, 5, NULL);
    #else
        xTaskCreate(i2s_echo, "i2s_echo", 8192, NULL, 5, NULL);
    #endif
#endif
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
    // 等待网络就绪（默认走 ETH；如启用 WiFi，则任一就绪即可）
    uint32_t waited_ms = 0;
    uint32_t last_log_ms = 0;
    while ((my_wifi_info.first != 1) && (my_eth_info.first != 1)) {
        vTaskDelay(pdMS_TO_TICKS(200));
        waited_ms += 200;
        if (waited_ms - last_log_ms >= 2000) {
            last_log_ms = waited_ms;
            ESP_LOGI(TAG, "Waiting network... wifi_first=%d eth_first=%d", my_wifi_info.first, my_eth_info.first);
        }
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
    
    // 3. 全链路 ask_tts：一次请求完成 AI -> TTS，并流式输出到 I2S（保证文字与语音一致）
    ESP_LOGI(TAG, "3. 全链路 ask_tts(流式播放)...");
    if (edgetts_ask_tts_stream(client, "你好，请介绍一下自己", "xiaoxiao", "wav", on_tts_pcm_chunk, NULL, NULL)) {
        ESP_LOGI(TAG, "✅ ask_tts 流式播放完成");
    } else {
        ESP_LOGE(TAG, "❌ ask_tts 流式播放失败: %s", edgetts_get_error(client));
    }

    // 4. MIC 全链路在 mic_voice_chat_task 中单独运行
    
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
    //ETH(W5500)以太网初始化（默认优先使用以太网）
    app_eth();
    {
        bool enable_wifi = false;
        if (enable_wifi) {
            app_wifi();
        }
    }
    //SD_CARD初始化
    app_sd_card();
    //剩余GPIO测试
    //app_gpio();
    app_audio();
    
    // 启动EdgeTTS测试任务（默认关闭，专注调试 MIC 链路时不要自动跑整套测试）
#if ENABLE_EDGETTS_TEST_TASK
    xTaskCreate(edgetts_test_task, "edgetts_test", 8192, NULL, 3, NULL);
#endif

    // 开机自动运行 MIC 全链路：录音 -> voice_chat(out=audio) -> 播放
#if ENABLE_MIC_VOICE_CHAT_TASK
    {
        BaseType_t mic_status = xTaskCreate(mic_voice_chat_task, "mic_voice_chat", 8192, NULL, 3, NULL);
        if (mic_status == pdPASS) {
            ESP_LOGI(TAG, "mic_voice_chat_task created");
        } else {
            ESP_LOGE(TAG, "❌ mic_voice_chat_task create failed");
        }
    }
#endif
    
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

static void mic_voice_chat_task(void *arg)
{
    (void)arg;

    // 等待网络就绪（优先等以太网/WiFi 任一获得 IP）
    ESP_LOGI(TAG, "mic_voice_chat_task start | waiting for IP...");
    for (int i = 0; i < 300; i++) {
        bool wifi_ok = (my_wifi_info.ip_string[0] != 0);
        bool eth_ok = (my_eth_info.ip_string[0] != 0);
        if (wifi_ok || eth_ok) {
            ESP_LOGI(TAG, "network ready | wifi_ip=%s | eth_ip=%s", my_wifi_info.ip_string, my_eth_info.ip_string);
            break;
        }
        if ((i % 10) == 0) {
            ESP_LOGI(TAG, "waiting IP... (%d/300) | wifi_ip=%s | eth_ip=%s", i, my_wifi_info.ip_string, my_eth_info.ip_string);
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }

    ESP_LOGI(TAG, "========== MIC voice_chat pipeline start ==========");

    edgetts_client_t* client = edgetts_client_create("192.168.1.117", 3003);
    if (!client) {
        ESP_LOGE(TAG, "❌ edgetts_client_create failed");
        vTaskDelete(NULL);
        return;
    }

    ESP_LOGI(TAG, "MIC录音%u秒...", (unsigned)MIC_RECORD_SECONDS);
    uint8_t* wav = NULL;
    size_t wav_size = 0;

    if (!record_wav_fixed_mono(MIC_RECORD_SECONDS, &wav, &wav_size)) {
        ESP_LOGE(TAG, "❌ 录音失败");
        edgetts_client_destroy(client);
        vTaskDelete(NULL);
        return;
    }

    ESP_LOGI(TAG, "录音完成 | wav_size=%u", (unsigned)wav_size);
    ESP_LOGI(TAG, "发送到后端 /mcu/voice_chat?out=text 获取识别文本...");
    {
        char* question = NULL;
        char* answer = NULL;
        if (edgetts_voice_chat_text(client, wav, wav_size, "tencent", "wav", &question, &answer, NULL)) {
            ESP_LOGI(TAG, "ASR: %s", question ? question : "");
            ESP_LOGI(TAG, "AI : %s", answer ? answer : "");
        } else {
            ESP_LOGE(TAG, "❌ voice_chat(text) 失败: %s", edgetts_get_error(client));
        }
        if (question) {
            free(question);
        }
        if (answer) {
            free(answer);
        }
    }

    free(wav);
    edgetts_client_destroy(client);
    ESP_LOGI(TAG, "========== MIC voice_chat pipeline done ==========");
    vTaskDelete(NULL);
}
