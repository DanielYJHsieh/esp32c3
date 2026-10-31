# EPD24 Mini 轉接板 v1.0（DESPI-C02 縮小版，排線接 MCU）

取代 Good Display DESPI-C02（41 × 22 mm）的獨立小轉接板，驅動 24pin SPI 電子紙（目前用 GDEQ0426T82，SSD1677），用 **JST SH 1.0mm 8P 排線**接到 ESP32-C3 Super Mini（或任何 3.3V MCU）。

- 板子 **18.0 × 21.5 mm**（DESPI-C02 的約 43%）
- 雙層、零件全在單面（F 面），0402 為主，可整片交 JLCPCB 貼片
- e-paper 電路跟 `../EPD24_SuperMini_Adapter_HW` v1.0 相同，只把 Super Mini 排針換成排線座；要直接疊在 Super Mini 上、或要電池電路，用那個專案

## 接頭

| 位置 | 接頭 | 說明 |
|---|---|---|
| 上緣 | J1：24P 0.5mm 翻蓋 FPC 座 | 面板排線從上緣插入 |
| 下緣 | J2：JST SH 1.0mm 8P 臥式（SM08B-SRSS-TB） | 排線從下緣插入，pin 1 在左邊（從零件面看） |

### J2 腳位與 Super Mini 接法

腳位順序同 DESPI-C02 的 8pin 排針，原本的接線說明可以直接沿用。Super Mini 這端的 GPIO 同 `esp32c3_spi_display`（`main/epaper_driver.h`），韌體不用改。

| J2 | 訊號 | ESP32-C3 Super Mini |
|---|---|---|
| 1 | 3.3V | 3.3 |
| 2 | GND | G |
| 3 | SDI (MOSI) | IO3 |
| 4 | SCLK | IO2 |
| 5 | CS | IO10 |
| 6 | D/C | IO4 |
| 7 | RES | IO5 |
| 8 | BUSY | IO6 |

板子背面也印了這張腳位表。現成 SH 排線的顏色各家不同，**接之前用三用電表對一下 pin 1**。

## 電路

照原廠原理圖 `DESPI-C02_SCH V1.0`（2018.07.06）。

| 項目 | DESPI-C02 | 本板 |
|---|---|---|
| RESE 電阻 | DIP 切 0.47Ω / 3Ω（新版 2.2Ω） | **固定 0.47Ω**（GDEQ0426T82 目前 DIP 撥 0.47） |
| BS | R4 3Ω 接地 + R5 10k 上拉 | 直接接地（4 線 SPI） |
| 二極體 | MBR0530（SOD-123） | B5819WS（SOD-323，40V 1A） |
| 電感 | 10µH 1A | 10µH、2520 封裝、Isat ≥ 1A |
| 高壓電容 | 4.7µF/25V | 4.7µF/25V **0603** |
| 低壓電容 | 1µF/50V | 1µF/25V **0402**（VDD、VPP、VCOM、3V3 都在 10V 以下） |
| 8pin 排針、DIP 開關、LDO | 有 | 拿掉；排針換成 JST SH 8P |

**換別的面板**要先查它規格書的 RESE 值；0.47Ω 不一定適用所有面板。

## 驗證結果

- **DRC：0 違規、0 未連接**（JLCPCB 2 層標準製程：線寬／線距 ≥ 0.127 mm、過孔 0.5／0.3 mm、銅箔到板邊 ≥ 0.3 mm）
- **ERC：0 違規**
- **電路圖與 PCB 的 21 條網路逐條比對，完全一致**（`kicad/compare_nets.py`）
- 二極體方向已在 3D 預覽核對（D3 陰極接 PREVGH、D1 陰極接 NEG、D2 陰極接 GND）
- 還沒打樣，沒有實際上電驗證

## 下單前要確認

1. **FPC 座的接觸面（上接 / 下接）**：BOM 選的 C262567（AFC07-S24FCA-00）是**下接**。拿現在那塊 DESPI-C02 對照，排線金手指朝哪面、FPC 座是哪一型。選錯的話腳位會整排反過來。
2. **FPC 座外形**：footprint 用 KiCad 內建的 `Jushuo_AFC07-S24FCA-00`。
3. **電感**：已選 Sunlord WPN252012H100MT（C98353，Isat 1.1A）。
4. **LCSC 料號已填**（2026-10-30 查 JLC 料庫）。上傳 BOM 後看缺料和 Basic / Extended 標示，缺料時照「規格」欄換同封裝。
5. JLCPCB 貼片預覽要檢查 **D1~D3 的方向**（陰極色帶）、**Q1、J1、J2 的旋轉角度**。

## 檔案

| 檔案 | 內容 |
|---|---|
| `EPD24_Mini_Adapter_v1.0_Gerber.zip` | Gerber + 鑽孔，直接上傳板廠 |
| `BOM.md` | 零件清單（貼片零件、另購料、挑料注意） |
| `BOM_JLCPCB_v1.0.csv` / `CPL_JLCPCB_v1.0.csv` | JLCPCB 貼片用 BOM、座標檔 |
| `EPD24_Mini_Adapter_schematic.pdf` | 電路圖 |
| `pcb_3d_top.png` / `pcb_3d_bottom.png` | 3D 預覽 |
| `kicad/` | KiCad 專案與產生程式 |

下單參數：2 層、FR-4、板厚 1.0mm 或 1.6mm 皆可、1oz、無鉛噴錫。

## 重新產生

在 `kicad/` 資料夾：

```bash
"D:\Program Files\KiCad\bin\python.exe" build_pcb.py --route
```

| 檔案 | 用途 |
|---|---|
| `build_pcb.py` | 放零件、網路、板框、絲印、設計規則、接地過孔（加 `--route` 會接著佈線；某條網路走不通會自動移到最前面重試） |
| `route.py` | 格點自動佈線（格點 0.05mm）、GND 縫合過孔、鋪銅 |
| `gen_sch.py` | 產生電路圖（`python gen_sch.py`） |
| `drc_summary.py` | 跑 DRC 並印摘要 |
| `compare_nets.py` | 電路圖網路表 vs PCB 比對（先 `kicad-cli sch export netlist -o sch.net`） |
| `export_fab.py` | 匯出 Gerber zip、BOM（CSV + `BOM.md`）、CPL、電路圖 PDF、3D 預覽 |

## 韌體備註

- `esp32c3_spi_display/main/epaper_driver.h` 的 `PIN_MISO` 和 `PIN_RST` 都設成 GPIO5。面板不需要 MISO，建議 SPI 設定改成 `miso_io_num = -1`，免得干擾 RES。
