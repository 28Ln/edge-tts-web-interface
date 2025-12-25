#include "es8311.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdlib.h>
#include <string.h>

static const char *TAG = "ES8311";

/* ES8311寄存器地址 */
#define ES8311_RESET_REG00             0x00
#define ES8311_CLK_MANAGER_REG01       0x01
#define ES8311_CLK_MANAGER_REG02       0x02
#define ES8311_CLK_MANAGER_REG03       0x03
#define ES8311_CLK_MANAGER_REG04       0x04
#define ES8311_CLK_MANAGER_REG05       0x05
#define ES8311_CLK_MANAGER_REG06       0x06
#define ES8311_CLK_MANAGER_REG07       0x07
#define ES8311_CLK_MANAGER_REG08       0x08
#define ES8311_SDPIN_REG09             0x09
#define ES8311_SDPOUT_REG0A            0x0A
#define ES8311_SYSTEM_REG0B            0x0B
#define ES8311_SYSTEM_REG0C            0x0C
#define ES8311_SYSTEM_REG0D            0x0D
#define ES8311_SYSTEM_REG0E            0x0E
#define ES8311_SYSTEM_REG0F            0x0F
#define ES8311_SYSTEM_REG10            0x10
#define ES8311_SYSTEM_REG11            0x11
#define ES8311_SYSTEM_REG12            0x12
#define ES8311_SYSTEM_REG13            0x13
#define ES8311_SYSTEM_REG14            0x14
#define ES8311_ADC_REG15               0x15
#define ES8311_ADC_REG16               0x16
#define ES8311_ADC_REG17               0x17
#define ES8311_ADC_REG18               0x18
#define ES8311_ADC_REG19               0x19
#define ES8311_ADC_REG1A               0x1A
#define ES8311_ADC_REG1B               0x1B
#define ES8311_ADC_REG1C               0x1C
#define ES8311_DAC_REG31               0x31
#define ES8311_DAC_REG32               0x32
#define ES8311_DAC_REG33               0x33
#define ES8311_DAC_REG34               0x34
#define ES8311_DAC_REG35               0x35
#define ES8311_DAC_REG37               0x37
#define ES8311_GPIO_REG44              0x44
#define ES8311_GP_REG45                0x45
#define ES8311_CHD1_REGFD              0xFD
#define ES8311_CHD2_REGFE              0xFE
#define ES8311_CHVER_REGFF             0xFF

/* ES8311设备结构体 */
typedef struct {
    i2c_port_t i2c_port;
    uint8_t dev_addr;
} es8311_dev_t;

/* 写寄存器 */
static esp_err_t es8311_write_reg(es8311_dev_t *dev, uint8_t reg_addr, uint8_t data)
{
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (dev->dev_addr << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, reg_addr, true);
    i2c_master_write_byte(cmd, data, true);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(dev->i2c_port, cmd, 1000 / portTICK_PERIOD_MS);
    i2c_cmd_link_delete(cmd);
    return ret;
}

/* 读寄存器 */
static esp_err_t es8311_read_reg(es8311_dev_t *dev, uint8_t reg_addr, uint8_t *data)
{
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (dev->dev_addr << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, reg_addr, true);
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (dev->dev_addr << 1) | I2C_MASTER_READ, true);
    i2c_master_read_byte(cmd, data, I2C_MASTER_NACK);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(dev->i2c_port, cmd, 1000 / portTICK_PERIOD_MS);
    i2c_cmd_link_delete(cmd);
    return ret;
}

es8311_handle_t es8311_create(i2c_port_t port, uint8_t dev_addr)
{
    es8311_dev_t *dev = (es8311_dev_t *)malloc(sizeof(es8311_dev_t));
    if (dev == NULL) {
        ESP_LOGE(TAG, "Failed to allocate memory for ES8311");
        return NULL;
    }
    dev->i2c_port = port;
    dev->dev_addr = dev_addr;
    
    // 验证设备存在
    uint8_t chip_id = 0;
    if (es8311_read_reg(dev, ES8311_CHD1_REGFD, &chip_id) != ESP_OK) {
        ESP_LOGW(TAG, "ES8311 not found at address 0x%02X, but continuing...", dev_addr);
    } else {
        ESP_LOGI(TAG, "ES8311 found, chip ID: 0x%02X", chip_id);
    }
    
    return (es8311_handle_t)dev;
}

esp_err_t es8311_init(es8311_handle_t handle, const es8311_clock_config_t *clk_cfg,
                      es8311_resolution_t res_in, es8311_resolution_t res_out)
{
    if (handle == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    es8311_dev_t *dev = (es8311_dev_t *)handle;
    esp_err_t ret = ESP_OK;
    
    ESP_LOGI(TAG, "Initializing ES8311 codec");
    
    // 软复位
    ret |= es8311_write_reg(dev, ES8311_RESET_REG00, 0x1F);
    vTaskDelay(20 / portTICK_PERIOD_MS);
    ret |= es8311_write_reg(dev, ES8311_RESET_REG00, 0x80);
    
    // 时钟配置
    ret |= es8311_write_reg(dev, ES8311_CLK_MANAGER_REG01, 0x3F);
    
    uint8_t reg02 = 0x00;
    if (clk_cfg->mclk_inverted) reg02 |= 0x01;
    if (clk_cfg->sclk_inverted) reg02 |= 0x02;
    ret |= es8311_write_reg(dev, ES8311_CLK_MANAGER_REG02, reg02);
    
    // MCLK分频配置
    ret |= es8311_write_reg(dev, ES8311_CLK_MANAGER_REG03, 0x10);
    ret |= es8311_write_reg(dev, ES8311_CLK_MANAGER_REG04, 0x10);
    ret |= es8311_write_reg(dev, ES8311_CLK_MANAGER_REG05, 0x00);
    ret |= es8311_write_reg(dev, ES8311_CLK_MANAGER_REG06, 0x03);
    ret |= es8311_write_reg(dev, ES8311_CLK_MANAGER_REG07, 0x00);
    ret |= es8311_write_reg(dev, ES8311_CLK_MANAGER_REG08, 0xFF);
    
    // SDP配置 (I2S格式)
    uint8_t sdp_in = 0x0C;  // 16bit, I2S
    uint8_t sdp_out = 0x0C; // 16bit, I2S
    ret |= es8311_write_reg(dev, ES8311_SDPIN_REG09, sdp_in);
    ret |= es8311_write_reg(dev, ES8311_SDPOUT_REG0A, sdp_out);
    
    // 系统配置
    ret |= es8311_write_reg(dev, ES8311_SYSTEM_REG0B, 0x00);
    ret |= es8311_write_reg(dev, ES8311_SYSTEM_REG0C, 0x00);
    ret |= es8311_write_reg(dev, ES8311_SYSTEM_REG0D, 0x01);
    ret |= es8311_write_reg(dev, ES8311_SYSTEM_REG0E, 0x02);
    ret |= es8311_write_reg(dev, ES8311_SYSTEM_REG0F, 0x44);
    ret |= es8311_write_reg(dev, ES8311_SYSTEM_REG10, 0x0A);
    ret |= es8311_write_reg(dev, ES8311_SYSTEM_REG11, 0x00);
    ret |= es8311_write_reg(dev, ES8311_SYSTEM_REG12, 0x02);
    ret |= es8311_write_reg(dev, ES8311_SYSTEM_REG13, 0x00);
    ret |= es8311_write_reg(dev, ES8311_SYSTEM_REG14, 0x1A);
    
    // ADC配置
    ret |= es8311_write_reg(dev, ES8311_ADC_REG15, 0x00);
    ret |= es8311_write_reg(dev, ES8311_ADC_REG16, 0x24);
    ret |= es8311_write_reg(dev, ES8311_ADC_REG17, 0xC8);
    ret |= es8311_write_reg(dev, ES8311_ADC_REG18, 0x00);
    ret |= es8311_write_reg(dev, ES8311_ADC_REG19, 0x33);
    ret |= es8311_write_reg(dev, ES8311_ADC_REG1A, 0x00);
    ret |= es8311_write_reg(dev, ES8311_ADC_REG1B, 0x00);
    ret |= es8311_write_reg(dev, ES8311_ADC_REG1C, 0x08);
    
    // DAC配置
    ret |= es8311_write_reg(dev, ES8311_DAC_REG31, 0x00);
    ret |= es8311_write_reg(dev, ES8311_DAC_REG32, 0xBF); // 默认音量
    ret |= es8311_write_reg(dev, ES8311_DAC_REG33, 0x00);
    ret |= es8311_write_reg(dev, ES8311_DAC_REG34, 0x00);
    ret |= es8311_write_reg(dev, ES8311_DAC_REG35, 0x00);
    ret |= es8311_write_reg(dev, ES8311_DAC_REG37, 0x00);
    
    // GPIO配置
    ret |= es8311_write_reg(dev, ES8311_GPIO_REG44, 0x00);
    ret |= es8311_write_reg(dev, ES8311_GP_REG45, 0x00);
    
    // 启动
    ret |= es8311_write_reg(dev, ES8311_RESET_REG00, 0x80);
    
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "ES8311 codec initialized successfully");
    } else {
        ESP_LOGE(TAG, "ES8311 codec initialization failed");
    }
    
    return ret;
}

esp_err_t es8311_sample_frequency_config(es8311_handle_t handle, uint32_t mclk_freq, uint32_t sample_freq)
{
    if (handle == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    // 简化实现：假设使用标准配置
    ESP_LOGI(TAG, "Sample frequency config: MCLK=%lu, Sample=%lu", mclk_freq, sample_freq);
    return ESP_OK;
}

esp_err_t es8311_voice_volume_set(es8311_handle_t handle, uint8_t volume, int *volume_set)
{
    if (handle == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    es8311_dev_t *dev = (es8311_dev_t *)handle;
    
    if (volume > 100) volume = 100;
    
    // 将0-100映射到0-255
    uint8_t reg_val = (volume * 255) / 100;
    
    esp_err_t ret = es8311_write_reg(dev, ES8311_DAC_REG32, reg_val);
    
    if (volume_set) {
        *volume_set = volume;
    }
    
    ESP_LOGI(TAG, "Volume set to %d%% (reg=0x%02X)", volume, reg_val);
    return ret;
}

esp_err_t es8311_voice_volume_get(es8311_handle_t handle, uint8_t *volume)
{
    if (handle == NULL || volume == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    es8311_dev_t *dev = (es8311_dev_t *)handle;
    uint8_t reg_val = 0;
    
    esp_err_t ret = es8311_read_reg(dev, ES8311_DAC_REG32, &reg_val);
    if (ret == ESP_OK) {
        *volume = (reg_val * 100) / 255;
    }
    
    return ret;
}

esp_err_t es8311_microphone_config(es8311_handle_t handle, bool digital_mic)
{
    if (handle == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    es8311_dev_t *dev = (es8311_dev_t *)handle;
    
    uint8_t reg_val = digital_mic ? 0x40 : 0x00;
    return es8311_write_reg(dev, ES8311_ADC_REG15, reg_val);
}

esp_err_t es8311_microphone_gain_set(es8311_handle_t handle, uint8_t gain)
{
    if (handle == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    es8311_dev_t *dev = (es8311_dev_t *)handle;
    
    // 增益范围 0-10
    if (gain > 10) gain = 10;
    
    return es8311_write_reg(dev, ES8311_ADC_REG16, gain | 0x20);
}

esp_err_t es8311_mute(es8311_handle_t handle, bool enable)
{
    if (handle == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    es8311_dev_t *dev = (es8311_dev_t *)handle;
    
    uint8_t reg_val = enable ? 0x60 : 0x00;
    return es8311_write_reg(dev, ES8311_DAC_REG31, reg_val);
}

esp_err_t es8311_delete(es8311_handle_t handle)
{
    if (handle == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    free(handle);
    return ESP_OK;
}
