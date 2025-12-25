#ifndef _ES8311_H
#define _ES8311_H

#include "driver/i2c.h"
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ES8311 I2C地址 */
#define ES8311_ADDRRES_0    0x18
#define ES8311_ADDRRES_1    0x19

/* ES8311分辨率 */
typedef enum {
    ES8311_RESOLUTION_16 = 16,
    ES8311_RESOLUTION_18 = 18,
    ES8311_RESOLUTION_20 = 20,
    ES8311_RESOLUTION_24 = 24,
    ES8311_RESOLUTION_32 = 32
} es8311_resolution_t;

/* ES8311时钟配置 */
typedef struct {
    bool mclk_inverted;
    bool sclk_inverted;
    bool mclk_from_mclk_pin;
    uint32_t mclk_frequency;
    uint32_t sample_frequency;
} es8311_clock_config_t;

/* ES8311句柄 */
typedef void* es8311_handle_t;

/**
 * @brief 创建ES8311句柄
 */
es8311_handle_t es8311_create(i2c_port_t port, uint8_t dev_addr);

/**
 * @brief 初始化ES8311
 */
esp_err_t es8311_init(es8311_handle_t handle, const es8311_clock_config_t *clk_cfg,
                      es8311_resolution_t res_in, es8311_resolution_t res_out);

/**
 * @brief 配置采样频率
 */
esp_err_t es8311_sample_frequency_config(es8311_handle_t handle, uint32_t mclk_freq, uint32_t sample_freq);

/**
 * @brief 设置音量 (0-100)
 */
esp_err_t es8311_voice_volume_set(es8311_handle_t handle, uint8_t volume, int *volume_set);

/**
 * @brief 获取音量
 */
esp_err_t es8311_voice_volume_get(es8311_handle_t handle, uint8_t *volume);

/**
 * @brief 配置麦克风
 */
esp_err_t es8311_microphone_config(es8311_handle_t handle, bool digital_mic);

/**
 * @brief 设置麦克风增益
 */
esp_err_t es8311_microphone_gain_set(es8311_handle_t handle, uint8_t gain);

/**
 * @brief 静音控制
 */
esp_err_t es8311_mute(es8311_handle_t handle, bool enable);

/**
 * @brief 销毁ES8311句柄
 */
esp_err_t es8311_delete(es8311_handle_t handle);

#ifdef __cplusplus
}
#endif

#endif
