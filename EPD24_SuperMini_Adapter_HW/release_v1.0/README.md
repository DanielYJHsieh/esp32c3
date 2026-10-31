# EPD24 Super Mini 轉接背板 v1.0（DESPI-C02 縮小版）

取代 Good Display DESPI-C02（41 × 22 mm）的小型轉接板：直接疊在 **ESP32-C3 Super Mini** 背面，驅動 24pin SPI 電子紙（目前用 GDEQ0426T82，SSD1677）。

- 板子 **18.0 × 26.8 mm**，寬同 Super Mini，只多出上緣 FPC 座那一段
- 雙層、零件全在單面（F 面），0402 為主，可整片交 JLCPCB 貼片
- 腳位跟 `esp32c3/esp32c3_spi_display`（`main/epaper_driver.h`）一樣，韌體不用改腳位

## 疊法

```
   Super Mini（晶片、按鍵朝上）
   ─────────── 排針 / 直接焊 ───────────
   本板 B 面（只有絲印：5V / G / 3V3 / USB / CHIP SIDE UP）
   本板 F 面（零件、FPC 座朝下）→ 面板排線從 USB 端插入
```

- Super Mini 的 USB 端對齊本板印「USB」的那一端；FPC 座在同一端，排線往 USB 方向出。
- 從零件面看，Super Mini 的腳位是**左右鏡像**的：左排 5V G 3V3 IO4 IO3 IO2 IO1 IO0，右排 IO5 IO6 IO7 IO8 IO9 IO10 IO20 IO21。
- 本板比 Super Mini 短 2 mm（天線那端），只跟陶瓷天線重疊約 0.5 mm，盡量不影響 WiFi。

## 腳位

| 面板 FPC | 訊號 | Super Mini |
|---|---|---|
| 9 | BUSY | IO6 |
| 10 | RES | IO5 |
| 11 | D/C | IO4 |
| 12 | CS | IO10 |
| 13 | SCLK | IO2 |
| 14 | SDI (MOSI) | IO3 |
| 15、16 | VDDIO、VCI | 3V3 |
| 8、17 | BS、VSS | GND（BS 接地 = 4 線 SPI） |

完整網路見 `NETLIST.md`。

## 跟 DESPI-C02 的差異

電路照原廠原理圖 `DESPI-C02_SCH V1.0`（2018.07.06）。

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

## 驗證結果

- **DRC：0 違規、0 未連接**（JLCPCB 2 層標準製程：線寬／線距 ≥ 0.127mm、過孔 0.5／0.3mm、銅箔到板邊 ≥ 0.3mm）
- **ERC：0 違規**
- **電路圖與 PCB 的 21 條網路逐條比對，完全一致**（`kicad/compare_nets.py`）
- 還沒打樣，沒有實際上電驗證

## 下單前要確認

1. **FPC 座的接觸面（上接 / 下接）**：拿現在那塊 DESPI-C02 對照，排線金手指朝哪面、FPC 座是哪一型。AFC07-S24FCA-00 的接觸面以 LCSC 規格書為準。選錯的話腳位會整排反過來。
2. **FPC 座外形**：footprint 用 KiCad 內建的 `Jushuo_AFC07-S24FCA-00`。換別家的 24P 0.5mm 翻蓋座，要先確認焊墊位置一樣。
3. **電感 Isat ≥ 1A**：2520 的 10µH 很多款 Isat 不到 1A，挑料時要看規格書。
4. **BOM 的 LCSC 料號**還沒填，依 `BOM_JLCPCB_v1.0.csv` 的「Spec」欄到 LCSC 挑。
5. JLCPCB 貼片預覽要檢查 **D1~D3 的方向**（陰極色帶）和 **Q1、J1 的旋轉角度**，必要時在網頁上修正。

## 檔案

| 檔案 | 內容 |
|---|---|
| `EPD24_SuperMini_Adapter_v1.0_Gerber.zip` | Gerber + 鑽孔，直接上傳板廠 |
| `BOM_JLCPCB_v1.0.csv` / `CPL_JLCPCB_v1.0.csv` | JLCPCB 貼片用 BOM、座標檔（J2/J3 排針孔不貼） |
| `EPD24_SuperMini_Adapter_schematic.pdf` | 電路圖 |
| `pcb_3d_top.png` / `pcb_3d_bottom.png` | 3D 預覽（排針 3D 模型故意不畫，因為 Super Mini 在背面） |
| `NETLIST.md` | 網路表 |
| `kicad/` | KiCad 專案與產生程式 |

下單參數：2 層、FR-4、**板厚 1.0mm 或 1.6mm 皆可**、1oz、無鉛噴錫。

## 重新產生

在 `kicad/` 資料夾：

```bash
"D:\Program Files\KiCad\bin\python.exe" build_pcb.py --route
```

| 檔案 | 用途 |
|---|---|
| `build_pcb.py` | 放零件、網路、板框、絲印、設計規則、接地過孔（加 `--route` 會接著佈線） |
| `route.py` | 格點自動佈線（改自 `D1mini_Fixture_Shield_HW/kicad/route.py`，格點 0.05mm） |
| `gen_sch.py` | 產生電路圖（`python gen_sch.py`） |
| `drc_summary.py` | 跑 DRC 並印摘要 |
| `compare_nets.py` | 電路圖網路表 vs PCB 比對（先 `kicad-cli sch export netlist -o sch.net`） |
| `export_fab.py` | 匯出 Gerber zip、BOM、CPL、電路圖 PDF、3D 預覽 |

自動佈線約 3 分鐘。GND 不走線，每個 GND 焊墊旁都有接地過孔，靠兩面鋪銅連接。

## 韌體備註

`esp32c3_spi_display/main/epaper_driver.h` 的 `PIN_MISO` 和 `PIN_RST` 都設成 GPIO5。面板不需要 MISO，建議 SPI 設定改成 `miso_io_num = -1`，免得干擾 RES。
