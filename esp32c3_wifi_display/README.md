# ESP32-C3 WiFi E-Paper Display

WiFi 控制的 E-Paper 顯示器專案，結合了 ESP32-C3 的 WiFi 功能和 GDEQ0426T82 E-Paper 顯示器。

## 功能特色

- ✅ WiFi 連接和 HTTP 服務器
- ✅ 網頁介面上傳圖片
- ✅ E-Paper 顯示器驅動 (800x480)
- ✅ 全螢幕和部分更新
- ✅ RESTful API

## 硬體需求

### ESP32-C3 開發板
- RISC-V 架構
- WiFi 支援

### E-Paper 顯示器
- **型號**: GDEQ0426T82
- **尺寸**: 4.26"
- **解析度**: 800x480
- **控制器**: SSD1677
- **介面**: SPI

### 接線

```
ESP32-C3    E-Paper
--------------------------------
GPIO2   ->  SCLK
GPIO3   ->  MOSI
GPIO10  ->  CS
GPIO4   ->  DC
GPIO5   ->  RST
GPIO6   ->  BUSY
GND     ->  GND
3.3V    ->  VCC
```

## 軟體架構

```
wifi_display_main.c  - 主程式，WiFi 和 HTTP 服務器
epaper_driver.c      - E-Paper 驅動程式
epaper_driver.h      - E-Paper 驅動標頭檔
font.h               - 字體定義
```

## 編譯與燒錄

### 1. 設定環境

Windows:
```powershell
C:\Users\<username>\esp\v5.5.1\esp-idf\export.ps1
```

Linux/macOS:
```bash
. $HOME/esp/esp-idf/export.sh
```

### 2. 配置 WiFi

編輯 `main/wifi_display_main.c`:
```c
#define WIFI_SSID           "your_ssid"
#define WIFI_PASS           "your_password"
```

### 3. 編譯

```bash
cd esp32c3_wifi_display
idf.py build
```

### 4. 燒錄

```bash
idf.py -p COM4 flash
```

### 5. 監控

```bash
idf.py -p COM4 monitor
```

## 使用方式

### 1. 啟動設備

燒錄完成後，ESP32-C3 會：
1. 連接到配置的 WiFi 網路
2. 啟動 HTTP 服務器
3. 顯示啟動畫面

### 2. 查看 IP 地址

從序列埠監控輸出中找到 IP 地址：
```
I (xxx) WiFi_Display: Got IP address: 192.168.0.xxx
```

### 3. 開啟網頁介面

在瀏覽器中訪問：
```
http://192.168.0.xxx
```

### 4. 上傳圖片

1. 點擊「選擇文件」按鈕
2. 選擇圖片文件
3. 點擊「上傳並顯示」
4. E-Paper 將顯示上傳的圖片

## API 端點

### GET /
主頁面，提供網頁介面

### POST /upload
上傳圖片數據
- Content-Type: multipart/form-data
- 參數: image (file)

### GET /status
查詢設備狀態
- 返回: JSON 格式的狀態信息

## 記憶體使用

- **Flash**: ~250KB
- **RAM**: ~50KB (含 framebuffer)
- **Framebuffer**: 48,000 bytes (800×480÷8)

## 顯示性能

- **全螢幕更新**: ~1610ms
- **部分更新**: ~410ms

## 開發計劃

- [ ] 圖片格式支援 (BMP, PNG)
- [ ] 圖片縮放和裁剪
- [ ] 多頁顯示管理
- [ ] OTA 更新功能
- [ ] 更多圖形效果

## 參考專案

- Arduino wifi_spi_display
- esp32c3_spi_display
- esp32c3_wifi_led_control

## 版本歷史

- **v1.0** (2025-10-28)
  - 初始版本
  - WiFi 連接和 HTTP 服務器
  - E-Paper 基本顯示功能
  - 網頁上傳介面

## 授權

MIT License
