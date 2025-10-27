/*
 * ESP32-C3 WiFi LED 控制程式
 * 
 * 功能：
 * - 連接到現有 WiFi 網路
 * - 透過網頁介面控制 LED
 * - 客戶端連接時 LED 恆亮，斷線時閃爍
 * - 序列埠命令控制
 * 
 * 硬體需求：
 * - ESP32-C3 開發板
 * - LED 連接到 GPIO 8 (反向邏輯，LOW=亮)
 * 
 * 版本：v1.0
 * 日期：2025-10-26
 */

#include <stdio.h>
#include <string.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_http_server.h"
#include "esp_timer.h"
#include "nvs_flash.h"
#include "driver/gpio.h"

// ============================================
// 常數定義
// ============================================

#define LED_GPIO            8
#define WIFI_SSID           "lulumi_ap"
#define WIFI_PASS           "1978120505"
#define WIFI_MAXIMUM_RETRY  5

#define LED_ON_TIME         200    // LED 開啟時間 (ms)
#define LED_OFF_TIME        800    // LED 關閉時間 (ms)

// WiFi 事件標誌
#define WIFI_CONNECTED_BIT  BIT0
#define WIFI_FAIL_BIT       BIT1

// ============================================
// 全域變數
// ============================================

static const char *TAG = "WiFi_LED";
static EventGroupHandle_t s_wifi_event_group;
static int s_retry_num = 0;
static httpd_handle_t server = NULL;

// LED 控制變數
static bool led_state = false;
static bool manual_control = false;
static bool client_connected = false;
static uint32_t total_flashes = 0;
static uint32_t connection_count = 0;
static int64_t start_time = 0;

// ============================================
// LED 控制函數
// ============================================

/**
 * 初始化 LED GPIO
 */
static void led_init(void)
{
    gpio_reset_pin(LED_GPIO);
    gpio_set_direction(LED_GPIO, GPIO_MODE_OUTPUT);
    gpio_set_level(LED_GPIO, 1);  // 初始關閉 (反向邏輯)
    led_state = false;
    ESP_LOGI(TAG, "LED initialized on GPIO %d (inverted logic: LOW=ON)", LED_GPIO);
}

/**
 * 設定 LED 狀態
 */
static void led_set(bool on)
{
    gpio_set_level(LED_GPIO, on ? 0 : 1);  // 反向邏輯：LOW=亮
    led_state = on;
}

/**
 * LED 閃爍任務
 */
static void led_blink_task(void *arg)
{
    int64_t last_toggle = 0;
    bool blink_state = false;
    
    while (1) {
        if (manual_control) {
            // 手動控制模式，不自動改變
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        }
        
        if (client_connected) {
            // 客戶端已連接：LED 恆亮
            if (!led_state) {
                led_set(true);
                ESP_LOGI(TAG, "Client connected - LED ON (steady)");
            }
            vTaskDelay(pdMS_TO_TICKS(100));
        } else {
            // 客戶端未連接：閃爍模式
            int64_t now = esp_timer_get_time() / 1000;  // 轉換為毫秒
            
            if (blink_state) {
                // LED 目前是亮的
                if (now - last_toggle >= LED_ON_TIME) {
                    led_set(false);
                    blink_state = false;
                    last_toggle = now;
                    total_flashes++;
                }
            } else {
                // LED 目前是暗的
                if (now - last_toggle >= LED_OFF_TIME) {
                    led_set(true);
                    blink_state = true;
                    last_toggle = now;
                }
            }
            vTaskDelay(pdMS_TO_TICKS(10));
        }
    }
}

// ============================================
// WiFi 事件處理
// ============================================

/**
 * WiFi 事件處理函數
 */
static void wifi_event_handler(void* arg, esp_event_base_t event_base,
                                int32_t event_id, void* event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
        ESP_LOGI(TAG, "Connecting to WiFi...");
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        if (s_retry_num < WIFI_MAXIMUM_RETRY) {
            esp_wifi_connect();
            s_retry_num++;
            ESP_LOGI(TAG, "Retry to connect to the AP (%d/%d)", s_retry_num, WIFI_MAXIMUM_RETRY);
        } else {
            xEventGroupSetBits(s_wifi_event_group, WIFI_FAIL_BIT);
            ESP_LOGE(TAG, "Failed to connect to WiFi");
        }
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        ESP_LOGI(TAG, "Got IP: " IPSTR, IP2STR(&event->ip_info.ip));
        s_retry_num = 0;
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
        client_connected = true;
        connection_count++;
    }
}

/**
 * 初始化 WiFi
 */
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
            .password = WIFI_PASS,
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,
        },
    };
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "WiFi initialization finished.");
    ESP_LOGI(TAG, "Connecting to SSID: %s", WIFI_SSID);

    // 等待連接結果
    EventBits_t bits = xEventGroupWaitBits(s_wifi_event_group,
            WIFI_CONNECTED_BIT | WIFI_FAIL_BIT,
            pdFALSE,
            pdFALSE,
            portMAX_DELAY);

    if (bits & WIFI_CONNECTED_BIT) {
        ESP_LOGI(TAG, "Connected to WiFi SSID: %s", WIFI_SSID);
    } else if (bits & WIFI_FAIL_BIT) {
        ESP_LOGE(TAG, "Failed to connect to SSID: %s", WIFI_SSID);
    } else {
        ESP_LOGE(TAG, "Unexpected WiFi event");
    }
}

// ============================================
// HTTP 伺服器處理函數
// ============================================

/**
 * 主頁面處理
 */
static esp_err_t root_handler(httpd_req_t *req)
{
    const char* html_page = 
        "<!DOCTYPE html><html><head>"
        "<meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>ESP32-C3 LED 控制器</title>"
        "<style>"
        "body { font-family: Arial; text-align: center; margin: 20px; background: #f0f0f0; }"
        ".container { max-width: 400px; margin: 0 auto; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }"
        ".button { display: inline-block; padding: 15px 25px; margin: 10px; font-size: 16px; text-decoration: none; border-radius: 5px; color: white; }"
        ".btn-on { background-color: #4CAF50; }"
        ".btn-off { background-color: #f44336; }"
        ".btn-toggle { background-color: #2196F3; }"
        ".status { margin: 20px 0; padding: 15px; background: #e7f3ff; border-radius: 5px; }"
        "h1 { color: #333; }"
        "</style>"
        "</head><body>"
        "<div class='container'>"
        "<h1>🔵 ESP32-C3 LED 控制器</h1>"
        "<div class='status'>"
        "<h3>目前狀態</h3>"
        "<p>LED: %s</p>"
        "<p>WiFi: ✅ 已連接</p>"
        "<p>模式: %s</p>"
        "</div>"
        "<a href='/led/on' class='button btn-on'>開啟 LED</a><br>"
        "<a href='/led/off' class='button btn-off'>關閉 LED</a><br>"
        "<a href='/led/toggle' class='button btn-toggle'>切換 LED</a><br>"
        "<p><small>總閃爍次數: %u</small></p>"
        "<p><small>連接次數: %u</small></p>"
        "<p><small>運行時間: %lld 秒</small></p>"
        "</div>"
        "<script>setTimeout(function() { location.reload(); }, 5000);</script>"
        "</body></html>";
    
    char response[2048];
    int64_t uptime = (esp_timer_get_time() - start_time) / 1000000;
    
    snprintf(response, sizeof(response), html_page,
             led_state ? "🔵 開啟" : "⚫ 關閉",
             manual_control ? "手動控制" : (client_connected ? "恆亮模式" : "閃爍模式"),
             total_flashes,
             connection_count,
             uptime);
    
    httpd_resp_send(req, response, HTTPD_RESP_USE_STRLEN);
    return ESP_OK;
}

/**
 * LED ON 處理
 */
static esp_err_t led_on_handler(httpd_req_t *req)
{
    led_set(true);
    manual_control = true;
    ESP_LOGI(TAG, "Web control: LED ON");
    
    httpd_resp_set_status(req, "302 Found");
    httpd_resp_set_hdr(req, "Location", "/");
    httpd_resp_send(req, NULL, 0);
    return ESP_OK;
}

/**
 * LED OFF 處理
 */
static esp_err_t led_off_handler(httpd_req_t *req)
{
    led_set(false);
    manual_control = true;
    ESP_LOGI(TAG, "Web control: LED OFF");
    
    httpd_resp_set_status(req, "302 Found");
    httpd_resp_set_hdr(req, "Location", "/");
    httpd_resp_send(req, NULL, 0);
    return ESP_OK;
}

/**
 * LED Toggle 處理
 */
static esp_err_t led_toggle_handler(httpd_req_t *req)
{
    led_set(!led_state);
    manual_control = true;
    ESP_LOGI(TAG, "Web control: LED %s", led_state ? "ON" : "OFF");
    
    httpd_resp_set_status(req, "302 Found");
    httpd_resp_set_hdr(req, "Location", "/");
    httpd_resp_send(req, NULL, 0);
    return ESP_OK;
}

/**
 * 狀態 API 處理
 */
static esp_err_t status_handler(httpd_req_t *req)
{
    char json[256];
    int64_t uptime = (esp_timer_get_time() - start_time) / 1000000;
    
    snprintf(json, sizeof(json),
             "{\"led\":%s,\"connected\":%s,\"manual\":%s,\"flashes\":%" PRIu32 ",\"connections\":%" PRIu32 ",\"uptime\":%lld}",
             led_state ? "true" : "false",
             client_connected ? "true" : "false",
             manual_control ? "true" : "false",
             total_flashes,
             connection_count,
             uptime);
    
    httpd_resp_set_type(req, "application/json");
    httpd_resp_send(req, json, HTTPD_RESP_USE_STRLEN);
    return ESP_OK;
}

/**
 * 啟動 HTTP 伺服器
 */
static httpd_handle_t start_webserver(void)
{
    httpd_handle_t server = NULL;
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.lru_purge_enable = true;

    ESP_LOGI(TAG, "Starting HTTP server on port: '%d'", config.server_port);
    if (httpd_start(&server, &config) == ESP_OK) {
        // 註冊 URI 處理函數
        httpd_uri_t root = {
            .uri       = "/",
            .method    = HTTP_GET,
            .handler   = root_handler,
            .user_ctx  = NULL
        };
        httpd_register_uri_handler(server, &root);

        httpd_uri_t led_on = {
            .uri       = "/led/on",
            .method    = HTTP_GET,
            .handler   = led_on_handler,
            .user_ctx  = NULL
        };
        httpd_register_uri_handler(server, &led_on);

        httpd_uri_t led_off = {
            .uri       = "/led/off",
            .method    = HTTP_GET,
            .handler   = led_off_handler,
            .user_ctx  = NULL
        };
        httpd_register_uri_handler(server, &led_off);

        httpd_uri_t led_toggle = {
            .uri       = "/led/toggle",
            .method    = HTTP_GET,
            .handler   = led_toggle_handler,
            .user_ctx  = NULL
        };
        httpd_register_uri_handler(server, &led_toggle);

        httpd_uri_t status = {
            .uri       = "/status",
            .method    = HTTP_GET,
            .handler   = status_handler,
            .user_ctx  = NULL
        };
        httpd_register_uri_handler(server, &status);

        ESP_LOGI(TAG, "HTTP server started successfully");
        return server;
    }

    ESP_LOGE(TAG, "Error starting HTTP server!");
    return NULL;
}

// ============================================
// 序列埠命令處理
// ============================================

/**
 * 序列埠命令處理任務
 */
static void uart_command_task(void *arg)
{
    char cmd[64];
    int idx = 0;
    
    ESP_LOGI(TAG, "UART command task started. Type 'help' for available commands.");
    
    while (1) {
        int c = getchar();
        if (c != EOF) {
            if (c == '\n' || c == '\r') {
                if (idx > 0) {
                    cmd[idx] = '\0';
                    idx = 0;
                    
                    // 處理命令
                    if (strcmp(cmd, "status") == 0 || strcmp(cmd, "s") == 0) {
                        ESP_LOGI(TAG, "========================================");
                        ESP_LOGI(TAG, "Status:");
                        ESP_LOGI(TAG, "  LED: %s", led_state ? "ON" : "OFF");
                        ESP_LOGI(TAG, "  WiFi: %s", client_connected ? "Connected" : "Disconnected");
                        ESP_LOGI(TAG, "  Mode: %s", manual_control ? "Manual" : "Auto");
                        ESP_LOGI(TAG, "  Flashes: %u", total_flashes);
                        ESP_LOGI(TAG, "  Connections: %u", connection_count);
                        ESP_LOGI(TAG, "  Uptime: %lld sec", (esp_timer_get_time() - start_time) / 1000000);
                        ESP_LOGI(TAG, "========================================");
                    } else if (strcmp(cmd, "on") == 0) {
                        led_set(true);
                        manual_control = true;
                        ESP_LOGI(TAG, "LED turned ON");
                    } else if (strcmp(cmd, "off") == 0) {
                        led_set(false);
                        manual_control = true;
                        ESP_LOGI(TAG, "LED turned OFF");
                    } else if (strcmp(cmd, "auto") == 0) {
                        manual_control = false;
                        ESP_LOGI(TAG, "Switched to AUTO mode");
                    } else if (strcmp(cmd, "help") == 0 || strcmp(cmd, "h") == 0) {
                        ESP_LOGI(TAG, "========================================");
                        ESP_LOGI(TAG, "Available Commands:");
                        ESP_LOGI(TAG, "  status (s) - Show current status");
                        ESP_LOGI(TAG, "  on         - Turn LED ON");
                        ESP_LOGI(TAG, "  off        - Turn LED OFF");
                        ESP_LOGI(TAG, "  auto       - Switch to auto mode");
                        ESP_LOGI(TAG, "  help (h)   - Show this help");
                        ESP_LOGI(TAG, "  clear      - Clear statistics");
                        ESP_LOGI(TAG, "========================================");
                    } else if (strcmp(cmd, "clear") == 0) {
                        total_flashes = 0;
                        connection_count = 0;
                        start_time = esp_timer_get_time();
                        ESP_LOGI(TAG, "Statistics cleared");
                    } else {
                        ESP_LOGW(TAG, "Unknown command: %s (type 'help' for available commands)", cmd);
                    }
                }
            } else if (idx < sizeof(cmd) - 1) {
                cmd[idx++] = c;
            }
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

// ============================================
// 啟動畫面
// ============================================

static void show_startup_screen(void)
{
    printf("\n");
    printf("########################################\n");
    printf("#                                      #\n");
    printf("#   ESP32-C3 WiFi LED 控制程式         #\n");
    printf("#                                      #\n");
    printf("########################################\n");
    printf("\n");
    printf("版本: v1.0\n");
    printf("WiFi SSID: %s\n", WIFI_SSID);
    printf("LED GPIO: %d (反向邏輯: LOW=ON)\n", LED_GPIO);
    printf("\n");
    printf("功能說明:\n");
    printf("• WiFi 連接時 → LED 恆亮\n");
    printf("• WiFi 斷線時 → LED 閃爍 (200ms亮/800ms暗)\n");
    printf("• 網頁控制: http://<ESP_IP>\n");
    printf("• 序列埠命令: 輸入 'help' 查看可用命令\n");
    printf("\n");
}

// ============================================
// 主函數
// ============================================

void app_main(void)
{
    // 顯示啟動畫面
    show_startup_screen();
    
    // 記錄啟動時間
    start_time = esp_timer_get_time();
    
    // 初始化 NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    
    // 初始化 LED
    led_init();
    
    // 初始化 WiFi
    wifi_init_sta();
    
    // 啟動 HTTP 伺服器
    server = start_webserver();
    
    // 建立 LED 閃爍任務
    xTaskCreate(led_blink_task, "led_blink", 2048, NULL, 5, NULL);
    
    // 建立序列埠命令處理任務
    xTaskCreate(uart_command_task, "uart_cmd", 4096, NULL, 5, NULL);
    
    ESP_LOGI(TAG, "System initialized successfully!");
    ESP_LOGI(TAG, "Type 'help' in serial monitor for available commands");
}
