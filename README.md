# ESP32-C3 Projects

這是 ESP32-C3 的開發專案集合，使用 ESP-IDF v5.5.1 框架。本 repository 包含多個實用專案，從基礎入門到進階應用，幫助你快速開始 ESP32-C3 開發。

## 🎯 你可以做什麼？ What Can I Do?

使用這個 repository，你可以：

1. **🚀 快速入門**: 從 `blink` 和 `hello_world` 開始，學習 ESP32-C3 基礎
2. **🖥️ E-Paper 顯示**: 使用 `esp32c3_spi_display` 驅動 4.26" E-Paper 顯示器
3. **📡 WiFi 應用**: 透過 `esp32c3_wifi_display` 和 `esp32c3_wifi_led_control` 學習 WiFi 連接和網頁控制
4. **🔋 電池管理**: 使用 `battery_management` 打造低功耗、長續航的電池供電裝置
5. **💡 物聯網專案**: 結合以上技術，開發自己的 IoT 應用

## 📚 專案列表

### 1. blink
**基礎 LED 閃爍測試專案**

- 適合初學者的第一個專案
- 學習 GPIO 控制和 LED 驅動
- 支援普通 LED 和可程式化 LED（如 WS2812）

[查看詳細說明](blink/README.md)

---

### 2. hello_world
**Hello World 基礎測試專案**

- ESP32-C3 的入門專案
- 學習 FreeRTOS 任務和串口輸出
- 驗證開發環境是否正確設定

[查看詳細說明](hello_world/README.md)

---

### 3. esp32c3_spi_display
**E-Paper 顯示器驅動專案** ⭐

使用 ESP32-C3 驅動 GDEQ0426T82 E-Paper 顯示器，適合製作電子標籤、資訊看板等低功耗顯示應用。

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

[查看詳細說明](esp32c3_spi_display/README.md)

---

### 4. esp32c3_wifi_display
**WiFi E-Paper 顯示器專案** ⭐

結合 WiFi 功能與 E-Paper 顯示器，可透過網頁介面上傳圖片並顯示。適合製作智能資訊看板、照片牆等應用。

#### 功能特色
- ✅ WiFi 連接和 HTTP 服務器
- ✅ 網頁介面上傳圖片
- ✅ E-Paper 顯示器驅動 (800x480)
- ✅ 全螢幕和部分更新
- ✅ RESTful API

#### 使用情境
- 遠端更新電子標籤
- 智能家庭資訊看板
- 照片展示裝置

[查看詳細說明](esp32c3_wifi_display/README.md)

---

### 5. esp32c3_wifi_led_control
**WiFi LED 控制專案**

透過 WiFi 網頁介面控制 LED，學習基礎的 IoT 控制應用。

#### 功能特色
- ✅ WiFi 連接
- ✅ 網頁控制介面
- ✅ LED 開關控制
- ✅ RESTful API

#### 應用場景
- 遠端燈光控制
- 智能家居原型
- IoT 學習專案

[查看詳細說明](esp32c3_wifi_led_control/README.md)

---

### 6. battery_management
**電池供電與充放電管理系統** ⭐⭐

為 ESP32-C3 SuperMini 開發板提供完整的電池供電解決方案，使用 TP4054 充電 IC + MOSFET 自動切換架構。

#### 設計特點
- ✅ 極致小型化（~10×15mm，比模組小 60%）
- ✅ P-MOSFET 自動切換（效率 >99%，壓降僅 0.02V）
- ✅ N-MOSFET 省電 ADC 監測（平時 0μA）
- ✅ 充電電流可調（推薦 130mA）
- ✅ 超長續航（500mAh 電池可用 2-3 個月）
- ✅ Deep Sleep 功耗 < 5.5μA

#### 適用場景
- 低功耗 IoT 裝置
- 電池供電的感測器
- 便攜式電子裝置
- E-Paper 顯示器專案

#### ESP32-C3 vs ESP8266 電源優勢
- **Deep Sleep 電流**: 5μA（ESP8266: 20μA）- 省電 4 倍
- **ADC 解析度**: 12-bit（ESP8266: 10-bit）- 更精確的電量監測
- **ULP 協處理器**: 支援後台處理，ESP8266 無此功能

[查看詳細說明](battery_management/README.md)

---

## 🚀 快速開始

### 前置需求

- **ESP-IDF**: v5.5.1
- **工具鏈**: riscv32-esp-elf-gcc 14.2.0
- **目標晶片**: ESP32-C3 (RISC-V)
- **硬體**: ESP32-C3 SuperMini 開發板或其他 ESP32-C3 開發板

### 安裝 ESP-IDF

請參考 [ESP-IDF 安裝指南](https://docs.espressif.com/projects/esp-idf/en/latest/esp32c3/get-started/index.html)

### 編譯與燒錄

```bash
# 1. 設定 ESP-IDF 環境
. $HOME/esp/esp-idf/export.sh  # Linux/macOS
# 或
C:\Users\<username>\esp\v5.5.1\esp-idf\export.ps1  # Windows PowerShell

# 2. 進入專案目錄（以 blink 為例）
cd blink

# 3. 設定目標晶片（首次）
idf.py set-target esp32c3

# 4. 編譯
idf.py build

# 5. 燒錄（請將 COM4 替換為你的串口）
idf.py -p COM4 flash

# 6. 監控輸出
idf.py -p COM4 monitor

# 或者合併步驟 5 和 6
idf.py -p COM4 flash monitor
```

### 串口設定

- **Windows**: 通常是 `COM3`, `COM4` 等
- **Linux**: 通常是 `/dev/ttyUSB0`, `/dev/ttyUSB1` 等
- **macOS**: 通常是 `/dev/cu.usbserial-xxx`

查看串口：
```bash
# Windows (PowerShell)
[System.IO.Ports.SerialPort]::getportnames()

# Linux
ls /dev/ttyUSB*

# macOS
ls /dev/cu.*
```

## 🎓 學習路徑建議

### 初學者（第 1-2 週）
1. 從 **hello_world** 開始，熟悉開發環境
2. 嘗試 **blink** 專案，學習 GPIO 控制
3. 閱讀 ESP-IDF 基礎文檔

### 進階學習（第 3-4 週）
4. 學習 **esp32c3_wifi_led_control**，掌握 WiFi 連接
5. 嘗試修改網頁介面，增加功能

### 實作專案（第 5-8 週）
6. 挑戰 **esp32c3_spi_display**，驅動 E-Paper 顯示器
7. 進階到 **esp32c3_wifi_display**，結合 WiFi 和顯示器
8. 研究 **battery_management**，打造低功耗裝置

### 獨立開發（第 9 週+）
9. 結合多個專案的技術，開發自己的 IoT 應用
10. 分享你的專案成果！

## 💡 專案組合建議

### 組合 1：智能電子標籤
- **esp32c3_wifi_display** + **battery_management**
- 適合製作可遠端更新、電池供電的電子標籤
- 續航時間：2-3 個月（每日更新 2 次）

### 組合 2：智能家居控制中心
- **esp32c3_wifi_led_control** + 自訂感測器
- 透過網頁控制家中裝置
- 可擴展加入溫濕度、人體感應等功能

### 組合 3：離線資訊顯示
- **esp32c3_spi_display** + **battery_management**
- 顯示天氣、日曆、待辦事項等
- 超低功耗，適合長期使用

## 📖 文件資源

### 官方文件
- [ESP32-C3 技術參考手冊](docs/esp32-c3_technical_reference_manual_en.pdf)
- [ESP32-C3 數據手冊](docs/esp32_c3_datasheet.pdf)
- [ESP-IDF 程式設計指南](https://docs.espressif.com/projects/esp-idf/en/latest/esp32c3/)

### 硬體資源
- [ESP32-C3 SuperMini 電路圖](docs/esp32-c3-supermini-schematic.png)
- [ESP32-C3 SuperMini 腳位圖](docs/esp32_c3_supermini_pinout.jpg)
- 元件規格書：查看 `docs/` 目錄

## 🛠️ 開發工具推薦

- **IDE**: Visual Studio Code + ESP-IDF 擴充功能
- **串口工具**: PuTTY, minicom, 或 `idf.py monitor`
- **版本控制**: Git
- **電路圖**: KiCad, EasyEDA

## ❓ 常見問題

### Q1: 燒錄失敗怎麼辦？
**A**: 
1. 確認串口正確（`idf.py -p COM4 flash`）
2. 按住 BOOT 按鈕，按一下 RESET 按鈕，然後放開 BOOT
3. 檢查 USB 線材是否支援數據傳輸
4. 嘗試降低波特率：`idf.py -p COM4 -b 115200 flash`

### Q2: 編譯錯誤怎麼辦？
**A**:
1. 確認 ESP-IDF 版本是 v5.5.1
2. 執行 `idf.py fullclean` 清除建置檔案
3. 重新編譯：`idf.py build`
4. 檢查是否缺少相依套件

### Q3: WiFi 連接失敗？
**A**:
1. 檢查 WiFi 帳號密碼是否正確
2. 確認路由器支援 2.4GHz（ESP32-C3 不支援 5GHz）
3. 查看串口輸出的錯誤訊息
4. 嘗試重置 WiFi 設定：`idf.py erase-flash`

### Q4: E-Paper 顯示器沒反應？
**A**:
1. 檢查接線是否正確（參考專案 README）
2. 確認 E-Paper 型號是否正確（GDEQ0426T82）
3. 檢查 BUSY 腳位是否正常（高電平表示正在更新）
4. 嘗試全螢幕更新而非部分更新

### Q5: 如何降低功耗？
**A**:
1. 使用 Deep Sleep 模式（參考 battery_management）
2. 關閉不需要的週邊設備（WiFi, BLE）
3. 降低 CPU 頻率
4. 參考 [ESP32-C3 低功耗模式指南](docs/ESP32C3_POWER_FEATURES.md)

## 🤝 貢獻

歡迎提出 Issue 或 Pull Request！

如果你有：
- 🐛 發現 Bug
- 💡 新功能建議
- 📝 文件改進
- 🎨 範例程式碼

請隨時開啟 Issue 討論或直接提交 PR。

## 📝 版本歷史

- **v1.0** (2025-10-28)
  - 完成 E-Paper 驅動程式
  - 實現圖形繪製功能
  - 加入中英文字體系統
  - 加入網格測試模式
  - 新增電池管理系統文檔

## 📄 授權

MIT License

---

## 📧 聯絡方式

如有任何問題或建議，請透過 GitHub Issues 聯繫。

---

**祝你開發順利！Happy Coding! 🎉**
