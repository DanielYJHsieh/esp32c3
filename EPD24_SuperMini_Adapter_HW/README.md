# EPD24 Super Mini 轉接背板 v1.1（DESPI-C02 縮小版 + 電池管理）

取代 Good Display DESPI-C02（41 × 22 mm）的小型轉接板：直接疊在 **ESP32-C3 Super Mini** 背面，驅動 24pin SPI 電子紙（目前用 GDEQ0426T82，SSD1677）。
**v1.1 併入電池背板 v2.1 的電路**（`../battery_management/hardware/kicad_v2`）：USB 充電、電池 / USB 自動切換、電量偵測，一片搞定。

- 板子 **18.0 × 26.8 mm**，寬同 Super Mini，只多出上緣 FPC 座那一段（v1.0 同尺寸）
- 雙層、零件全在單面（F 面），0402 為主，可整片交 JLCPCB 貼片
- e-paper 腳位跟 `esp32c3/esp32c3_spi_display`（`main/epaper_driver.h`）一樣，但 **SDI 改到 IO7**，韌體要跟著改 `PIN_MOSI`（見「韌體備註」）；電池腳位跟 `battery_management/firmware/battery_monitor_v2` 一樣（CHRG = IO20）
- **GPIO0~5 保留給 ADC 和 deep sleep 喚醒**（C3 只有這幾支能從 deep sleep 喚醒，ADC 只有 0~4 能用）：IO0 = VBAT / 2，IO1、IO3 = 兩顆喚醒按鍵（2026-10-31 改腳位）
- v1.0（只有 e-paper，沒有電池電路）凍結在 `release_v1.0/`

## 疊法

```
   Super Mini（晶片、按鍵朝上）
   ─────────── 排針 / 直接焊 ───────────
   本板 B 面（只有絲印：5V / G / 3V3 / USB / CHIP SIDE UP）
   本板 F 面（零件、FPC 座）→ 面板排線從 USB 端插入
   Kapton 絕緣 + 泡棉雙面膠
   鋰電池
```

- Super Mini 的 USB 端對齊本板印「USB」的那一端；FPC 座在同一端，排線往 USB 方向出。
- 從零件面看，Super Mini 的腳位是**左右鏡像**的：左排 5V G 3V3 IO4 IO3 IO2 IO1 IO0，右排 IO5 IO6 IO7 IO8 IO9 IO10 IO20 IO21。
- 本板比 Super Mini 短 2 mm（天線那端），只跟陶瓷天線重疊約 0.5 mm，盡量不影響 WiFi。
- 電池疊在零件面外側，**中間一定要貼 Kapton**，避免電池鋁殼碰到零件。

## 腳位

| 功能 | 訊號 | Super Mini | 接法 |
|---|---|---|---|
| e-paper | BUSY | IO6 | 排針 |
| | RES | IO5 | 排針 |
| | D/C | IO4 | 排針 |
| | CS | IO10 | 排針 |
| | SCLK | IO2 | 排針 |
| | SDI (MOSI) | **IO7**（C3 原生 FSPID） | 排針 |
| 電池 | CHRG（Low = 充電中） | **IO20** | 排針 |
| | VBAT / 2 | IO0（ADC1_CH0） | 排針 |
| 喚醒按鍵 | K1（按下 = Low，100k 上拉） | **IO1** | 排針 + 左側 K1 焊墊 |
| | K2（按下 = Low，100k 上拉） | **IO3** | 排針 + 左側 K2 焊墊 |
| 電源 | VBUS | 5V | 排針 |
| | 3V3（面板、升壓電路） | 3V3 | 排針 |
| | GND | G | 排針 |
| | **VSYS** | **正面 W5 的 A 端** | **右側 VSYS 焊墊飛線** |

用到的 GPIO：0、1、2、3、4、5、6、7、10、20。剩下 IO8、9、21 可另作他用（8、9 是 strapping 腳，接東西要注意）。

左側中段三個焊墊（絲印「K1 K2 G」，由左到右）接外接按鍵：K1、K2 各接一顆常開按鍵，另一端都接 G。按鍵裝在外殼上（零件面會被電池蓋住）。板上已有 R7 / R8 100k 上拉到 3V3，韌體用 `esp_deep_sleep_enable_gpio_wakeup(BIT(1) | BIT(3), ESP_GPIO_WAKEUP_GPIO_LOW)` 即可，不用開內部上拉。

右下角三個焊墊（絲印「VSYS/B+/B-」，由上到下）：

| 焊墊 | 接到 |
|---|---|
| VSYS（TP3） | 28–30 AWG 飛線，繞過板邊到 Super Mini 正面 **W5 的 A 端** |
| B+（TP1） | 電池 + |
| B−（TP2） | 電池 − |

電池線從右側（IO5–21 那側）出，跟電池背板 v2 一樣；可焊 1.25 mm 2P 公母對插線，電池可單獨更換。

## 電路

### e-paper（同 v1.0）

照原廠原理圖 `DESPI-C02_SCH V1.0`（2018.07.06）。

| 項目 | DESPI-C02 | 本板 |
|---|---|---|
| RESE 電阻 | DIP 切 0.47Ω / 3Ω（新版 2.2Ω） | **固定 0.47Ω**（GDEQ0426T82 目前 DIP 撥 0.47） |
| BS | R4 3Ω 接地 + R5 10k 上拉 | 直接接地 |
| 二極體 | MBR0530（SOD-123） | B5819WS（SOD-323，40V 1A） |
| 電感 | 10µH 1A | 10µH、2520 封裝、Isat ≥ 1A |
| 高壓電容 | 4.7µF/25V | 4.7µF/25V **0603** |
| 低壓電容 | 1µF/50V | 1µF/25V **0402**（VDD、VPP、VCOM、3V3 都在 10V 以下） |
| 8pin 排針、DIP 開關 | 有 | 拿掉 |

**換別的面板**要先查它規格書的 RESE 值；0.47Ω 不一定適用所有面板。

### 電池（v1.1 新增，同電池背板 v2.1）

| 編號 | 零件 | 用途 |
|---|---|---|
| U2 | TP4054 | 線性充電，4.2V；R4 5.1k = 196 mA，給 ≥ 400 mAh 電池（小電池 100–400 mAh 改 10k = 100 mA；R4 不要小於 5.1k） |
| Q2 | AO3401A | Load-sharing：G = VBUS、S = VSYS、D = 電池。插 USB 時關閉，拔 USB 時電池接手供 VSYS |
| R3 | 100k | Q2 Gate 下拉 |
| R5、R6、C16 | 1M / 1M 1%、100nF | VBAT / 2 → IO0，常駐約 2 µA |
| C13 | 1µF | TP4054 VCC（不要加大，會拖慢拔 USB 後的切換） |
| C14、C15 | 10µF、22µF | VBAT、VSYS（WiFi 發射尖峰補強） |

### 喚醒按鍵（2026-10-31 新增）

| 編號 | 零件 | 用途 |
|---|---|---|
| R7、R8 | 100k | IO1、IO3 上拉到 3V3 |
| TP4、TP5、TP6 | 焊墊 0.9 × 1.1 mm | K1（IO1）、K2（IO3）、G，外接按鍵 |

跟電池背板 v2.1 的差別：電阻電容從 0603 / 0805 縮成 0402 / 0603；5V、G、IO0、IO20 直接走排針，不用跳線；**VSYS 還是要一條飛線**（W5 在 Super Mini 正面，沒辦法從排針拿到）。

電池規格、充電電流選擇、續航估算、保護機制都跟電池背板一樣，見 `../battery_management/docs/BACKPACK_V2_PCB_SPEC.md`。

## 組裝

### 先改 Super Mini（同電池背板 v2）
1. **拆掉電源 LED**（「PW」旁的紅色 LED 或它的電阻）。不拆的話每天多耗約 9 mAh。
2. **W5 保持完整**；如果之前改過（抬過一端），要焊回去。
3. 找出 **W5 的 A 端**：三用電表二極體檔，紅棒接 5V，黑棒碰 W5 兩端，讀到 0.2–0.35 V 的那端就是 A（VSYS）。

### 組裝順序
1. 本板貼片完成（JLCPCB）。
2. **上電前量測**（二極體檔，還沒接電池）：紅棒 B+、黑棒 VSYS 應讀到 0.5–0.7 V（Q2 寄生二極體）；反過來要不通。
3. Super Mini 疊到本板 B 面，焊排針。
4. VSYS 焊墊飛線到 W5 的 A 端，越短越好。
5. 焊電池線到 B+ / B−。**插電池前先量極性。**
6. 功能測試：插拔 USB 不重開機；充飽後拔 USB，電池電壓 ≤ 4.2 V；e-paper 能刷新；IO20 充電中讀到 Low；deep sleep 時按 K1、K2 都能喚醒。
7. 零件面貼 Kapton，再用泡棉膠貼電池。

## 驗證結果

- **DRC：0 違規、0 未連接**（JLCPCB 2 層標準製程：線寬／線距 ≥ 0.127 mm、過孔 0.5／0.3 mm、銅箔到板邊 ≥ 0.3 mm）。只有 6 個自製焊墊 footprint 不在庫表的提示，不影響生產。
- **ERC：0 錯誤**（同樣只有自製焊墊 footprint 庫的提示）
- **電路圖與 PCB 的 29 條網路逐條比對，完全一致**（`kicad/compare_nets.py`）
- 還沒打樣，沒有實際上電驗證

## 下單前要確認

1. **FPC 座的接觸面（上接 / 下接）**：BOM 選的 C262567（AFC07-S24FCA-00）是**下接**。拿現在那塊 DESPI-C02 對照，排線金手指朝哪面、FPC 座是哪一型。AFC07-S24FCA-00 的接觸面以 LCSC 規格書為準。選錯的話腳位會整排反過來。
2. **FPC 座外形**：footprint 用 KiCad 內建的 `Jushuo_AFC07-S24FCA-00`。換別家的 24P 0.5mm 翻蓋座，要先確認焊墊位置一樣。
3. **電感**：已選 Sunlord WPN252012H100MT（C98353，Isat 1.1A）；缺料要換時，2520 的 10µH 很多款 Isat 不到 1A，要看規格書。
4. **LCSC 料號已填**（2026-10-30 查 JLC 料庫）。上傳 BOM 後看缺料和 Basic / Extended 標示，缺料時照「Spec」欄換同封裝。
5. JLCPCB 貼片預覽要檢查 **D1~D3 的方向**（陰極色帶）、**Q1、Q2、U2、J1 的旋轉角度**，必要時在網頁上修正。

## 檔案

| 檔案 | 內容 |
|---|---|
| `EPD24_SuperMini_Adapter_v1.1_Gerber.zip` | Gerber + 鑽孔，直接上傳板廠 |
| `BOM.md` | 完整零件清單：貼片零件（e-paper / 電池分開列）、手焊料、另購料、挑料注意 |
| `BOM_JLCPCB_v1.1.csv` / `CPL_JLCPCB_v1.1.csv` | JLCPCB 貼片用 BOM、座標檔（J2/J3 排針孔、TP1~TP6 焊墊不貼） |
| `EPD24_SuperMini_Adapter_schematic.pdf` | 電路圖 |
| `pcb_3d_top.png` / `pcb_3d_bottom.png` | 3D 預覽（排針 3D 模型故意不畫，因為 Super Mini 在背面） |
| `NETLIST.md` | 網路表 |
| `kicad/` | KiCad 專案與產生程式 |
| `release_v1.0/` | v1.0（只有 e-paper）凍結備份 |

下單參數：2 層、FR-4、**板厚 1.0mm 或 1.6mm 皆可**、1oz、無鉛噴錫。

## 重新產生

在 `kicad/` 資料夾：

```bash
"D:\Program Files\KiCad\bin\python.exe" build_pcb.py --route
```

| 檔案 | 用途 |
|---|---|
| `build_pcb.py` | 放零件、網路、板框、絲印、設計規則、接地過孔（加 `--route` 會接著佈線；某條網路走不通會自動移到最前面重試，最多 8 輪） |
| `route.py` | 格點自動佈線（改自 `D1mini_Fixture_Shield_HW/kicad/route.py`，格點 0.05mm）、GND 縫合過孔、鋪銅 |
| `gen_sch.py` | 產生電路圖（`python gen_sch.py`） |
| `drc_summary.py` | 跑 DRC 並印摘要 |
| `compare_nets.py` | 電路圖網路表 vs PCB 比對（先 `kicad-cli sch export netlist -o sch.net`） |
| `export_fab.py` | 匯出 Gerber zip、BOM（CSV + `BOM.md`）、CPL、電路圖 PDF、3D 預覽 |

自動佈線一輪約 3 分鐘。GND 不走線，每個 GND 焊墊旁都有接地過孔，空位再每 1.5 mm 補一顆縫合過孔，靠兩面鋪銅連接。
鋪銅後會自動檢查 GND 孤島：落在孤島上的縫合過孔刪掉、跟主鋪銅斷開的 GND 塊補一條 GND 線；Super Mini 的 G 腳（J2.2）在訊號線之前先拉一條 GND 線到 C9（`route.py` 的 `GND_FIRST`），免得被圍住。FPC 座焊墊上不打過孔。

## 韌體備註

- `esp32c3_spi_display/main/epaper_driver.h` 要配合本板改成 `PIN_MOSI = 7`、`PIN_MISO = -1`（原本 MOSI = 3、MISO 借 GPIO5 佔位，會跟 RES 衝突）；韌體另外改。
- 電池供電時，進 deep sleep 前要先送面板 deep sleep 指令（SSD1677 `0x10`），面板才會降到約 1 µA。
