# ESP32-C3 SPI E-Paper Display Project

## 專案說明

本專案使用 ESP32-C3 開發板驅動 GDEQ0426T82 4.26" E-Paper 顯示器 (800x480 解析度)。

## 硬體需求

- ESP32-C3 Super Mini 開發板
- GDEQ0426T82 4.26" E-Paper 顯示器 (800x480)
- USB 傳輸線

## 腳位連接

| E-Paper | ESP32-C3 | 說明 |
|---------|----------|------|
| SCLK    | GPIO 2   | SPI 時鐘 |
| MOSI    | GPIO 3   | SPI 資料輸出 |
| CS      | GPIO 10  | SPI 片選 |
| DC      | GPIO 4   | 資料/命令選擇 |
| RST     | GPIO 5   | 硬體重置 |
| BUSY    | GPIO 6   | 忙碌狀態 |
| VCC     | 3.3V     | 電源 |
| GND     | GND      | 接地 |

## 功能特點

- **全螢幕更新**: 支援 800x480 全解析度顯示
- **部分更新**: 支援指定區域更新，加快刷新速度
- **Frame Buffer**: 使用 48KB 完整 frame buffer，支援複雜圖形
- **ESP-IDF 原生**: 使用 ESP-IDF SPI Master 驅動，效能優異

## 測試項目

### 測試 1: 白屏清除
清除整個螢幕為白色，測試全螢幕更新功能。

### 測試 2: 部分更新 (400x120)
在左上角繪製 400x120 像素的矩形圖案，測試部分更新功能。

### 測試 3: 中央部分更新 (500x240)
在螢幕中央繪製 500x240 像素的複雜圖案，測試大面積部分更新。

## 編譯與燒錄

### 1. 設定環境

```bash
# Windows PowerShell
. $HOME\esp\v5.5.1\esp-idf\export.ps1
```

### 2. 編譯專案

```bash
cd d:\1_myproject\esp-idf\esp32c3\esp32c3_spi_display
idf.py build
```

### 3. 燒錄到開發板

```bash
idf.py -p COM6 flash monitor
```

## 架構說明

### 檔案結構

```
esp32c3_spi_display/
├── CMakeLists.txt              # 專案配置
├── sdkconfig.defaults          # 預設配置
├── README.md                   # 本文件
└── main/
    ├── CMakeLists.txt          # 主程式配置
    ├── epaper_driver.h         # E-Paper 驅動標頭檔
    ├── epaper_driver.c         # E-Paper 驅動實作
    └── spi_display_main.c      # 主程式
```

### 驅動層次

1. **SPI 通訊層**: 使用 ESP-IDF SPI Master 驅動
2. **E-Paper 協議層**: 實作 GDEQ0426T82 命令協議
3. **圖形繪製層**: 提供像素、矩形等繪圖函數
4. **應用層**: 三個測試程式

## API 說明

### 初始化函數

```c
esp_err_t epaper_init(epaper_t *epaper);        // 初始化顯示器
esp_err_t epaper_deinit(epaper_t *epaper);      // 反初始化
void epaper_sleep(epaper_t *epaper);            // 進入睡眠模式
```

### 繪圖函數

```c
void epaper_set_pixel(epaper_t *epaper, uint16_t x, uint16_t y, uint8_t color);
void epaper_fill_rect(epaper_t *epaper, uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t color);
void epaper_draw_rect(epaper_t *epaper, uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t color);
void epaper_clear_screen(epaper_t *epaper, uint8_t color);
```

### 顯示更新函數

```c
void epaper_display_full(epaper_t *epaper);     // 全螢幕更新
void epaper_display_partial(epaper_t *epaper, uint16_t x, uint16_t y, uint16_t w, uint16_t h);  // 部分更新
```

## 技術規格

- **解析度**: 800 x 480 像素
- **色彩**: 黑白雙色
- **Frame Buffer**: 48000 bytes (48 KB)
- **SPI 速度**: 4 MHz
- **更新時間**: 
  - 全螢幕更新: ~3-5 秒
  - 部分更新: ~1-2 秒

## 記憶體使用

- Frame Buffer: 48 KB (heap)
- 程式碼: ~30 KB (flash)
- 堆疊: ~8 KB (RAM)

## 注意事項

1. E-Paper 顯示器需要較長的更新時間，請耐心等待
2. BUSY 信號為高電平時表示顯示器正在更新，請勿中斷電源
3. 頻繁更新會縮短 E-Paper 壽命，建議間隔至少 180 秒
4. 部分更新速度較快但可能有殘影，建議定期全螢幕更新

## 版本歷史

- v1.0 (2025-10-27): 初始版本
  - 實作 SPI 驅動層
  - 實作 E-Paper 協議
  - 實作三個測試功能
  - 支援全螢幕和部分更新

## 授權

本專案使用 MIT 授權。

## 作者

ESP32-C3 開發團隊
