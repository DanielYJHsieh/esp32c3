/*
 * GDEQ0426T82 E-Paper Display Driver Implementation
 * 
 * 版本: v1.0
 * 日期: 2025-10-27
 */

#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "epaper_driver.h"
#include "font.h"

static const char *TAG = "EPaper";

// ============================================
// GPIO 控制函數
// ============================================

/**
 * 初始化控制 GPIO
 */
static void epaper_gpio_init(void)
{
    // DC pin (Data/Command)
    gpio_reset_pin(PIN_DC);
    gpio_set_direction(PIN_DC, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_DC, 0);
    
    // RST pin (Reset)
    gpio_reset_pin(PIN_RST);
    gpio_set_direction(PIN_RST, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_RST, 1);
    
    // BUSY pin (Busy status)
    gpio_reset_pin(PIN_BUSY);
    gpio_set_direction(PIN_BUSY, GPIO_MODE_INPUT);
    gpio_set_pull_mode(PIN_BUSY, GPIO_PULLUP_ONLY);
    
    ESP_LOGI(TAG, "GPIO initialized: DC=%d, RST=%d, BUSY=%d", PIN_DC, PIN_RST, PIN_BUSY);
}

/**
 * 硬體重置
 */
void epaper_reset(void)
{
    gpio_set_level(PIN_RST, 0);
    vTaskDelay(pdMS_TO_TICKS(20));
    gpio_set_level(PIN_RST, 1);
    vTaskDelay(pdMS_TO_TICKS(20));
    ESP_LOGI(TAG, "Hardware reset completed");
}

/**
 * 等待 BUSY 信號變為低電平 (空閒)
 */
void epaper_wait_busy(void)
{
    ESP_LOGI(TAG, "Waiting for display ready...");
    uint32_t timeout = 0;
    const uint32_t max_timeout = 300;  // 3 秒超時 (適合部分更新)
    
    while (gpio_get_level(PIN_BUSY) == 1) {
        vTaskDelay(pdMS_TO_TICKS(10));
        timeout++;
        if (timeout > max_timeout) {
            ESP_LOGW(TAG, "BUSY timeout after %d ms! Display may not respond.", timeout * 10);
            break;
        }
    }
    
    if (timeout < max_timeout) {
        ESP_LOGI(TAG, "Display ready (waited %d ms)", timeout * 10);
    }
}

// ============================================
// SPI 通訊函數
// ============================================

/**
 * 發送命令
 */
void epaper_send_command(epaper_t *epaper, uint8_t cmd)
{
    gpio_set_level(PIN_DC, 0);  // Command mode
    
    spi_transaction_t t = {
        .length = 8,
        .tx_buffer = &cmd,
        .rx_buffer = NULL
    };
    
    esp_err_t ret = spi_device_transmit(epaper->spi, &t);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SPI command send failed: %s", esp_err_to_name(ret));
    }
}

/**
 * 發送單個資料位元組
 */
void epaper_send_data(epaper_t *epaper, uint8_t data)
{
    gpio_set_level(PIN_DC, 1);  // Data mode
    
    spi_transaction_t t = {
        .length = 8,
        .tx_buffer = &data,
        .rx_buffer = NULL
    };
    
    esp_err_t ret = spi_device_transmit(epaper->spi, &t);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SPI data send failed: %s", esp_err_to_name(ret));
    }
}

/**
 * 批量發送資料
 */
void epaper_send_data_bulk(epaper_t *epaper, const uint8_t *data, size_t len)
{
    if (len == 0) return;
    
    gpio_set_level(PIN_DC, 1);  // Data mode
    
    // 分批發送，每次最多 4KB
    const size_t chunk_size = 4096;
    size_t offset = 0;
    
    while (offset < len) {
        size_t current_len = (len - offset > chunk_size) ? chunk_size : (len - offset);
        
        spi_transaction_t t = {
            .length = current_len * 8,
            .tx_buffer = data + offset,
            .rx_buffer = NULL
        };
        
        esp_err_t ret = spi_device_transmit(epaper->spi, &t);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "SPI bulk data send failed at offset %d: %s", offset, esp_err_to_name(ret));
            return;
        }
        
        offset += current_len;
    }
}

// ============================================
// 初始化和控制函數
// ============================================

/**
 * 初始化 E-Paper 顯示器
 */
esp_err_t epaper_init(epaper_t *epaper)
{
    if (epaper == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    ESP_LOGI(TAG, "Initializing GDEQ0426T82 E-Paper Display (800x480)");
    
    // 初始化 GPIO
    epaper_gpio_init();
    
    // 配置 SPI 匯流排
    spi_bus_config_t buscfg = {
        .mosi_io_num = PIN_MOSI,
        .miso_io_num = PIN_MISO,
        .sclk_io_num = PIN_SCLK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 4096
    };
    
    esp_err_t ret = spi_bus_initialize(SPI_HOST_ID, &buscfg, SPI_DMA_CH_AUTO);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SPI bus initialization failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    // 配置 SPI 設備
    spi_device_interface_config_t devcfg = {
        .clock_speed_hz = SPI_CLOCK_SPEED,
        .mode = 0,
        .spics_io_num = PIN_CS,
        .queue_size = 7,
        .flags = 0,
        .pre_cb = NULL
    };
    
    ret = spi_bus_add_device(SPI_HOST_ID, &devcfg, &epaper->spi);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SPI device add failed: %s", esp_err_to_name(ret));
        spi_bus_free(SPI_HOST_ID);
        return ret;
    }
    
    // 分配 framebuffer
    epaper->framebuffer = (uint8_t *)heap_caps_malloc(EPAPER_BUFFER_SIZE, MALLOC_CAP_8BIT);
    if (epaper->framebuffer == NULL) {
        ESP_LOGE(TAG, "Failed to allocate framebuffer (%d bytes)", EPAPER_BUFFER_SIZE);
        spi_bus_remove_device(epaper->spi);
        spi_bus_free(SPI_HOST_ID);
        return ESP_ERR_NO_MEM;
    }
    
    ESP_LOGI(TAG, "Framebuffer allocated: %d bytes", EPAPER_BUFFER_SIZE);
    memset(epaper->framebuffer, 0xFF, EPAPER_BUFFER_SIZE);  // 初始化為白色
    
    // 硬體重置
    epaper_reset();
    vTaskDelay(pdMS_TO_TICKS(10));
    
    // 初始化顯示器設定 (參考 GxEPD2_426_GDEQ0426T82)
    ESP_LOGI(TAG, "Configuring display settings...");
    
    // Software reset
    epaper_send_command(epaper, 0x12);  // SWRESET
    vTaskDelay(pdMS_TO_TICKS(10));
    
    // Temperature sensor control
    epaper_send_command(epaper, 0x18);
    epaper_send_data(epaper, 0x80);
    
    // Boost soft start configuration
    epaper_send_command(epaper, 0x0C);
    epaper_send_data(epaper, 0xAE);
    epaper_send_data(epaper, 0xC7);
    epaper_send_data(epaper, 0xC3);
    epaper_send_data(epaper, 0xC0);
    epaper_send_data(epaper, 0x80);
    
    // Driver output control (gates)
    epaper_send_command(epaper, 0x01);
    epaper_send_data(epaper, (EPAPER_HEIGHT - 1) % 256);      // A0-A7
    epaper_send_data(epaper, (EPAPER_HEIGHT - 1) / 256);      // A8-A9
    epaper_send_data(epaper, 0x02);                           // SM (interlaced)
    
    // Border waveform control
    epaper_send_command(epaper, 0x3C);
    epaper_send_data(epaper, 0x01);
    
    // Set initial RAM area (full screen)
    // Data entry mode: X increment, Y decrement (reversed)
    epaper_send_command(epaper, 0x11);
    epaper_send_data(epaper, 0x01);
    
    // Set X range [0, WIDTH-1]
    epaper_send_command(epaper, 0x44);
    epaper_send_data(epaper, 0);
    epaper_send_data(epaper, 0);
    epaper_send_data(epaper, (EPAPER_WIDTH - 1) % 256);
    epaper_send_data(epaper, (EPAPER_WIDTH - 1) / 256);
    
    // Set Y range [HEIGHT-1, 0] (reversed)
    epaper_send_command(epaper, 0x45);
    epaper_send_data(epaper, (EPAPER_HEIGHT - 1) % 256);
    epaper_send_data(epaper, (EPAPER_HEIGHT - 1) / 256);
    epaper_send_data(epaper, 0);
    epaper_send_data(epaper, 0);
    
    // Set X counter
    epaper_send_command(epaper, 0x4E);
    epaper_send_data(epaper, 0);
    epaper_send_data(epaper, 0);
    
    // Set Y counter
    epaper_send_command(epaper, 0x4F);
    epaper_send_data(epaper, (EPAPER_HEIGHT - 1) % 256);
    epaper_send_data(epaper, (EPAPER_HEIGHT - 1) / 256);
    
    epaper->initialized = true;
    ESP_LOGI(TAG, "E-Paper initialization completed successfully");
    
    return ESP_OK;
}

/**
 * 反初始化 E-Paper
 */
esp_err_t epaper_deinit(epaper_t *epaper)
{
    if (epaper == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    if (epaper->framebuffer != NULL) {
        free(epaper->framebuffer);
        epaper->framebuffer = NULL;
    }
    
    spi_bus_remove_device(epaper->spi);
    spi_bus_free(SPI_HOST_ID);
    
    epaper->initialized = false;
    ESP_LOGI(TAG, "E-Paper deinitialized");
    
    return ESP_OK;
}

/**
 * 進入深度睡眠模式
 */
void epaper_sleep(epaper_t *epaper)
{
    epaper_send_command(epaper, CMD_DEEP_SLEEP);
    epaper_send_data(epaper, 0xA5);
    ESP_LOGI(TAG, "E-Paper entering deep sleep mode");
}

// ============================================
// Framebuffer 操作函數
// ============================================

/**
 * 設定單個像素
 */
void epaper_set_pixel(epaper_t *epaper, uint16_t x, uint16_t y, uint8_t color)
{
    if (x >= EPAPER_WIDTH || y >= EPAPER_HEIGHT) {
        return;
    }
    
    uint32_t addr = (y * EPAPER_WIDTH + x) / 8;
    uint8_t bit = 7 - (x % 8);
    
    if (color == COLOR_BLACK) {
        epaper->framebuffer[addr] &= ~(1 << bit);
    } else {
        epaper->framebuffer[addr] |= (1 << bit);
    }
}

/**
 * 取得單個像素
 */
uint8_t epaper_get_pixel(epaper_t *epaper, uint16_t x, uint16_t y)
{
    if (x >= EPAPER_WIDTH || y >= EPAPER_HEIGHT) {
        return COLOR_WHITE;
    }
    
    uint32_t addr = (y * EPAPER_WIDTH + x) / 8;
    uint8_t bit = 7 - (x % 8);
    
    return (epaper->framebuffer[addr] & (1 << bit)) ? COLOR_WHITE : COLOR_BLACK;
}

/**
 * 填充矩形區域
 */
void epaper_fill_rect(epaper_t *epaper, uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t color)
{
    for (uint16_t j = 0; j < h; j++) {
        for (uint16_t i = 0; i < w; i++) {
            epaper_set_pixel(epaper, x + i, y + j, color);
        }
    }
}

/**
 * 繪製矩形邊框
 */
void epaper_draw_rect(epaper_t *epaper, uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t color)
{
    // 上下邊
    for (uint16_t i = 0; i < w; i++) {
        epaper_set_pixel(epaper, x + i, y, color);
        epaper_set_pixel(epaper, x + i, y + h - 1, color);
    }
    
    // 左右邊
    for (uint16_t j = 0; j < h; j++) {
        epaper_set_pixel(epaper, x, y + j, color);
        epaper_set_pixel(epaper, x + w - 1, y + j, color);
    }
}

// ============================================
// 顯示更新函數
// ============================================

/**
 * 清除螢幕
 */
void epaper_clear_screen(epaper_t *epaper, uint8_t color)
{
    memset(epaper->framebuffer, color, EPAPER_BUFFER_SIZE);
}

/**
 * 全螢幕更新 (參考 GxEPD2)
 */
void epaper_display_full(epaper_t *epaper)
{
    ESP_LOGI(TAG, "Starting full display update...");
    
    // Write to "previous" buffer (0x26)
    epaper_send_command(epaper, 0x26);
    epaper_send_data_bulk(epaper, epaper->framebuffer, EPAPER_BUFFER_SIZE);
    
    // Write to "current" buffer (0x24)
    epaper_send_command(epaper, 0x24);
    epaper_send_data_bulk(epaper, epaper->framebuffer, EPAPER_BUFFER_SIZE);
    
    // Power on and update
    epaper_send_command(epaper, 0x21);  // Display Update Control
    epaper_send_data(epaper, 0x40);     // Bypass RED as 0
    epaper_send_data(epaper, 0x00);     // Single chip application
    
    // Use fast update if available
    epaper_send_command(epaper, 0x1A);  // Write to temperature register
    epaper_send_data(epaper, 0x5A);     // Fast update temperature
    
    epaper_send_command(epaper, 0x22);  // Display Update Sequence
    epaper_send_data(epaper, 0xd7);     // Fast refresh sequence
    
    epaper_send_command(epaper, 0x20);  // Master Activation
    vTaskDelay(pdMS_TO_TICKS(100));
    
    epaper_wait_busy();
    ESP_LOGI(TAG, "Full display update completed");
}

/**
 * 部分更新 (參考 GxEPD2)
 */
void epaper_display_partial(epaper_t *epaper, uint16_t x, uint16_t y, uint16_t w, uint16_t h)
{
    ESP_LOGI(TAG, "Starting partial update: x=%d, y=%d, w=%d, h=%d", x, y, w, h);
    
    // Make x, w multiple of 8 (byte boundary)
    w += x % 8;
    x -= x % 8;
    w = (w + 7) & ~7;
    
    // Limit to screen bounds
    if (x >= EPAPER_WIDTH || y >= EPAPER_HEIGHT) return;
    if (x + w > EPAPER_WIDTH) w = EPAPER_WIDTH - x;
    if (y + h > EPAPER_HEIGHT) h = EPAPER_HEIGHT - y;
    
    // Set partial RAM area (Y reversed for this display)
    uint16_t y_reversed = EPAPER_HEIGHT - y - h;
    
    // Data entry mode: X increment, Y decrement (reversed)
    epaper_send_command(epaper, 0x11);
    epaper_send_data(epaper, 0x01);
    
    // Set X range
    epaper_send_command(epaper, 0x44);
    epaper_send_data(epaper, x % 256);
    epaper_send_data(epaper, x / 256);
    epaper_send_data(epaper, (x + w - 1) % 256);
    epaper_send_data(epaper, (x + w - 1) / 256);
    
    // Set Y range (reversed)
    epaper_send_command(epaper, 0x45);
    epaper_send_data(epaper, (y_reversed + h - 1) % 256);
    epaper_send_data(epaper, (y_reversed + h - 1) / 256);
    epaper_send_data(epaper, y_reversed % 256);
    epaper_send_data(epaper, y_reversed / 256);
    
    // Set X counter
    epaper_send_command(epaper, 0x4E);
    epaper_send_data(epaper, x % 256);
    epaper_send_data(epaper, x / 256);
    
    // Set Y counter (reversed)
    epaper_send_command(epaper, 0x4F);
    epaper_send_data(epaper, (y_reversed + h - 1) % 256);
    epaper_send_data(epaper, (y_reversed + h - 1) / 256);
    
    // Write data to BOTH previous buffer (0x26) and current buffer (0x24)
    // This prevents ghosting from old data in the previous buffer
    
    // Write to previous buffer first
    epaper_send_command(epaper, 0x26);
    for (uint16_t j = 0; j < h; j++) {
        uint16_t row = y + j;
        uint16_t start_byte = (row * EPAPER_WIDTH + x) / 8;
        uint16_t byte_count = w / 8;
        epaper_send_data_bulk(epaper, &epaper->framebuffer[start_byte], byte_count);
    }
    
    // Reset counters for current buffer write
    epaper_send_command(epaper, 0x4E);
    epaper_send_data(epaper, x % 256);
    epaper_send_data(epaper, x / 256);
    
    epaper_send_command(epaper, 0x4F);
    epaper_send_data(epaper, (y_reversed + h - 1) % 256);
    epaper_send_data(epaper, (y_reversed + h - 1) / 256);
    
    // Write to current buffer (0x24)
    epaper_send_command(epaper, 0x24);
    
    // Send partial region data
    for (uint16_t j = 0; j < h; j++) {
        uint16_t row = y + j;
        uint16_t start_byte = (row * EPAPER_WIDTH + x) / 8;
        uint16_t byte_count = w / 8;
        epaper_send_data_bulk(epaper, &epaper->framebuffer[start_byte], byte_count);
    }
    
    // Power on and partial update
    epaper_send_command(epaper, 0x21);  // Display Update Control
    epaper_send_data(epaper, 0x00);     // RED normal
    epaper_send_data(epaper, 0x00);     // Single chip application
    
    epaper_send_command(epaper, 0x22);  // Display Update Sequence
    epaper_send_data(epaper, 0xfc);     // Partial update sequence
    
    epaper_send_command(epaper, 0x20);  // Master Activation
    vTaskDelay(pdMS_TO_TICKS(100));
    
    epaper_wait_busy();
    
    ESP_LOGI(TAG, "Partial update completed");
}

// ============================================
// 文字繪製函數
// ============================================

/**
 * 繪製 8x16 ASCII 字符
 */
void epaper_draw_char_8x16(epaper_t *epaper, uint16_t x, uint16_t y, char c, uint8_t color)
{
    if (x + 8 > EPAPER_WIDTH || y + 16 > EPAPER_HEIGHT) {
        return;
    }
    
    // 使用新的字體 API
    const uint8_t *font_data = get_ascii_font(c);
    
    for (int row = 0; row < 16; row++) {
        uint8_t line = font_data[row];
        for (int col = 0; col < 8; col++) {
            if (line & (0x80 >> col)) {
                epaper_set_pixel(epaper, x + col, y + row, color);
            }
        }
    }
}

/**
 * 繪製 16x16 中文字符
 */
void epaper_draw_chinese_16x16(epaper_t *epaper, uint16_t x, uint16_t y, const char *utf8_char, uint8_t color)
{
    if (x + 16 > EPAPER_WIDTH || y + 16 > EPAPER_HEIGHT) {
        return;
    }
    
    const uint8_t *font_data = get_chinese_font(utf8_char);
    if (font_data == NULL) {
        ESP_LOGI(TAG, "Chinese char not found");
        return; // 字符不存在
    }
    
    ESP_LOGI(TAG, "Drawing Chinese char at (%d,%d)", x, y);
    
    for (int row = 0; row < 16; row++) {
        uint8_t byte1 = font_data[row * 2];
        uint8_t byte2 = font_data[row * 2 + 1];
        
        if (row < 3) {  // 只輸出前3行作為範例
            ESP_LOGI(TAG, "  Row %d: 0x%02X 0x%02X", row, byte1, byte2);
        }
        
        // 處理高字節 (前 8 位)
        for (int col = 0; col < 8; col++) {
            if (byte1 & (0x80 >> col)) {
                epaper_set_pixel(epaper, x + col, y + row, color);
            }
        }
        
        // 處理低字節 (後 8 位)
        for (int col = 0; col < 8; col++) {
            if (byte2 & (0x80 >> col)) {
                epaper_set_pixel(epaper, x + 8 + col, y + row, color);
            }
        }
    }
}

/**
 * 繪製混合字符串 (支持 ASCII 和中文)
 */
void epaper_draw_string(epaper_t *epaper, uint16_t x, uint16_t y, const char *str, uint8_t color)
{
    uint16_t cursor_x = x;
    const char *p = str;
    
    while (*p != '\0') {
        if ((uint8_t)*p < 0x80) {
            // ASCII 字符
            epaper_draw_char_8x16(epaper, cursor_x, y, *p, color);
            cursor_x += 8;
            p++;
        } else {
            // UTF-8 中文字符 (3 字節)
            epaper_draw_chinese_16x16(epaper, cursor_x, y, p, color);
            cursor_x += 16;
            p += 3; // 跳過 3 個字節
        }
    }
}

