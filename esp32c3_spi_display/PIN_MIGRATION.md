# 腳位調整交接（2026-10-31）：MOSI 改 IO7、加兩顆喚醒按鈕

這份文件給接手的 session。決定已經做好，照這份改 `esp32c3_spi_display` 就好。

## 為什麼要改

這個專案要同時接三樣東西：電子紙（DESPI-C02 / GDEQ0426T82）、電池背板 v2.1、兩顆能把 ESP32-C3 從 deep sleep 叫醒的按鈕。

ESP32-C3 有兩個限制：
- **能從 deep sleep 喚醒的只有 GPIO0–5**（`esp_deep_sleep_enable_gpio_wakeup`）。
- **能用的 ADC 只有 GPIO0–4**（ADC1）。GPIO5 是 ADC2，C3 的 ADC2 有硬體問題，ESP-IDF 已不支援。

所以 GPIO0–5 要留給電量偵測和按鈕，其他訊號往外搬。電子紙的 SPI 走 GPIO 矩陣，可以接任何腳。

## 新的腳位分配（定案）

| GPIO | 用途 | 跟舊版比 |
|---|---|---|
| IO0 | 電池 VBAT/2（ADC1_CH0，1M/1M 分壓） | 不變 |
| **IO1** | **按鈕 A**（deep sleep 喚醒，低電位觸發） | 新增（原本是 CHRG） |
| IO2 | 電子紙 SCLK | 不變 |
| **IO3** | **按鈕 B**（deep sleep 喚醒，低電位觸發） | 新增（原本是 MOSI） |
| IO4 | 電子紙 DC | 不變 |
| IO5 | 電子紙 RST | 不變 |
| IO6 | 電子紙 BUSY | 不變 |
| **IO7** | **電子紙 MOSI（SDI）** | 從 IO3 搬來；IO7 是 C3 硬體 SPI 原生的 FSPID 腳 |
| IO10 | 電子紙 CS | 不變 |
| **IO20** | 電池 TP4054 CHRG（Low = 充電中，內部上拉） | 從 IO1 搬來（電池背板已實測，見下方） |
| IO8 | 空，板上藍色 LED（Low = 亮），strapping | — |
| IO9 | 空，板上 BOOT 鍵，strapping；醒著時可當第 3 顆按鈕，不能喚醒 deep sleep | — |
| IO21 | 空，UART0 TX，開機時會輸出 ROM 訊息 | — |

按鈕不放 IO2：IO2 是 strapping 腳，開機時必須是 High，按著按鈕重開會開不了機。

## 要做的事

### 1. 程式（`main/epaper_driver.h`）
```c
#define PIN_MOSI            7    // 原本 3
#define PIN_MISO            -1   // 原本借用 5 佔位，但 5 是 RST，改成不使用
```
- 確認 `epaper_driver.c` 的 `spi_bus_config_t` 在 `miso_io_num = -1` 時正常（ESP-IDF 支援 -1）。
- `spi_display_main.c` 開機印腳位的地方會自動跟著變，不用改。
- 更新 `README.md` 的腳位表。

### 2. 按鈕與 deep sleep 喚醒（新增）
- 接法：按鈕一端接 GPIO，另一端接 GND；每顆加 **100 kΩ 上拉到 3V3**（deep sleep 時一定維持 High，不靠內部上拉）。
- 進 deep sleep 前：
  ```c
  esp_deep_sleep_enable_gpio_wakeup(BIT(1) | BIT(3), ESP_GPIO_WAKEUP_GPIO_LOW);
  ```
- 醒來後：`esp_sleep_get_wakeup_cause()` 為 `ESP_SLEEP_WAKEUP_GPIO` 時，用 `esp_sleep_get_gpio_wakeup_status()` 判斷是 IO1 還是 IO3。
- 按鈕醒著時也要能讀（例如換頁），記得去彈跳。
- 進 deep sleep 前如果按鈕還按著（Low），低電位喚醒會立刻觸發：先等放開再睡。

### 3. 電池（如果這個專案要一起讀電池）
照 `../battery_management/firmware/battery_monitor_v2/main/battery_monitor_main.c`：
- VBAT：ADC1_CH0（GPIO0），`ADC_ATTEN_DB_12` + `adc_cali` 曲線校正，16 次平均 × 2。
- CHRG：GPIO20，輸入 + 內部上拉，Low = 充電中。GPIO20 不能喚醒 deep sleep，只用來讀狀態。
- 量 VBAT 要在開 WiFi / BLE 之前。

### 4. 實體接線
- DESPI-C02 的 **SDI** 線從 SuperMini 的 IO3 改焊到 **IO7**（右排第 3 根，背面看 USB 朝上）。
- 按鈕 A → IO1（左排第 7 根）、按鈕 B → IO3（左排第 5 根），各加 100 kΩ 上拉到 3.3。

### 5. 驗證
- 編譯：`idf.py set-target esp32c3 && idf.py build`（這台 PC 沒有 ESP-IDF 的話，用 Arduino 寫一支等效的測試程式也可以）。
- 開機 log 的腳位表顯示 MOSI = 7。
- 電子紙全刷、局部刷新都正常。
- deep sleep 後分別按 A、B，都能叫醒並正確判斷是哪一顆。

## 已經完成、不用再做的
- 電池背板 v2.1（`../battery_management/hardware/kicad_v2`）已手焊實測：拔插 USB 不重開；只用電池時 ADC 讀 4.110 V、電表 4.111 V；CHRG 在 IO20 讀得到 Low。
- 電池背板的文件與 `battery_monitor_v2` 韌體已改成 CHRG = GPIO20（commit `411cd9d`）。
- 測試程式：`../battery_management/firmware/battery_test_v2`（Arduino，`--fqbn esp32:esp32:esp32c3:CDCOnBoot=cdc`）。

## 不要動的
- `../EPD24_SuperMini_Adapter_HW/`（整合板）：另一個 session 正在改成同一組腳位。
- 電池背板的 PCB / Gerber：已下單，絲印 P3 仍印「IO1」，實際接 IO20。
