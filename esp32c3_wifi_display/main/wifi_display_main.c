/*
 * ESP32-C3 WiFi E-Paper Display (WebSocket Client)
 * 
 * 功能：
 * - 連接到 WiFi 網路
 * - WebSocket Client 連接到 Raspberry Pi Server
 * - 接收圖片數據並在 E-Paper 顯示器上顯示
 * - 基於 Arduino client_esp8266 架構移植
 * 
 * 硬體需求：
 * - ESP32-C3 開發板
 * - GDEQ0426T82 4.26" E-Paper 顯示器 (800x480)
 * 
 * 版本：v2.0 (WebSocket Client)
 * 日期：2025-10-28
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "freertos/queue.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_websocket_client.h"
#include "nvs_flash.h"
#include "epaper_driver.h"
#include "lwip/sockets.h"
#include "lwip/netdb.h"

// ============================================
// WiFi 配置
// ============================================

#define WIFI_SSID           "lulumi_ap"
#define WIFI_PASS           "1978120505"
#define WIFI_MAXIMUM_RETRY  5

// WebSocket 服務器配置（備用）
#define DEFAULT_SERVER_IP       "192.168.0.41"
#define DEFAULT_SERVER_PORT     8765

// UDP 自動發現配置
#define UDP_BROADCAST_PORT      8888
#define UDP_DISCOVERY_TIMEOUT   10000  // 10 秒超時（毫秒）

// 協議定義（與 Arduino client_esp8266 一致）
#define PROTO_HEADER            0xA5
#define PROTO_HEADER_SIZE       8       // 1 + 1 + 2 + 4 bytes
#define PROTO_TYPE_FULL         0x01    // 完整畫面更新
#define PROTO_TYPE_TILE         0x02    // 分區更新
#define PROTO_TYPE_DELTA        0x03    // 差分更新
#define PROTO_TYPE_CMD          0x04    // 控制指令
#define PROTO_TYPE_ACK          0x10    // 確認
#define PROTO_TYPE_NAK          0x11    // 否認

// 顯示器尺寸定義
#define DISPLAY_WIDTH           800
#define DISPLAY_HEIGHT          480

// 分區定義（800x480 分成 3 個水平條帶）
#define TILE_COUNT              3
#define TILE_WIDTH              800
#define TILE_HEIGHT             160     // 480 / 3 = 160
#define TILE_BUFFER_SIZE        (TILE_WIDTH * TILE_HEIGHT / 8)  // 16000 bytes

// WiFi 事件標誌
#define WIFI_CONNECTED_BIT  BIT0
#define WIFI_FAIL_BIT       BIT1

// ============================================
// 全域變數
// ============================================

static const char *TAG = "WS_Display";
static EventGroupHandle_t s_wifi_event_group;
static int s_retry_num = 0;
static esp_websocket_client_handle_t ws_client = NULL;
static epaper_t epaper = {0};

// Server 自動發現
static char discovered_server_ip[32] = "";
static int discovered_server_port = 0;
static bool server_discovered = false;

// 協議封包處理
typedef struct {
    uint8_t header;      // 0xA5
    uint8_t type;        // 封包類型
    uint16_t seq_id;     // 序號
    uint32_t length;     // Payload 長度
} __attribute__((packed)) packet_header_t;

static uint8_t *tile_buffer = NULL;  // 分區緩衝區 (16KB)
static uint32_t packet_buffer_pos = 0;
static uint8_t packet_buffer[20480];  // 20KB 封包接收緩衝
static uint16_t last_tile_seq_id = 0;  // 追蹤 tile 序列

// 圖片接收緩衝區（舊版協議使用）
#define MAX_IMAGE_SIZE  (20 * 1024)  // 20KB（協議模式主要使用 tile_buffer）
static uint8_t *image_buffer = NULL;
static size_t image_buffer_pos = 0;
static bool receiving_image = false;

// ============================================
// WiFi 事件處理
// ============================================

static void wifi_event_handler(void* arg, esp_event_base_t event_base,
                              int32_t event_id, void* event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        if (s_retry_num < WIFI_MAXIMUM_RETRY) {
            esp_wifi_connect();
            s_retry_num++;
            ESP_LOGI(TAG, "Retry to connect to AP... (%d/%d)", s_retry_num, WIFI_MAXIMUM_RETRY);
        } else {
            xEventGroupSetBits(s_wifi_event_group, WIFI_FAIL_BIT);
        }
        ESP_LOGW(TAG, "Connect to AP failed");
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        ESP_LOGI(TAG, "Got IP address: " IPSTR, IP2STR(&event->ip_info.ip));
        s_retry_num = 0;
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
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

    ESP_LOGI(TAG, "WiFi initialization finished");

    // 等待連接結果
    EventBits_t bits = xEventGroupWaitBits(s_wifi_event_group,
            WIFI_CONNECTED_BIT | WIFI_FAIL_BIT,
            pdFALSE,
            pdFALSE,
            portMAX_DELAY);

    if (bits & WIFI_CONNECTED_BIT) {
        ESP_LOGI(TAG, "Connected to AP SSID:%s", WIFI_SSID);
    } else if (bits & WIFI_FAIL_BIT) {
        ESP_LOGE(TAG, "Failed to connect to SSID:%s", WIFI_SSID);
    } else {
        ESP_LOGE(TAG, "UNEXPECTED EVENT");
    }
}

// ============================================
// UDP 自動發現 Server
// ============================================

/**
 * UDP 自動發現伺服器
 * 監聽 UDP 廣播訊息來找到伺服器 IP
 * 格式: EPAPER_SERVER:192.168.0.41:8765
 * 
 * @return true 如果成功發現伺服器，false 否則
 */
static bool discover_server(void)
{
    ESP_LOGI(TAG, "*** Starting UDP Server Discovery (Port %d)... ***", UDP_BROADCAST_PORT);
    
    // 創建 UDP socket
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock < 0) {
        ESP_LOGE(TAG, "Failed to create UDP socket");
        return false;
    }

    // 設置 socket 為非阻塞模式
    int flags = fcntl(sock, F_GETFL, 0);
    fcntl(sock, F_SETFL, flags | O_NONBLOCK);

    // 綁定到廣播端口
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(UDP_BROADCAST_PORT);

    if (bind(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        ESP_LOGE(TAG, "Failed to bind UDP socket");
        close(sock);
        return false;
    }

    ESP_LOGI(TAG, "UDP socket bound to port %d, waiting for broadcast...", UDP_BROADCAST_PORT);

    // 監聽廣播訊息
    char buffer[128];
    struct sockaddr_in sender_addr;
    socklen_t sender_len = sizeof(sender_addr);
    
    uint32_t start_time = xTaskGetTickCount();
    uint32_t timeout_ticks = pdMS_TO_TICKS(UDP_DISCOVERY_TIMEOUT);
    
    while ((xTaskGetTickCount() - start_time) < timeout_ticks) {
        int len = recvfrom(sock, buffer, sizeof(buffer) - 1, 0,
                          (struct sockaddr *)&sender_addr, &sender_len);
        
        if (len > 0) {
            buffer[len] = '\0';
            ESP_LOGI(TAG, "Received UDP packet: %s", buffer);
            
            // 檢查格式: EPAPER_SERVER:192.168.0.41:8765
            if (strncmp(buffer, "EPAPER_SERVER:", 14) == 0) {
                char *ip_start = buffer + 14;
                char *port_start = strchr(ip_start, ':');
                
                if (port_start != NULL) {
                    *port_start = '\0';  // 分隔 IP 和 Port
                    port_start++;
                    
                    // 複製 IP 和 Port
                    strncpy(discovered_server_ip, ip_start, sizeof(discovered_server_ip) - 1);
                    discovered_server_port = atoi(port_start);
                    
                    ESP_LOGI(TAG, "✓ Server discovered!");
                    ESP_LOGI(TAG, "  IP:   %s", discovered_server_ip);
                    ESP_LOGI(TAG, "  Port: %d", discovered_server_port);
                    
                    server_discovered = true;
                    close(sock);
                    return true;
                }
            }
        }
        
        // 短暫延遲避免 CPU 過載
        vTaskDelay(pdMS_TO_TICKS(100));
    }
    
    close(sock);
    ESP_LOGW(TAG, "✗ Server discovery timeout (no response in %d seconds)", 
             UDP_DISCOVERY_TIMEOUT / 1000);
    return false;
}

// ============================================
// 協議封包處理
// ============================================

/**
 * 解析封包頭
 */
static bool parse_packet_header(const uint8_t *data, packet_header_t *header)
{
    if (data[0] != PROTO_HEADER) {
        return false;
    }
    
    header->header = data[0];
    header->type = data[1];
    // 小端序 (Little-Endian)
    header->seq_id = data[2] | (data[3] << 8);
    header->length = data[4] | 
                     (data[5] << 8) | 
                     (data[6] << 16) | 
                     ((uint32_t)data[7] << 24);
    
    return true;
}

/**
 * 發送 ACK
 */
static void send_ack(uint16_t seq_id)
{
    uint8_t ack_packet[PROTO_HEADER_SIZE];
    ack_packet[0] = PROTO_HEADER;
    ack_packet[1] = PROTO_TYPE_ACK;
    ack_packet[2] = seq_id & 0xFF;
    ack_packet[3] = (seq_id >> 8) & 0xFF;
    ack_packet[4] = 0;
    ack_packet[5] = 0;
    ack_packet[6] = 0;
    ack_packet[7] = 0;
    
    esp_websocket_client_send_bin(ws_client, (char*)ack_packet, PROTO_HEADER_SIZE, portMAX_DELAY);
    ESP_LOGI(TAG, "Sent ACK for seq_id: %d", seq_id);
}

/**
 * 發送 NAK
 */
static void send_nak(uint16_t seq_id)
{
    uint8_t nak_packet[PROTO_HEADER_SIZE];
    nak_packet[0] = PROTO_HEADER;
    nak_packet[1] = PROTO_TYPE_NAK;
    nak_packet[2] = seq_id & 0xFF;
    nak_packet[3] = (seq_id >> 8) & 0xFF;
    nak_packet[4] = 0;
    nak_packet[5] = 0;
    nak_packet[6] = 0;
    nak_packet[7] = 0;
    
    esp_websocket_client_send_bin(ws_client, (char*)nak_packet, PROTO_HEADER_SIZE, portMAX_DELAY);
    ESP_LOGW(TAG, "Sent NAK for seq_id: %d", seq_id);
}

/**
 * 處理分區更新（TILE）
 */
static void handle_tile_update(const uint8_t *payload, uint32_t length, uint16_t seq_id)
{
    if (length < 1) {
        ESP_LOGE(TAG, "Tile data too short");
        send_nak(seq_id);
        return;
    }
    
    uint8_t tile_index = payload[0];
    payload++;
    length--;
    
    if (tile_index >= TILE_COUNT) {
        ESP_LOGE(TAG, "Invalid tile index: %d", tile_index);
        send_nak(seq_id);
        return;
    }
    
    if (length != TILE_BUFFER_SIZE) {
        ESP_LOGE(TAG, "Tile data size mismatch: expected %d, got %lu", 
                 TILE_BUFFER_SIZE, length);
        send_nak(seq_id);
        return;
    }
    
    const char* tile_names[] = {"Top", "Middle", "Bottom"};
    uint16_t tile_y = tile_index * TILE_HEIGHT;
    
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "Tile Update: %s (index=%d, Y=%d-%d)", 
             tile_names[tile_index], tile_index, tile_y, tile_y + TILE_HEIGHT);
    
    // 記憶體監控
    ESP_LOGI(TAG, "Free heap: %lu bytes", esp_get_free_heap_size());
    
    // 如果是第一個 tile 且序號不連續（與上一組差距 > 3），表示新的圖片開始，先清除螢幕移除殘影
    if (tile_index == 0 && (last_tile_seq_id == 0 || seq_id > last_tile_seq_id + 3)) {
        ESP_LOGI(TAG, "New image sequence detected (last_seq: %d, current_seq: %d), clearing screen...", 
                 last_tile_seq_id, seq_id);
        memset(epaper.framebuffer, 0xFF, EPAPER_BUFFER_SIZE);  // 全白
        epaper_display_full(&epaper);
        vTaskDelay(pdMS_TO_TICKS(500));  // 等待清除完成
    }
    last_tile_seq_id = seq_id;
    
    // 清空分區緩衝區（防止殘留數據）
    memset(tile_buffer, 0xFF, TILE_BUFFER_SIZE);  // 0xFF = 白色
    
    // 複製數據到分區緩衝區
    memcpy(tile_buffer, payload, TILE_BUFFER_SIZE);
    
    ESP_LOGI(TAG, "Displaying tile...");
    
    // 直接將分區數據寫入 E-Paper 的對應位置
    // 設置部分窗口
    uint32_t start_time = xTaskGetTickCount();
    
    // 將 tile_buffer 的數據複製到 framebuffer 的對應位置
    for (int y = 0; y < TILE_HEIGHT; y++) {
        uint32_t fb_offset = ((tile_y + y) * DISPLAY_WIDTH) / 8;
        uint32_t tile_offset = (y * TILE_WIDTH) / 8;
        memcpy(epaper.framebuffer + fb_offset, tile_buffer + tile_offset, TILE_WIDTH / 8);
    }
    
    // 執行部分更新 - 更新整個分區
    epaper_display_partial(&epaper, 0, tile_y, TILE_WIDTH, TILE_HEIGHT);
    
    uint32_t elapsed = pdTICKS_TO_MS(xTaskGetTickCount() - start_time);
    ESP_LOGI(TAG, "Tile %s displayed in %lu ms", tile_names[tile_index], elapsed);
    
    // 發送 ACK
    send_ack(seq_id);
    
    // 發送 READY 訊息
    esp_websocket_client_send_text(ws_client, "READY", 5, portMAX_DELAY);
    ESP_LOGI(TAG, "========================================");
}

/**
 * 處理完整螢幕更新
 */
static void handle_full_update(const uint8_t *payload, uint32_t length, uint16_t seq_id)
{
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "Full Screen Update");
    ESP_LOGI(TAG, "Free heap: %lu bytes", esp_get_free_heap_size());
    
    // 完整螢幕大小：800x480 = 48000 bytes
    const uint32_t FULL_SCREEN_SIZE = (DISPLAY_WIDTH * DISPLAY_HEIGHT) / 8;
    
    if (length != FULL_SCREEN_SIZE) {
        ESP_LOGE(TAG, "Full screen data size mismatch: expected %lu, got %lu", 
                 FULL_SCREEN_SIZE, length);
        send_nak(seq_id);
        return;
    }
    
    uint32_t start_time = xTaskGetTickCount();
    
    ESP_LOGI(TAG, "Clearing previous screen content...");
    // 清除 E-Paper 顯示器（移除殘影）
    memset(epaper.framebuffer, 0xFF, EPAPER_BUFFER_SIZE);  // 全白
    epaper_display_full(&epaper);
    vTaskDelay(pdMS_TO_TICKS(1000));  // 等待清除完成
    
    ESP_LOGI(TAG, "Writing new image data...");
    // 複製完整圖片數據到 framebuffer
    memcpy(epaper.framebuffer, payload, FULL_SCREEN_SIZE);
    
    // 執行完整更新
    epaper_display_full(&epaper);
    
    uint32_t elapsed = pdTICKS_TO_MS(xTaskGetTickCount() - start_time);
    ESP_LOGI(TAG, "Full screen displayed in %lu ms", elapsed);
    
    // 發送 ACK
    send_ack(seq_id);
    
    // 發送 READY 訊息
    esp_websocket_client_send_text(ws_client, "READY", 5, portMAX_DELAY);
    ESP_LOGI(TAG, "========================================");
}

/**
 * 處理完整封包
 */
static void handle_packet(const uint8_t *data, uint32_t length)
{
    packet_header_t header;
    
    if (length < PROTO_HEADER_SIZE) {
        ESP_LOGE(TAG, "Packet too short");
        return;
    }
    
    if (!parse_packet_header(data, &header)) {
        ESP_LOGE(TAG, "Invalid packet header");
        return;
    }
    
    ESP_LOGI(TAG, "Packet: Type=0x%02X, SeqID=%d, Length=%lu", 
             header.type, header.seq_id, header.length);
    
    if (length < PROTO_HEADER_SIZE + header.length) {
        ESP_LOGE(TAG, "Incomplete packet");
        return;
    }
    
    const uint8_t *payload = data + PROTO_HEADER_SIZE;
    
    switch (header.type) {
        case PROTO_TYPE_TILE:
            handle_tile_update(payload, header.length, header.seq_id);
            break;
            
        case PROTO_TYPE_FULL:
            handle_full_update(payload, header.length, header.seq_id);
            break;
            
        case PROTO_TYPE_CMD:
            ESP_LOGI(TAG, "Command packet (not implemented)");
            send_ack(header.seq_id);
            break;
            
        default:
            ESP_LOGW(TAG, "Unknown packet type: 0x%02X", header.type);
            send_nak(header.seq_id);
            break;
    }
}

// ============================================
// 圖片處理（舊版 - 保留用於非協議模式）
// ============================================

/**
 * 處理接收到的圖片數據
 */
static void process_image_data(const uint8_t *data, size_t len)
{
    ESP_LOGI(TAG, "Processing image data: %d bytes", len);
    
    // 清除顯示器
    epaper_clear_screen(&epaper, COLOR_WHITE);
    
    // TODO: 解析圖片格式並顯示
    // 目前先繪製測試圖案
    
    // 繪製邊框
    epaper_draw_rect(&epaper, 50, 50, 700, 380, COLOR_BLACK);
    
    // 繪製一些測試方塊
    epaper_fill_rect(&epaper, 100, 100, 200, 100, COLOR_BLACK);
    epaper_fill_rect(&epaper, 350, 100, 200, 100, COLOR_BLACK);
    epaper_fill_rect(&epaper, 100, 250, 200, 100, COLOR_BLACK);
    epaper_fill_rect(&epaper, 350, 250, 200, 100, COLOR_BLACK);
    
    // 顯示
    epaper_display_full(&epaper);
    
    ESP_LOGI(TAG, "Image displayed successfully");
}

// ============================================
// WebSocket 事件處理
// ============================================

/**
 * WebSocket 事件處理函數
 */
static void websocket_event_handler(void *handler_args, esp_event_base_t base, 
                                    int32_t event_id, void *event_data)
{
    esp_websocket_event_data_t *data = (esp_websocket_event_data_t *)event_data;
    
    switch (event_id) {
        case WEBSOCKET_EVENT_CONNECTED:
            ESP_LOGI(TAG, "WebSocket connected to server");
            // 發送就緒訊息
            esp_websocket_client_send_text(ws_client, "ESP32-C3 Ready", 14, portMAX_DELAY);
            packet_buffer_pos = 0;
            break;
            
        case WEBSOCKET_EVENT_DISCONNECTED:
            ESP_LOGW(TAG, "WebSocket disconnected");
            receiving_image = false;
            image_buffer_pos = 0;
            packet_buffer_pos = 0;
            break;
            
        case WEBSOCKET_EVENT_DATA:
            if (data->op_code == 0x01) {
                // 文字訊息
                char msg[128];
                int len = data->data_len < 127 ? data->data_len : 127;
                memcpy(msg, data->data_ptr, len);
                msg[len] = '\0';
                ESP_LOGI(TAG, "Text message: %s", msg);
                
                // 檢查舊版圖片傳輸協議（保留向後相容）
                if (strncmp((char*)data->data_ptr, "IMAGE_START:", 12) == 0) {
                    receiving_image = true;
                    image_buffer_pos = 0;
                    ESP_LOGI(TAG, "Starting old-style image reception");
                } else if (strncmp((char*)data->data_ptr, "IMAGE_END", 9) == 0) {
                    receiving_image = false;
                    ESP_LOGI(TAG, "Image reception complete: %d bytes", image_buffer_pos);
                    
                    if (image_buffer_pos > 0) {
                        process_image_data(image_buffer, image_buffer_pos);
                    }
                    image_buffer_pos = 0;
                }
            } else if (data->op_code == 0x02) {
                // 二進制數據 - WebSocket 可能分片傳送
                // 累積所有片段直到 fin=1
                
                if (packet_buffer_pos + data->data_len < sizeof(packet_buffer)) {
                    // 持續累積數據
                    memcpy(packet_buffer + packet_buffer_pos, data->data_ptr, data->data_len);
                    packet_buffer_pos += data->data_len;
                    
                    // 只在接收完整訊息時處理（fin=1 且 payload 完成）
                    if (data->fin && packet_buffer_pos == data->payload_len) {
                        ESP_LOGI(TAG, "Complete packet received: %lu bytes", packet_buffer_pos);
                        
                        // 檢查是否為協議封包
                        if (packet_buffer_pos >= PROTO_HEADER_SIZE && 
                            packet_buffer[0] == PROTO_HEADER) {
                            // 處理協議封包
                            handle_packet(packet_buffer, packet_buffer_pos);
                        } else if (receiving_image) {
                            // 舊版圖片數據模式
                            if (image_buffer_pos + packet_buffer_pos < MAX_IMAGE_SIZE) {
                                memcpy(image_buffer + image_buffer_pos, packet_buffer, packet_buffer_pos);
                                image_buffer_pos += packet_buffer_pos;
                                ESP_LOGI(TAG, "Image data accumulated: %d bytes", image_buffer_pos);
                            }
                        }
                        
                        // 重置緩衝區準備下一個封包
                        packet_buffer_pos = 0;
                    } else {
                        // 還在累積中，等待更多片段
                        ESP_LOGD(TAG, "Accumulating: %lu/%d bytes", 
                                 packet_buffer_pos, data->payload_len);
                    }
                } else {
                    ESP_LOGE(TAG, "Packet buffer overflow! Received=%lu, Capacity=%d", 
                             packet_buffer_pos + data->data_len, sizeof(packet_buffer));
                    packet_buffer_pos = 0;
                }
            }
            break;
            
        case WEBSOCKET_EVENT_ERROR:
            ESP_LOGE(TAG, "WebSocket error");
            packet_buffer_pos = 0;
            break;
            
        default:
            break;
    }
}

/**
 * 啟動 WebSocket Client
 */
static void start_websocket_client(void)
{
    char ws_uri[128];
    
    // 使用發現的伺服器 IP 或預設 IP
    if (server_discovered) {
        snprintf(ws_uri, sizeof(ws_uri), "ws://%s:%d", 
                 discovered_server_ip, discovered_server_port);
        ESP_LOGI(TAG, "*** Using discovered server IP ***");
    } else {
        snprintf(ws_uri, sizeof(ws_uri), "ws://%s:%d", 
                 DEFAULT_SERVER_IP, DEFAULT_SERVER_PORT);
        ESP_LOGW(TAG, "*** Using default server IP (no discovery response) ***");
    }
    
    ESP_LOGI(TAG, "Connecting to WebSocket server: %s", ws_uri);
    
    esp_websocket_client_config_t ws_cfg = {
        .uri = ws_uri,
        .reconnect_timeout_ms = 5000,
        .network_timeout_ms = 10000,
    };
    
    ws_client = esp_websocket_client_init(&ws_cfg);
    esp_websocket_register_events(ws_client, WEBSOCKET_EVENT_ANY, 
                                  websocket_event_handler, NULL);
    
    esp_err_t ret = esp_websocket_client_start(ws_client);
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "WebSocket client started successfully");
    } else {
        ESP_LOGE(TAG, "WebSocket client start failed: %s", esp_err_to_name(ret));
    }
}

// ============================================
// 主程式
// ============================================

void app_main(void)
{
    printf("\n");
    printf("########################################\n");
    printf("#                                      #\n");
    printf("#  ESP32-C3 E-Paper WebSocket Client   #\n");
    printf("#  GDEQ0426T82 (800x480)               #\n");
    printf("#  with UDP Server Discovery           #\n");
    printf("#                                      #\n");
    printf("########################################\n");
    printf("\n");

    // 初始化 NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // 分配圖片緩衝區（舊版協議使用）
    image_buffer = (uint8_t *)malloc(MAX_IMAGE_SIZE);
    if (image_buffer == NULL) {
        ESP_LOGE(TAG, "Failed to allocate image buffer");
        return;
    }
    ESP_LOGI(TAG, "Image buffer allocated: %d bytes", MAX_IMAGE_SIZE);
    
    // 分配 Tile 緩衝區（協議模式使用）
    tile_buffer = (uint8_t *)malloc(TILE_BUFFER_SIZE);
    if (tile_buffer == NULL) {
        ESP_LOGE(TAG, "Failed to allocate tile buffer");
        free(image_buffer);
        return;
    }
    ESP_LOGI(TAG, "Tile buffer allocated: %d bytes", TILE_BUFFER_SIZE);
    
    // 初始化協議變數
    packet_buffer_pos = 0;
    memset(packet_buffer, 0, sizeof(packet_buffer));
    
    // 記憶體狀態報告
    ESP_LOGI(TAG, "=== Memory Status ===");
    ESP_LOGI(TAG, "Free heap: %lu bytes", esp_get_free_heap_size());
    ESP_LOGI(TAG, "Largest free block: %lu bytes", heap_caps_get_largest_free_block(MALLOC_CAP_8BIT));
    ESP_LOGI(TAG, "====================");

    // 初始化 E-Paper 顯示器
    ESP_LOGI(TAG, "Initializing E-Paper display...");
    ret = epaper_init(&epaper);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize E-Paper display!");
        free(image_buffer);
        return;
    }
    ESP_LOGI(TAG, "E-Paper display initialized successfully!");

    // 清空 framebuffer（不顯示，等待接收圖片數據）
    epaper_clear_screen(&epaper, COLOR_WHITE);
    ESP_LOGI(TAG, "Framebuffer cleared, ready for data reception");

    // 初始化 WiFi
    ESP_LOGI(TAG, "Initializing WiFi...");
    wifi_init_sta();

    // UDP 自動發現伺服器
    ESP_LOGI(TAG, "*** [Step 1] Auto-discovering WebSocket server... ***");
    discover_server();
    
    if (!server_discovered) {
        ESP_LOGW(TAG, "Will use default server: %s:%d", 
                 DEFAULT_SERVER_IP, DEFAULT_SERVER_PORT);
    }

    // 啟動 WebSocket Client
    ESP_LOGI(TAG, "*** [Step 2] Starting WebSocket client... ***");
    start_websocket_client();

    // 主循環
    ESP_LOGI(TAG, "System ready, waiting for WebSocket messages...");
    
    uint32_t loop_count = 0;
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(10000));  // 每 10 秒
        
        // 定期記憶體報告
        loop_count++;
        if (loop_count % 6 == 0) {  // 每 60 秒
            ESP_LOGI(TAG, "=== Memory Status (Runtime) ===");
            ESP_LOGI(TAG, "Free heap: %lu bytes", esp_get_free_heap_size());
            ESP_LOGI(TAG, "Min free heap: %lu bytes", esp_get_minimum_free_heap_size());
            ESP_LOGI(TAG, "Largest free block: %lu bytes", 
                     heap_caps_get_largest_free_block(MALLOC_CAP_8BIT));
            ESP_LOGI(TAG, "===============================");
        }
        
        // 檢查 WebSocket 連接狀態
        if (ws_client && !esp_websocket_client_is_connected(ws_client)) {
            ESP_LOGW(TAG, "WebSocket disconnected, attempting to reconnect...");
            vTaskDelay(pdMS_TO_TICKS(5000));
        }
    }
}
