# ESP32-C3 電池供電官方設計規範實作

本文件基於 Espressif 官方 [ESP32-C3 Hardware Design Guidelines](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c3/) 實作電池供電系統。

---

## 📘 官方規範摘要

### 1. 電源供應要求（Power Supply）

#### 官方推薦配置
```
來源: ESP32-C3 Hardware Design Guidelines > Power Supply
```

| 供電引腳 | 電壓範圍 | 典型值 | 濾波電容 | 說明 |
|----------|----------|--------|----------|------|
| **VDD3P3_CPU** (Pin 17) | 3.0V - 3.6V | 3.3V | 0.1μF | 數位電源，靠近引腳 |
| **VDD3P3** | 3.0V - 3.6V | 3.3V | 10μF + 0.1μF | 類比/RF 電源，加 LC 濾波 |
| **VDD3P3_RTC** | 3.0V - 3.6V | 3.3V | 0.1μF | RTC 電源 |
| **VDD_SPI** (Pin 18) | 3.0V - 3.6V | 3.3V | 1μF | Flash 供電（由 VDD3P3_CPU 提供）|

**關鍵要求**:
- ✅ **推薦系統電壓**: 3.3V
- ✅ **最小輸出電流**: 500mA
- ✅ **電源入口**: ESD 二極體 + 至少 10μF 電容
- ✅ **VDD3P3 LC 濾波**: 電感額定電流 ≥ 500mA

#### RF 電源特殊要求
```
來源: Hardware Design Guidelines > Analog Power Supply
```

VDD3P3（RF 電源）在 WiFi 傳輸時電流突增，需要：
1. **10μF 電容**（與 0.1μF 配合，抑制電壓塌陷）
2. **LC 濾波電路**（抑制高頻諧波）
   - 電感: 建議 2.2μH - 4.7μH
   - 額定電流: ≥ 500mA
   - 推薦型號: TDK MLZ2012M2R2W 或類似

---

## 🔋 電池供電架構設計

### 方案: 標準 LDO 穩壓（官方推薦）

#### 完整架構圖

```
USB 5V (充電)
   |
   ▼
┌──────────────────┐
│   TP4056 充電    │
│   + DW01A 保護   │  ← 鋰電池充電管理
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  18650 鋰電池    │
│  3.7V 3400mAh    │  ← 能量存儲
│  (帶保護板)      │
└────────┬─────────┘
         │ BAT+ (3.2V-4.2V)
         │
┌────────▼─────────┐
│  LDO 穩壓器      │
│  ME6211C33       │  ← 3.3V 穩壓輸出
│  或 XC6206P332   │
└────────┬─────────┘
         │ 3.3V
         ├─────────────────┬────────────────────┬─────────────────┐
         │                 │                    │                 │
         ▼                 ▼                    ▼                 ▼
    ┌────────┐      ┌──────────┐        ┌──────────┐      ┌─────────┐
    │10μF    │      │ LC 濾波   │        │ 0.1μF    │      │ 0.1μF   │
    │(電源   │      │ (L=2.2μH) │        │          │      │         │
    │ 入口)  │      │ (C=10μF)  │        │          │      │         │
    └───┬────┘      └─────┬────┘        └────┬─────┘      └────┬────┘
        │                 │                   │                 │
        ▼                 ▼                   ▼                 ▼
       GND          VDD3P3 (RF)       VDD3P3_CPU (Pin17)  VDD3P3_RTC
                    類比/RF電源         數位電源             RTC電源
                    
                    
電池電壓監測 (ADC):
BAT+ ──┬── 100kΩ ──┬── 33kΩ ──┬── GND
       │           │          │
       │           └──────────> GPIO0 (ADC1_CH0)
       │
       └──────────────────────> (供電)
```

---

## 🔧 核心組件選型

### 1. LDO 穩壓器

根據官方要求（500mA 輸出，低靜態電流），推薦以下 LDO：

#### 方案 A: ME6211C33 (Microne) ⭐ 推薦

| 參數 | 規格 | 符合官方要求 |
|------|------|--------------|
| 輸出電壓 | 3.3V ±2% | ✅ |
| 輸入電壓 | 2.0V - 6.0V | ✅ 支援 3.2V-4.2V 電池 |
| 最大電流 | 500mA | ✅ 剛好滿足 |
| 靜態電流 | 3μA (典型) | ✅ 不影響 Deep Sleep |
| Dropout | 90mV @ 100mA | ✅ 電池 3.4V 時仍可輸出 3.3V |
| 封裝 | SOT-23-5 | 易焊接 |
| 價格 | NT$8 | 便宜 |

**電路連接**:
```
ME6211C33 (SOT-23-5)
Pin 1: VIN  ← 電池 + (3.2V-4.2V)
Pin 2: GND  → 地
Pin 3: EN   ← 使能（接 VIN 或 CHIP_EN 控制）
Pin 4: NC   （不接）
Pin 5: VOUT → 3.3V 輸出
```

#### 方案 B: XC6206P332 (Torex)

| 參數 | 規格 |
|------|------|
| 輸出電壓 | 3.3V ±2% |
| 輸入電壓 | 1.8V - 6.0V |
| 最大電流 | 200mA |
| 靜態電流 | 1μA |
| Dropout | 250mV @ 100mA |
| 封裝 | SOT-89 |
| 價格 | NT$10 |

⚠️ 注意：最大電流只有 200mA，需確認 WiFi 峰值電流不超過。

#### 方案 C: MCP1700-3302 (Microchip)

| 參數 | 規格 |
|------|------|
| 輸出電壓 | 3.3V ±4% |
| 輸入電壓 | 2.7V - 6.0V |
| 最大電流 | 250mA |
| 靜態電流 | 1.6μA |
| Dropout | 178mV @ 250mA |
| 封裝 | TO-92 (直插) |
| 價格 | NT$15 |

✅ 適合麵包板測試（直插），但最大電流略低。

**選型建議**: 
- **自製 PCB**: 用 **ME6211C33**（500mA，低靜態）
- **麵包板測試**: 用 **MCP1700-3302**（直插）
- **低功耗優先**: 用 **XC6206P332**（1μA）

---

### 2. 濾波電容配置

根據官方設計指南要求：

#### 電源入口（LDO 輸入）
```
推薦: 10μF 陶瓷電容（X7R 或 X5R）
位置: LDO VIN 引腳附近（< 5mm）
作用: 吸收充電切換瞬態，提供瞬時電流
```

#### VDD3P3_CPU (Pin 17)
```
推薦: 0.1μF 陶瓷電容
位置: 靠近 Pin 17（< 3mm）
作用: 高頻去耦，抑制數位雜訊
```

#### VDD3P3 (RF 電源)
```
推薦: 10μF + 0.1μF 並聯
位置: LC 濾波器輸出端，靠近晶片
作用: 
  - 10μF: 防止 WiFi 傳輸時電壓塌陷
  - 0.1μF: 高頻去耦
```

#### VDD3P3_RTC
```
推薦: 0.1μF 陶瓷電容
位置: 靠近 RTC 電源引腳
作用: RTC 穩定運行
```

**電容選型建議**:
| 容值 | 封裝 | 電壓 | 介質 | 數量 | 單價 |
|------|------|------|------|------|------|
| 10μF | 0805 | 10V | X7R | 2 | NT$2 |
| 0.1μF | 0603 | 16V | X7R | 3 | NT$1 |

---

### 3. LC 濾波電路（VDD3P3 RF 電源）

#### 官方要求
```
來源: Hardware Design Guidelines > Analog Power Supply

"Add an LC circuit to the VDD3P3 power rail to suppress high-frequency harmonics.
The inductor's rated current is preferably 500 mA and above."
```

#### 推薦配置

**電感選型**: 
| 型號 | 電感值 | 額定電流 | DCR | 封裝 | 價格 |
|------|--------|----------|-----|------|------|
| TDK MLZ2012M2R2W | 2.2μH | 700mA | 0.3Ω | 0805 | NT$5 |
| Murata BLM21PG220SN1 | 22μH | 500mA | 0.5Ω | 0805 | NT$4 |
| Sunlord GZ2012D221TF | 220nH | 1A | 0.15Ω | 0805 | NT$3 |

**推薦**: TDK MLZ2012M2R2W（平衡性能，高額定電流）

**電路連接**:
```
LDO 3.3V ──> [L = 2.2μH] ──┬──> [C = 10μF] ──┬──> VDD3P3 (RF)
                            │                │
                            └──> [C = 0.1μF] ┴──> GND
```

---

### 4. 電池與充電模組

#### 18650 鋰電池（推薦）

| 型號 | 容量 | 電壓 | 保護 | 價格 |
|------|------|------|------|------|
| Samsung ICR18650-26F | 2600mAh | 3.7V | 帶保護板 | NT$60 |
| Panasonic NCR18650B | 3400mAh | 3.7V | 帶保護板 | NT$80 |

**必須帶保護板**（DW01A + FS8205A），防止：
- 過充（> 4.3V）
- 過放（< 2.5V）
- 短路

#### TP4056 充電模組

| 參數 | 規格 |
|------|------|
| 輸入電壓 | 4.5V - 5.5V（USB 5V）|
| 充電電流 | 1000mA（預設，可調）|
| 充電截止 | 4.2V ±1% |
| 保護功能 | 過充/過放/短路（DW01A）|
| 狀態指示 | CHRG（紅燈）, STDBY（藍燈）|
| 價格 | NT$20 |

---

## ⚡ CHIP_EN 電源時序控制

### 官方要求

根據 Hardware Design Guidelines > Chip Power-up and Reset Timing：

```
"When ESP32-C3 uses a 3.3 V system power supply, the power rails need some time
to stabilize before CHIP_EN is pulled up and the chip is enabled."
```

**時序參數**:
| 參數 | 說明 | 最小值 |
|------|------|--------|
| tSTBL | 電源穩定後，CHIP_EN 拉高前的延遲 | 50 μs |
| tRST | CHIP_EN 保持 LOW 以重置晶片 | 50 μs |

### RC 延遲電路

**官方推薦**: R = 10kΩ, C = 1μF

```
3.3V ──┬────────────────────> CHIP_EN (Pin 7)
       │
       R = 10kΩ
       │
       ├─── C = 1μF ───┬─── GND
       │               │
       │               │
    [Reset Button] ────┘
```

**工作原理**:
1. 上電時，C 充電，CHIP_EN 緩慢上升
2. RC 時間常數 τ = 10kΩ × 1μF = 10ms（遠大於 50μs）
3. 按下 Reset Button，C 放電，CHIP_EN 瞬間拉 LOW

**改進方案**（針對電池充電場景）:

若有慢速電源上升（如電池充電），官方建議加入：
- **外部複位 IC**（如 MCP120 或 TPL5110）
- **閾值電壓**: 約 3.0V

```
3.3V ──> [MCP120-300 複位 IC] ──> CHIP_EN
            閾值 3.0V
```

---

## 📊 ADC 電池電壓監測

### 官方 ADC 規格

根據 Hardware Design Guidelines > ADC：

**建議使用 ADC1**（ADC2 未出廠校準）:
| 衰減設定 | 測量範圍 | 誤差（校準後）| 適用場景 |
|----------|----------|---------------|----------|
| ATTEN=0 | 0 - 750mV | ±10mV | 精密測量 |
| ATTEN=1 | 0 - 1050mV | ±10mV | - |
| ATTEN=2 | 0 - 1300mV | ±10mV | - |
| **ATTEN=3** | **0 - 2500mV** | **±35mV** | **電池監測** ⭐ |

**推薦配置**: 
- 使用 **ATTEN=3 (11dB)**，測量範圍 0-2500mV
- 搭配分壓電路，將 4.2V 降至 ~1.04V

### 分壓電路設計

#### 目標
將電池電壓 3.0V-4.2V 降至 ADC 安全範圍 0-2.5V

#### 電路
```
BAT+ (3.0-4.2V)
   │
   R1 = 100kΩ
   │
   ├─────────> GPIO0 (ADC1_CH0)
   │
   R2 = 33kΩ
   │
  GND
```

#### 計算
**分壓公式**: 
$$V_{ADC} = V_{BAT} \times \frac{R2}{R1 + R2} = V_{BAT} \times \frac{33k\Omega}{133k\Omega} = V_{BAT} \times 0.248$$

**對應表**:
| 電池電壓 | ADC 電壓 | ADC 值 (12-bit) | 電量 % |
|----------|----------|-----------------|--------|
| 4.2V (100%) | 1.04V | 1290 | 100% |
| 4.0V (80%) | 0.99V | 1227 | 80% |
| 3.7V (50%) | 0.92V | 1138 | 50% |
| 3.5V (30%) | 0.87V | 1077 | 30% |
| 3.3V (15%) | 0.82V | 1015 | 15% |
| 3.0V (5%) | 0.74V | 917 | 5% |

✅ 所有電壓均 < 2.5V，符合 ATTEN=3 範圍

#### 官方推薦改進

根據 Hardware Design Guidelines > ADC：
```
"Please add a 0.1 μF filter capacitor between ESP pins and ground when using the
ADC function to improve accuracy."
```

**改進後電路**:
```
BAT+ ──┬── 100kΩ ──┬── 33kΩ ──┬── GND
       │           │          │
       │           ├── 0.1μF ──┤
       │           │          │
       │           └──────────> GPIO0 (ADC1_CH0)
```

**濾波電容作用**: 抑制電源雜訊，提高 ADC 精度

---

## 🛡️ ESD 保護

### 官方建議

```
來源: Hardware Design Guidelines > Power Supply

"It is suggested to add an ESD protection diode and at least 10 μF capacitor at
the power entrance."
```

### ESD 二極體選型

推薦型號: **PESD5V0S1BA** (NXP)

| 參數 | 規格 |
|------|------|
| 鉗位電壓 | 9.2V @ 8A |
| 工作電壓 | 5V |
| 電容 | 35pF |
| 封裝 | SOD-323 |
| 價格 | NT$5 |

### 連接方式

```
USB 5V ──┬──────────> TP4056 IN+
         │
         ├── PESD5V0S1BA ──┬── GND
         │                 │
         └── 10μF ─────────┘
```

---

## 📦 完整 BOM 表

### 主要組件

| 項目 | 型號/規格 | 數量 | 單價 | 小計 | 符合官方規範 |
|------|-----------|------|------|------|--------------|
| **電源管理** |
| LDO 穩壓器 | ME6211C33M (SOT-23-5) | 1 | NT$8 | NT$8 | ✅ 500mA 輸出 |
| 電感（LC 濾波）| TDK MLZ2012M2R2W (2.2μH) | 1 | NT$5 | NT$5 | ✅ 額定 700mA |
| 電容 10μF | 0805 X7R 10V | 3 | NT$2 | NT$6 | ✅ VDD3P3 + 電源入口 |
| 電容 0.1μF | 0603 X7R 16V | 4 | NT$1 | NT$4 | ✅ 各電源引腳 |
| ESD 二極體 | PESD5V0S1BA (SOD-323) | 1 | NT$5 | NT$5 | ✅ 電源保護 |
| **充電與電池** |
| TP4056 模組 | 帶 DW01A 保護 | 1 | NT$20 | NT$20 | ✅ 充電管理 |
| 18650 電池 | 3400mAh 帶保護板 | 1 | NT$70 | NT$70 | ✅ 能量存儲 |
| 電池座 | 18650 單節 | 1 | NT$10 | NT$10 | - |
| **CHIP_EN 控制** |
| 電阻 | 10kΩ 0603 | 1 | NT$1 | NT$1 | ✅ RC 延遲 |
| 電容 | 1μF 0603 | 1 | NT$1 | NT$1 | ✅ RC 延遲 |
| **ADC 監測** |
| 電阻 | 100kΩ 0603 | 1 | NT$1 | NT$1 | ✅ 分壓 |
| 電阻 | 33kΩ 0603 | 1 | NT$1 | NT$1 | ✅ 分壓 |
| 電容（ADC 濾波）| 0.1μF 0603 | 1 | NT$1 | NT$1 | ✅ 官方推薦 |
| **其他** |
| 杜邦線、麵包板 | - | - | NT$20 | NT$20 | 測試用 |

### 總計
- **核心組件**: NT$113
- **含測試材料**: NT$133

✅ **所有組件符合官方硬體設計規範**

---

## 🔌 完整電路圖

### 原理圖（符合官方設計）

```
                           ESP32-C3 晶片
                    ┌─────────────────────────┐
                    │                         │
USB 5V ──┬─> ESD ──┬─> [10μF] ─┬─> GND       │
         │         │           │             │
         └─> TP4056 IN+         │             │
              │                 │             │
              ├─> B+ ─> 18650 Battery         │
              │    B- ─> GND                  │
              │                                │
              └─> OUT+ ──┬──> [10μF] ──┬─> GND
                         │             │
                         └──> ME6211C33 (LDO)
                                │
                         ┌──────┴─────────┬───────────┬────────────┐
                         │                │           │            │
                     [10μF]            [2.2μH]    [10kΩ]      [0.1μF]
                         │ (電源入口)     │ (LC)     │ (RC)       │
                         ├────────────────┤          │            │
                         │            [10μF+0.1μF]   │        [0.1μF]
                         │                │          │            │
                      3.3V────┬──────────┴──────────┴────────────┴───
                              │           │          │            │
                              │           │          │            │
                              ▼           ▼          ▼            ▼
                          Pin 17      VDD3P3     Pin 7      VDD3P3_RTC
                        VDD3P3_CPU     (RF)     CHIP_EN      (RTC)
                              │           │          │
                              │           │          └─[1μF]─> GND
                              │           │
                              │           └──────────────────────┐
                              │                                  │
                              │  ┌───────────────────────────┐   │
                              └──┤ ESP32-C3 內部電路          │───┘
                                 │ (WiFi, CPU, Peripherals)  │
                                 └───────────────────────────┘
                                           │
                                         GPIO0 (ADC)
                                           │
                                 ┌─────────┴─────────┐
                  BAT+ ──[100kΩ]─┴─[33kΩ]─┬─[0.1μF]─┬─> GND
                                           │         │
                                           └─────────┘
```

---

## 📋 設計檢查清單

### ✅ 電源設計
- [ ] 使用 3.3V 穩壓輸出（符合官方推薦）
- [ ] LDO 最大電流 ≥ 500mA
- [ ] LDO 靜態電流 < 5μA（不影響 Deep Sleep）
- [ ] VDD3P3_CPU 有 0.1μF 去耦電容（靠近 Pin 17）
- [ ] VDD3P3 (RF) 有 10μF + 0.1μF 電容
- [ ] VDD3P3 有 LC 濾波（L ≥ 2.2μH，額定 ≥ 500mA）
- [ ] VDD3P3_RTC 有 0.1μF 去耦電容
- [ ] 電源入口有 ESD 二極體 + 10μF 電容

### ✅ CHIP_EN 控制
- [ ] RC 延遲電路（R=10kΩ, C=1μF）
- [ ] CHIP_EN 不懸空
- [ ] tSTBL ≥ 50μs（電源穩定時間）
- [ ] tRST ≥ 50μs（複位保持時間）

### ✅ ADC 電池監測
- [ ] 使用 ADC1（不用 ADC2）
- [ ] 分壓電路確保 ADC 電壓 < 2.5V
- [ ] ADC 引腳加 0.1μF 濾波電容
- [ ] 軟體啟用 ATTEN=3 (11dB 衰減)
- [ ] 實作官方軟體校準演算法

### ✅ 充電安全
- [ ] 電池帶保護板（DW01A + FS8205A）
- [ ] TP4056 充電電流 ≤ 1C（3400mAh 電池用 1A）
- [ ] 充電狀態指示（CHRG/STDBY LED）

### ✅ PCB 佈局（若自製 PCB）
- [ ] 電源引腳附近電容 < 5mm
- [ ] VDD3P3 LC 濾波靠近晶片
- [ ] 電源走線加粗（≥ 0.5mm）
- [ ] GND 大面積鋪銅

---

## 📚 參考文件

### 官方文件
1. [ESP32-C3 Hardware Design Guidelines](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c3/schematic-checklist.html)
2. [ESP32-C3 Datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-c3_datasheet_en.pdf)
3. [ESP32-C3 Technical Reference Manual](https://www.espressif.com/sites/default/files/documentation/esp32-c3_technical_reference_manual_en.pdf)
4. [ESP-IDF ADC Calibration](https://docs.espressif.com/projects/esp-idf/en/latest/esp32c3/api-reference/peripherals/adc_calibration.html)

### 相關資源
- [ESP32-C3 參考電路圖](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c3/_images/esp32c3-sche-core.png)
- [ESP32-C3 Power Scheme](https://www.espressif.com/sites/default/files/documentation/esp32-c3_datasheet_en.pdf#cd-pwr-scheme)
- [TP4056 Datasheet](https://datasheet.lcsc.com/szlcsc/1904031009_TPOWER-TP4056_C382139.pdf)
