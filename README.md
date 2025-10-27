# ESP32-C3 Projects

這是 ESP32-C3 的開發專案集合，使用 ESP-IDF v5.5.1 框架。

## 專案列表

### 1. blink
基礎 LED 閃爍測試專案

### 2. hello_world
Hello World 基礎測試專案

### 3. esp32c3_spi_display
E-Paper 顯示器驅動專案
- **顯示器**: GDEQ0426T82 (4.26" 800x480)
- **控制器**: SSD1677
- **通訊介面**: SPI (4MHz, Mode 0)

#### 功能特色
- ✅ 完整的 E-Paper 驅動程式
- ✅ 全螢幕更新 (1610ms)
- ✅ 部分更新 (410ms)
- ✅ 圖形繪製功能 (點、線、矩形、填充)
- ✅ 文字渲染系統 (ASCII + 中文字體)
- ✅ 網格測試模式

#### 硬體連接
```
ESP32-C3    E-Paper
GPIO2   ->  SCLK
GPIO3   ->  MOSI
GPIO10  ->  CS
GPIO4   ->  DC
GPIO5   ->  RST
GPIO6   ->  BUSY
```

#### 記憶體使用
- Flash: 240KB / 1MB (23%)
- RAM: 48KB framebuffer + 應用程式

## 開發環境

- **ESP-IDF**: v5.5.1
- **工具鏈**: riscv32-esp-elf-gcc 14.2.0
- **目標晶片**: ESP32-C3 (RISC-V)

## 編譯與燒錄

```bash
# 設定 ESP-IDF 環境
. $HOME/esp/esp-idf/export.sh  # Linux/macOS
# 或
C:\Users\<username>\esp\v5.5.1\esp-idf\export.ps1  # Windows

# 進入專案目錄
cd esp32c3_spi_display

# 編譯
idf.py build

# 燒錄
idf.py -p COM4 flash

# 監控輸出
idf.py -p COM4 monitor
```

## 版本歷史

- **v1.0** (2025-10-28)
  - 完成 E-Paper 驅動程式
  - 實現圖形繪製功能
  - 加入中英文字體系統
  - 加入網格測試模式

## 授權

MIT License
