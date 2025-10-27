/*
 * ESP32-C3 SPI E-Paper Display 主程式
 * 
 * 功能：
 * - 初始化 GDEQ0426T82 E-Paper 顯示器 (800x480)
 * - 測試 1: 白屏清除
 * - 測試 2: 部分更新 (400x120 矩形)
 * - 測試 3: 中央部分更新 (500x240 矩形)
 * 
 * 硬體需求：
 * - ESP32-C3 開發板
 * - GDEQ0426T82 4.26" E-Paper 顯示器
 * 
 * 版本：v1.0
 * 日期：2025-10-27
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "epaper_driver.h"

static const char *TAG = "Main";
static epaper_t epaper = {0};

// ============================================
// 啟動畫面
// ============================================

static void show_startup_screen(void)
{
    printf("\n");
    printf("########################################\n");
    printf("#                                      #\n");
    printf("#  ESP32-C3 E-Paper 顯示程式           #\n");
    printf("#  GDEQ0426T82 (800x480)               #\n");
    printf("#                                      #\n");
    printf("########################################\n");
    printf("\n");
    printf("版本: v1.0\n");
    printf("顯示器: GDEQ0426T82 4.26\" 800x480\n");
    printf("\n");
    printf("SPI 腳位配置:\n");
    printf("  SCLK : GPIO %d\n", PIN_SCLK);
    printf("  MOSI : GPIO %d\n", PIN_MOSI);
    printf("  CS   : GPIO %d\n", PIN_CS);
    printf("  DC   : GPIO %d\n", PIN_DC);
    printf("  RST  : GPIO %d\n", PIN_RST);
    printf("  BUSY : GPIO %d\n", PIN_BUSY);
    printf("\n");
    printf("測試項目:\n");
    printf("  1. 白屏清除測試\n");
    printf("  2. 網格全屏測試\n");
    printf("  3. 部分更新測試 (400x120)\n");
    printf("  4. 中央部分更新測試 (500x240)\n");
    printf("\n");
}

// ============================================
// 測試功能
// ============================================

/**
 * 測試 1: 白屏清除
 * 清除整個螢幕為白色
 */
static void test_clear_screen(void)
{
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "測試 1: 白屏清除");
    ESP_LOGI(TAG, "========================================");
    
    // 清除 framebuffer 為白色
    epaper_clear_screen(&epaper, COLOR_WHITE);
    
    // 全螢幕更新
    epaper_display_full(&epaper);
    
    ESP_LOGI(TAG, "白屏清除完成");
    ESP_LOGI(TAG, "");
    
    vTaskDelay(pdMS_TO_TICKS(2000));
}

/**
 * 測試 2: 網格全屏測試
 * 繪製覆蓋整個螢幕的網格圖案
 */
static void test_grid_pattern(void)
{
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "測試 2: 網格全屏測試");
    ESP_LOGI(TAG, "========================================");
    
    // 清除 framebuffer
    epaper_clear_screen(&epaper, COLOR_WHITE);
    
    // 網格參數
    const uint16_t grid_spacing = 50;  // 網格間距 50 像素
    
    ESP_LOGI(TAG, "繪製網格圖案 (間距=%d像素)", grid_spacing);
    
    // 繪製垂直線
    for (uint16_t x = 0; x < EPAPER_WIDTH; x += grid_spacing) {
        for (uint16_t y = 0; y < EPAPER_HEIGHT; y++) {
            epaper_set_pixel(&epaper, x, y, COLOR_BLACK);
        }
    }
    
    // 繪製水平線
    for (uint16_t y = 0; y < EPAPER_HEIGHT; y += grid_spacing) {
        for (uint16_t x = 0; x < EPAPER_WIDTH; x++) {
            epaper_set_pixel(&epaper, x, y, COLOR_BLACK);
        }
    }
    
    // 繪製外框 (加粗邊框)
    epaper_draw_rect(&epaper, 0, 0, EPAPER_WIDTH, EPAPER_HEIGHT, COLOR_BLACK);
    epaper_draw_rect(&epaper, 1, 1, EPAPER_WIDTH - 2, EPAPER_HEIGHT - 2, COLOR_BLACK);
    epaper_draw_rect(&epaper, 2, 2, EPAPER_WIDTH - 4, EPAPER_HEIGHT - 4, COLOR_BLACK);
    
    // 在四個角落繪製標記
    epaper_fill_rect(&epaper, 10, 10, 30, 30, COLOR_BLACK);
    epaper_fill_rect(&epaper, EPAPER_WIDTH - 40, 10, 30, 30, COLOR_BLACK);
    epaper_fill_rect(&epaper, 10, EPAPER_HEIGHT - 40, 30, 30, COLOR_BLACK);
    epaper_fill_rect(&epaper, EPAPER_WIDTH - 40, EPAPER_HEIGHT - 40, 30, 30, COLOR_BLACK);
    
    // 在中心繪製十字標記
    uint16_t center_x = EPAPER_WIDTH / 2;
    uint16_t center_y = EPAPER_HEIGHT / 2;
    epaper_draw_rect(&epaper, center_x - 50, center_y - 50, 100, 100, COLOR_BLACK);
    epaper_fill_rect(&epaper, center_x - 40, center_y - 5, 80, 10, COLOR_BLACK);
    epaper_fill_rect(&epaper, center_x - 5, center_y - 40, 10, 80, COLOR_BLACK);
    
    // 全螢幕更新顯示
    epaper_display_full(&epaper);
    
    ESP_LOGI(TAG, "網格全屏測試完成");
    ESP_LOGI(TAG, "");
    
    vTaskDelay(pdMS_TO_TICKS(3000));
}

/**
 * 測試 3: 部分更新
 * 在螢幕上繪製一個 400x120 的黑色矩形框
 */
static void test_partial_update(void)
{
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "測試 2: 部分更新 (400x120)");
    ESP_LOGI(TAG, "========================================");
    
    // 定義矩形位置 (左上角區域)
    uint16_t x = 50;
    uint16_t y = 50;
    uint16_t w = 400;
    uint16_t h = 120;
    
    ESP_LOGI(TAG, "繪製黑色矩形框: x=%d, y=%d, w=%d, h=%d", x, y, w, h);
    
    // 繪製矩形邊框 (黑色)
    epaper_draw_rect(&epaper, x, y, w, h, COLOR_BLACK);
    
    // 繪製內部填充 (白色，但邊框為黑色)
    epaper_fill_rect(&epaper, x + 5, y + 5, w - 10, h - 10, COLOR_WHITE);
    
    // 添加一些黑色填充區域作為視覺效果
    epaper_fill_rect(&epaper, x + 20, y + 20, 100, 30, COLOR_BLACK);
    epaper_fill_rect(&epaper, x + 20, y + 70, 200, 30, COLOR_BLACK);
    
    // 部分更新顯示
    epaper_display_partial(&epaper, x, y, w, h);
    
    ESP_LOGI(TAG, "部分更新完成");
    ESP_LOGI(TAG, "");
    
    vTaskDelay(pdMS_TO_TICKS(2000));
}

/**
 * 測試 4: 中央部分更新
 * 在螢幕中央繪製一個 500x240 的圖案
 */
static void test_partial_update_center(void)
{
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "測試 4: 中央部分更新 (500x240)");
    ESP_LOGI(TAG, "========================================");
    
    // 計算中央位置
    uint16_t w = 500;
    uint16_t h = 240;
    uint16_t x = (EPAPER_WIDTH - w) / 2;
    uint16_t y = (EPAPER_HEIGHT - h) / 2;
    
    ESP_LOGI(TAG, "繪製中央圖案: x=%d, y=%d, w=%d, h=%d", x, y, w, h);
    
    // 繪製外框 (黑色)
    epaper_draw_rect(&epaper, x, y, w, h, COLOR_BLACK);
    
    // 繪製內部白色背景
    epaper_fill_rect(&epaper, x + 3, y + 3, w - 6, h - 6, COLOR_WHITE);
    
    // 繪製一些裝飾性圖案
    // 上方黑色條紋
    epaper_fill_rect(&epaper, x + 10, y + 10, w - 20, 40, COLOR_BLACK);
    
    // 中央大型矩形
    epaper_draw_rect(&epaper, x + 50, y + 70, w - 100, h - 140, COLOR_BLACK);
    epaper_fill_rect(&epaper, x + 55, y + 75, w - 110, h - 150, COLOR_BLACK);
    
    // 底部文字區域 (白色矩形)
    epaper_fill_rect(&epaper, x + 20, y + h - 60, w - 40, 40, COLOR_WHITE);
    epaper_draw_rect(&epaper, x + 20, y + h - 60, w - 40, 40, COLOR_BLACK);
    
    // 添加一些小方塊作為裝飾
    for (int i = 0; i < 10; i++) {
        epaper_fill_rect(&epaper, x + 30 + i * 45, y + h - 50, 30, 20, COLOR_BLACK);
    }
    
    // 部分更新顯示
    epaper_display_partial(&epaper, x, y, w, h);
    
    ESP_LOGI(TAG, "中央部分更新完成");
    ESP_LOGI(TAG, "");
    
    vTaskDelay(pdMS_TO_TICKS(2000));
}

// ============================================
// 主程式
// ============================================

void app_main(void)
{
    // 顯示啟動畫面
    show_startup_screen();
    
    // 初始化 NVS (雖然這個專案不需要，但保持一致性)
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    
    // 初始化 E-Paper 顯示器
    ESP_LOGI(TAG, "Initializing E-Paper display...");
    ret = epaper_init(&epaper);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize E-Paper display: %s", esp_err_to_name(ret));
        ESP_LOGE(TAG, "System halted!");
        while (1) {
            vTaskDelay(pdMS_TO_TICKS(1000));
        }
    }
    
    ESP_LOGI(TAG, "E-Paper display initialized successfully!");
    ESP_LOGI(TAG, "");
    
    // 等待一下讓系統穩定
    vTaskDelay(pdMS_TO_TICKS(1000));
    
    // 執行測試序列
    ESP_LOGI(TAG, "開始執行測試序列...");
    ESP_LOGI(TAG, "");
    
    // 測試 1: 白屏清除
    test_clear_screen();
    
    // 測試 2: 網格全屏測試
    test_grid_pattern();
    
    // 測試 3: 部分更新 (400x120)
    test_partial_update();
    
    // 測試 4: 中央部分更新 (500x240)
    test_partial_update_center();
    
    // 所有測試完成
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "所有測試完成！");
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "");
    ESP_LOGI(TAG, "E-Paper 顯示器現在顯示測試圖案");
    ESP_LOGI(TAG, "系統將進入空閒狀態...");
    
    // 進入睡眠模式以節省電力
    vTaskDelay(pdMS_TO_TICKS(5000));
    epaper_sleep(&epaper);
    ESP_LOGI(TAG, "E-Paper 已進入深度睡眠模式");
    
    // 主循環 (空閒)
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(10000));
    }
}
