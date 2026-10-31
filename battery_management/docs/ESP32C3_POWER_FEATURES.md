# ESP32-C3 電源管理特性詳解

本文件深入介紹 ESP32-C3 的電源管理特性，以及如何應用於電池供電場景。

---

## 🔋 ESP32-C3 電源模式概覽

ESP32-C3 支援多種電源模式，可根據應用場景切換：

| 模式 | CPU | WiFi | 藍牙 | RTC | 電流消耗 | 喚醒時間 |
|------|-----|------|------|-----|----------|----------|
| **Active** | ✅ | ✅ | ✅ | ✅ | 80-120mA | - |
| **Modem Sleep** | ✅ | 間歇 | 間歇 | ✅ | 20-40mA | 即時 |
| **Light Sleep** | ⏸️ | ❌ | ❌ | ✅ | 800μA | 3-5ms |
| **Deep Sleep** | ❌ | ❌ | ❌ | ✅ | **5μA** | 100-300ms |
| **Hibernation** | ❌ | ❌ | ❌ | ⏸️ | 1μA | 200-400ms |

> ESP32-C3 **沒有 ULP 協處理器**，Deep Sleep 時沒有任何處理器在跑，見下方「ESP32-C3 沒有 ULP 協處理器」。

> 💡 **電子紙應用推薦**: **Deep Sleep**，每日喚醒 1-2 次更新顯示，其餘時間休眠。

---

## 🌙 Deep Sleep 模式詳解

### 1. Deep Sleep 特性

在 Deep Sleep 模式下：
- ✅ **保留**: RTC 控制器、RTC 記憶體（8KB）、RTC GPIO（GPIO0~5，可喚醒；GPIO6~21 為高阻抗）
- ❌ **關閉**: CPU、WiFi、藍牙、大部分 GPIO、外設（SPI/I2C/UART）
- 💾 **RAM**: 主記憶體不保留，需存儲重要數據到 RTC Memory
- ⚡ **電流**: 典型 **5μA**（@ 3.3V）

### 2. 喚醒方式

ESP32-C3 支援以下喚醒源：

#### a) Timer 喚醒（最常用）
```c
#include "esp_sleep.h"

// 設定 10 分鐘後喚醒
esp_sleep_enable_timer_wakeup(10 * 60 * 1000000ULL); // 單位: 微秒
esp_deep_sleep_start();
```

#### b) GPIO 喚醒（外部中斷）

ESP32-C3 只有 **GPIO0 ~ GPIO5**（VDD3P3_RTC 供電的腳）能把晶片從 Deep Sleep 喚醒，其他 GPIO 只能喚醒 Light Sleep。
```c
// GPIO1（電池背板 TP4054 CHRG）變 Low = 開始充電時喚醒
esp_deep_sleep_enable_gpio_wakeup(BIT(1), ESP_GPIO_WAKEUP_GPIO_LOW);
esp_deep_sleep_start();
```

> ESP32-C3 **不支援 EXT0 / EXT1 喚醒**（`esp_sleep_enable_ext0_wakeup()` / `ext1` 是 ESP32、S2、S3 的 API）。C3 的 Deep Sleep 喚醒源只有 Timer 和上面的 GPIO 喚醒。

### 3. RTC Memory 應用

RTC Memory 在 Deep Sleep 期間保持數據，用於：
- 儲存 WiFi 連線資訊（加速重連）
- 儲存狀態變數（如更新計數、上次電池電壓、上次顯示內容的版本號）

**範例**:
```c
RTC_DATA_ATTR static uint32_t boot_count = 0;        // 宣告 RTC 變數
RTC_DATA_ATTR static uint32_t last_content_hash = 0; // 上次顯示內容的版本 / hash

void app_main(void)
{
    boot_count++;
    ESP_LOGI(TAG, "開機次數: %" PRIu32, boot_count);

    // 內容沒變就不用刷新，直接回去睡
    if (new_content_hash == last_content_hash) {
        esp_deep_sleep_start();
    }
}
```

**RTC Memory 容量**: 8KB（ESP32-C3），相比 ESP8266 的 512 bytes 大 16 倍！

> ⚠️ **整張 framebuffer 放不進 RTC Memory**：800×480 黑白一張就要 48,000 bytes，C3 的 RTC Memory 只有 8KB（C3 只有 RTC FAST memory，所有 `RTC_DATA_ATTR` 變數都放這裡）。
> - 電子紙**斷電也會保留畫面**，不需要為了「維持顯示」保存 framebuffer。
> - 要保留圖片避免重新下載，就存到 **Flash**（NVS 或自訂資料分區），醒來再讀回 RAM。
> - RTC Memory 只放小的狀態變數（計數、hash、WiFi channel／BSSID）。

---

## 📊 電源消耗實測數據

### 測試條件
- 開發板: ESP32-C3-DevKitM-1
- 電源: 3.3V
- 測試工具: μCurrent Gold 電流表

### Active 模式（WiFi 連線中）
```
平均電流: 120mA
峰值電流: 200mA（TX 時）
持續時間: 通常 < 10 秒（連線 + 下載圖片）
```

### Deep Sleep 模式
```
平均電流: 5-7μA
實測最低: 4.8μA（關閉所有外設）
實測最高: 8μA（保留 RTC GPIO 輸出）
```

### Light Sleep 模式
```
平均電流: 800-1200μA
適用場景: 需要快速喚醒（如 3ms）且不在意電流的場景
```

---

## 🔌 工作電壓範圍

### ESP32-C3 電壓規格
- **推薦範圍**: 3.0V - 3.6V
- **絕對極限**: 2.3V - 3.6V
- **典型電壓**: 3.3V

### 與鋰電池電壓對應

| 電池電壓 | 電量 | ESP32-C3 狀態 | 建議動作 |
|----------|------|---------------|----------|
| 4.2V | 100% | ⚠️ 超出範圍 | **需 LDO 穩壓至 3.3V** |
| 3.7V | 50% | ✅ 正常 | 可直接供電 |
| 3.3V | 15% | ✅ 正常 | 可直接供電 |
| 3.0V | 5% | ⚠️ 臨界 | 進入低功耗保護 |
| 2.75V | 0% | ❌ 欠壓 | 保護板截止 |

**結論**: 
- 若電池電壓 > 3.6V（如新充滿的 4.2V），**必須加 LDO**
- 若電池電壓 3.0V-3.6V，可直接供電（某些開發板已有板載穩壓）

---

## 🧮 ADC 電池電壓監測

### ESP32-C3 ADC 規格
- **解析度**: 12-bit（0-4095）
- **參考電壓**: 內部 1.1V（可調整衰減）
- **衰減設定**:
  - 0dB: 0-1.0V（預設）
  - 2.5dB: 0-1.35V
  - 6dB: 0-2.0V
  - **11dB**: 0-3.3V（推薦用於電池監測）

### 直接讀取電池電壓（方案 A）

**硬體**: 電池 3.0V-4.2V → ADC（需分壓）

```c
#include "driver/adc.h"
#include "esp_adc_cal.h"

// 配置 ADC (GPIO2 = ADC1_CH2)
adc1_config_width(ADC_WIDTH_BIT_12);
adc1_config_channel_atten(ADC1_CHANNEL_2, ADC_ATTEN_DB_11); // 0-3.3V

// 讀取電壓（分壓電路: 100kΩ + 33kΩ）
int raw = adc1_get_raw(ADC1_CHANNEL_2);
float voltage_adc = (raw / 4095.0) * 3.3;  // ADC 電壓
float battery_voltage = voltage_adc * (100 + 33) / 33.0; // 還原電池電壓
```

### 分壓電路設計

**目標**: 將 4.2V 電池電壓降至 3.3V 以下

```
電池 4.2V ──┬── R1 (100kΩ) ──┬── R2 (33kΩ) ──┬── GND
            │                 │                │
            │                 └───> ADC (GPIO2)
            │
            └──────────────────────> 供電
```

**分壓比例**: 
- Vout = Vin × R2 / (R1 + R2)
- Vout = 4.2V × 33kΩ / 133kΩ = **1.04V** ✅（< 3.3V，安全）

**電量換算**:
| 電池電壓 | ADC 電壓 | ADC 值（12-bit） | 電量 |
|----------|----------|------------------|------|
| 4.2V | 1.04V | 1290 | 100% |
| 3.7V | 0.92V | 1138 | 50% |
| 3.3V | 0.82V | 1015 | 15% |
| 3.0V | 0.74V | 917 | 5% |

---

## 🚫 ESP32-C3 沒有 ULP 協處理器

ESP32-C3 **沒有** ULP（Ultra Low Power）協處理器，`esp_sleep_enable_ulp_wakeup()`、`ulp_run()` 在 C3 上不能用。Deep Sleep 時沒有處理器在跑，無法在背景定時讀 ADC、只在電壓過低時才喚醒主 CPU。

### 替代做法：定時喚醒電池監測

**場景**：定期檢查電池電壓，低於門檻才做事

1. 設定 Timer 喚醒後進入 Deep Sleep
2. 醒來後先讀 ADC（不開 WiFi，約數 ms）
3. 電壓正常 → 立刻回 Deep Sleep；過低 → 處理警告

```c
esp_sleep_enable_timer_wakeup(10 * 60 * 1000000ULL);  // 10 分鐘
esp_deep_sleep_start();
```

每次醒來不開 WiFi、只讀 ADC，耗電遠小於一次 WiFi 更新。想再省，可用 **deep sleep wake stub**：喚醒後先在 RTC 記憶體裡跑一小段程式，判斷不用處理就直接回去睡，不必完整開機（見參考資料）。

### 需要 ULP 時

| 晶片 | 低功耗處理器 |
|------|--------------|
| ESP32-C3 | ❌ 無 |
| ESP32-S3 | ✅ ULP（RISC-V + FSM） |
| ESP32-C6 | ✅ LP 核心（RISC-V） |

---

## 🔧 Deep Sleep 優化技巧

### 1. 減少喚醒時間（100ms → 50ms）

**方法**: 保存 WiFi 連線資訊到 RTC Memory
```c
RTC_DATA_ATTR uint8_t wifi_channel = 0;
RTC_DATA_ATTR uint8_t wifi_bssid[6];

void fast_wifi_connect() {
    if (wifi_channel > 0) {
        // 使用已知的 channel 和 BSSID，加速連線
        WiFi.begin(ssid, password, wifi_channel, wifi_bssid);
    } else {
        WiFi.begin(ssid, password);
        // 儲存資訊供下次使用
        wifi_channel = WiFi.channel();
        memcpy(wifi_bssid, WiFi.BSSID(), 6);
    }
}
```

### 2. 部分硬體保持供電

**場景**: Deep Sleep 期間讓 E-Paper 的 RES（GPIO5）保持 High，不要浮接

ESP32-C3 上用 `gpio_hold_en()` 加 `gpio_deep_sleep_hold_en()`（只呼叫 `gpio_hold_en()` 在 Deep Sleep 期間不會保持；`rtc_gpio_*` 是 ESP32、S2、S3 的 API）。
```c
#include "driver/gpio.h"

// 進入 Deep Sleep 前
gpio_set_direction(GPIO_NUM_5, GPIO_MODE_OUTPUT);
gpio_set_level(GPIO_NUM_5, 1);
gpio_hold_en(GPIO_NUM_5);        // 鎖定這支腳
gpio_deep_sleep_hold_en();       // Deep Sleep 期間保持所有已鎖定的腳
esp_deep_sleep_start();

// 醒來後：先把腳設回輸出並給好電位，再解除鎖定（解除時會回到預設模式）
gpio_set_direction(GPIO_NUM_5, GPIO_MODE_OUTPUT);
gpio_set_level(GPIO_NUM_5, 1);
gpio_hold_dis(GPIO_NUM_5);
```
> BUSY 是輸入腳，不需要鎖定。

### 3. 減少 Serial 輸出

```c
// 生產環境關閉 Serial（節省 ~2mA + 加速開機）
esp_log_level_set("*", ESP_LOG_NONE);
```

---

## 📐 功耗計算範例

### 場景: 每日早上 7:00 更新天氣

**時間分配**:
- Deep Sleep: 23 小時 59 分
- Active (WiFi 連線 + E-Paper 更新): 1 分鐘

**電流消耗**:
- Deep Sleep: 5μA × 23.983 小時 = 0.12mAh
- Active: 120mA × 0.017 小時 (1 分鐘) = 2.04mAh
- **總計**: 2.16mAh/天

**續航時間**（3400mAh 電池）:
- 理論: 3400mAh ÷ 2.16mAh/天 = **1574 天**
- 實際（考慮保護板自耗 + 電池自放電）: **21-30 天**

---

## 🆚 與 ESP8266 對比

| 項目 | ESP32-C3 | ESP8266 | 差異 |
|------|----------|---------|------|
| Deep Sleep 電流 | 5μA | 20μA | **ESP32-C3 省 4 倍** |
| RTC Memory | 8KB | 512 bytes | ESP32-C3 大 16 倍 |
| 喚醒時間 | 100-300ms | 300-500ms | ESP32-C3 快 40% |
| ADC 精度 | 12-bit | 10-bit | ESP32-C3 精度 4 倍 |
| ULP 協處理器 | ❌ | ❌ | 兩者都沒有（S3、C6 才有） |
| WiFi 功耗 | 120mA | 80mA | ESP8266 略優 |

**總結**: 對於電池供電的電子紙應用，ESP32-C3 的超低休眠功耗優勢明顯。

---

## 📚 參考資料

- [ESP32-C3 Datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-c3_datasheet_en.pdf)
- [ESP32-C3 Low Power Mode Guide](https://docs.espressif.com/projects/esp-idf/en/latest/esp32c3/api-guides/low-power-mode.html)
- [ESP-IDF Sleep Modes API](https://docs.espressif.com/projects/esp-idf/en/latest/esp32c3/api-reference/system/sleep_modes.html)
- [ESP-IDF GPIO API (ESP32-C3)：gpio_hold_en / gpio_deep_sleep_hold_en](https://docs.espressif.com/projects/esp-idf/en/latest/esp32c3/api-reference/peripherals/gpio.html)
- [Deep-sleep Wake Stubs (ESP32-C3)](https://docs.espressif.com/projects/esp-idf/en/latest/esp32c3/api-guides/deep-sleep-stub.html)
